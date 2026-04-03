/**
 * Peek Profile Picture Tool
 * Allows the AI to selectively process Discord user profile pictures on-demand
 * This prevents automatic processing and enables targeted avatar analysis
 */

import { GoogleGenAI } from "@google/genai";
import type { Part } from "@google/genai";
import { log } from "../../utils/misc/logger";
import type { EnhancedImageContent } from "@/types/tool/enhancedContextTypes";
import { resolveAvatarByDiscordId } from "@/utils/discord/avatarResolver";
import { decryptApiKey } from "@/utils/security/crypto";
import {
  toZaiApiModelName,
  ZAI_CODING_CHAT_COMPLETIONS_URL,
  ZAI_GENERAL_CHAT_COMPLETIONS_URL,
} from "@/providers/zai/zaiShared";
import {
  BaseTool,
  type ToolContext,
  type ToolResult,
  type ToolParameterSchema,
} from "../../types/tool/interfaces";
import {
  ContextItemTag,
  type StructuredContextItem,
} from "../../types/misc/context";

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

/** Default prompt sent to the vision model when analyzing a profile picture */
const DEFAULT_AVATAR_ANALYSIS_PROMPT =
  "Describe this user's profile picture in detail. Include their appearance, style, and any notable elements visible in the avatar.";

/**
 * Tool for processing Discord user profile pictures on-demand
 * Available for providers with image processing capabilities
 */
export class PeekProfilePictureTool extends BaseTool {
  /**
   * Static map to store pending enhanced context items
   * This prevents base64 data from being serialized in tool responses
   * Keys are user IDs, values are enhanced context items with base64 data
   */
  static pendingEnhancedContextItems = new Map<string, StructuredContextItem>();
  name = "peek_profile_picture";
  description =
    "Process and analyze a Discord user's profile picture using AI vision capabilities. ONLY use this when specifically asked to look at someone's avatar. The target may be 'self' for the current active persona, a Discord/webhook ID, or a persona ID. Prefer 'self' when you mean the active persona instead of the bot's Discord user ID. If you don't see a user ID or mention in recent messages, avoid calling this function.";
  category = "utility" as const;
  requiresFollowUp = true;

  parameters: ToolParameterSchema = {
    type: "object",
    properties: {
      user_id: {
        type: "string",
        description:
          "The target ID to analyze. Accepts 'self' for the current active persona, a Discord/webhook ID (17-19 digits), or a persona DB ID (short numeric or persona:<tomori_id>). Prefer 'self' when you mean the active persona instead of the bot's Discord user ID.",
      },
      reason: {
        type: "string",
        description:
          "Optional brief explanation of why you want to analyze this user's profile picture. This helps with debugging and understanding AI decision-making.",
      },
    },
    required: ["user_id"],
  };

  /**
   * Discord snowflake ID validation pattern
   * Discord IDs are 17-19 digit snowflakes
   */
  private static readonly DISCORD_ID_PATTERN = /^\d{17,19}$/;
  private static readonly PERSONA_ID_PATTERN = /^(?:self|(?:persona:)?\d{1,10})$/i;

  /**
   * Check if profile picture tool is available for the given provider.
   * Availability is provider-agnostic; model vision support is handled by `isAvailableForContext()`.
   * @param _provider - LLM provider name
   * @returns True (availability gated by isAvailableForContext)
   */
  isAvailableFor(_provider: string): boolean {
    return true;
  }

