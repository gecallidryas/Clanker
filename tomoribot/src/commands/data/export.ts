import type {
  ChatInputCommandInteraction,
  Client,
  SlashCommandSubcommandBuilder,
  ModalSubmitInteraction,
} from "discord.js";
import { AttachmentBuilder, MessageFlags, EmbedBuilder } from "discord.js";
import { localizer } from "../../utils/text/localizer";
import { log, ColorCode } from "../../utils/misc/logger";
import {
  replyInfoEmbed,
  promptWithPaginatedModal,
  safeSelectOptionText,
} from "../../utils/discord/interactionHelper";
import type { UserRow } from "../../types/db/schema";
import {
  exportPersonaPersonalMemories,
  exportPersonaServerMemories,
  exportPersonalSettings,
  exportServerConfig,
  exportGlobalPersonalMemories,
} from "../../utils/db/dataExport";
import { loadAllPersonasForServer } from "@/utils/db/dbRead";
import type { SelectOption } from "../../types/discord/modal";

const EXPORT_PERSONA_MODAL_ID = "data_export_persona_modal";
const EXPORT_PERSONA_SELECT_ID = "persona_select";
const EXPORT_TYPE_PERSONA_PERSONAL_MEMORIES = "persona_personal_memories";
const EXPORT_TYPE_PERSONA_SERVER_MEMORIES = "persona_server_memories";
const EXPORT_TYPE_PERSONAL_SETTINGS = "personal_settings";
const EXPORT_TYPE_SERVER_CONFIG = "server_config";
const EXPORT_TYPE_GLOBAL_PERSONAL_MEMORIES = "global_personal_memories";

function getLocalizedExportTypeName(
  locale: string,
  exportType: string,
): string {
  switch (exportType) {
    case EXPORT_TYPE_PERSONA_PERSONAL_MEMORIES:
      return localizer(
        locale,
        "commands.data.export.type_choice_persona_personal_memories",
      );
    case EXPORT_TYPE_PERSONA_SERVER_MEMORIES:
      return localizer(
        locale,
        "commands.data.export.type_choice_persona_server_memories",
      );
    case EXPORT_TYPE_PERSONAL_SETTINGS:
      return localizer(
        locale,
        "commands.data.export.type_choice_personal_settings",
      );
    case EXPORT_TYPE_SERVER_CONFIG:
      return localizer(
        locale,
        "commands.data.export.type_choice_server_config",
      );
    case EXPORT_TYPE_GLOBAL_PERSONAL_MEMORIES:
      return localizer(
        locale,
        "commands.data.export.type_choice_global_personal_memories",
      );
    default:
      return exportType;
  }
}

/**
 * Configure the 'export' subcommand
 */
export const configureSubcommand = (
  subcommand: SlashCommandSubcommandBuilder,
) =>
  subcommand
    .setName("export")
    .setDescription(localizer("en-US", "commands.data.export.description"))
    .addStringOption((option) =>
      option
        .setName("type")
        .setDescription(
          localizer("en-US", "commands.data.export.type_description"),
        )
        .setRequired(true)
        .addChoices(
          {
            name: localizer(
              "en-US",
              "commands.data.export.type_choice_persona_personal_memories",
            ),
            value: EXPORT_TYPE_PERSONA_PERSONAL_MEMORIES,
          },
          {
            name: localizer(
              "en-US",
              "commands.data.export.type_choice_persona_server_memories",
            ),
            value: EXPORT_TYPE_PERSONA_SERVER_MEMORIES,
          },
          {
            name: localizer(
              "en-US",
              "commands.data.export.type_choice_personal_settings",
            ),
            value: EXPORT_TYPE_PERSONAL_SETTINGS,
          },
          {
            name: localizer(
              "en-US",
              "commands.data.export.type_choice_server_config",
            ),
            value: EXPORT_TYPE_SERVER_CONFIG,
          },
          {
            name: localizer(
              "en-US",
              "commands.data.export.type_choice_global_personal_memories",
            ),
            value: EXPORT_TYPE_GLOBAL_PERSONAL_MEMORIES,
          },
        ),
    );

