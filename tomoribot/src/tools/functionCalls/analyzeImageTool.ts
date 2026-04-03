/**
 * Vision analysis tool for non-vision chat models.
 * Delegates image analysis to a configured vision model via the same provider's API.
 * Only available when: (1) a vision model is configured AND (2) the active chat model cannot see images.
 */

import { GoogleGenAI } from "@google/genai";
import type { Part } from "@google/genai";
import { BaseTool } from "@/types/tool/interfaces";
import type {
	ToolContext,
	ToolResult,
	ToolParameterSchema,
} from "@/types/tool/interfaces";
import { decryptApiKey } from "@/utils/security/crypto";
import { log, ColorCode } from "@/utils/misc/logger";
import { sendToolProgressNotice } from "@/utils/discord/toolProgressNotice";
import {
	toZaiApiModelName,
	ZAI_CODING_CHAT_COMPLETIONS_URL,
	ZAI_GENERAL_CHAT_COMPLETIONS_URL,
} from "@/providers/zai/zaiShared";

/**
 * Provider-to-chat-completions-URL mapping for OpenAI-compatible providers.
 * Google uses its own SDK and is handled separately.
 */
const PROVIDER_CHAT_COMPLETIONS_URLS: Record<string, string> = {
	openrouter: "https://openrouter.ai/api/v1/chat/completions",
	zai: ZAI_GENERAL_CHAT_COMPLETIONS_URL,
	zaicoding: ZAI_CODING_CHAT_COMPLETIONS_URL,
	deepseek: "https://api.deepseek.com/chat/completions",
};

/** Discord message ID pattern (17-19 digit snowflake) */
const DISCORD_ID_PATTERN = /^\d{17,19}$/;

/** Default prompt sent to the vision model when no custom prompt is provided */
const DEFAULT_VISION_PROMPT =
	"Describe what you see in this image in detail. Include any text, objects, people, colors, and notable elements.";

/** Maximum total size of all images in bytes (8 MB) to avoid API rejections */
const MAX_TOTAL_IMAGE_BYTES = 8 * 1024 * 1024;

/**
 * Built-in tool that analyzes images using a dedicated vision model.
 * Allows non-vision chat models (e.g., Z.ai glm-5) to understand images
 * by routing the analysis through a vision-capable model (e.g., Z.ai glm-4.6v).
 */
export class AnalyzeImageTool extends BaseTool {
	name = "analyze_image";
	description =
		"Analyze images in a Discord message using AI vision. Returns detailed descriptions of all images found in the message. Use this when a user sends an image and you need to understand its contents.";
	category = "utility" as const;
	requiresFollowUp = true;

	// Only expose to non-vision models during context building (system prompt tool list).
	// The full vision_llm check happens in isAvailableForContext() at execution time.
	requiredModelCapabilities = { sees_images: false as const };

	parameters: ToolParameterSchema = {
		type: "object",
		properties: {
			message_id: {
				type: "string",
				description:
					"The Discord message ID containing the image(s) to analyze. Use the message ID provided in the [System: Media message ID for tool use: ...] hint.",
			},
			prompt: {
				type: "string",
				description:
					"Optional question or instruction for the vision model (e.g., 'What text is in this image?' or 'Describe the mood of this photo'). If omitted, a general description is returned.",
			},
		},
		required: ["message_id"],
	};

	/**
	 * Basic provider check — available for all providers.
	 * The real gating logic is in isAvailableForContext().
	 */
	isAvailableFor(_provider: string): boolean {
		return true;
	}

	/**
	 * Context-aware availability check.
	 * Only expose this tool when:
	 * 1. A vision model is configured (tomoriState.vision_llm exists)
	 * 2. The active chat model does NOT support images (sees_images = false)
	 */
	isAvailableForContext(_provider: string, context: ToolContext): boolean {
		const hasVisionModel = !!context.tomoriState?.vision_llm;
		const chatModelSeesImages =
			context.tomoriState?.llm?.sees_images ?? false;

		// Only available when vision model is set AND chat model can't see images
		return hasVisionModel && !chatModelSeesImages;
	}

