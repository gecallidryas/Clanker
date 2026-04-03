/**
 * Shared image extraction utilities for Discord messages.
 * Provides a unified pipeline for extracting images from attachments, embeds,
 * stickers, and custom emojis, then converting them to base64 format.
 *
 * Used by both `generate_image` (Gemini Imagen) and `generate_image_nai` (NovelAI)
 * tools to avoid duplicating extraction logic.
 */

import { log } from "../misc/logger";
import type { ToolContext } from "../../types/tool/interfaces";

/** Intermediate representation of a discovered image URL before base64 conversion */
interface ImageUrlInfo {
	url: string;
	mimeType: string;
	/** Human-readable source label for logging (e.g. "attachment: photo.png") */
	source: string;
}

/** Base64-encoded image data ready for API consumption */
export interface ExtractedImage {
	mimeType: string;
	/** Raw base64-encoded image data (no data-URI prefix) */
	data: string;
}

/**
 * Build a Discord CDN URL for a custom emoji.
 * Always uses PNG so animated emojis fall back to their first frame.
 * @param emojiId - Discord emoji snowflake ID
 * @returns CDN URL string
 */
function buildEmojiCdnUrl(emojiId: string): string {
	return `https://cdn.discordapp.com/emojis/${emojiId}.png`;
}

/**
 * Extract custom emoji image URLs from message text content.
 * Deduplicates by emoji ID so the same emoji used twice only produces one image.
 * @param content - Raw message text
 * @returns Array of image URL info objects for each unique custom emoji
 */
function extractCustomEmojis(content: string): ImageUrlInfo[] {
	const emojiUrls: ImageUrlInfo[] = [];
	if (!content) return emojiUrls;

	// Regex created inside the function to avoid stale lastIndex from module-level g-flag regex
	const emojiPattern = /<(a?):([^:]+):(\d{17,20})>/g;
	const seenEmojiIds = new Set<string>();
	let match: RegExpExecArray | null;

	// biome-ignore lint/suspicious/noAssignInExpressions: Standard regex exec loop pattern
	while ((match = emojiPattern.exec(content)) !== null) {
		const emojiName = match[2];
		const emojiId = match[3];

		if (seenEmojiIds.has(emojiId)) continue;
		seenEmojiIds.add(emojiId);

		emojiUrls.push({
			url: buildEmojiCdnUrl(emojiId),
			mimeType: "image/png",
			source: `emoji: ${emojiName}`,
		});
	}

	return emojiUrls;
}

/**
 * Extract all images from a Discord message and convert them to base64.
 *
 * Extraction sources (checked in order):
 * 1. Direct file attachments with image/* MIME type
 * 2. Embed images (e.g. Twitter/X previews, direct image links)
 * 3. Embed thumbnails (fallback for embeds that use thumbnail instead of image)
 * 4. Discord stickers (served as PNG)
 * 5. Custom emojis parsed from message text
 *
 * Each source is fetched independently — individual failures are logged and skipped
 * so that other images in the same message can still be processed.
 *
 * @param messageId - Discord message snowflake ID to fetch
 * @param context - Tool execution context providing channel access
 * @returns Array of base64-encoded images with MIME types
 * @throws Error if the message is not found or no images could be processed
 */
export async function extractImagesFromMessage(
	messageId: string,
	context: ToolContext,
): Promise<ExtractedImage[]> {
	// 1. Fetch the Discord message
	const message = await context.channel.messages.fetch(messageId);

	if (!message) {
		throw new Error(`Message ${messageId} not found`);
	}

	// Collect all discovered image URLs before base64 conversion
	const imageUrls: ImageUrlInfo[] = [];

	// 2. Direct attachments
	const imageAttachments = message.attachments.filter((attachment) =>
		attachment.contentType?.startsWith("image/"),
	);

	for (const attachment of imageAttachments.values()) {
		imageUrls.push({
			url: attachment.url,
			mimeType: attachment.contentType || "image/jpeg",
			source: `attachment: ${attachment.name}`,
		});
	}

	// 3. Embed images and thumbnails
	for (const embed of message.embeds) {
		if (embed.image?.url) {
			imageUrls.push({
				url: embed.image.url,
				mimeType: "image/jpeg", // Embeds don't provide explicit MIME type
				source: `embed.image: ${embed.url || "unknown"}`,
			});
		}

		if (embed.thumbnail?.url) {
			imageUrls.push({
				url: embed.thumbnail.url,
				mimeType: "image/jpeg",
				source: `embed.thumbnail: ${embed.url || "unknown"}`,
			});
		}
	}

	// 4. Discord stickers
	if (message.stickers.size > 0) {
		for (const sticker of message.stickers.values()) {
			imageUrls.push({
				url: sticker.url,
				mimeType: "image/png", // Discord serves stickers as PNG
				source: `sticker: ${sticker.name}`,
			});
		}
	}

	// 5. Custom emojis from message text
	if (message.content) {
		imageUrls.push(...extractCustomEmojis(message.content));
	}

	// Validate we found at least one image source
	if (imageUrls.length === 0) {
		throw new Error(
			`No images found in message ${messageId} (checked attachments, embeds, stickers, and custom emojis)`,
		);
	}

	log.info(
		`Found ${imageUrls.length} image(s) in message ${messageId} (${imageAttachments.size} attachment(s), ${imageUrls.length - imageAttachments.size} embed/sticker/emoji)`,
	);

	// 6. Convert each URL to base64
	const results: ExtractedImage[] = [];

	for (const imageInfo of imageUrls) {
		try {
			const imageResponse = await fetch(imageInfo.url);
			if (!imageResponse.ok) {
				log.warn(
					`Failed to fetch image from ${imageInfo.source}: ${imageResponse.status}`,
				);
				continue;
			}

			const imageArrayBuffer = await imageResponse.arrayBuffer();
			results.push({
				mimeType: imageInfo.mimeType,
				data: Buffer.from(imageArrayBuffer).toString("base64"),
			});

			log.info(
				`Successfully converted image from ${imageInfo.source} to base64`,
			);
		} catch (imgErr) {
			log.warn(
				`Failed to process image from ${imageInfo.source}:`,
				imgErr as Error,
			);
		}
	}

	// Ensure at least one image was successfully processed
	if (results.length === 0) {
		throw new Error(
			`Failed to process any images from message ${messageId}`,
		);
	}

	return results;
}

/**
 * Fetch an image from a URL and return it as a raw Buffer.
 * Useful for tools that need the buffer directly (e.g. for sharp processing).
 * @param imageUrl - URL to fetch
 * @returns Image data as a Buffer
 * @throws Error if the fetch fails
 */
export async function fetchImageAsBuffer(imageUrl: string): Promise<Buffer> {
	const response = await fetch(imageUrl);
	if (!response.ok) {
		throw new Error(
			`Failed to fetch image: ${response.status} ${response.statusText}`,
		);
	}

	const arrayBuffer = await response.arrayBuffer();
	return Buffer.from(arrayBuffer);
}

/**
 * Fetch an image from a URL and return it as a base64-encoded string.
 * Convenience wrapper over fetchImageAsBuffer for tools that need base64 directly.
 * @param imageUrl - URL to fetch
 * @returns Base64-encoded image data (no data-URI prefix)
 * @throws Error if the fetch fails
 */
export async function fetchImageAsBase64(imageUrl: string): Promise<string> {
	const buffer = await fetchImageAsBuffer(imageUrl);
	return buffer.toString("base64");
}
