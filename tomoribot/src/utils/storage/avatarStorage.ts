/**
 * Persona avatar storage utilities.
 *
 * Production stores avatars in S3/CloudFront.
 * Non-production stores avatars on the local filesystem under data/avatars.
 */

import {
	DeleteObjectCommand,
	PutObjectCommand,
	S3Client,
} from "@aws-sdk/client-s3";
import { promises as fs } from "node:fs";
import path from "node:path";
import { PERSONA_LIMITS } from "@/utils/security/rateLimiter";
import { safeDownload } from "@/utils/security/safeDownload";
import { log } from "@/utils/misc/logger";

type AvatarUploadOptions = {
	personaId: number;
	serverDiscId?: string;
	label?: string;
	buffer: Buffer;
};

type AvatarStorageConfig = {
	bucket: string;
	region: string;
	prefix: string;
	publicBaseUrl: string;
};

const IS_PRODUCTION = process.env.RUN_ENV === "production";
const LOCAL_AVATAR_BASE_DIR = path.resolve(process.cwd(), "data", "avatars");
const LOCAL_AVATAR_ROOT_PREFIX = "data/avatars/";
let cachedClient: S3Client | null = null;
let cachedRegion: string | null = null;

function getAvatarStorageConfig(): AvatarStorageConfig | null {
	if (!IS_PRODUCTION) {
		return null;
	}

	const bucket = process.env.AVATAR_S3_BUCKET?.trim();
	if (!bucket) {
		log.warn(
			"[Avatar Storage] AVATAR_S3_BUCKET is missing; falling back to Discord CDN URLs.",
		);
		return null;
	}

	const region =
		process.env.AVATAR_S3_REGION?.trim() ||
		process.env.AWS_REGION?.trim() ||
		"us-east-1";
	const prefix = (process.env.AVATAR_S3_PREFIX || "avatars")
		.replace(/^\/+/, "")
		.replace(/\/+$/, "");
	const publicBaseUrl =
		process.env.AVATAR_PUBLIC_BASE_URL?.trim() ||
		`https://${bucket}.s3.${region}.amazonaws.com`;

	return {
		bucket,
		region,
		prefix,
		publicBaseUrl,
	};
}

function getS3Client(region: string): S3Client {
	if (!cachedClient || cachedRegion !== region) {
		cachedRegion = region;
		cachedClient = new S3Client({ region });
	}
	return cachedClient;
}

function buildAvatarObjectKey(
	config: AvatarStorageConfig,
	options: AvatarUploadOptions,
): string {
	const timestamp = Date.now();
	const serverSegment = options.serverDiscId
		? `servers/${options.serverDiscId}`
		: "servers/unknown";
	return `${config.prefix}/${serverSegment}/personas/${options.personaId}/${timestamp}.png`;
}

function buildPublicUrl(config: AvatarStorageConfig, key: string): string {
	const baseUrl = config.publicBaseUrl.replace(/\/+$/, "");
	return `${baseUrl}/${key}`;
}

function buildLocalStoredPath(options: AvatarUploadOptions): string {
	const timestamp = Date.now();
	const serverSegment = options.serverDiscId || "unknown";
	return path.posix.join(
		"data",
		"avatars",
		"servers",
		serverSegment,
		"personas",
		String(options.personaId),
		`${timestamp}.png`,
	);
}

function normalizeStoredPath(storedPath: string): string {
	return storedPath.replace(/\\/g, "/").replace(/^\/+/, "");
}

function resolveLocalAvatarPath(storedPath: string): string | null {
	const normalizedPath = normalizeStoredPath(storedPath);
	const resolvedPath = path.resolve(process.cwd(), normalizedPath);
	const relativePath = path.relative(LOCAL_AVATAR_BASE_DIR, resolvedPath);

	if (
		relativePath === "" ||
		(!relativePath.startsWith("..") && !path.isAbsolute(relativePath))
	) {
		return resolvedPath;
	}

	log.warn(
		`[Avatar Storage] Rejected path outside data/avatars: ${storedPath}`,
	);
	return null;
}

function extractKeyFromAvatarUrl(
	config: AvatarStorageConfig,
	url: string,
): string | null {
	try {
		const parsed = new URL(url);
		const baseHost = new URL(config.publicBaseUrl).hostname;
		const hostname = parsed.hostname;
		const pathName = parsed.pathname.replace(/^\/+/, "");

		if (hostname !== baseHost) {
			const s3Host = `${config.bucket}.s3.${config.region}.amazonaws.com`;
			const s3HostLegacy = `${config.bucket}.s3.amazonaws.com`;
			if (hostname !== s3Host && hostname !== s3HostLegacy) {
				return null;
			}
		}

		if (!pathName.startsWith(`${config.prefix}/`)) {
			return null;
		}

		return pathName;
	} catch {
		return null;
	}
}

function getNonProductionPublicBaseUrl(): string | null {
	if (IS_PRODUCTION) {
		return null;
	}

	const baseUrl = process.env.AVATAR_PUBLIC_BASE_URL?.trim();
	return baseUrl && baseUrl.length > 0 ? baseUrl.replace(/\/+$/, "") : null;
}

