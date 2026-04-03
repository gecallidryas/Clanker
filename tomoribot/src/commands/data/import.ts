import type {
  ChatInputCommandInteraction,
  Client,
  SlashCommandSubcommandBuilder,
  ModalSubmitInteraction,
} from "discord.js";
import { MessageFlags, EmbedBuilder } from "discord.js";
import { localizer } from "../../utils/text/localizer";
import { log, ColorCode } from "../../utils/misc/logger";
import {
  replyInfoEmbed,
  promptWithPaginatedModal,
  safeSelectOptionText,
} from "../../utils/discord/interactionHelper";
import type { UserRow } from "../../types/db/schema";
import { memoryGuard, IMPORT_LIMITS } from "../../utils/security/rateLimiter";
import { invalidateTomoriStateCache } from "../../utils/cache/tomoriStateCache";
import { invalidateUserCache } from "../../utils/cache/userCache";
import {
  validateImportFile,
  importPersonalData,
  importServerData,
  importPersonalMemories,
  importServerMemories,
  importPersonalSettings,
  importServerConfig,
  type ImportFileType,
} from "../../utils/db/dataImportV2";
import { loadAllPersonasForServer } from "@/utils/db/dbRead";
import type {
  PersonalExportData,
  ServerExportData,
  PersonalMemoriesExportData,
  ServerMemoriesExportData,
  PersonalSettingsExportData,
  ServerConfigOnlyExportData,
} from "../../types/db/dataExport";
import type { SelectOption } from "../../types/discord/modal";

const IMPORT_PERSONA_MODAL_ID = "data_import_persona_modal";
const IMPORT_PERSONA_SELECT_ID = "persona_select";
const IMPORT_GLOBAL_TARGET_VALUE = "global";

function isMemoryRelatedImportType(type: ImportFileType): boolean {
  return (
    type === "personal_memories" ||
    type === "global_personal_memories" ||
    type === "server_memories" ||
    type === "personal" ||
    type === "server"
  );
}

function isServerRelatedImportType(type: ImportFileType): boolean {
  return (
    type === "server_memories" || type === "server_config" || type === "server"
  );
}

function getLocalizedImportTypeName(
  locale: string,
  importType: ImportFileType,
): string {
  switch (importType) {
    case "personal_memories":
      return localizer(
        locale,
        "commands.data.export.type_choice_persona_personal_memories",
      );
    case "server_memories":
      return localizer(
        locale,
        "commands.data.export.type_choice_persona_server_memories",
      );
    case "personal_settings":
      return localizer(
        locale,
        "commands.data.export.type_choice_personal_settings",
      );
    case "server_config":
      return localizer(
        locale,
        "commands.data.export.type_choice_server_config",
      );
    case "global_personal_memories":
      return localizer(
        locale,
        "commands.data.export.type_choice_global_personal_memories",
      );
    case "personal":
      return localizer(locale, "commands.data.import.legacy_personal_label");
    case "server":
      return localizer(locale, "commands.data.import.legacy_server_label");
    default:
      return importType;
  }
}

/**
 * Helper function to localize error messages from utility functions
 * Handles both simple locale keys and keys with pipe-separated variables
 * @param locale - User's locale
 * @param errorString - Error string (locale key or key|var1|var2...)
 * @returns Localized error message
 */
function localizeError(locale: string, errorString: string): string {
  const parts = errorString.split("|");
  const key = parts[0];

  if (parts.length === 1) {
    // Simple locale key without variables
    return localizer(locale, key);
  }

  // Handle keys with variables
  if (key === "commands.data.import.error_invalid_memory") {
    return localizer(locale, key, { details: parts[1] });
  }
  if (key === "commands.data.import.error_invalid_server_memory") {
    return localizer(locale, key, { details: parts[1] });
  }
  if (key === "commands.data.import.error_incompatible_version") {
    return localizer(locale, key, { expected: parts[1], actual: parts[2] });
  }
  if (key === "commands.data.import.error_unknown_type") {
    return localizer(locale, key, { type: parts[1] });
  }

  // Fallback: just localize the key
  return localizer(locale, key);
}

// Maximum file size for imports (uses centralized constant)
const MAX_FILE_SIZE = IMPORT_LIMITS.MAX_DATA_IMPORT_SIZE_MB * 1024 * 1024;

/**
 * Configure the 'import' subcommand
 */
