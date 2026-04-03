/**
 * Shared Text Extraction Utility
 * Provides reusable text extraction from document buffers (PDF, TXT, MD)
 * Used by both /teach document and the read_document tool
 */

import { log } from "@/utils/misc/logger";
import { safeDownload } from "@/utils/security/safeDownload";
import { normalizeDocumentText } from "@/utils/documents/documentService";
import { memoryGuard } from "@/utils/security/rateLimiter";

/** File extensions supported for inline document extraction */
export const EXTRACTABLE_EXTENSIONS = [".pdf", ".txt", ".md"] as const;

/** MIME types supported for inline document extraction */
export const EXTRACTABLE_CONTENT_TYPES = [
	"application/pdf",
	"text/plain",
	"text/markdown",
] as const;

/**
 * Check if a file is an extractable document by extension or MIME type
 * @param contentType - MIME type of the file (may be null)
 * @param filename - Filename to check by extension
 * @returns True if the file is a supported document type
 */
export function isExtractableDocument(
	contentType: string | null,
	filename: string,
): boolean {
	const lowerName = filename.toLowerCase();

	// Check by extension
	const hasExtension = EXTRACTABLE_EXTENSIONS.some((ext) =>
		lowerName.endsWith(ext),
	);
	if (hasExtension) return true;

	// Check by MIME type
	if (contentType) {
		return (EXTRACTABLE_CONTENT_TYPES as readonly string[]).includes(
			contentType,
		);
	}

	return false;
}

/**
 * Extract text from a raw buffer based on file type
 * Supports PDF (via pdf-parse), TXT, and MD files
 *
 * @param buffer - Raw file buffer
 * @param filename - Filename used to determine file type
 * @param contentType - Optional MIME type for additional type detection
 * @returns Extracted text content
 */
export async function extractTextFromBuffer(
	buffer: Buffer,
	filename: string,
	contentType?: string | null,
): Promise<string> {
	const lowerName = filename.toLowerCase();
	const isPdf =
		contentType === "application/pdf" || lowerName.endsWith(".pdf");

	if (isPdf) {
		const pdfParse = (await import("pdf-parse")).default;
		const parsed = await pdfParse(buffer);
		return parsed.text ?? "";
	}

	return buffer.toString("utf8");
}

/**
 * Result of a full text extraction pipeline
 */
export interface ExtractTextResult {
	/** Whether extraction succeeded */
	success: boolean;
	/** Extracted and normalized text (only if success) */
	text?: string;
	/** Whether the text was truncated to fit maxTextLength */
	truncated: boolean;
	/** Original text length before truncation (only if truncated) */
	originalLength?: number;
	/** Error category if extraction failed */
	error?: "size_exceeded" | "extraction_failed" | "memory_pressure" | "timeout" | "download_failed" | "empty_document";
}

/**
 * Full extraction pipeline: download -> extract -> normalize -> truncate
 * Handles memory guard checks, safe download, text extraction, and truncation
 *
 * @param url - URL to download the document from
 * @param filename - Filename for type detection
 * @param contentType - MIME type of the file
 * @param options - Size and length limits
 * @returns Extraction result with text or error details
 */
export async function extractTextFromUrl(
	url: string,
	filename: string,
	contentType: string | null,
	options: {
		maxSizeBytes: number;
		maxTextLength: number;
		knownSize?: number;
		timeoutMs?: number;
	},
): Promise<ExtractTextResult> {
	// 1. Check memory guard — block under warning/critical pressure
	const memCheck = memoryGuard.checkMemory();
	if (memCheck.status === "warning" || memCheck.status === "critical") {
		log.warn(
			`textExtractor: Blocked extraction due to memory pressure (${memCheck.status})`,
		);
		return { success: false, truncated: false, error: "memory_pressure" };
	}

	// 2. Download the file with size and timeout protections
	const maxSizeMB = options.maxSizeBytes / (1024 * 1024);
	const downloadResult = await safeDownload(url, {
		maxSizeMB,
		timeoutMs: options.timeoutMs ?? 15000,
		knownSize: options.knownSize,
	});

	if (!downloadResult.success || !downloadResult.buffer) {
		const errorType =
			downloadResult.error === "size_exceeded"
				? "size_exceeded"
				: downloadResult.error === "timeout"
					? "timeout"
					: "download_failed";
		log.warn(
			`textExtractor: Download failed for ${filename}: ${downloadResult.error} - ${downloadResult.details}`,
		);
		return { success: false, truncated: false, error: errorType };
	}

	// 3. Extract text from the buffer
	let rawText: string;
	try {
		rawText = await extractTextFromBuffer(
			downloadResult.buffer,
			filename,
			contentType,
		);
	} catch (error) {
		log.error(
			`textExtractor: Failed to extract text from ${filename}`,
			error as Error,
		);
		return { success: false, truncated: false, error: "extraction_failed" };
	}

	// 4. Normalize text (remove null bytes, normalize whitespace)
	const normalizedText = normalizeDocumentText(rawText);

	if (!normalizedText || normalizedText.trim().length === 0) {
		return { success: false, truncated: false, error: "empty_document" };
	}

	// 5. Truncate if necessary
	const truncated = normalizedText.length > options.maxTextLength;
	const finalText = truncated
		? normalizedText.slice(0, options.maxTextLength)
		: normalizedText;

	return {
		success: true,
		text: finalText,
		truncated,
		originalLength: truncated ? normalizedText.length : undefined,
	};
}
