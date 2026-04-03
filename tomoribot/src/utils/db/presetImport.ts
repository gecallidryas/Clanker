/**
 * Preset Import Utilities
 * Handles importing and validating TomoriBot personality data
 */

import { sql } from "@/utils/db/client";
import { log } from "../misc/logger";
import {
  PRESET_EXPORT_VERSION,
  presetExportSchema,
  type PresetExportData,
  type ImportResult,
  type ValidationResult,
} from "../../types/preset/presetExport";
import {
  validateMemoryContent,
  validateAttributeAndDialogue,
} from "./memoryLimits";
import { validateTomoriConfigFields } from "./sqlSecurity";

function isUniqueViolation(error: unknown): boolean {
  return (
    typeof error === "object" &&
    error !== null &&
    "code" in error &&
    (error as { code?: string }).code === "23505"
  );
}

/**
 * Imports TomoriBot preset personality data, replacing existing personality
 * @param serverDiscId - Discord server ID to import preset for
 * @param importData - The validated preset export data to import
 * @param identityMode - preserve: keep/import lineage, fork: assign a fresh lineage
 * @returns ImportResult indicating success or failure with item counts
 */
export async function importPresetData(
  serverDiscId: string,
  importData: PresetExportData,
  identityMode: "preserve" | "fork" = "preserve",
): Promise<ImportResult> {
  try {
    // 1. Validate all array content for security
    // Use appropriate validation for each content type:
    // - Attributes: Use sample dialogue validation (2000 char limit) for long personality descriptions
    // - Sample dialogues: Use sample dialogue validation (2000 char limit)
    // - Trigger words: Use regular memory validation (256 char limit)

    // Check attribute_list (use 2000 char limit for detailed personality descriptions)
    for (const attribute of importData.attribute_list) {
      const validation = validateAttributeAndDialogue(attribute);
      if (!validation.isValid) {
        return {
          success: false,
          error: `commands.persona.import.error_invalid_attribute|${validation.error}`,
        };
      }
    }

    // Check sample_dialogues_in (uses higher limit for sample dialogues)
    for (const dialogue of importData.sample_dialogues_in) {
      const validation = validateAttributeAndDialogue(dialogue);
      if (!validation.isValid) {
        return {
          success: false,
          error: `commands.persona.import.error_invalid_dialogue_in|${validation.error}`,
        };
      }
    }

    // Check sample_dialogues_out (uses higher limit for sample dialogues)
    for (const dialogue of importData.sample_dialogues_out) {
      const validation = validateAttributeAndDialogue(dialogue);
      if (!validation.isValid) {
        return {
          success: false,
          error: `commands.persona.import.error_invalid_dialogue_out|${validation.error}`,
        };
      }
    }

    // Check trigger_words
    for (const triggerWord of importData.trigger_words) {
      const validation = validateMemoryContent(triggerWord);
      if (!validation.isValid) {
        return {
          success: false,
          error: `commands.persona.import.error_invalid_trigger_word|${validation.error}`,
        };
      }
    }

    // 2. Validate sample dialogues arrays match in length
    if (
      importData.sample_dialogues_in.length !==
      importData.sample_dialogues_out.length
    ) {
      return {
        success: false,
        error: "commands.persona.import.error_dialogue_mismatch",
      };
    }

    // 3. Validate trigger_words field for SQL security
    try {
      validateTomoriConfigFields(["trigger_words"]);
    } catch (error) {
      log.error("Config field validation failed during preset import:", error);
      return {
        success: false,
        error: "commands.persona.import.error_invalid_config",
      };
    }

    // 4. Get internal server ID and tomori ID (main persona only)
    const serverRows = await sql`
			SELECT s.server_id, t.tomori_id, t.persona_lineage_id
			FROM servers s
			JOIN tomoris t ON s.server_id = t.server_id
			WHERE s.server_disc_id = ${serverDiscId}
			AND t.is_alter = false
			LIMIT 1
		`;

    if (!serverRows.length) {
      return {
        success: false,
        error: "commands.persona.import.error_no_server_data",
      };
    }

    const serverId = serverRows[0].server_id;
    const mainTomoriId = serverRows[0].tomori_id;
    const importedLineageId = importData.persona_lineage_id ?? null;

    // 4.5. Enforce persona nickname uniqueness within this server (excluding current main persona)
    const conflictingNameRows = await sql<Array<{ tomori_id: number }>>`
			SELECT tomori_id
			FROM tomoris
			WHERE server_id = ${serverId}
			  AND tomori_id <> ${mainTomoriId}
			  AND lower(btrim(tomori_nickname)) = lower(btrim(${importData.tomori_nickname}))
			LIMIT 1
		`;
    if (conflictingNameRows.length > 0) {
      return {
        success: false,
        error: `commands.persona.import.error_name_conflict|${importData.tomori_nickname}`,
      };
    }

    // 5. Format arrays as PostgreSQL array literals for safe insertion
    const attributeArrayLiteral = `{${importData.attribute_list
      .map((item: string) => `"${item.replace(/(["\\])/g, "\\$1")}"`)
      .join(",")}}`;

    const dialoguesInArrayLiteral = `{${importData.sample_dialogues_in
      .map((item: string) => `"${item.replace(/(["\\])/g, "\\$1")}"`)
      .join(",")}}`;

    const dialoguesOutArrayLiteral = `{${importData.sample_dialogues_out
      .map((item: string) => `"${item.replace(/(["\\])/g, "\\$1")}"`)
      .join(",")}}`;

    const triggerWordsArrayLiteral = `{${importData.trigger_words
      .map((item: string) => `"${item.replace(/(["\\])/g, "\\$1")}"`)
      .join(",")}}`;
    const shouldUseImportedLineage =
      identityMode === "preserve" && importedLineageId !== null;

    // 5.5. Build NAI tags array literal for safe insertion
    const naiTagsArrayLiteral = `{${(importData.nai_tags ?? [])
      .map((item: string) => `"${item.replace(/(["\\])/g, "\\$1")}"`)
      .join(",")}}`;

    // 6. Update tomoris table with personality data, lineage behavior, and NovelAI fields
    try {
      await sql`
				UPDATE tomoris
				SET
					tomori_nickname = ${importData.tomori_nickname},
					attribute_list = ${attributeArrayLiteral}::text[],
					sample_dialogues_in = ${dialoguesInArrayLiteral}::text[],
					sample_dialogues_out = ${dialoguesOutArrayLiteral}::text[],
					persona_lineage_id = CASE
						WHEN ${identityMode} = 'fork' THEN nextval('persona_lineage_id_seq')
						WHEN ${shouldUseImportedLineage} THEN ${importedLineageId}::bigint
						ELSE persona_lineage_id
					END,
					nai_tags = ${naiTagsArrayLiteral}::text[],
					nai_char_ref_url = ${importData.nai_char_ref_url ?? null},
					nai_attg_author = ${importData.nai_attg_author ?? null},
					nai_attg_title = ${importData.nai_attg_title ?? null},
					nai_attg_tags = ${importData.nai_attg_tags ?? null},
					nai_attg_genre = ${importData.nai_attg_genre ?? null},
					nai_attg_stars = ${importData.nai_attg_stars ?? null}
				WHERE tomori_id = ${mainTomoriId}
			`;
    } catch (error) {
      if (isUniqueViolation(error)) {
        return {
          success: false,
          error: `commands.persona.import.error_name_conflict|${importData.tomori_nickname}`,
        };
      }
      throw error;
    }

    // 7. Update persona-scoped trigger words + optional persona prompt
    const importedPersonaPrompt =
      typeof importData.persona_prompt === "string"
        ? importData.persona_prompt
        : null;

    await sql`
			INSERT INTO persona_configs (tomori_id, trigger_words, persona_prompt)
			VALUES (
				${mainTomoriId},
				${triggerWordsArrayLiteral}::text[],
				${importedPersonaPrompt}
			)
			ON CONFLICT (tomori_id) DO UPDATE
			SET
				trigger_words = EXCLUDED.trigger_words,
				persona_prompt = EXCLUDED.persona_prompt
		`;

    await sql`
			UPDATE tomori_configs
			SET
				trigger_words = ${triggerWordsArrayLiteral}::text[]
			WHERE server_id = ${serverId}
		`;

    log.success(
      `Successfully imported preset for server ${serverDiscId}: ${importData.tomori_nickname}`,
    );

    return {
      success: true,
      itemsImported: {
        nickname: importData.tomori_nickname,
        attributeCount: importData.attribute_list.length,
        dialogueCount: importData.sample_dialogues_in.length,
        triggerWordCount: importData.trigger_words.length,
      },
    };
  } catch (error) {
    log.error(`Error importing preset data for server ${serverDiscId}:`, error);
    return {
      success: false,
      error: "commands.persona.import.error_import_failed",
    };
  }
}

/**
 * Validates and parses a preset import file
 * @param jsonData - The parsed JSON data from the PNG metadata
 * @returns Validation result with parsed data or error message
 */
export function validatePresetFile(jsonData: unknown): ValidationResult {
  // 1. Check if data is an object
  if (typeof jsonData !== "object" || jsonData === null) {
    return {
      valid: false,
      error: "commands.persona.import.error_not_json",
    };
  }

  // 2. Check version compatibility
  const version = (jsonData as { version?: string }).version;
  if (version !== PRESET_EXPORT_VERSION) {
    return {
      valid: false,
      error: `commands.persona.import.error_incompatible_version|${PRESET_EXPORT_VERSION}|${version || "unknown"}`,
    };
  }

  // 3. Check type field
  const type = (jsonData as { type?: string }).type;
  if (type !== "preset") {
    return {
      valid: false,
      error: `commands.persona.import.error_invalid_type|${type}`,
    };
  }

  // 4. Validate with Zod schema
  const validated = presetExportSchema.safeParse(jsonData);
  if (!validated.success) {
    log.error("Preset import validation failed:", validated.error);
    return {
      valid: false,
      error: "commands.persona.import.error_invalid_format",
    };
  }

  return {
    valid: true,
    data: validated.data.data,
  };
}