  /**
   * Enhanced availability check that considers context flags and model vision capabilities
   * @param provider - LLM provider name
   * @param context - Tool context that may contain disable flags and tomoriState
   * @returns True if tool should be available
   */
  isAvailableForContext(provider: string, context?: ToolContext): boolean {
    // Base provider check
    if (!this.isAvailableFor(provider)) {
      return false;
    }

    // Require context with tomoriState
    if (!context?.tomoriState) {
      log.warn(
        "PeekProfilePictureTool: No tomoriState in context, defaulting to unavailable",
      );
      return false;
    }

    // Check if model has vision capabilities OR a dedicated vision model is configured.
    // A non-vision primary model with a vision_llm set will redirect analysis to
    // the vision model instead of using an enhanced context restart.
    const hasVision = context.tomoriState.llm.sees_images;
    const hasVisionModel = !!context.tomoriState.vision_llm;

    if (!hasVision && !hasVisionModel) {
      log.info(
        `PeekProfilePictureTool: Model ${context.tomoriState.llm.llm_codename} does not support vision and no vision model is configured. Tool disabled.`,
      );
      return false;
    }

    // Check for profile picture processing disable flag in context
    if (context?.streamContext?.disableProfilePictureProcessing) {
      log.info(
        "PeekProfilePictureTool: Temporarily disabled during enhanced context restart",
      );
      return false;
    }

    return true;
  }