export function isLocalPersonaAvatarPath(reference?: string | null): boolean {
	if (!reference) {
		return false;
	}

	return resolveLocalAvatarPath(reference) !== null;
}

export function resolvePersonaAvatarPublicUrl(
	reference?: string | null,
): string | null {
	if (!reference) {
		return null;
	}

	const trimmedReference = reference.trim();
	if (!trimmedReference) {
		return null;
	}

	if (/^https?:\/\//i.test(trimmedReference)) {
		return trimmedReference;
	}

	const publicBaseUrl = getNonProductionPublicBaseUrl();
	if (!publicBaseUrl) {
		return null;
	}

	const normalizedPath = normalizeStoredPath(trimmedReference);
	if (!normalizedPath.startsWith(LOCAL_AVATAR_ROOT_PREFIX)) {
		return null;
	}

	const relativePath = normalizedPath.slice(LOCAL_AVATAR_ROOT_PREFIX.length);
	return `${publicBaseUrl}/${relativePath}`;
}

export async function loadStoredPersonaAvatarBuffer(
	reference: string,
): Promise<Buffer | null> {
	const trimmedReference = reference.trim();
	if (!trimmedReference) {
		return null;
	}

	if (/^https?:\/\//i.test(trimmedReference)) {
		const downloadResult = await safeDownload(trimmedReference, {
			maxSizeMB: PERSONA_LIMITS.MAX_AVATAR_SIZE_MB,
		});

		if (!downloadResult.success || !downloadResult.buffer) {
			return null;
		}

		return downloadResult.buffer;
	}

	const absolutePath = resolveLocalAvatarPath(trimmedReference);
	if (!absolutePath) {
		return null;
	}

	try {
		return await fs.readFile(absolutePath);
	} catch (error) {
		log.warn(
			`[Avatar Storage] Failed to load local persona avatar ${trimmedReference}`,
			error,
		);
		return null;
	}
}

export async function loadStoredPersonaAvatarDataUri(
	reference: string,
): Promise<string | null> {
	const buffer = await loadStoredPersonaAvatarBuffer(reference);
	if (!buffer) {
		return null;
	}

	return `data:image/png;base64,${buffer.toString("base64")}`;
}

export async function uploadPersonaAvatarToS3(
	options: AvatarUploadOptions,
): Promise<string | null> {
	const label = options.label ? ` (${options.label})` : "";
	if (IS_PRODUCTION) {
		const config = getAvatarStorageConfig();
		if (!config) {
			return null;
		}

		const key = buildAvatarObjectKey(config, options);
		const client = getS3Client(config.region);

		try {
			await client.send(
				new PutObjectCommand({
					Bucket: config.bucket,
					Key: key,
					Body: options.buffer,
					ContentType: "image/png",
					CacheControl: "public, max-age=31536000, immutable",
				}),
			);
			const publicUrl = buildPublicUrl(config, key);
			log.success(
				`[Avatar Storage] Uploaded persona avatar${label} to S3 (${publicUrl})`,
			);
			return publicUrl;
		} catch (error) {
			log.warn(
				`[Avatar Storage] Failed to upload persona avatar${label} to S3`,
				error,
			);
			return null;
		}
	}

	const storedPath = buildLocalStoredPath(options);
	const absolutePath = resolveLocalAvatarPath(storedPath);
	if (!absolutePath) {
		return null;
	}

	try {
		await fs.mkdir(path.dirname(absolutePath), { recursive: true });
		await fs.writeFile(absolutePath, options.buffer);
		log.success(
			`[Avatar Storage] Stored persona avatar${label} at ${storedPath}`,
		);
		return normalizeStoredPath(storedPath);
	} catch (error) {
		log.warn(
			`[Avatar Storage] Failed to store persona avatar${label} locally`,
			error,
		);
		return null;
	}
}

export async function deletePersonaAvatarFromS3(
	reference: string,
): Promise<boolean> {
	const target = reference.trim();
	if (!target) {
		return false;
	}

	if (/^https?:\/\//i.test(target)) {
		if (!IS_PRODUCTION) {
			return false;
		}

		const config = getAvatarStorageConfig();
		if (!config) {
			return false;
		}

		const key = extractKeyFromAvatarUrl(config, target);
		if (!key) {
			return false;
		}

		const client = getS3Client(config.region);

		try {
			await client.send(
				new DeleteObjectCommand({
					Bucket: config.bucket,
					Key: key,
				}),
			);
			log.info(`[Avatar Storage] Deleted avatar object ${key}`);
			return true;
		} catch (error) {
			log.warn(`[Avatar Storage] Failed to delete avatar object ${key}`, error);
			return false;
		}
	}

	const absolutePath = resolveLocalAvatarPath(target);
	if (!absolutePath) {
		return false;
	}

	try {
		await fs.unlink(absolutePath);
		log.info(
			`[Avatar Storage] Deleted local persona avatar ${normalizeStoredPath(target)}`,
		);
		return true;
	} catch (error) {
		if (
			typeof error === "object" &&
			error !== null &&
			"code" in error &&
			error.code === "ENOENT"
		) {
			return false;
		}

		log.warn(
			`[Avatar Storage] Failed to delete local persona avatar ${target}`,
			error,
		);
		return false;
	}
}
