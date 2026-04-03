import { StickerFormatType } from "discord.js";
import { z } from "zod";
import {
	DEFAULT_NAI_NEGATIVE_TAGS,
	DEFAULT_NAI_STYLE_TAGS,
} from "@/utils/image/naiTagDefaults";
import {
	logitBiasEntrySchema,
	normalizeLogitBiasEntries,
} from "@/types/provider/logitBias";

export enum HumanizerDegree {
  NONE = 0,
  LIGHT = 1,
  MEDIUM = 2,
  HEAVY = 3,
}

export enum PrivacyLevel {
  MINIMAL = 0, // Minimal privacy (full personalization features)
  PARTIAL = 1, // Partial privacy (limited personalization)
  FULL = 2, // Full privacy (maximum protection - completely invisible)
}

export enum CooldownType {
  OFF = 0, // No cooldown on message triggers (default)
  PER_USER = 1, // Each user has their own cooldown per server
  PER_CHANNEL = 2, // Each channel has its own cooldown
  SERVER_WIDE = 3, // Everyone waits (server managers exempt)
  STRICT_SERVER_WIDE = 4, // Everyone waits (no exceptions)
  COMMAND_CATEGORY = 5, // Command category cooldowns (per-user, global across servers)
}

export const userSchema = z.object({
  user_id: z.number().optional(),
  user_disc_id: z.string(),
  user_nickname: z.string(),
  language_pref: z.string().default("en-US"),
  registration_locale: z.string().nullable(), // Static locale captured at registration
  privacy_level: z.nativeEnum(PrivacyLevel).default(PrivacyLevel.MINIMAL),
	personal_memories: z.array(z.string()).default([]),
	nai_char_tags: z.array(z.string()).default([]), // Added March 2026 - User-specific NovelAI character tags
	nai_char_ref_url: z.string().nullable().optional(), // Added March 2026 - User-specific NovelAI character reference image
	impersonation_prompt: z.string().nullable().optional(), // Added March 2026 - Global user-owned prompt for user impersonation replies
	shortterm_cache_crossserver_opt_in: z.boolean().default(false), // Short-term memory cross-server sharing
  created_at: z.date().optional(),
  updated_at: z.date().optional(),
});
export type UserRow = z.infer<typeof userSchema>;

export const serverSchema = z.object({
  server_id: z.number().optional(),
  server_disc_id: z.string(),
  is_dm_channel: z.boolean().default(false), // Added for DM support
  registration_locale: z.string().nullable(), // Static locale captured at server setup
  created_at: z.date().optional(),
  updated_at: z.date().optional(),
});
export type ServerRow = z.infer<typeof serverSchema>;

export const tomoriSchema = z.object({
  tomori_id: z.number().optional(),
  server_id: z.number(),
  persona_lineage_id: z
    .preprocess((value) => {
      if (typeof value === "bigint") {
        return Number(value);
      }
      if (typeof value === "string" && value.trim() !== "") {
        return Number(value);
      }
      return value;
    }, z.number().int().nonnegative())
    .default(0),
  tomori_nickname: z.string(),
  attribute_list: z.array(z.string()).default([]),
  sample_dialogues_in: z.array(z.string()).default([]),
  sample_dialogues_out: z.array(z.string()).default([]),
  autoch_counter: z.number().default(0),
  autoch_next_target: z.number().default(0),
  is_alter: z.boolean().default(false), // Added January 2026 - Distinguishes main persona (false) from alter personas (true)
  webhook_avatar_url: z.string().nullable().optional(), // Added January 2026 - Stored alter avatar reference (production URL; non-production URL or local avatar path)
	alter_triggers: z.array(z.string()).default([]), // Added January 2026 - Trigger words for alter personas (main personas use tomori_configs.trigger_words)
	nai_tags: z.array(z.string()).default([]), // Imageboard-style persona appearance tags for NovelAI character profile resolution
	nai_char_ref_url: z.string().nullable().optional(), // Added March 2026 - Persona-specific NovelAI character reference image
	elevenlabs_voice_id: z.string().nullable().optional(), // Added March 2026 - Server-local ElevenLabs voice selection
	elevenlabs_voice_name: z.string().nullable().optional(), // Added March 2026 - Cached ElevenLabs voice display name
	nai_attg_author: z.string().nullable().optional(), // Added March 2026 - ATTG: Story author name
  nai_attg_title: z.string().nullable().optional(), // Added March 2026 - ATTG: Story title
  nai_attg_tags: z.string().nullable().optional(), // Added March 2026 - ATTG: Genre/style tags
  nai_attg_genre: z.string().nullable().optional(), // Added March 2026 - ATTG: Genre categories
  nai_attg_stars: z.number().int().min(1).max(5).nullable().optional(), // Added March 2026 - ATTG: Quality stars (Erato only)
  created_at: z.date().optional(),
  updated_at: z.date().optional(),
});
export type TomoriRow = z.infer<typeof tomoriSchema>;

export const llmSchema = z.object({
  llm_id: z.number().optional(),
  llm_provider: z.string(),
  llm_codename: z.string(),
  is_smartest: z.boolean().default(false),
  is_default: z.boolean().default(false),
  is_reasoning: z.boolean().default(false),
  is_deprecated: z.boolean().default(false),
  is_free: z.boolean().default(false),
  has_tools: z.boolean().default(false),
  sees_images: z.boolean().default(false),
  sees_videos: z.boolean().default(false),
  sees_youtube: z.boolean().default(false),
  is_uncensored: z.boolean().default(false),
  supports_structoutput: z.boolean().default(false),
  llm_description: z.string().nullable().optional(),
  ja_description: z.string().nullable().optional(),
  created_at: z.date().optional(),
  updated_at: z.date().optional(),
});
export type LlmRow = z.infer<typeof llmSchema>;