  /**
   * Execute profile picture processing
   * @param args - Arguments containing user_id and optional reason
   * @param context - Tool execution context
   * @returns Promise resolving to tool result with processed image data
   */
  async execute(
    args: Record<string, unknown>,
    context: ToolContext,
  ): Promise<ToolResult> {
    // Check if profile picture processing is temporarily disabled during enhanced context restart
    if (context.streamContext?.disableProfilePictureProcessing) {
      log.info(
        "PeekProfilePictureTool: Execution blocked - Profile picture processing temporarily disabled during enhanced context restart",
      );
      return {
        success: false,
        error: "Profile picture processing is temporarily disabled",
        message:
          "Profile picture processing is temporarily disabled while analyzing another image.",
        data: {
          status: "temporarily_disabled",
          reason: "Enhanced context restart in progress",
        },
      };
    }

    // Validate parameters
    const validation = this.validateParameters(args);
    if (!validation.isValid) {
      return {
        success: false,
        error: `Invalid parameters: ${validation.errors?.join(", ") || `Missing required parameters: ${validation.missingParams?.join(", ")}`}`,
        message:
          "The user_id argument was missing or not in the expected format. Please provide a valid Discord user ID.",
      };
    }

    const userId = args.user_id as string;
    const reason = (args.reason as string) || "User-requested avatar analysis";

    log.info(
      `Processing profile picture for user ID: ${userId} - Reason: ${reason}`,
    );

    try {
      // Validate Discord user ID format
      if (!this.isValidDiscordId(userId)) {
        return {
          success: false,
          error: "Invalid target ID format",
          message:
            "The provided ID is invalid. Use 'self', a 17-19 digit Discord/webhook ID, or a short numeric persona ID.",
          data: {
            status: "invalid_user_id",
            provided_id: userId,
            expected_format:
              "'self', 17-19 digit Discord/webhook ID, or short numeric persona ID",
          },
        };
      }

      // Resolve ID as either Discord user or webhook and get avatar URL
      const avatarData = await resolveAvatarByDiscordId(userId, context, {
        forceStatic: true,
      });

      // Fetch and convert the avatar image to base64
      const base64ImageData = await this.fetchAndConvertImageToBase64(
        avatarData.avatarUrl,
      );

      log.success(
        `Profile picture fetched for ${userId} (Username: ${avatarData.username})`,
      );

      // Build display text with optional server nickname
      let userDisplayText = avatarData.username;
      if (avatarData.serverNickname) {
        userDisplayText += ` (Nickname: ${avatarData.serverNickname})`;
      }
      const targetTypeLabel =
        avatarData.sourceType === "persona"
          ? "persona"
          : avatarData.sourceType === "webhook"
            ? "webhook"
            : "user";

      // Non-vision redirect path: if the primary model cannot see images but a dedicated
      // vision model is configured, call the vision model directly with the avatar image
      // and return a text description. The primary model then responds to that description.
      if (!context.tomoriState.llm.sees_images && context.tomoriState.vision_llm) {
        return await this.redirectToVisionModel(
          base64ImageData,
          targetTypeLabel,
          userDisplayText,
          reason,
          context,
        );
      }

      // Enhanced context restart path: inject the raw image into the context so the
      // vision-capable primary model can see it directly on the next iteration.
      // Check if this is the bot's own profile picture (Discord user identity only)
      const isBotSelf =
        avatarData.sourceType === "user" &&
        context.client.user &&
        userId === context.client.user.id;
      const contextText = isBotSelf
        ? "[This message contains profile picture content from a previous avatar analysis request you made for yourself]"
        : `[This message contains profile picture content from a previous avatar analysis request you made for ${targetTypeLabel}: ${userDisplayText}]`;

      // Create artificial user message containing the profile picture Part
      // This will be added to the context for the restart
      // Special marker 'enhancedContext: true' indicates this should be processed by provider
      const imageContextItem: StructuredContextItem = {
        role: "user",
        metadataTag: ContextItemTag.DIALOGUE_HISTORY,
        parts: [
          {
            type: "text",
            text: contextText,
          },
          {
            type: "image",
            uri: `data:image/png;base64,${base64ImageData}`,
            mimeType: "image/png",
            inlineData: {
              mimeType: "image/png",
              data: base64ImageData,
            },
            isProfilePicture: true,
            enhancedContext: true, // Special marker for processing
          } as EnhancedImageContent,
        ],
      };

      // Return completely clean response following BraveSearchHandler pattern
      // Store image data externally and return clean text only
      // This prevents rate limit issues while still triggering enhanced context restart

      // Store the enhanced context item in a module-level map for tomoriChat to access
      // This is the cleanest way to avoid serializing base64 data in tool responses
      PeekProfilePictureTool.pendingEnhancedContextItems.set(
        userId,
        imageContextItem,
      );

      return {
        success: true,
        message: `Profile picture analyzed for ${targetTypeLabel}: ${avatarData.username}. Image processing completed and ready for enhanced context restart.`,
        data: {
          type: "context_restart_with_image",
          user_id: userId,
          username: avatarData.username,
          avatar_url: avatarData.avatarUrl,
          avatar_source: avatarData.sourceType,
          reason: reason,
          // Clean metadata only - no base64 data anywhere in response
          image_processed: true,
          status: "completed",
          has_pending_context: true,
        },
      };
    } catch (error) {
      log.error(
        `Profile picture processing failed for user ID: ${userId}`,
        error as Error,
      );

      // Categorize errors for better user experience
      let errorMessage = "Failed to process the user's profile picture.";
      let errorStatus = "profile_processing_failed";

      if (error instanceof Error) {
        if (
          error.message.includes("No Discord user or webhook found") ||
          (error.message.includes("User with ID") &&
            error.message.includes("not found"))
        ) {
          errorMessage = `No Discord user, webhook, or active persona avatar with ID ${userId} was found. Please check the ID and try again.`;
          errorStatus = "user_or_webhook_not_found";
        } else if (error.message.includes("privacy settings")) {
          errorMessage =
            "Cannot access this user's profile due to privacy settings.";
          errorStatus = "privacy_restricted";
        } else if (error.message.includes("Avatar image processing failed")) {
          errorMessage =
            "Failed to download and process the user's avatar image. The image may be corrupted or inaccessible.";
          errorStatus = "image_processing_failed";
        } else if (error.message.includes("Failed to fetch avatar image")) {
          errorMessage =
            "Could not download the avatar image from Discord's servers. Please try again later.";
          errorStatus = "image_fetch_failed";
        }
      }

      return {
        success: false,
        error:
          error instanceof Error
            ? error.message
            : "Unknown error occurred during profile picture processing",
        message: errorMessage,
        data: {
          status: errorStatus,
          provided_user_id: userId,
          reason: error instanceof Error ? error.message : "Unknown error",
        },
      };
    }
  }