export const configureSubcommand = (
  subcommand: SlashCommandSubcommandBuilder,
) =>
  subcommand
    .setName("import")
    .setDescription(localizer("en-US", "commands.data.import.description"))
    .addAttachmentOption((option) =>
      option
        .setName("file")
        .setDescription(
          localizer("en-US", "commands.data.import.file_description"),
        )
        .setRequired(true),
    )
    .addStringOption((option) =>
      option
        .setName("confirmation")
        .setDescription(
          localizer("en-US", "commands.data.import.confirmation_description"),
        )
        .setRequired(true)
        .addChoices(
          {
            name: localizer(
              "en-US",
              "commands.data.import.confirmation_choice_yes",
            ),
            value: "yes",
          },
          {
            name: localizer(
              "en-US",
              "commands.data.import.confirmation_choice_no",
            ),
            value: "no",
          },
        ),
    );

/**
 * Executes the 'import' command
 * Imports user or server data from an uploaded JSON file
 * @param client - The Discord client instance
 * @param interaction - The chat input command interaction
 * @param userData - The user data for the invoking user
 * @param locale - The user's preferred locale
 */
export async function execute(
  _client: Client,
  interaction: ChatInputCommandInteraction,
  _userData: UserRow,
  locale: string,
): Promise<void> {
  const serverDiscId = interaction.guild?.id ?? interaction.user.id;
  let responseInteraction:
    | ChatInputCommandInteraction
    | ModalSubmitInteraction = interaction;

  try {
    const confirmation = interaction.options.getString("confirmation", true);
    if (confirmation !== "yes") {
      await replyInfoEmbed(interaction, locale, {
        titleKey: "commands.data.import.cancelled_title",
        descriptionKey: "commands.data.import.cancelled_description",
        color: ColorCode.INFO,
        flags: MessageFlags.Ephemeral,
      });
      return;
    }

    const attachment = interaction.options.getAttachment("file", true);

    if (!attachment.name.endsWith(".json")) {
      await replyInfoEmbed(interaction, locale, {
        titleKey: "commands.data.import.invalid_file_type_title",
        descriptionKey: "commands.data.import.invalid_file_type_description",
        color: ColorCode.ERROR,
        flags: MessageFlags.Ephemeral,
      });
      return;
    }

    if (attachment.size > MAX_FILE_SIZE) {
      await replyInfoEmbed(interaction, locale, {
        titleKey: "commands.data.import.file_too_large_title",
        descriptionKey: "commands.data.import.file_too_large_description",
        color: ColorCode.ERROR,
        flags: MessageFlags.Ephemeral,
      });
      return;
    }

    let jsonData: unknown;
    const controller = new AbortController();
    const timeoutId = setTimeout(() => controller.abort(), 10000);

    try {
      const response = await fetch(attachment.url, {
        signal: controller.signal,
      });
      clearTimeout(timeoutId);

      if (!response.ok) {
        throw new Error(`HTTP ${response.status}`);
      }

      const textContent = await response.text();
      jsonData = JSON.parse(textContent);
    } catch (error) {
      clearTimeout(timeoutId);

      if (error instanceof Error && error.name === "AbortError") {
        log.warn("Data import download timed out");
        await replyInfoEmbed(interaction, locale, {
          titleKey: "commands.data.import.failed_title",
          descriptionKey: "commands.data.import.error_download_timeout",
          color: ColorCode.ERROR,
          flags: MessageFlags.Ephemeral,
        });
        return;
      }

      log.error("Failed to download or parse import file:", error as Error);
      await replyInfoEmbed(interaction, locale, {
        titleKey: "commands.data.import.parse_failed_title",
        descriptionKey: "commands.data.import.parse_failed_description",
        color: ColorCode.ERROR,
        flags: MessageFlags.Ephemeral,
      });
      return;
    }

    const validation = validateImportFile(jsonData);
    if (!validation.valid || !validation.type || !validation.data) {
      await interaction.reply({
        embeds: [
          new EmbedBuilder()
            .setTitle(
              localizer(locale, "commands.data.import.invalid_file_title"),
            )
            .setDescription(
              validation.error
                ? localizeError(locale, validation.error)
                : localizer(
                    locale,
                    "commands.data.import.invalid_file_description",
                  ),
            )
            .setColor(ColorCode.ERROR),
        ],
        flags: MessageFlags.Ephemeral,
      });
      return;
    }

    const importType = validation.type;
    const importData = validation.data;

    if (isServerRelatedImportType(importType) && interaction.guild) {
      const hasPermission =
        interaction.memberPermissions?.has("ManageGuild") ?? false;
      if (!hasPermission) {
        await replyInfoEmbed(interaction, locale, {
          titleKey: "commands.data.import.no_permission_title",
          descriptionKey: "commands.data.import.no_permission_description",
          color: ColorCode.ERROR,
          flags: MessageFlags.Ephemeral,
        });
        return;
      }
    }

    let selectedTomoriId: number | undefined;
    let selectedPersonaLineageId = 0;
    let selectedMemoryTargetValue: string | undefined;

    if (isMemoryRelatedImportType(importType)) {
      const personas = await loadAllPersonasForServer(serverDiscId);
      const personaSelectOptions: SelectOption[] = [
        {
          label: localizer(locale, "commands.data.import.global_option_label"),
          value: IMPORT_GLOBAL_TARGET_VALUE,
          description: localizer(
            locale,
            "commands.data.import.global_option_description",
          ),
        },
        ...personas
          .filter((persona) => persona.tomori_id !== undefined)
          .map((persona) => ({
            label: safeSelectOptionText(persona.tomori_nickname),
            value: persona.tomori_id?.toString() ?? "",
            description: persona.is_alter
              ? localizer(
                  locale,
                  "commands.data.import.alter_persona_description",
                )
              : localizer(
                  locale,
                  "commands.data.import.main_persona_description",
                ),
          }))
          .filter((option) => option.value !== ""),
      ];

      const personaModalResult = await promptWithPaginatedModal(
        interaction,
        locale,
        {
          modalCustomId: IMPORT_PERSONA_MODAL_ID,
          modalTitleKey: "commands.data.import.persona_modal_title",
          components: [
            {
              customId: IMPORT_PERSONA_SELECT_ID,
              labelKey: "commands.data.import.persona_select_label",
              descriptionKey: "commands.data.import.persona_select_description",
              placeholder: "commands.data.import.persona_select_placeholder",
              required: true,
              options: personaSelectOptions,
            },
          ],
        },
      );
      if (personaModalResult.outcome !== "submit") {
        log.info(
          `Data import persona modal ${personaModalResult.outcome} for user ${interaction.user.id}`,
        );
        return;
      }

      const modalSubmitInteraction = personaModalResult.interaction;
      if (!modalSubmitInteraction) {
        return;
      }
      responseInteraction = modalSubmitInteraction;
      selectedMemoryTargetValue =
        personaModalResult.values?.[IMPORT_PERSONA_SELECT_ID];

      if (
        selectedMemoryTargetValue &&
        selectedMemoryTargetValue !== IMPORT_GLOBAL_TARGET_VALUE
      ) {
        const selectedPersona =
          personas.find(
            (persona) =>
              persona.tomori_id?.toString() === selectedMemoryTargetValue,
          ) ?? null;
        if (!selectedPersona) {
          await replyInfoEmbed(responseInteraction, locale, {
            titleKey: "general.errors.invalid_option_title",
            descriptionKey: "general.errors.invalid_option_description",
            color: ColorCode.ERROR,
          });
          return;
        }
        selectedTomoriId = selectedPersona.tomori_id;
        selectedPersonaLineageId = selectedPersona.persona_lineage_id ?? 0;
      }
    }

    await responseInteraction.deferReply({ flags: MessageFlags.Ephemeral });

    const memCheck = memoryGuard.checkMemory();
    if (memCheck.status === "critical") {
      await responseInteraction.editReply({
        embeds: [
          new EmbedBuilder()
            .setTitle(
              localizer(locale, "rate_limit.error_memory_critical_title"),
            )
            .setDescription(
              localizer(locale, "rate_limit.error_memory_critical_description"),
            )
            .setColor(ColorCode.ERROR),
        ],
      });
      return;
    }

    let importResult:
      | Awaited<ReturnType<typeof importPersonalData>>
      | Awaited<ReturnType<typeof importServerData>>
      | Awaited<ReturnType<typeof importPersonalMemories>>
      | Awaited<ReturnType<typeof importServerMemories>>
      | Awaited<ReturnType<typeof importPersonalSettings>>
      | Awaited<ReturnType<typeof importServerConfig>>;

    switch (importType) {
      case "personal_memories":
      case "global_personal_memories": {
        const personalMemoriesData = importData as PersonalMemoriesExportData;
        const targetLineageId =
          selectedMemoryTargetValue === IMPORT_GLOBAL_TARGET_VALUE
            ? 0
            : selectedPersonaLineageId;
        importResult = await importPersonalMemories(
          interaction.user.id,
          personalMemoriesData.personal_memories,
          targetLineageId,
        );
        break;
      }
      case "server_memories": {
        const serverMemoriesData = importData as ServerMemoriesExportData;
        importResult =
          selectedMemoryTargetValue === IMPORT_GLOBAL_TARGET_VALUE
            ? await importServerMemories(
                serverDiscId,
                serverMemoriesData.server_memories,
                { mode: "global" },
              )
            : await importServerMemories(
                serverDiscId,
                serverMemoriesData.server_memories,
                { mode: "persona", tomoriId: selectedTomoriId },
              );
        break;
      }
      case "personal_settings": {
        const personalSettingsData = importData as PersonalSettingsExportData;
        importResult = await importPersonalSettings(
          interaction.user.id,
          personalSettingsData,
        );
        break;
      }
      case "server_config": {
        const serverConfigData = importData as ServerConfigOnlyExportData;
        importResult = await importServerConfig(
          serverDiscId,
          serverConfigData.config,
        );
        break;
      }
      case "personal": {
        const personalData = importData as PersonalExportData;
        const targetLineageId =
          selectedMemoryTargetValue === IMPORT_GLOBAL_TARGET_VALUE
            ? 0
            : selectedPersonaLineageId;
        importResult = await importPersonalData(
          interaction.user.id,
          personalData,
          targetLineageId,
        );
        break;
      }
      case "server": {
        const serverData = importData as ServerExportData;
        if (selectedMemoryTargetValue === IMPORT_GLOBAL_TARGET_VALUE) {
          const configResult = await importServerConfig(
            serverDiscId,
            serverData.config,
          );
          if (!configResult.success) {
            importResult = configResult;
            break;
          }
          const memoriesResult = await importServerMemories(
            serverDiscId,
            serverData.server_memories,
            { mode: "global" },
          );
          importResult = memoriesResult.success
            ? {
                success: true,
                itemsImported: {
                  memoriesCount:
                    memoriesResult.itemsImported?.memoriesCount ?? 0,
                  configFieldsCount:
                    configResult.itemsImported?.configFieldsCount ?? 0,
                },
              }
            : memoriesResult;
        } else {
          importResult = await importServerData(
            serverDiscId,
            serverData,
            selectedTomoriId,
          );
        }
        break;
      }
      default:
        await responseInteraction.editReply({
          embeds: [
            new EmbedBuilder()
              .setTitle(
                localizer(locale, "general.errors.invalid_option_title"),
              )
              .setDescription(
                localizer(locale, "general.errors.invalid_option_description"),
              )
              .setColor(ColorCode.ERROR),
          ],
        });
        return;
    }

    if (!importResult.success) {
      await responseInteraction.editReply({
        embeds: [
          new EmbedBuilder()
            .setTitle(localizer(locale, "commands.data.import.failed_title"))
            .setDescription(
              importResult.error
                ? localizeError(locale, importResult.error)
                : localizer(locale, "commands.data.import.failed_description"),
            )
            .setColor(ColorCode.ERROR),
        ],
      });
      return;
    }

    if (
      importType === "personal" ||
      importType === "personal_memories" ||
      importType === "global_personal_memories" ||
      importType === "personal_settings"
    ) {
      invalidateUserCache(interaction.user.id);
    }
    if (
      importType === "server" ||
      importType === "server_memories" ||
      importType === "server_config"
    ) {
      invalidateTomoriStateCache(serverDiscId);
    }

    const memoriesCount = importResult.itemsImported?.memoriesCount || 0;
    const configFieldsCount =
      importResult.itemsImported?.configFieldsCount || 0;
    const localizedType = getLocalizedImportTypeName(locale, importType);

    await responseInteraction.editReply({
      embeds: [
        new EmbedBuilder()
          .setTitle(localizer(locale, "commands.data.import.success_title"))
          .setDescription(
            localizer(locale, "commands.data.import.success_description", {
              type: localizedType,
              memories_count: memoriesCount,
              config_count: configFieldsCount,
            }),
          )
          .setColor(ColorCode.SUCCESS),
      ],
    });
  } catch (error) {
    log.error("Error executing import command:", error, {
      errorType: "CommandExecutionError",
      metadata: { commandName: "import" },
    });

    // If we haven't replied yet, reply with error
    if (!responseInteraction.replied && !responseInteraction.deferred) {
      await replyInfoEmbed(responseInteraction, locale, {
        titleKey: "general.errors.unknown_error_title",
        descriptionKey: "general.errors.unknown_error_description",
        color: ColorCode.ERROR,
        flags: MessageFlags.Ephemeral,
      });
    } else {
      await responseInteraction.editReply({
        embeds: [
          new EmbedBuilder()
            .setTitle(localizer(locale, "general.errors.unknown_error_title"))
            .setDescription(
              localizer(locale, "general.errors.unknown_error_description"),
            )
            .setColor(ColorCode.ERROR),
        ],
      });
    }
  }
}