export const diffusionModelSchema = z.object({
  diffusion_model_id: z.number().optional(),
  provider: z.string(),
  codename: z.string(),
  model_description: z.string().nullable().optional(),
  ja_description: z.string().nullable().optional(),
  is_default: z.boolean().default(false),
  is_deprecated: z.boolean().default(false),
  is_free: z.boolean().default(false),
  is_uncensored: z.boolean().default(false),
  created_at: z.date().optional(),
  updated_at: z.date().optional(),
});
export type DiffusionModelRow = z.infer<typeof diffusionModelSchema>;

export const embeddingModelSchema = z.object({
  embedding_model_id: z.number().optional(),
  provider: z.string(),
  codename: z.string(),
  model_family: z.string(),
  model_description: z.string().nullable().optional(),
  ja_description: z.string().nullable().optional(),
  is_default: z.boolean().default(false),
  is_deprecated: z.boolean().default(false),
  created_at: z.date().optional(),
  updated_at: z.date().optional(),
});
export type EmbeddingModelRow = z.infer<typeof embeddingModelSchema>;

/**
 * Normalizes a JSONB array value from the database driver.
 * Handles the case where Bun SQL returns JSONB columns as strings
 * instead of parsed objects — parses the string before returning.
 * @param value - Raw value from the database (may be array, string, or other)
 * @returns Parsed array, or empty array if parsing fails
 */
function normalizeJsonbArray(value: unknown): unknown[] {
	if (Array.isArray(value)) return value;
	if (typeof value === "string") {
		try {
			const parsed = JSON.parse(value);
			return Array.isArray(parsed) ? parsed : [];
		} catch {
			return [];
		}
	}
	return [];
}

function normalizeFallbackLlmIds(value: unknown): number[] {
  let source: unknown = value;
  if (typeof source === "string") {
    try {
      source = JSON.parse(source);
    } catch {
      return [];
    }
  }

  if (!Array.isArray(source)) {
    return [];
  }

  return source
    .map((id) => {
      const parsed =
        typeof id === "number"
          ? id
          : typeof id === "string"
            ? Number(id)
            : NaN;
      return Number.isInteger(parsed) ? parsed : null;
    })
    .filter((id): id is number => id !== null);
}