  /**
   * Redirect profile picture analysis to the configured vision model.
   * Used when the primary chat model cannot see images but a vision_llm is configured.
   * Calls the vision model's API directly with the avatar image and returns a text description.
   * @param base64ImageData - Base64-encoded avatar image
   * @param targetTypeLabel - "user", "webhook", or "persona"
   * @param userDisplayText - Display name (with optional nickname)
   * @param reason - Original reason for the request
   * @param context - Tool execution context
   * @returns Promise resolving to a text-description ToolResult
   */
  private async redirectToVisionModel(
    base64ImageData: string,
    targetTypeLabel: string,
    userDisplayText: string,
    reason: string,
    context: ToolContext,
  ): Promise<ToolResult> {
    // Vision model is guaranteed to exist here (caller already checked)
    // biome-ignore lint/style/noNonNullAssertion: caller checked vision_llm
    const visionLlm = context.tomoriState.vision_llm!;

    if (!context.tomoriState.config.api_key) {
      return {
        success: false,
        error: "No API key configured for this server.",
      };
    }

    // 1. Decrypt the API key
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

    // 2. Resolve API model name and provider from the vision LLM row
    const provider = visionLlm.llm_provider.toLowerCase();
    const apiModelName =
      provider === "zai" || provider === "zaicoding"
        ? toZaiApiModelName(visionLlm.llm_codename)
        : visionLlm.llm_codename;

    const prompt = `${DEFAULT_AVATAR_ANALYSIS_PROMPT} This is the profile picture of ${targetTypeLabel}: ${userDisplayText}. Reason for analysis: ${reason}`;

    log.info(
      `PeekProfilePictureTool: Redirecting avatar analysis to vision model ${provider}/${apiModelName} (primary model is non-vision)`,
    );

    // 3. Route to the appropriate API based on provider family
    let analysisResult: string;

    if (provider === "google") {
      analysisResult = await this.callGoogleVisionWithBase64(
        apiKey,
        apiModelName,
        base64ImageData,
        prompt,
      );
    } else {
      const endpointUrl = this.getVisionEndpointUrl(provider, context);
      analysisResult = await this.callOpenAICompatibleVisionWithBase64(
        apiKey,
        apiModelName,
        endpointUrl,
        base64ImageData,
        prompt,
      );
    }

    log.success(
      `PeekProfilePictureTool: Vision model analysis completed for ${targetTypeLabel}: ${userDisplayText}`,
    );

    return {
      success: true,
      message: analysisResult,
      data: {
        type: "vision_model_redirect",
        target_type: targetTypeLabel,
        username: userDisplayText,
        vision_model: visionLlm.llm_codename,
        vision_provider: provider,
      },
    };
  }

  /**
   * Resolve the chat completions endpoint URL for a given provider.
   * @param provider - Lowercase provider name
   * @param context - Tool context (for custom endpoint URL)
   * @returns Chat completions URL
   */
  private getVisionEndpointUrl(provider: string, context: ToolContext): string {
    const knownUrl = PROVIDER_CHAT_COMPLETIONS_URLS[provider];
    if (knownUrl) return knownUrl;

    const customUrl = context.tomoriState.config.custom_endpoint_url;
    if (customUrl) {
      return customUrl.endsWith("/chat/completions")
        ? customUrl
        : `${customUrl}/chat/completions`;
    }

    return "https://api.openai.com/v1/chat/completions";
  }

  /**
   * Call the Google GenAI vision API with a single base64 image.
   * @param apiKey - Decrypted Google API key
   * @param model - Model name (e.g., "gemini-2.0-flash")
   * @param base64ImageData - Base64-encoded image data (PNG)
   * @param prompt - Analysis prompt
   * @returns Text description from the vision model
   */
  private async callGoogleVisionWithBase64(
    apiKey: string,
    model: string,
    base64ImageData: string,
    prompt: string,
  ): Promise<string> {
    const genAI = new GoogleGenAI({ apiKey });

    const parts: Part[] = [
      { text: prompt },
      {
        inlineData: {
          data: base64ImageData,
          mimeType: "image/png",
        },
      },
    ];

    const result = await genAI.models.generateContent({
      model,
      contents: [{ role: "user", parts }],
    });

    const text = result.text;
    if (!text) {
      throw new Error("Google Vision API returned an empty response.");
    }

    return text;
  }

