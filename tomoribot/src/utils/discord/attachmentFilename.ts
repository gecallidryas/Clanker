import { createHash } from "node:crypto";

type AttachmentFilenamePartOptions = {
	fallback?: string;
	maxLength?: number;
};

const COMBINING_MARKS_REGEX = /\p{M}+/gu;
const NON_WORD_FILENAME_CHARS_REGEX = /[^A-Za-z0-9_-]+/g;
const DUPLICATE_SEPARATOR_REGEX = /_+/g;
const LEADING_OR_TRAILING_SEPARATOR_REGEX = /^[_-]+|[_-]+$/g;
const RESERVED_FILENAME_CHARS = new Set(["<", ">", ":", "\"", "/", "\\", "|", "?", "*"]);

function replaceUnsafeFilenameChars(value: string): string {
	let sanitizedValue = "";

	for (const char of value) {
		const codePoint = char.codePointAt(0);
		if (
			codePoint === undefined ||
			codePoint <= 0x1f ||
			codePoint === 0x7f ||
			RESERVED_FILENAME_CHARS.has(char)
		) {
			sanitizedValue += " ";
			continue;
		}

		sanitizedValue += char;
	}

	return sanitizedValue;
}

function sanitizeFilenamePartValue(value: string, maxLength: number): string {
	return Array.from(
		replaceUnsafeFilenameChars(value)
			.normalize("NFKC")
			.normalize("NFKD")
			.replace(COMBINING_MARKS_REGEX, "")
			.trim()
			.replace(NON_WORD_FILENAME_CHARS_REGEX, "_")
			.replace(DUPLICATE_SEPARATOR_REGEX, "_")
			.replace(LEADING_OR_TRAILING_SEPARATOR_REGEX, ""),
	)
		.slice(0, maxLength)
		.join("");
}

function buildFilenameHash(value: string): string {
	return createHash("sha1").update(value).digest("hex").slice(0, 8);
}

export function sanitizeAttachmentFilenamePart(
	value: string,
	options?: AttachmentFilenamePartOptions,
): string {
	const maxLength = options?.maxLength ?? 50;
	const fallback = options?.fallback ?? "file";
	const sanitizedValue = sanitizeFilenamePartValue(value, maxLength);

	if (sanitizedValue.length > 0) {
		return sanitizedValue;
	}

	const sanitizedFallback = sanitizeFilenamePartValue(fallback, maxLength);
	const effectiveFallback = sanitizedFallback.length > 0 ? sanitizedFallback : "file";
	const hashSuffix = `-${buildFilenameHash(value)}`;
	const baseMaxLength = Math.max(maxLength - hashSuffix.length, 1);

	return `${effectiveFallback.slice(0, baseMaxLength)}${hashSuffix}`;
}