export const tomoriConfigSchema = z.object({
  tomori_config_id: z.number().optional(),
  tomori_id: z.number().nullable().optional(), // Legacy pointer (server-scoped configs use server_id)
  server_id: z.number().nullable().optional(), // Added January 2026 - Server-scoped config (nullable for legacy rows)
  llm_id: z.number(),
  embedding_model_id: z.number().int().nullable().optional(), // Added February 2026 - Embedding model for document retrieval
	diffusion_model_id: z.number().int().nullable().optional(), // Added December 2025 - Image generation model
	vision_llm_id: z.number().int().nullable().optional(), // Added March 2026 - Dedicated vision model for non-vision chat models (FK to llms)
	nai_diffusion_model_id: z.number().int().nullable().optional(), // Added March 2026 - Dedicated NovelAI image model override for generate_image_nai
	nai_style_tags: z.array(z.string()).default([...DEFAULT_NAI_STYLE_TAGS]), // Added March 2026 - Server-wide NovelAI style/quality tags
	nai_negative_tags: z.array(z.string()).default([...DEFAULT_NAI_NEGATIVE_TAGS]), // Added March 2026 - Server-wide NovelAI negative prompt tags
	nai_sampler: z.string().nullable().optional(), // Added March 2026 - Server override for NovelAI image sampler
	nai_steps: z.number().int().min(1).max(50).nullable().optional(), // Added March 2026 - Server override for NovelAI image steps
	nai_scale: z.number().min(0.0).max(10.0).nullable().optional(), // Added March 2026 - Server override for NovelAI image scale
	nai_noise_schedule: z.string().nullable().optional(), // Added March 2026 - Server override for NovelAI noise schedule
	nai_cfg_rescale: z.number().min(0.0).max(1.0).nullable().optional(), // Added March 2026 - Server override for NovelAI cfg_rescale
	llm_temperature: z.number().min(0.0).max(2.0).default(1.0),
  llm_top_p: z.number().min(0.0).max(1.0).default(0.95), // Added February 2026 - Nucleus sampling
  llm_top_k: z.number().int().min(0).max(40).default(0), // Added February 2026 - Top-K sampling (0=disabled)
  llm_frequency_penalty: z.number().min(-2.0).max(2.0).default(0.0), // Added February 2026 - Frequency penalty (0.0=neutral)
  llm_presence_penalty: z.number().min(-2.0).max(2.0).default(0.0), // Added February 2026 - Presence penalty (0.0=neutral)
  llm_min_p: z.number().min(0.0).max(1.0).default(0.0), // Added February 2026 - Min-P sampling (0.0=disabled)
	llm_logit_biases: z.preprocess(
		(value) => normalizeLogitBiasEntries(value),
		z.array(logitBiasEntrySchema).default([]),
	), // Added March 2026 - Stored OpenAI-style logit bias entries (text or explicit token IDs)
  api_key: z.instanceof(Buffer).nullable(),
  key_version: z.number().int().default(1).optional(), // Added November 2025 - Encryption key version for rotation
  trigger_words: z.array(z.string()).default([]),
  autoch_disc_ids: z.array(z.string()).default([]),
	rp_channel_ids: z.array(z.string()).default([]), // Added February 2026 - Channels where emojis/stickers are always suppressed
	welcome_channel_disc_id: z.string().nullable().optional(), // Added March 2026 - Channel used for member join welcomes
	thought_log_channel_disc_id: z.string().nullable().optional(), // Added March 2026 - Channel used for reasoning/thought log embeds
	welcome_prompt: z.string().nullable().optional(), // Added March 2026 - Additional prompt appended to join welcomes
	welcome_persona_id: z.number().int().nullable().optional(), // Added March 2026 - NULL means random persona selection for welcomes
	autoch_threshold: z.number().default(0),
	autoch_threshold_max: z.number().default(0),
  always_reply_enabled: z.boolean().default(false), // Added March 2026 - Main persona replies to all user messages (guild only, alters still require triggers)
  self_reply_limit: z.number().int().min(0).max(10).default(3), // Added January 2026 - Self-reply chain limit for persona-to-persona triggering
	send_message_limit: z.number().int().min(0).max(40).default(0), // Added March 2026 - Max Discord messages per response (0 = unlimited, capped by MAX_FLUSH_COUNT)
  triggered_persona_limit: z.number().int().min(1).max(10).default(3), // Added February 2026 - Max personas triggered by a single message
  message_fetch_limit: z.number().int().min(20).max(100).default(80), // Added February 2026 - Max recent messages fetched for context
  server_memteaching_enabled: z.boolean().default(true),
  attribute_memteaching_enabled: z.boolean().default(false),
  sampledialogue_memteaching_enabled: z.boolean().default(false),
  self_teaching_enabled: z.boolean().default(true),
  web_search_enabled: z.boolean().default(true), // New: Added for Web Search permission (Brave Search)
  personal_memories_enabled: z.boolean().default(true),
  humanizer_degree: z
    .nativeEnum(HumanizerDegree)
    .default(HumanizerDegree.LIGHT),
  emoji_usage_enabled: z.boolean().default(true), // Added May 5, 2025
  sticker_usage_enabled: z.boolean().default(true), // Added May 5, 2025
  pin_message_enabled: z.boolean().default(true), // Added November 5, 2025 - Permission for pin message tool
  imagegen_enabled: z.boolean().default(true), // Added January 2026 - Permission for image generation
  hide_respond_embed: z.boolean().default(false), // Added January 2026 - Hide respond command success embed
  hide_impersonation_embeds: z.boolean().default(false), // Added February 2026 - Hide impersonation confirmation embeds
  voice_message_enabled: z.boolean().default(true), // Added March 2026 - Allow Tomori to send ElevenLabs TTS voice messages
  voice_transcript_chat_mode: z.boolean().default(false), // Added March 2026 - Post voice transcripts as webhook chat messages instead of using internal cache
  self_debug_enabled: z.boolean().default(false), // Added March 2026 - Include Tomori error embeds in context as [System: ...]
  uncensor_injection_enabled: z.boolean().default(false), // Added February 2026 - Prompt injection mitigation toggle
  uncensor_unicode_space_enabled: z.boolean().default(false), // Added February 2026 - Unicode space replacement toggle
  uncensor_sanitize_enabled: z.boolean().default(false), // Added February 2026 - Sensitive word sanitization toggle
  videogen_enabled: z.boolean().default(true), // Added January 2026 - Reserved for future video generation
  timezone_offset: z.number().int().min(-12).max(14).default(0),
  system_prompt: z.string().nullable(), // Added December 2025 - Custom system prompt for personality instructions
  cooldown_type: z.nativeEnum(CooldownType).default(CooldownType.OFF), // Added January 2026 - Message trigger cooldown type
  cooldown_length: z.number().int().min(1).max(86400).default(5), // Added January 2026 - Cooldown duration in seconds
  custom_endpoint_url: z.string().nullable().optional(), // Added January 2026 - Custom OpenAI-compatible endpoint URL (non-production only)
  custom_model_name: z.string().nullable().optional(), // Added January 2026 - Actual model name for custom endpoints (e.g., "gemma3:latest" for Ollama)
  nai_preset_name: z.string().nullable().optional(), // Added March 2026 - Active NovelAI sampling preset name (null for non-NAI providers)
  fallback_llm_ids: z.preprocess(
    (value) => normalizeFallbackLlmIds(value),
    z.array(z.number().int()).default([]),
  ), // Added March 2026 - Ordered fallback llm_ids for provider failover (stored as JSONB)
  nai_exclusive_imggen: z.boolean().default(false), // Added March 2026 - Hides standard generate_image when NovelAI opt key is present
  other_model_codename: z.string().nullable().optional(), // Added March 2026 - Real OpenRouter model codename for other-model (e.g. "xai/grok-2")
  other_model_capabilities: z.preprocess(
    (value) => (typeof value === "string" ? JSON.parse(value) : value),
    z
      .object({
        hasTools: z.boolean().default(false),
        seesImages: z.boolean().default(false),
        seesVideos: z.boolean().default(false),
        supportsStructuredOutput: z.boolean().default(false),
      })
      .nullable()
      .optional(),
  ), // Added March 2026 - Cached capabilities for other-model (stored as JSONB)
  other_model_capabilities_fetched_at: z.preprocess(
    (value) => (typeof value === "string" ? new Date(value) : value),
    z.date().nullable().optional(),
  ), // Added March 2026 - Timestamp of last capability fetch for other-model
  created_at: z.date().optional(),
  updated_at: z.date().optional(),
});
export type TomoriConfigRow = z.infer<typeof tomoriConfigSchema>;