  /**
   * Call an OpenAI-compatible vision API with a single base64 image.
   * @param apiKey - Decrypted API key
   * @param model - Model name
   * @param endpointUrl - Chat completions endpoint URL
   * @param base64ImageData - Base64-encoded image data (PNG)
   * @param prompt - Analysis prompt
   * @returns Text description from the vision model
   */
  private async callOpenAICompatibleVisionWithBase64(
    apiKey: string,
    model: string,
    endpointUrl: string,
    base64ImageData: string,
    prompt: string,
  ): Promise<string> {
    const requestBody = {
      model,
      messages: [
        {
          role: "user",
          content: [
            { type: "text", text: prompt },
            {
              type: "image_url",
              image_url: {
                url: `data:image/png;base64,${base64ImageData}`,
              },
            },
          ],
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
   * Validate Discord user ID format using snowflake pattern
   * @param userId - Discord user ID to validate
   * @returns True if ID matches Discord snowflake format
   */
  private isValidDiscordId(userId: string): boolean {
    return (
      PeekProfilePictureTool.DISCORD_ID_PATTERN.test(userId) ||
      PeekProfilePictureTool.PERSONA_ID_PATTERN.test(userId)
    );
  }

  /**
   * Fetch avatar image from Discord CDN and convert to base64
   * @param avatarUrl - Discord avatar URL to fetch
   * @returns Promise resolving to base64 encoded image data
   */
  private async fetchAndConvertImageToBase64(
    avatarUrl: string,
  ): Promise<string> {
    try {
      // Fetch the image from Discord CDN
      const response = await fetch(avatarUrl);

      if (!response.ok) {
        throw new Error(
          `Failed to fetch avatar image: ${response.status} ${response.statusText}`,
        );
      }

      // Get the image as array buffer
      const imageBuffer = await response.arrayBuffer();

      // Convert array buffer to base64
      const base64String = Buffer.from(imageBuffer).toString("base64");

      return base64String;
    } catch (error) {
      log.error(
        `Failed to fetch and convert avatar image: ${avatarUrl}`,
        error as Error,
      );

      if (error instanceof Error) {
        throw new Error(`Avatar image processing failed: ${error.message}`);
      }
      throw new Error("Unknown error occurred while processing avatar image");
    }
  }

  /**
   * Helper method to check if a user ID is a valid Discord snowflake
   * @param userId - User ID to validate
   * @returns True if the ID matches Discord snowflake patterns
   */
  static isValidDiscordUserId(userId: string): boolean {
    return PeekProfilePictureTool.DISCORD_ID_PATTERN.test(userId);
  }

  /**
   * Get and remove pending enhanced context item for a user
   * Used by tomoriChat during restart processing
   * @param userId - User ID to get pending context for
   * @returns Enhanced context item if found, undefined otherwise
   */
  static getPendingEnhancedContext(
    userId: string,
  ): StructuredContextItem | undefined {
    const contextItem =
      PeekProfilePictureTool.pendingEnhancedContextItems.get(userId);
    if (contextItem) {
      // Remove from map to prevent memory leaks
      PeekProfilePictureTool.pendingEnhancedContextItems.delete(userId);
    }
    return contextItem;
  }

  /**
   * Check if a user has pending enhanced context
   * @param userId - User ID to check
   * @returns True if user has pending enhanced context
   */
  static hasPendingEnhancedContext(userId: string): boolean {
    return PeekProfilePictureTool.pendingEnhancedContextItems.has(userId);
  }

  /**
   * Clear all pending enhanced context items (for cleanup)
   */
  static clearAllPendingEnhancedContext(): void {
    PeekProfilePictureTool.pendingEnhancedContextItems.clear();
  }
}
