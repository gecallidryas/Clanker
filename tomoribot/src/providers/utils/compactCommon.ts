/**
 * Shared schemas and utilities for conversation compaction generators.
 *
 * All providers that support conversation compaction (OpenRouter, Custom, DeepSeek,
 * NVIDIA, ZAI, Zaicoding) use the same roleplay summary schema. This module provides
 * a single source of truth for the JSON schema and Zod validation schema, so each
 * provider's compactGenerator.ts only needs to handle the provider-specific HTTP wiring.
 */
import { z } from "zod";

/**
 * JSON Schema for the roleplay summary structured output.
 *
 * Used by `response_format: { type: "json_schema", json_schema: { ... } }`
 * (OpenRouter, NVIDIA) or injected into the system prompt for providers
 * that only support `json_object` mode (DeepSeek, ZAI, Custom).
 */
export function buildRoleplaySchema() {
	return {
		type: "object" as const,
		properties: {
			overall_scene_summary: { type: "string" as const },
			characters: {
				type: "array" as const,
				items: {
					type: "object" as const,
					properties: {
						name: { type: "string" as const },
						current_goals: { type: "string" as const },
						emotional_status: { type: "string" as const },
						physical_status: { type: "string" as const },
						appearance_clothing: { type: "string" as const },
						inventory: { type: "string" as const },
					},
					required: [
						"name",
						"current_goals",
						"emotional_status",
						"physical_status",
						"appearance_clothing",
						"inventory",
					],
				},
			},
		},
		required: ["overall_scene_summary", "characters"],
	};
}

/**
 * Zod schema for validating the roleplay summary response.
 *
 * Used by providers that validate locally with Zod (DeepSeek, ZAI, Custom)
 * rather than relying on strict server-side schema enforcement.
 */
export const CompactRoleplaySummarySchema = z.object({
	overall_scene_summary: z.string(),
	characters: z.array(
		z.object({
			name: z.string(),
			current_goals: z.string(),
			emotional_status: z.string(),
			physical_status: z.string(),
			appearance_clothing: z.string(),
			inventory: z.string(),
		}),
	),
});