/**
 * Schema for a NovelAI sampling preset row.
 * Stores the full parameter JSON alongside human-readable descriptions.
 * Schema-compatible fields (temperature, top_k, top_p, min_p) are written
 * to tomori_configs; NAI-specific fields are merged at generation time.
 */
export const naiPresetSchema = z.object({
  nai_preset_id: z.number(),
  preset_name: z.string(),
  model_target: z.string(), // "kayra" or "erato"
  is_default: z.boolean(),
  preset_desc: z.string(), // EN human-readable description
  ja_preset_desc: z.string(), // JA human-readable description
  parameters: z.record(z.string(), z.unknown()),
  created_at: z.date().optional(),
});
export type NaiPresetRow = z.infer<typeof naiPresetSchema>;

export const personaConfigSchema = z.object({
  tomori_id: z.number(),
  trigger_words: z.array(z.string()).default([]),
  persona_prompt: z.string().nullable().optional(),
  llm_id: z.number().int().nullable().optional(), // Added March 2026 - Persona-specific LLM model override
  created_at: z.date().optional(),
  updated_at: z.date().optional(),
});
export type PersonaConfigRow = z.infer<typeof personaConfigSchema>;

/**
 * Schema for per-channel LLM model overrides.
 * When set, overrides the global llm_id for all personas in that channel.
 */
export const channelLlmOverrideSchema = z.object({
  server_id: z.number(),
  channel_disc_id: z.string(),
  llm_id: z.number(),
  created_at: z.date().optional(),
  updated_at: z.date().optional(),
});
export type ChannelLlmOverrideRow = z.infer<typeof channelLlmOverrideSchema>;

export const tomoriPresetSchema = z.object({
  tomori_preset_id: z.number(),
  tomori_preset_name: z.string(),
  tomori_preset_desc: z.string(),
  preset_attribute_list: z.array(z.string()).default([]),
  preset_sample_dialogues_in: z.array(z.string()).default([]),
  preset_sample_dialogues_out: z.array(z.string()).default([]),
  preset_language: z.string(),
  preset_avatar_path: z.string().nullable().optional(),
  preset_trigger_words: z.array(z.string()).default([]),
  created_at: z.date().optional(),
  updated_at: z.date().optional(),
});
export type TomoriPresetRow = z.infer<typeof tomoriPresetSchema>;

export const systemPromptPresetSchema = z.object({
  system_prompt_preset_id: z.number(),
  system_prompt_preset_name: z.string(),
  system_prompt_preset_desc: z.string(),
  ja_description: z.string().nullable().optional(),
  preset_prompt_text: z.string(),
  created_at: z.date().optional(),
  updated_at: z.date().optional(),
});
export type SystemPromptPresetRow = z.infer<typeof systemPromptPresetSchema>;

export const serverEmojiSchema = z.object({
  server_emoji_id: z.number().optional(),
  server_id: z.number(),
  emoji_disc_id: z.string(),
  emoji_name: z.string(),
  emoji_desc: z.string().default(""),
  emotion_key: z.string(),
  is_global: z.boolean().default(false),
  is_animated: z.boolean().default(false),
  created_at: z.date().optional(),
  updated_at: z.date().optional(),
});
export type ServerEmojiRow = z.infer<typeof serverEmojiSchema>;

export const serverStickerSchema = z.object({
  server_sticker_id: z.number().optional(),
  server_id: z.number(),
  sticker_disc_id: z.string(),
  sticker_name: z.string(),
  sticker_desc: z.string().default(""),
  emotion_key: z.string(),
  is_global: z.boolean().default(false),
  //is_animated: z.boolean().default(false),
  sticker_format: z
    .nativeEnum(StickerFormatType)
    .default(StickerFormatType.PNG),
  created_at: z.date().optional(),
  updated_at: z.date().optional(),
});
export type ServerStickerRow = z.infer<typeof serverStickerSchema>;

export const serverMemorySchema = z.object({
  server_memory_id: z.number().optional(),
  server_id: z.number(),
  tomori_id: z.number().nullable().optional(),
  persona_lineage_id: z.preprocess((value) => {
    if (typeof value === "bigint") {
      return Number(value);
    }
    if (typeof value === "string" && value.trim() !== "") {
      return Number(value);
    }
    return value;
  }, z.number().int().nonnegative()),
  user_id: z.number().nullable(), // Nullable - set to NULL if user deleted
  content: z.string(),
  created_at: z.date().optional(),
  updated_at: z.date().optional(),
});
export type ServerMemoryRow = z.infer<typeof serverMemorySchema>;

export const personalMemorySchema = z.object({
  personal_memory_id: z.number().optional(),
  user_id: z.number(),
  persona_lineage_id: z.preprocess((value) => {
    if (typeof value === "bigint") {
      return Number(value);
    }
    if (typeof value === "string" && value.trim() !== "") {
      return Number(value);
    }
    return value;
  }, z.number().int().nonnegative()),
  content: z.string(),
  created_at: z.date().optional(),
  updated_at: z.date().optional(),
});
export type PersonalMemoryRow = z.infer<typeof personalMemorySchema>;

