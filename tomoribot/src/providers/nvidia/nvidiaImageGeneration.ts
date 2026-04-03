import type {
	ProviderNativeImageGenerationRequest,
	ProviderNativeImageGenerationResult,
} from "@/types/provider/featureInterfaces";
import { log } from "@/utils/misc/logger";
import {
	NVIDIA_IMAGE_ASPECT_RATIO_MAP,
	NVIDIA_IMAGE_GENERATION_URL,
} from "@/providers/nvidia/nvidiaConstants";

function normalizeAspectRatio(aspectRatio: string): string {
	return NVIDIA_IMAGE_ASPECT_RATIO_MAP[aspectRatio] ?? "1:1";
}

function extractBase64Image(result: unknown): string | null {
	const record =
		typeof result === "object" && result !== null
			? (result as Record<string, unknown>)
			: null;
	if (!record) {
		return null;
	}

	if (typeof record.image === "string") {
		return record.image;
	}

	if (Array.isArray(record.artifacts)) {
		for (const artifact of record.artifacts) {
			if (typeof artifact !== "object" || artifact === null) {
				continue;
			}
			const candidate = artifact as Record<string, unknown>;
			if (typeof candidate.base64 === "string") {
				return candidate.base64;
			}
			if (typeof candidate.b64_json === "string") {
				return candidate.b64_json;
			}
		}
	}

	if (Array.isArray(record.data)) {
		for (const entry of record.data) {
			if (typeof entry !== "object" || entry === null) {
				continue;
			}
			const candidate = entry as Record<string, unknown>;
			if (typeof candidate.b64_json === "string") {
				return candidate.b64_json;
			}
			if (typeof candidate.base64 === "string") {
				return candidate.base64;
			}
		}
	}

	if (Array.isArray(record.images)) {
		for (const entry of record.images) {
			if (typeof entry !== "object" || entry === null) {
				continue;
			}
			const candidate = entry as Record<string, unknown>;
			if (typeof candidate.base64 === "string") {
				return candidate.base64;
			}
		}
	}

	return null;
}

function extractImageUrl(result: unknown): string | null {
	const record =
		typeof result === "object" && result !== null
			? (result as Record<string, unknown>)
			: null;
	if (!record) {
		return null;
	}

	if (typeof record.url === "string") {
		return record.url;
	}

	if (Array.isArray(record.data)) {
		for (const entry of record.data) {
			if (typeof entry !== "object" || entry === null) {
				continue;
			}
			const candidate = entry as Record<string, unknown>;
			if (typeof candidate.url === "string") {
				return candidate.url;
			}
		}
	}

	if (Array.isArray(record.images)) {
		for (const entry of record.images) {
			if (typeof entry !== "object" || entry === null) {
				continue;
			}
			const candidate = entry as Record<string, unknown>;
			if (typeof candidate.url === "string") {
				return candidate.url;
			}
		}
	}

	return null;
}

function extractMimeTypeFromResult(result: unknown): string | null {
	const record =
		typeof result === "object" && result !== null
			? (result as Record<string, unknown>)
			: null;
	if (!record) {
		return null;
	}

	if (typeof record.mime_type === "string") {
		return record.mime_type;
	}

	if (typeof record.mimeType === "string") {
		return record.mimeType;
	}

	if (Array.isArray(record.artifacts)) {
		for (const artifact of record.artifacts) {
			if (typeof artifact !== "object" || artifact === null) {
				continue;
			}
			const candidate = artifact as Record<string, unknown>;
			if (typeof candidate.mime_type === "string") {
				return candidate.mime_type;
			}
			if (typeof candidate.mimeType === "string") {
				return candidate.mimeType;
			}
		}
	}

	return null;
}

async function fetchImageUrlAsBase64(
	imageUrl: string,
): Promise<ProviderNativeImageGenerationResult> {
	const imageResponse = await fetch(imageUrl);
	if (!imageResponse.ok) {
		log.error(
			"Failed to fetch NVIDIA generated image URL",
			new Error(`HTTP ${imageResponse.status}`),
			{
				errorType: "NvidiaImageFetchError",
				metadata: { imageUrl },
			},
		);
		return { imageData: null, mimeType: null };
	}

	const contentType = imageResponse.headers.get("Content-Type") ?? "image/jpeg";
	const mimeType = contentType.split(";")[0].trim();
	const arrayBuffer = await imageResponse.arrayBuffer();
	const imageData = Buffer.from(arrayBuffer).toString("base64");

	return {
		imageData,
		mimeType,
	};
}

export async function generateNvidiaNativeImage(
	request: ProviderNativeImageGenerationRequest,
): Promise<ProviderNativeImageGenerationResult> {
	if (request.referenceImages && request.referenceImages.length > 0) {
		log.warn(
			"NVIDIA image generation currently ignores reference images. Proceeding with text-only generation.",
			{
				model: request.model,
				referenceCount: request.referenceImages.length,
			},
		);
	}

	const aspectRatio = normalizeAspectRatio(request.aspectRatio);

	const response = await fetch(
		request.endpointUrl || NVIDIA_IMAGE_GENERATION_URL,
		{
			method: "POST",
			headers: {
				Authorization: `Bearer ${request.apiKey}`,
				"Content-Type": "application/json",
				Accept: "application/json, image/jpeg",
			},
			body: JSON.stringify({
				prompt: request.prompt,
				aspect_ratio: aspectRatio,
			}),
		},
	);

	if (!response.ok) {
		const errorBody = await response.text();
		log.error("NVIDIA image generation request failed", new Error(errorBody), {
			errorType: "NvidiaImageGenerationHttpError",
			metadata: {
				model: request.model,
				status: response.status,
				aspectRatio,
			},
		});
		throw new Error(
			`NVIDIA image generation failed: ${response.status} ${response.statusText}`,
		);
	}

	const contentType = response.headers.get("Content-Type") ?? "";
	if (contentType.toLowerCase().startsWith("image/")) {
		const mimeType = contentType.split(";")[0].trim();
		const imageData = Buffer.from(await response.arrayBuffer()).toString("base64");
		return {
			imageData,
			mimeType,
		};
	}

	const result = (await response.json()) as unknown;
	const base64Image = extractBase64Image(result);
	if (base64Image) {
		return {
			imageData: base64Image,
			mimeType: extractMimeTypeFromResult(result) ?? "image/jpeg",
		};
	}

	const imageUrl = extractImageUrl(result);
	if (imageUrl) {
		return await fetchImageUrlAsBase64(imageUrl);
	}

	log.warn("NVIDIA image generation returned no image payload", {
		model: request.model,
		aspectRatio,
	});
	return {
		imageData: null,
		mimeType: null,
	};
}
