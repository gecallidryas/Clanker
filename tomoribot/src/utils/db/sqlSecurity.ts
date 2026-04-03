/**
 * SQL Security Utilities
 *
 * This module provides security utilities for dynamic SQL query construction,
 * particularly for validating field names in UPDATE statements to prevent SQL injection.
 *
 * Field whitelists are automatically derived from Zod schemas to ensure consistency
 * and maintainability - when schemas change, security whitelists update automatically.
 */

import type {
  UserRow,
  TomoriRow,
  TomoriConfigRow,
} from "../../types/db/schema";
import { log } from "../misc/logger";

// Extract allowed field names from Zod schemas
// These exclude auto-managed fields (IDs, timestamps) that shouldn't be in dynamic updates
const ALLOWED_USER_FIELDS = new Set<keyof UserRow>([
  "user_disc_id",
  "user_nickname",
  "language_pref",
  "registration_locale", // Static field (set once at registration, but whitelisted for safety)
  "personal_memories",
  "privacy_level",
  "nai_char_tags",
  "nai_char_ref_url",
  "impersonation_prompt",
  "shortterm_cache_crossserver_opt_in",
  // Exclude: user_id (primary key), created_at, updated_at (auto-managed)
]);

const ALLOWED_TOMORI_FIELDS = new Set<keyof TomoriRow>([
  "server_id",
  "tomori_nickname",
  "attribute_list",
  "sample_dialogues_in",
  "sample_dialogues_out",
  "autoch_counter",
  "autoch_next_target",
  "nai_tags",
  "nai_char_ref_url",
  "elevenlabs_voice_id",
  "elevenlabs_voice_name",
  "nai_attg_author",
  "nai_attg_title",
  "nai_attg_tags",
  "nai_attg_genre",
  "nai_attg_stars",
  "persona_lineage_id",
  "is_alter",
  "webhook_avatar_url",
  "alter_triggers",
  // Exclude: tomori_id (primary key), created_at, updated_at (auto-managed)
]);

const ALLOWED_TOMORI_CONFIG_FIELDS = new Set<keyof TomoriConfigRow>([
  "llm_id",
  "embedding_model_id",
  "llm_temperature",
  "llm_top_p",
  "llm_top_k",
  "llm_frequency_penalty",
  "llm_presence_penalty",
  "llm_min_p",
  "llm_logit_biases",
  "api_key",
  "key_version",
  "trigger_words",
  "autoch_disc_ids",
  "autoch_threshold",
  "autoch_threshold_max",
  "message_fetch_limit",
  "server_memteaching_enabled",
  "attribute_memteaching_enabled",
  "sampledialogue_memteaching_enabled",
  "self_teaching_enabled",
  "web_search_enabled",
  "personal_memories_enabled",
  "humanizer_degree",
  "emoji_usage_enabled",
  "sticker_usage_enabled",
  "imagegen_enabled",
  "timezone_offset",
  "system_prompt",
	"nai_preset_name",
	"rp_channel_ids",
	"welcome_channel_disc_id",
	"thought_log_channel_disc_id",
	"welcome_prompt",
	"welcome_persona_id",
	"self_reply_limit",
  "triggered_persona_limit",
  "diffusion_model_id",
  "nai_diffusion_model_id",
  "pin_message_enabled",
  "hide_respond_embed",
  "hide_impersonation_embeds",
  "self_debug_enabled",
  "uncensor_injection_enabled",
  "uncensor_unicode_space_enabled",
  "uncensor_sanitize_enabled",
  "videogen_enabled",
  "cooldown_type",
  "cooldown_length",
  "custom_endpoint_url",
  "custom_model_name",
  "nai_exclusive_imggen",
  "nai_style_tags",
  "nai_negative_tags",
  "nai_sampler",
  "nai_steps",
  "nai_scale",
  "nai_noise_schedule",
  "nai_cfg_rescale",
  "fallback_llm_ids",
  // Exclude: tomori_config_id, tomori_id (keys), created_at, updated_at (auto-managed)
]);

/**
 * Validates that all provided field names are whitelisted for User table updates.
 * Throws an error if any field is not allowed to prevent SQL injection.
 *
 * @param fields - Array of field names to validate
 * @throws Error if any field name is not whitelisted
 */
export function validateUserFields(fields: string[]): void {
  for (const field of fields) {
    if (!ALLOWED_USER_FIELDS.has(field as keyof UserRow)) {
      const error = `Security violation: Invalid field name '${field}' for User table update. Allowed fields: ${Array.from(ALLOWED_USER_FIELDS).join(", ")}`;
      log.error(error);
      throw new Error(error);
    }
  }
}

/**
 * Validates that all provided field names are whitelisted for Tomori table updates.
 * Throws an error if any field is not allowed to prevent SQL injection.
 *
 * @param fields - Array of field names to validate
 * @throws Error if any field name is not whitelisted
 */
export function validateTomoriFields(fields: string[]): void {
  for (const field of fields) {
    if (!ALLOWED_TOMORI_FIELDS.has(field as keyof TomoriRow)) {
      const error = `Security violation: Invalid field name '${field}' for Tomori table update. Allowed fields: ${Array.from(ALLOWED_TOMORI_FIELDS).join(", ")}`;
      log.error(error);
      throw new Error(error);
    }
  }
}

/**
 * Validates that all provided field names are whitelisted for TomoriConfig table updates.
 * Throws an error if any field is not allowed to prevent SQL injection.
 *
 * @param fields - Array of field names to validate
 * @throws Error if any field name is not whitelisted
 */
export function validateTomoriConfigFields(fields: string[]): void {
  for (const field of fields) {
    if (!ALLOWED_TOMORI_CONFIG_FIELDS.has(field as keyof TomoriConfigRow)) {
      const error = `Security violation: Invalid field name '${field}' for TomoriConfig table update. Allowed fields: ${Array.from(ALLOWED_TOMORI_CONFIG_FIELDS).join(", ")}`;
      log.error(error);
      throw new Error(error);
    }
  }
}

/**
 * Get all allowed field names for User table (for documentation/debugging purposes)
 */
export function getAllowedUserFields(): readonly string[] {
  return Array.from(ALLOWED_USER_FIELDS);
}

/**
 * Get all allowed field names for Tomori table (for documentation/debugging purposes)
 */
export function getAllowedTomoriFields(): readonly string[] {
  return Array.from(ALLOWED_TOMORI_FIELDS);
}

/**
 * Get all allowed field names for TomoriConfig table (for documentation/debugging purposes)
 */
export function getAllowedTomoriConfigFields(): readonly string[] {
  return Array.from(ALLOWED_TOMORI_CONFIG_FIELDS);
}