export const documentSchema = z.object({
  document_id: z.number().optional(),
  server_id: z.number(),
  tomori_id: z.number().nullable().optional(),
  uploader_user_id: z.number().nullable().optional(),
  document_name: z.string(),
  file_name: z.string().nullable().optional(),
  mime_type: z.string().nullable().optional(),
  file_size_bytes: z.number().int().nullable().optional(),
  text_content: z.string(),
  source_type: z.string().default("upload"),
  created_at: z.date().optional(),
  updated_at: z.date().optional(),
});
export type DocumentRow = z.infer<typeof documentSchema>;

export const documentChunkSchema = z.object({
  document_chunk_id: z.number().optional(),
  document_id: z.number(),
  server_id: z.number(),
  embedding_model_id: z.number(),
  embedding_family: z.string(),
  chunk_index: z.number().int(),
  content: z.string(),
  embedding: z.unknown().optional(),
  created_at: z.date().optional(),
});
export type DocumentChunkRow = z.infer<typeof documentChunkSchema>;

export const personalizationBlacklistSchema = z.object({
  server_id: z.number(),
  user_disc_id: z.string(), // Discord ID - persists even if user deletes account
  created_at: z.date().optional(),
  updated_at: z.date().optional(),
});
export type PersonalizationBlacklistRow = z.infer<
  typeof personalizationBlacklistSchema
>;

/**
 * Channel Whitelist Schema
 * Defines channel allowlist entries with optional per-channel cooldown overrides.
 * When ANY channel is whitelisted, ONLY whitelisted channels can trigger the bot.
 */
export const channelWhitelistSchema = z.object({
  server_id: z.number(),
  channel_disc_id: z.string(),
  cooldown_type: z.nativeEnum(CooldownType).nullable().default(null),
  cooldown_length: z.number().int().min(0).max(86400).nullable().default(null),
  created_at: z.date().optional(),
  updated_at: z.date().optional(),
});
export type ChannelWhitelistRow = z.infer<typeof channelWhitelistSchema>;

/**
 * Role Whitelist Schema
 * Defines role-based trigger access for server-wide whitelist restrictions.
 * When ANY role is whitelisted, only members with whitelisted roles can trigger the bot.
 */
export const roleWhitelistSchema = z.object({
  server_id: z.number(),
  role_disc_id: z.string(),
  created_at: z.date().optional(),
  updated_at: z.date().optional(),
});
export type RoleWhitelistRow = z.infer<typeof roleWhitelistSchema>;

export const errorLogSchema = z.object({
  error_log_id: z.number().optional(), // Primary key, optional as it's generated
  // Context IDs - Optional because errors can occur outside specific contexts
  tomori_id: z.number().nullable().optional(),
  user_id: z.number().nullable().optional(),
  server_id: z.number().nullable().optional(),
  // Error Details
  error_type: z.string().default("GenericError"), // Categorize the error, default if not specified
  error_message: z.string(), // The main error message, required
  stack_trace: z.string().nullable().optional(), // Dedicated field for stack trace, optional
  error_metadata: z
    .record(z.string(), z.unknown())
    .nullable()
    .optional()
    .default({}), // Flexible JSON for extra context, optional
  // Timestamps
  created_at: z.date().optional(), // Handled by DB default
  updated_at: z.date().optional(), // Handled by DB default/trigger
});
export type ErrorLogRow = z.infer<typeof errorLogSchema>;

export interface ErrorContext {
  tomoriId?: number | null;
  userId?: number | null;
  serverId?: number | null; // Database ID only - use metadata for Discord snowflakes
  errorType?: string;
  metadata?: Record<string, unknown> | null;
}

export const cooldownSchema = z.object({
  cooldown_id: z.number().optional(),
  cooldown_type: z.number(),
  server_disc_id: z.string().nullable(),
  user_disc_id: z.string().nullable(),
  channel_disc_id: z.string().nullable(),
  command_category: z.string().nullable(),
  expiry_time: z.number(),
  created_at: z.string().optional(),
});
export type CooldownRow = z.infer<typeof cooldownSchema>;

export const optApiKeySchema = z.object({
  opt_api_key_id: z.number().optional(), // Primary key, optional as it's generated
  server_id: z.number(), // Foreign key to servers table
  service_name: z.string(), // Service name identifier (e.g., 'brave-search', 'duckduckgo-search', 'fetch')
  api_key: z.instanceof(Buffer).nullable(), // Encrypted API key using pgcrypto, nullable for free services
  key_version: z.number().int().default(1).optional(), // Added November 2025 - Encryption key version for rotation
  created_at: z.date().optional(), // Handled by DB default
  updated_at: z.date().optional(), // Handled by DB default/trigger
});
export type OptApiKeyRow = z.infer<typeof optApiKeySchema>;