	/**
	 * Execute the image analysis.
	 * 1. Validate parameters and context
	 * 2. Extract images from the Discord message
	 * 3. Decrypt the API key
	 * 4. Route the images to the vision model's API
	 * 5. Return the analysis result
	 */
	async execute(
		args: Record<string, unknown>,
		context: ToolContext,
	): Promise<ToolResult> {
		const messageId = args.message_id as string;
		const prompt = (args.prompt as string) || DEFAULT_VISION_PROMPT;

		// 1. Validate message_id format
		if (!messageId || !DISCORD_ID_PATTERN.test(messageId)) {
			return {
				success: false,
				error: `Invalid message_id: "${messageId}". Expected a Discord message ID (17-19 digit number).`,
			};
		}

		// 2. Verify vision model is configured
		const visionLlm = context.tomoriState?.vision_llm;
		if (!visionLlm) {
			return {
				success: false,
				error:
					"No vision model configured. Use /config model vision to set one.",
			};
		}

		// 3. Verify API key exists
		if (!context.tomoriState.config.api_key) {
			return {
				success: false,
				error: "No API key configured for this server.",
			};
		}

		try {
			await sendToolProgressNotice(
				context.channel,
				context.locale,
				{
					titleKey: "genai.vision.analyzing_title",
					descriptionKey: "genai.vision.analyzing_description",
					footerKey: "genai.vision.analyzing_footer",
					color: ColorCode.INFO,
				},
				{
					webhook: context.webhook,
					personaUsername: context.personaUsername,
					personaAvatarUrl: context.personaAvatarUrl,
				},
				"AnalyzeImageTool",
			);

			// 4. Extract images from the Discord message
			const images = await this.extractImagesFromMessage(
				messageId,
				context,
			);

			// 5. Decrypt the API key
			const keyVersion = context.tomoriState.config.key_version || 1;
			const apiKey = await decryptApiKey(
				context.tomoriState.config.api_key,
				keyVersion,
			);

			if (!apiKey) {
				return {
					success: false,
					error: "Failed to decrypt API key.",
				};
			}

			// 6. Resolve API model name and provider from the vision LLM row
			const provider = visionLlm.llm_provider.toLowerCase();
			const apiModelName =
				provider === "zai" || provider === "zaicoding"
					? toZaiApiModelName(visionLlm.llm_codename)
					: visionLlm.llm_codename;

			// 7. Route to the appropriate API based on provider family
			let analysisResult: string;

			if (provider === "google") {
				analysisResult = await this.callGoogleVision(
					apiKey,
					apiModelName,
					images,
					prompt,
				);
			} else {
				// OpenAI-compatible providers (openrouter, zai, zaicoding, deepseek, custom)
				const endpointUrl = this.getEndpointUrl(provider, context);
				analysisResult = await this.callOpenAICompatibleVision(
					apiKey,
					apiModelName,
					endpointUrl,
					images,
					prompt,
				);
			}

			log.info(
				`Vision analysis completed: ${images.length} image(s) analyzed via ${provider}/${apiModelName}`,
			);

			return {
				success: true,
				data: analysisResult,
				message: analysisResult,
			};
		} catch (error) {
			const errorMessage =
				error instanceof Error ? error.message : String(error);
			log.error(
				`Vision analysis failed for message ${messageId}:`,
				error as Error,
			);
			return {
				success: false,
				error: `Image analysis failed: ${errorMessage}`,
			};
		}
	}

	/**
	 * Resolve the chat completions endpoint URL for a given provider.
	 * Uses the static map for known providers, falls back to custom endpoint.
	 * @param provider - Lowercase provider name
	 * @param context - Tool context (for custom endpoint URL)
	 * @returns Chat completions URL
	 */
	private getEndpointUrl(provider: string, context: ToolContext): string {
		// Check known providers first
		const knownUrl = PROVIDER_CHAT_COMPLETIONS_URLS[provider];
		if (knownUrl) return knownUrl;

		// Custom provider: use the configured endpoint URL
		const customUrl = context.tomoriState.config.custom_endpoint_url;
		if (customUrl) {
			return customUrl.endsWith("/chat/completions")
				? customUrl
				: `${customUrl}/chat/completions`;
		}

		// Fallback: OpenAI default
		return "https://api.openai.com/v1/chat/completions";
	}

	/**
	 * Call an OpenAI-compatible vision API (Z.ai, OpenRouter, DeepSeek, Custom).
	 * Sends images as base64-encoded data URLs in the content array.
	 * @param apiKey - Decrypted API key
	 * @param model - Model name without provider prefix
	 * @param images - Array of base64-encoded image data
	 * @param prompt - User prompt/question for the vision model
	 * @returns Text description from the vision model
	 */
	private async callOpenAICompatibleVision(
		apiKey: string,
		model: string,
		endpointUrl: string,
		images: Array<{ mimeType: string; data: string }>,
		prompt: string,
	): Promise<string> {
		// Build the content array with text prompt and image parts
		const contentParts: Array<Record<string, unknown>> = [
			{ type: "text", text: prompt },
		];

		for (const image of images) {
			contentParts.push({
				type: "image_url",
				image_url: {
					url: `data:${image.mimeType};base64,${image.data}`,
				},
			});
		}

		const requestBody = {
			model,
			messages: [
				{
					role: "user",
					content: contentParts,
				},
			],
			max_tokens: 1024,
		};

		const response = await fetch(endpointUrl, {
			method: "POST",
			headers: {
				"Content-Type": "application/json",
				Authorization: `Bearer ${apiKey}`,
			},
			body: JSON.stringify(requestBody),
		});

		if (!response.ok) {
			const errorText = await response.text().catch(() => "Unknown error");
			throw new Error(
				`Vision API returned ${response.status}: ${errorText}`,
			);
		}

		const data = (await response.json()) as {
			choices?: Array<{
				message?: { content?: string };
			}>;
		};

		const content = data.choices?.[0]?.message?.content;
		if (!content) {
			throw new Error(
				"Vision API returned an empty response. The model may not support image inputs.",
			);
		}

		return content;
	}