/**
 * Executes the 'export' command
 * Exports user or server data to a JSON file and sends it via DM
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
  const exportType = interaction.options.getString("type", true);
  const serverDiscId = interaction.guild?.id ?? interaction.user.id;
  let responseInteraction:
    | ChatInputCommandInteraction
    | ModalSubmitInteraction = interaction;

  try {
    let targetTomoriId: number | undefined;
    let targetPersonaLineageId = 0;
    let targetPersonaNickname: string | null = null;

    const needsPersonaSelection =
      exportType === EXPORT_TYPE_PERSONA_PERSONAL_MEMORIES ||
      exportType === EXPORT_TYPE_PERSONA_SERVER_MEMORIES;

    if (needsPersonaSelection) {
      const personas = await loadAllPersonasForServer(serverDiscId);
      const personaSelectOptions: SelectOption[] = personas
        .filter((persona) => persona.tomori_id !== undefined)
        .map((persona) => ({
          label: safeSelectOptionText(persona.tomori_nickname),
          value: persona.tomori_id?.toString() ?? "",
          description: persona.is_alter
            ? localizer(
                locale,
                "commands.data.export.alter_persona_description",
              )
            : localizer(
                locale,
                "commands.data.export.main_persona_description",
              ),
        }))
        .filter((option) => option.value !== "");
      if (personaSelectOptions.length === 0) {
        await replyInfoEmbed(interaction, locale, {
          titleKey: "general.errors.invalid_option_title",
          descriptionKey: "general.errors.invalid_option_description",
          color: ColorCode.ERROR,
          flags: MessageFlags.Ephemeral,
        });
        return;
      }

      const personaModalResult = await promptWithPaginatedModal(
        interaction,
        locale,
        {
          modalCustomId: EXPORT_PERSONA_MODAL_ID,
          modalTitleKey: "commands.data.export.persona_modal_title",
          components: [
            {
              customId: EXPORT_PERSONA_SELECT_ID,
              labelKey: "commands.data.export.persona_select_label",
              descriptionKey: "commands.data.export.persona_select_description",
              placeholder: "commands.data.export.persona_select_placeholder",
              required: true,
              options: personaSelectOptions,
            },
          ],
        },
      );
      if (personaModalResult.outcome !== "submit") {
        log.info(
          `Data export persona modal ${personaModalResult.outcome} for user ${interaction.user.id}`,
        );
        return;
      }

      const modalSubmitInteraction = personaModalResult.interaction;
      if (!modalSubmitInteraction) {
        return;
      }
      responseInteraction = modalSubmitInteraction;
      const selectedPersonaId =
        personaModalResult.values?.[EXPORT_PERSONA_SELECT_ID];
      const selectedPersona =
        personas.find(
          (persona) => persona.tomori_id?.toString() === selectedPersonaId,
        ) ?? null;
      if (!selectedPersona) {
        await replyInfoEmbed(responseInteraction, locale, {
          titleKey: "general.errors.invalid_option_title",
          descriptionKey: "general.errors.invalid_option_description",
          color: ColorCode.ERROR,
        });
        return;
      }

      targetTomoriId = selectedPersona.tomori_id;
      targetPersonaLineageId = selectedPersona.persona_lineage_id ?? 0;
      targetPersonaNickname = selectedPersona.tomori_nickname;
    }

    const requiresServerPermission =
      exportType === EXPORT_TYPE_PERSONA_SERVER_MEMORIES ||
      exportType === EXPORT_TYPE_SERVER_CONFIG;
    if (requiresServerPermission && interaction.guild) {
      const hasPermission =
        interaction.memberPermissions?.has("ManageGuild") ?? false;
      if (!hasPermission) {
        await replyInfoEmbed(responseInteraction, locale, {
          titleKey: "commands.data.export.no_permission_title",
          descriptionKey: "commands.data.export.no_permission_description",
          color: ColorCode.ERROR,
          flags: MessageFlags.Ephemeral,
        });
        return;
      }
    }

    await responseInteraction.deferReply({ flags: MessageFlags.Ephemeral });

    let exportResult: Awaited<ReturnType<typeof exportPersonalSettings>>;
    let filename: string;
    const safeSlug = (targetPersonaNickname ?? "global")
      .replace(/[^a-zA-Z0-9-_]/g, "_")
      .slice(0, 32);
    const timestamp = Date.now();

    switch (exportType) {
      case EXPORT_TYPE_PERSONA_PERSONAL_MEMORIES:
        exportResult = await exportPersonaPersonalMemories(
          interaction.user.id,
          targetPersonaLineageId,
        );
        filename = `tomori-personal-memories-${safeSlug}-${interaction.user.id}-${timestamp}.json`;
        break;
      case EXPORT_TYPE_PERSONA_SERVER_MEMORIES:
        if (!targetTomoriId) {
          await responseInteraction.editReply({
            embeds: [
              new EmbedBuilder()
                .setTitle(
                  localizer(locale, "general.errors.invalid_option_title"),
                )
                .setDescription(
                  localizer(
                    locale,
                    "general.errors.invalid_option_description",
                  ),
                )
                .setColor(ColorCode.ERROR),
            ],
          });
          return;
        }
        exportResult = await exportPersonaServerMemories(
          serverDiscId,
          targetTomoriId,
        );
        filename = `tomori-server-memories-${safeSlug}-${serverDiscId}-${timestamp}.json`;
        break;
      case EXPORT_TYPE_PERSONAL_SETTINGS:
        exportResult = await exportPersonalSettings(interaction.user.id);
        filename = `tomori-personal-settings-${interaction.user.id}-${timestamp}.json`;
        break;
      case EXPORT_TYPE_SERVER_CONFIG:
        exportResult = await exportServerConfig(serverDiscId);
        filename = `tomori-server-config-${serverDiscId}-${timestamp}.json`;
        break;
      case EXPORT_TYPE_GLOBAL_PERSONAL_MEMORIES:
        exportResult = await exportGlobalPersonalMemories(interaction.user.id);
        filename = `tomori-global-personal-memories-${interaction.user.id}-${timestamp}.json`;
        break;
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

    if (!exportResult.success || !exportResult.data) {
      await responseInteraction.editReply({
        embeds: [
          new EmbedBuilder()
            .setTitle(localizer(locale, "commands.data.export.failed_title"))
            .setDescription(
              exportResult.error
                ? localizer(locale, exportResult.error)
                : localizer(locale, "commands.data.export.failed_description"),
            )
            .setColor(ColorCode.ERROR),
        ],
      });
      return;
    }

    const jsonString = JSON.stringify(exportResult.data, null, 2);
    const attachment = new AttachmentBuilder(Buffer.from(jsonString, "utf-8"), {
      name: filename,
    });

    try {
      const localizedType = getLocalizedExportTypeName(locale, exportType);
      await interaction.user.send({
        embeds: [
          new EmbedBuilder()
            .setTitle(localizer(locale, "commands.data.export.dm_title"))
            .setDescription(
              localizer(locale, "commands.data.export.dm_description", {
                type: localizedType,
              }),
            )
            .setColor(ColorCode.INFO),
        ],
        files: [attachment],
      });

      await responseInteraction.editReply({
        embeds: [
          new EmbedBuilder()
            .setTitle(localizer(locale, "commands.data.export.success_title"))
            .setDescription(
              localizer(locale, "commands.data.export.success_description", {
                type: localizedType,
              }),
            )
            .setColor(ColorCode.SUCCESS),
        ],
      });
    } catch (dmError) {
      log.warn(
        `Failed to send export DM to user ${interaction.user.id}:`,
        dmError as Error,
      );
      await responseInteraction.editReply({
        embeds: [
          new EmbedBuilder()
            .setTitle(localizer(locale, "commands.data.export.dm_failed_title"))
            .setDescription(
              localizer(locale, "commands.data.export.dm_failed_description"),
            )
            .setColor(ColorCode.ERROR),
        ],
      });
    }
  } catch (error) {
    log.error("Error executing export command:", error, {
      errorType: "CommandExecutionError",
      metadata: { commandName: "export", exportType },
    });

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