export const reminderSchema = z.object({
  reminder_id: z.number().optional(), // Primary key, optional as it's generated
  server_id: z.number(), // Foreign key to servers table
  channel_disc_id: z.string(), // Discord channel ID where reminder was set
  user_discord_id: z.string(), // Target user's Discord ID
  user_nickname: z.string(), // Target user's nickname for display
  reminder_purpose: z.string(), // What the reminder is for
  reminder_time: z.date(), // When to trigger the reminder (TIMESTAMP WITH TIME ZONE)
  repetition_interval_hours: z.number().int().nullable().optional(), // Optional: repeat interval in hours
  self_reminder: z.boolean().nullable().optional(), // Optional: reminder targets the bot itself
  created_by_user_id: z.number().nullable(), // Who requested the reminder (nullable - set to NULL if user deleted)
  persona_id: z.number().nullable().optional(), // Persona that created the reminder (nullable - fallback to main)
  created_at: z.date().optional(), // Handled by DB default
  updated_at: z.date().optional(), // Handled by DB default/trigger
});
export type ReminderRow = z.infer<typeof reminderSchema>;

/**
 * API Key Rotation error types for cooldown logic
 * - rate_limit: 429 errors, 60-second cooldown
 * - api_error: Other API errors (401, 403, etc.), 5-minute cooldown
 */
export const ApiKeyRotationErrorType = z.enum(["rate_limit", "api_error"]);
export type ApiKeyRotationErrorType = z.infer<typeof ApiKeyRotationErrorType>;

const coerceNumber = z.preprocess((value) => {
  if (typeof value === "bigint") {
    return Number(value);
  }
  if (typeof value === "string" && value.trim() !== "") {
    return Number(value);
  }
  return value;
}, z.number());

const coerceIntNumber = z.preprocess((value) => {
  if (typeof value === "bigint") {
    return Number(value);
  }
  if (typeof value === "string" && value.trim() !== "") {
    return Number(value);
  }
  return value;
}, z.number().int());

/**
 * Schema for API key rotation table entries
 * Used for load balancing (round-robin) and failover across multiple API keys
 */
export const apiKeyRotationSchema = z.object({
  rotation_key_id: z.number().optional(), // Primary key, auto-generated
  server_id: z.number(), // Foreign key to servers table
  provider: z.string(), // Must match current provider in tomori_configs
  api_key: z.instanceof(Buffer).nullable(), // NULL if is_main_key_pointer = true
  key_version: z.number().int().default(1), // Encryption key version
  is_main_key_pointer: z.boolean().default(false), // true = use tomori_configs.api_key
  is_enabled: z.boolean().default(true), // Manual or auto-disabled after errors
  usage_count: coerceNumber.default(0), // For round-robin tracking
  error_count: coerceIntNumber.default(0), // Consecutive errors
  last_used_at: z.date().nullable().optional(), // Last successful use
  last_error_at: z.date().nullable().optional(), // For cooldown logic
  last_error_type: ApiKeyRotationErrorType.nullable().optional(), // Error category for cooldown
  last_error_message: z.string().nullable().optional(), // Human-readable error
  created_at: z.date().optional(), // Handled by DB default
  updated_at: z.date().optional(), // Handled by DB default/trigger
});
export type ApiKeyRotationRow = z.infer<typeof apiKeyRotationSchema>;

/**
 * Schema for image quota configuration (per-server settings)
 * Controls daily user quotas and server-wide quota pools
 */
export const imageQuotaConfigSchema = z.object({
  server_id: z.number(), // Foreign key to servers table
  daily_user_quota: z.number().int().min(0).max(100).default(10), // Per-user daily limit (0 = unlimited)
  serverwide_quota: z.number().int().min(0).max(99999).default(0), // Total server quota (0 = unlimited)
  serverwide_quota_resets_in: z.number().int().min(1).max(365).default(365), // Days before server quota resets
  enabled: z.boolean().default(true), // Master toggle for quota system
  created_at: z.date().optional(), // Handled by DB default
  updated_at: z.date().optional(), // Handled by DB default/trigger
});
export type ImageQuotaConfigRow = z.infer<typeof imageQuotaConfigSchema>;

/**
 * Schema for per-user daily image quota tracking
 * Resets daily at midnight (server timezone)
 */
export const imageQuotaSchema = z.object({
  quota_id: z.number().optional(), // Primary key, auto-generated
  server_id: z.number(), // Foreign key to servers table
  user_disc_id: z.string(), // User's Discord ID
  usage_count: z.number().int().min(0).default(0), // Images generated today
  quota_date: z.date(), // Date this quota is for (YYYY-MM-DD)
  last_reset: z.date().optional(), // Handled by DB default
});
export type ImageQuotaRow = z.infer<typeof imageQuotaSchema>;

/**
 * Schema for server-wide image quota tracking
 * Resets based on serverwide_quota_resets_in configuration
 */
export const serverwideQuotaSchema = z.object({
  server_id: z.number(), // Primary key, foreign key to servers table
  usage_count: z.number().int().min(0).default(0), // Total images generated this period
  quota_period_start: z.date(), // When this quota period started
  quota_period_end: z.date(), // When this quota period ends (calculated from config)
  last_updated: z.date().optional(), // Handled by DB default
});
export type ServerwideQuotaRow = z.infer<typeof serverwideQuotaSchema>;

/**
 * Schema for text quota configuration (per-server settings)
 * Controls daily user quotas and server-wide quota pools for text generations
 */
export const textQuotaConfigSchema = z.object({
  server_id: z.number(), // Foreign key to servers table
  daily_user_quota: z.number().int().min(0).max(100).default(0), // Per-user daily limit (0 = unlimited)
  serverwide_quota: z.number().int().min(0).max(99999).default(0), // Total server quota (0 = unlimited)
  serverwide_quota_resets_in: z.number().int().min(1).max(365).default(365), // Days before server quota resets
  enabled: z.boolean().default(true), // Master toggle for quota system
  created_at: z.date().optional(), // Handled by DB default
  updated_at: z.date().optional(), // Handled by DB default/trigger
});
export type TextQuotaConfigRow = z.infer<typeof textQuotaConfigSchema>;