	/**
	 * Call Google GenAI vision API using the official SDK.
	 * @param apiKey - Decrypted Google API key
	 * @param model - Model name (e.g., "gemini-2.0-flash")
	 * @param images - Array of base64-encoded image data
	 * @param prompt - User prompt/question for the vision model
	 * @returns Text description from the vision model
	 */
	private async callGoogleVision(
		apiKey: string,
		model: string,
		images: Array<{ mimeType: string; data: string }>,
		prompt: string,
	): Promise<string> {
		const genAI = new GoogleGenAI({ apiKey });

		// Build parts array: text prompt + inline image data
		const parts: Part[] = [{ text: prompt }];
		for (const image of images) {
			parts.push({
				inlineData: {
					data: image.data,
					mimeType: image.mimeType,
				},
			});
		}

		const result = await genAI.models.generateContent({
			model,
			contents: [{ role: "user", parts }],
		});

		const text = result.text;
		if (!text) {
			throw new Error(
				"Google Vision API returned an empty response.",
			);
		}

		return text;
	}

	/**
	 * Extract images from a Discord message and convert to base64 format.
	 * Supports direct attachments, embedded images (Twitter/X), stickers, and custom emojis.
	 * @param messageId - Discord message ID to fetch images from
	 * @param context - Tool execution context with channel access
	 * @returns Array of objects with mimeType and base64 data
	 */
	private async extractImagesFromMessage(
		messageId: string,
		context: ToolContext,
	): Promise<Array<{ mimeType: string; data: string }>> {
		// 1. Fetch the Discord message
		const message = await context.channel.messages.fetch(messageId);
		if (!message) {
			throw new Error(`Message ${messageId} not found`);
		}

		// 2. Collect all image URLs from attachments, embeds, and stickers
		const imageUrls: Array<{
			url: string;
			mimeType: string;
			source: string;
		}> = [];

		// 2a. Direct image attachments
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

		// 2b. Embedded images (Twitter/X posts, direct image links)
		for (const embed of message.embeds) {
			if (embed.image?.url) {
				imageUrls.push({
					url: embed.image.url,
					mimeType: "image/jpeg",
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

		// 2c. Stickers
		for (const sticker of message.stickers.values()) {
			imageUrls.push({
				url: sticker.url,
				mimeType: "image/png",
				source: `sticker: ${sticker.name}`,
			});
		}

		if (imageUrls.length === 0) {
			throw new Error(
				`No images found in message ${messageId} (checked attachments, embeds, and stickers)`,
			);
		}

		log.info(
			`Found ${imageUrls.length} image(s) in message ${messageId} for vision analysis`,
		);

		// 3. Convert each image URL to base64, respecting size limit
		const inlineDataArray: Array<{ mimeType: string; data: string }> = [];
		let totalBytes = 0;

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

				// Check cumulative size limit
				if (totalBytes + imageArrayBuffer.byteLength > MAX_TOTAL_IMAGE_BYTES) {
					log.warn(
						`Skipping image from ${imageInfo.source}: would exceed ${MAX_TOTAL_IMAGE_BYTES} byte limit`,
					);
					continue;
				}

				totalBytes += imageArrayBuffer.byteLength;
				const base64Data = Buffer.from(imageArrayBuffer).toString("base64");

				inlineDataArray.push({
					mimeType: imageInfo.mimeType,
					data: base64Data,
				});

				log.info(
					`Fetched image from ${imageInfo.source} (${imageArrayBuffer.byteLength} bytes)`,
				);
			} catch (imgErr) {
				log.warn(
					`Failed to process image from ${imageInfo.source}:`,
					imgErr as Error,
				);
			}
		}

		if (inlineDataArray.length === 0) {
			throw new Error(
				`Failed to process any images from message ${messageId}`,
			);
		}

		return inlineDataArray;
	}
}