/**
 * Schema for per-user daily text quota tracking
 * Resets daily at midnight (server timezone)
 */
export const textQuotaSchema = z.object({
  quota_id: z.number().optional(), // Primary key, auto-generated
  server_id: z.number(), // Foreign key to servers table
  user_disc_id: z.string(), // User's Discord ID
  usage_count: z.number().int().min(0).default(0), // Text generations triggered today
  quota_date: z.date(), // Date this quota is for (YYYY-MM-DD)
  last_reset: z.date().optional(), // Handled by DB default
});
export type TextQuotaRow = z.infer<typeof textQuotaSchema>;

/**
 * Schema for server-wide text quota tracking
 * Resets based on serverwide_quota_resets_in configuration
 */
export const textServerwideQuotaSchema = z.object({
  server_id: z.number(), // Primary key, foreign key to servers table
  usage_count: z.number().int().min(0).default(0), // Total text generations this period
  quota_period_start: z.date(), // When this quota period started
  quota_period_end: z.date(), // When this quota period ends (calculated from config)
  updated_at: z.date().optional(), // Handled by DB default
});
export type TextServerwideQuotaRow = z.infer<typeof textServerwideQuotaSchema>;

/**
 * Schema for Matrix ↔ Discord channel bridge links.
 * Enforces strict 1-to-1 mapping: one Discord channel per Matrix room and vice versa.
 */
export const matrixChannelLinkSchema = z.object({
  link_id: z.number().optional(),
  server_id: z.number(),
  channel_disc_id: z.string(),
  matrix_room_id: z.string(),
  created_at: z.date().optional(),
});
export type MatrixChannelLinkRow = z.infer<typeof matrixChannelLinkSchema>;

export const randomTriggerSchema = z.object({
  trigger_id: z.number().optional(), // Primary key, auto-generated
  server_id: z.number(), // Foreign key to servers table
  channel_disc_id: z.string(), // Discord channel ID where trigger fires
  tomori_id: z.number().nullable().optional(), // NULL = "Random" persona selection
  timer_hours: z.number().int().min(1), // How often to roll the dice (hours)
  random_offset_range: z.number().int().min(0).nullable().optional(), // Optional +/- jitter range (hours)
  chance_percent: z.number().int().min(1).max(100), // Probability of firing (1-100%)
  silence_threshold_hours: z.number().int().nullable().optional(), // Skip if channel active within N hours
  respond_to_self: z.boolean().default(false), // Whether to fire if persona spoke last
  custom_prompt: z.string().nullable().optional(), // Optional injected system prompt
  failure_threshold: z.number().int().min(1).nullable().optional(), // NULL = disabled; force-fire after N consecutive misses
  consecutive_failures: z.number().int().min(0).default(0).optional(), // Current consecutive miss count; resets on fire
  next_trigger_at: z.date(), // Scheduled time for next dice roll
  created_at: z.date().optional(),
  updated_at: z.date().optional(),
});
export type RandomTriggerRow = z.infer<typeof randomTriggerSchema>;

/**
 * Tomori's combined state (base config + LLM settings + LLM info)
 */
export type TomoriState = TomoriRow & {
  config: TomoriConfigRow;
  llm: LlmRow; // Added LLM information
  trigger_words: string[]; // Persona-scoped trigger words from persona_configs
  persona_prompt: string | null; // Optional persona-specific prompt appended after system prompt
  server_memories: string[]; // Changed to string array to match implementation
  rotation_keys?: ApiKeyRotationRow[]; // Optional: API key rotation pool for load balancing/failover
  persona_llm?: LlmRow; // Added March 2026 - Persona-specific model override (highest priority in chain)
  vision_llm?: LlmRow; // Added March 2026 - Dedicated vision model for non-vision chat models
  nai_preset?: NaiPresetRow; // Added March 2026 - Active NovelAI sampling preset (null when not using NAI)
  fallback_llms?: LlmRow[]; // Added March 2026 - Resolved LLM rows for fallback model failover chain
};

/**
 * Schema for validating the combined Tomori state
 */
export const tomoriStateSchema = tomoriSchema.extend({
  config: tomoriConfigSchema,
  llm: llmSchema, // Added LLM schema validation
  trigger_words: z.array(z.string()).default([]),
  persona_prompt: z.string().nullable().default(null),
  server_memories: z.array(z.string()).default([]), // Changed to array of strings
  rotation_keys: z.array(apiKeyRotationSchema).optional(), // API key rotation pool
  persona_llm: llmSchema.optional(), // Added March 2026 - Persona-specific model override
  vision_llm: llmSchema.optional(), // Added March 2026 - Dedicated vision model for non-vision chat models
  nai_preset: naiPresetSchema.optional(), // Added March 2026 - Active NovelAI sampling preset
  fallback_llms: z.array(llmSchema).optional(), // Added March 2026 - Resolved fallback LLM rows
});

/**
 * Configuration data needed for server setup
 */
export const setupConfigSchema = z.object({
  serverId: z.string(),
  encryptedApiKey: z.instanceof(Buffer),
  keyVersion: z.number().int().default(1), // Encryption key version
  provider: z.string(), // LLM provider name (e.g., "google", "openai")
  presetId: z.number(),
  humanizer: z.number().default(1),
  tomoriName: z.string(),
  timezoneOffset: z.number().int().min(-12).max(14).default(0), // Timezone offset in hours
  locale: z.string(),
  registrationLocale: z.string().nullable(), // Analytics-only locale captured at setup; not used for functionality
});
export type SetupConfig = z.infer<typeof setupConfigSchema>;

/**
 * Result of the setup operation, containing all created database rows
 */
export const setupResultSchema = z.object({
  server: serverSchema,
  tomori: tomoriSchema,
  config: tomoriConfigSchema,
  emojis: z.array(serverEmojiSchema),
  stickers: z.array(serverStickerSchema),
});
export type SetupResult = z.infer<typeof setupResultSchema>;

/**
 * Guild MCP Server — per-guild remote MCP server registration.
 * Stored in guild_mcp_servers table; auth_token is PGP-encrypted BYTEA.
 */
export const guildMcpServerSchema = z.object({
	guild_mcp_id: z.number().optional(),
	server_id: z.number(),
	name: z.string(),
	url: z.string(),
	auth_token: z.instanceof(Buffer).nullable().optional(),
	key_version: z.number().int().default(1),
	is_enabled: z.boolean().default(true),
	server_type: z.string().nullable().optional(),
	created_at: z.date().optional(),
	updated_at: z.date().optional(),
});
export type GuildMcpServerRow = z.infer<typeof guildMcpServerSchema>;

/**
 * Saved Provider Config — snapshot of provider-specific settings stored in
 * saved_provider_configs. One row per provider per server; UPSERT on save.
 */
export const savedProviderConfigSchema = z.object({
	saved_config_id: z.number().optional(),
	server_id: z.number(),
	provider: z.string(),
	api_key: z.instanceof(Buffer).nullable(),
	key_version: z.number().int().default(1),
	llm_id: z.number().nullable(),
	diffusion_model_id: z.number().nullable(),
	embedding_model_id: z.number().nullable(),
	nai_diffusion_model_id: z.number().nullable(),
	vision_llm_id: z.number().nullable().optional(), // Added March 2026 - Vision model snapshot
	nai_preset_name: z.string().nullable(),
	llm_temperature: z.number().nullable().optional(), // Added March 2026 - Sampler snapshot
	llm_top_p: z.number().nullable().optional(), // Added March 2026 - Sampler snapshot
	llm_top_k: z.number().int().nullable().optional(), // Added March 2026 - Sampler snapshot
	llm_frequency_penalty: z.number().nullable().optional(), // Added March 2026 - Sampler snapshot
	llm_presence_penalty: z.number().nullable().optional(), // Added March 2026 - Sampler snapshot
	llm_min_p: z.number().nullable().optional(), // Added March 2026 - Sampler snapshot
	llm_logit_biases: z.preprocess(
		(value) => normalizeLogitBiasEntries(value),
		z.array(logitBiasEntrySchema).default([]),
	), // Added March 2026 - Logit bias snapshot
	custom_endpoint_url: z.string().nullable(),
	custom_model_name: z.string().nullable(),
	fallback_llm_ids: z.preprocess(
		(value) => normalizeFallbackLlmIds(value),
		z.array(z.number().int()).default([]),
	),
	channel_llm_overrides: z.preprocess(
		(value) => normalizeJsonbArray(value),
		z.array(z.object({
			channel_disc_id: z.string(),
			llm_id: z.number().int(),
		})).default([]),
	),
	persona_llm_overrides: z.preprocess(
		(value) => normalizeJsonbArray(value),
		z.array(z.object({
			tomori_id: z.number().int(),
			llm_id: z.number().int(),
		})).default([]),
	),
	saved_at: z.coerce.date().optional(),
	updated_at: z.coerce.date().optional(),
});
export type SavedProviderConfigRow = z.infer<typeof savedProviderConfigSchema>;

/**
 * Input type for upserting a saved provider config.
 * Omits auto-generated fields (saved_config_id, saved_at, updated_at).
 */
export type SavedProviderConfigUpsert = Omit<
	SavedProviderConfigRow,
	"saved_config_id" | "saved_at" | "updated_at"
>;

/**
 * SillyTavern Preset — imported preset metadata + raw JSON blob.
 * Stored in st_presets table; scoped per server_id.
 * Multiple presets may exist per server; only one is active at a time.
 */
export const stPresetSchema = z.object({
	preset_id: z.number().optional(),
	server_id: z.number(),
	preset_name: z.string(),
	raw_json: z.unknown(),
	is_active: z.boolean().default(false),
	created_at: z.date().optional(),
	updated_at: z.date().optional(),
});
export type StPresetRow = z.infer<typeof stPresetSchema>;

/**
 * SillyTavern Preset Node — individual toggleable prompt node parsed
 * from a preset's prompts array. Stored in st_preset_nodes table.
 * Nodes are ordered by node_order (matching the preset's prompt_order).
 */
export const stPresetNodeSchema = z.object({
	node_id: z.number().optional(),
	preset_id: z.number(),
	identifier: z.string(),
	name: z.string(),
	role: z.string().default("system"),
	content: z.string().default(""),
	is_marker: z.boolean().default(false),
	is_enabled: z.boolean().default(true),
	node_order: z.number(),
	injection_position: z.number().default(0),
	injection_depth: z.number().default(4),
	injection_order: z.number().default(100),
});
export type StPresetNodeRow = z.infer<typeof stPresetNodeSchema>;
