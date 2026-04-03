import type {
  ChatInputCommandInteraction,
  Client,
  ModalSubmitInteraction,
  SlashCommandSubcommandBuilder,
} from "discord.js";
import { MessageFlags } from "discord.js";
import { sql } from "@/utils/db/client";
import { localizer } from "../../utils/text/localizer";
import { log, ColorCode } from "../../utils/misc/logger";
import {
  replyInfoEmbed,
  promptWithPaginatedModal,
  safeSelectOptionText,
} from "../../utils/discord/interactionHelper";
import type { UserRow, ErrorContext, TomoriState } from "../../types/db/schema";
import { invalidateUserCache } from "../../utils/cache/userCache";
import { invalidateTomoriStateCache } from "../../utils/cache/tomoriStateCache";
import { loadAllPersonasForServer } from "@/utils/db/dbRead";
import type { SelectOption } from "../../types/discord/modal";

const DELETE_PERSONA_MODAL_ID = "data_delete_persona_modal";
const DELETE_PERSONA_SELECT_ID = "persona_select";
const DELETE_TYPE_PERSONA_PERSONAL_MEMORIES = "persona_personal_memories";
const DELETE_TYPE_PERSONA_SERVER_MEMORIES = "persona_server_memories";
const DELETE_TYPE_PERSONAL_SETTINGS = "personal_settings";
const DELETE_TYPE_SERVER_CONFIG = "server_config";
const DELETE_TYPE_GLOBAL_PERSONAL_MEMORIES = "global_personal_memories";

/**
 * Configure the 'delete' subcommand
 */
export const configureSubcommand = (
  subcommand: SlashCommandSubcommandBuilder,
) =>
  subcommand
    .setName("delete")
    .setDescription(localizer("en-US", "commands.data.delete.description"))
    .addStringOption((option) =>
      option
        .setName("type")
        .setDescription(
          localizer("en-US", "commands.data.delete.type_description"),
        )
        .setRequired(true)
        .addChoices(
          {
            name: localizer(
              "en-US",
              "commands.data.delete.type_choice_persona_personal_memories",
            ),
            value: DELETE_TYPE_PERSONA_PERSONAL_MEMORIES,
          },
          {
            name: localizer(
              "en-US",
              "commands.data.delete.type_choice_persona_server_memories",
            ),
            value: DELETE_TYPE_PERSONA_SERVER_MEMORIES,
          },
          {
            name: localizer(
              "en-US",
              "commands.data.delete.type_choice_personal_settings",
            ),
            value: DELETE_TYPE_PERSONAL_SETTINGS,
          },
          {
            name: localizer(
              "en-US",
              "commands.data.delete.type_choice_server_config",
            ),
            value: DELETE_TYPE_SERVER_CONFIG,
          },
          {
            name: localizer(
              "en-US",
              "commands.data.delete.type_choice_global_personal_memories",
            ),
            value: DELETE_TYPE_GLOBAL_PERSONAL_MEMORIES,
          },
        ),
    )
    .addStringOption((option) =>
      option
        .setName("confirmation")
        .setDescription(
          localizer("en-US", "commands.data.delete.confirmation_description"),
        )
        .setRequired(true)
        .addChoices(
          {
            name: localizer("en-US", "commands.data.delete.confirmation_yes"),
            value: "yes",
          },
          {
            name: localizer("en-US", "commands.data.delete.confirmation_no"),
            value: "no",
          },
        ),
    );

/**
 * Executes the 'delete' command
 * Permanently deletes user or server data with proper CASCADE behavior
 * @param client - The Discord client instance
 * @param interaction - The chat input command interaction
 * @param userData - The user data for the invoking user
 * @param locale - The user's preferred locale
 */
export async function execute(
  _client: Client,
  interaction: ChatInputCommandInteraction,
  userData: UserRow,
  locale: string,
): Promise<void> {
  const deleteType = interaction.options.getString("type", true);
  const confirmation = interaction.options.getString("confirmation", true);
  const serverDiscId = interaction.guild?.id ?? interaction.user.id;
  let responseInteraction:
    | ChatInputCommandInteraction
    | ModalSubmitInteraction = interaction;
  let selectedPersona: TomoriState | null = null;

  try {
    if (confirmation !== "yes") {
      await replyInfoEmbed(interaction, locale, {
        titleKey: "commands.data.delete.confirmation_required_title",
        descriptionKey:
          "commands.data.delete.confirmation_required_description",
        color: ColorCode.ERROR,
        flags: MessageFlags.Ephemeral,
      });
      return;
    }

    const requiresServerPermission =
      deleteType === DELETE_TYPE_PERSONA_SERVER_MEMORIES ||
      deleteType === DELETE_TYPE_SERVER_CONFIG;
    if (requiresServerPermission && interaction.guild) {
      const hasPermission =
        interaction.memberPermissions?.has("ManageGuild") ?? false;
      if (!hasPermission) {
        await replyInfoEmbed(interaction, locale, {
          titleKey: "commands.data.delete.no_permission_title",
          descriptionKey: "commands.data.delete.no_permission_description",
          color: ColorCode.ERROR,
          flags: MessageFlags.Ephemeral,
        });
        return;
      }
    }

    const needsPersonaSelection =
      deleteType === DELETE_TYPE_PERSONA_PERSONAL_MEMORIES ||
      deleteType === DELETE_TYPE_PERSONA_SERVER_MEMORIES;
    if (needsPersonaSelection) {
      const allPersonas = await loadAllPersonasForServer(serverDiscId);
      const personaSelectOptions: SelectOption[] = allPersonas
        .filter((persona) => persona.tomori_id !== undefined)
        .map((persona) => ({
          label: safeSelectOptionText(persona.tomori_nickname),
          value: persona.tomori_id?.toString() ?? "",
          description: persona.is_alter
            ? localizer(
                locale,
                "commands.data.delete.alter_persona_description",
              )
            : localizer(
                locale,
                "commands.data.delete.main_persona_description",
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
          modalCustomId: DELETE_PERSONA_MODAL_ID,
          modalTitleKey: "commands.data.delete.persona_modal_title",
          components: [
            {
              customId: DELETE_PERSONA_SELECT_ID,
              labelKey: "commands.data.delete.persona_select_label",
              descriptionKey: "commands.data.delete.persona_select_description",
              placeholder: "commands.data.delete.persona_select_placeholder",
              required: true,
              options: personaSelectOptions,
            },
          ],
        },
      );
      if (personaModalResult.outcome !== "submit") {
        log.info(
          `Data delete persona modal ${personaModalResult.outcome} for user ${interaction.user.id}`,
        );
        return;
      }

      const modalSubmitInteraction = personaModalResult.interaction;
      if (!modalSubmitInteraction) {
        return;
      }
      responseInteraction = modalSubmitInteraction;

      const selectedPersonaId =
        personaModalResult.values?.[DELETE_PERSONA_SELECT_ID];
      selectedPersona =
        allPersonas.find(
          (persona) => persona.tomori_id?.toString() === selectedPersonaId,
        ) ?? null;
      if (!selectedPersona?.tomori_id) {
        await replyInfoEmbed(responseInteraction, locale, {
          titleKey: "general.errors.invalid_option_title",
          descriptionKey: "general.errors.invalid_option_description",
          color: ColorCode.ERROR,
        });
        return;
      }
    }

    await responseInteraction.deferReply({ flags: MessageFlags.Ephemeral });

    if (deleteType === DELETE_TYPE_PERSONA_PERSONAL_MEMORIES) {
      const userRows = await sql<Array<{ user_id: number }>>`
				SELECT user_id
				FROM users
				WHERE user_disc_id = ${interaction.user.id}
				LIMIT 1
			`;
      const targetUserId = userRows[0]?.user_id;
      if (!targetUserId) {
        await replyInfoEmbed(responseInteraction, locale, {
          titleKey: "commands.data.delete.no_data_title",
          descriptionKey: "commands.data.delete.no_data_description",
          color: ColorCode.WARN,
        });
        return;
      }

      const targetLineageId = selectedPersona?.persona_lineage_id ?? 0;
      const deletedMemories = await sql<Array<{ personal_memory_id: number }>>`
				DELETE FROM personal_memories
				WHERE user_id = ${targetUserId}
				  AND persona_lineage_id = ${targetLineageId}
				RETURNING personal_memory_id
			`;
      if (deletedMemories.length === 0) {
        await replyInfoEmbed(responseInteraction, locale, {
          titleKey: "commands.data.delete.no_data_title",
          descriptionKey:
            "commands.data.delete.no_persona_memories_description",
          descriptionVars: {
            persona_name: selectedPersona?.tomori_nickname ?? "persona",
          },
          color: ColorCode.WARN,
        });
        return;
      }

      await replyInfoEmbed(responseInteraction, locale, {
        titleKey: "commands.data.delete.success_memory_scope_title",
        descriptionKey:
          "commands.data.delete.success_persona_memories_description",
        descriptionVars: {
          persona_name: selectedPersona?.tomori_nickname ?? "persona",
          memory_count: deletedMemories.length.toString(),
        },
        color: ColorCode.SUCCESS,
      });
      return;
    }

    if (deleteType === DELETE_TYPE_GLOBAL_PERSONAL_MEMORIES) {
      const userRows = await sql<Array<{ user_id: number }>>`
				SELECT user_id
				FROM users
				WHERE user_disc_id = ${interaction.user.id}
				LIMIT 1
			`;
      const targetUserId = userRows[0]?.user_id;
      if (!targetUserId) {
        await replyInfoEmbed(responseInteraction, locale, {
          titleKey: "commands.data.delete.no_data_title",
          descriptionKey: "commands.data.delete.no_data_description",
          color: ColorCode.WARN,
        });
        return;
      }

      const deletedMemories = await sql<Array<{ personal_memory_id: number }>>`
				DELETE FROM personal_memories
				WHERE user_id = ${targetUserId}
				  AND persona_lineage_id = 0
				RETURNING personal_memory_id
			`;
      if (deletedMemories.length === 0) {
        await replyInfoEmbed(responseInteraction, locale, {
          titleKey: "commands.data.delete.no_data_title",
          descriptionKey: "commands.data.delete.no_global_memories_description",
          color: ColorCode.WARN,
        });
        return;
      }

      await replyInfoEmbed(responseInteraction, locale, {
        titleKey: "commands.data.delete.success_memory_scope_title",
        descriptionKey:
          "commands.data.delete.success_global_memories_description",
        descriptionVars: { memory_count: deletedMemories.length.toString() },
        color: ColorCode.SUCCESS,
      });
      return;
    }

    if (deleteType === DELETE_TYPE_PERSONAL_SETTINGS) {
      const updatedUsers = await sql<Array<{ user_id: number }>>`
				UPDATE users
				SET
					user_nickname = ${interaction.user.username},
					language_pref = 'en-US',
					impersonation_prompt = NULL
				WHERE user_disc_id = ${interaction.user.id}
				RETURNING user_id
			`;
      if (!updatedUsers.length) {
        await replyInfoEmbed(responseInteraction, locale, {
          titleKey: "commands.data.delete.no_data_title",
          descriptionKey: "commands.data.delete.no_data_description",
          color: ColorCode.WARN,
        });
        return;
      }

      invalidateUserCache(interaction.user.id);

      await replyInfoEmbed(responseInteraction, locale, {
        titleKey: "commands.data.delete.success_personal_settings_title",
        descriptionKey:
          "commands.data.delete.success_personal_settings_description",
        color: ColorCode.SUCCESS,
      });
      return;
    }

    if (deleteType === DELETE_TYPE_PERSONA_SERVER_MEMORIES) {
      const serverRows = await sql<Array<{ server_id: number }>>`
				SELECT server_id
				FROM servers
				WHERE server_disc_id = ${serverDiscId}
				LIMIT 1
			`;
      const serverId = serverRows[0]?.server_id;
      if (!serverId) {
        await replyInfoEmbed(responseInteraction, locale, {
          titleKey: "commands.data.delete.no_server_data_title",
          descriptionKey: "commands.data.delete.no_server_data_description",
          color: ColorCode.WARN,
        });
        return;
      }

      const targetLineageId = selectedPersona?.persona_lineage_id ?? 0;
      const deletedMemories = await sql<Array<{ server_memory_id: number }>>`
				DELETE FROM server_memories
				WHERE server_id = ${serverId}
				  AND persona_lineage_id = ${targetLineageId}
				RETURNING server_memory_id
			`;
      if (deletedMemories.length === 0) {
        await replyInfoEmbed(responseInteraction, locale, {
          titleKey: "commands.data.delete.no_server_data_title",
          descriptionKey:
            "commands.data.delete.no_persona_server_memories_description",
          descriptionVars: {
            persona_name: selectedPersona?.tomori_nickname ?? "persona",
          },
          color: ColorCode.WARN,
        });
        return;
      }

      invalidateTomoriStateCache(serverDiscId);
      await replyInfoEmbed(responseInteraction, locale, {
        titleKey: "commands.data.delete.success_memory_scope_title",
        descriptionKey:
          "commands.data.delete.success_persona_server_memories_description",
        descriptionVars: {
          persona_name: selectedPersona?.tomori_nickname ?? "persona",
          memory_count: deletedMemories.length.toString(),
        },
        color: ColorCode.SUCCESS,
      });
      return;
    }

    if (deleteType === DELETE_TYPE_SERVER_CONFIG) {
      const serverRows = await sql<Array<{ server_id: number }>>`
				SELECT server_id
				FROM servers
				WHERE server_disc_id = ${serverDiscId}
				LIMIT 1
			`;
      const serverId = serverRows[0]?.server_id;
      if (!serverId) {
        await replyInfoEmbed(responseInteraction, locale, {
          titleKey: "commands.data.delete.no_server_data_title",
          descriptionKey: "commands.data.delete.no_server_data_description",
          color: ColorCode.WARN,
        });
        return;
      }

      let updatedRows = await sql<Array<{ tomori_config_id: number }>>`
				UPDATE tomori_configs
				SET
					llm_temperature = 1.2,
					llm_top_p = 0.95,
					humanizer_degree = 1,
					timezone_offset = 0,
					message_fetch_limit = 80,
					server_memteaching_enabled = true,
					attribute_memteaching_enabled = false,
					sampledialogue_memteaching_enabled = false,
					self_teaching_enabled = true,
					web_search_enabled = true,
					personal_memories_enabled = true,
					emoji_usage_enabled = true,
					sticker_usage_enabled = true,
					imagegen_enabled = true,
					self_debug_enabled = false
				WHERE server_id = ${serverId}
				RETURNING tomori_config_id
			`;

      if (!updatedRows.length) {
        const mainTomoriRows = await sql<Array<{ tomori_id: number }>>`
					SELECT tomori_id
					FROM tomoris
					WHERE server_id = ${serverId}
					  AND is_alter = false
					ORDER BY updated_at DESC NULLS LAST, tomori_id DESC
					LIMIT 1
				`;
        const mainTomoriId = mainTomoriRows[0]?.tomori_id;
        if (mainTomoriId) {
          updatedRows = await sql<Array<{ tomori_config_id: number }>>`
						UPDATE tomori_configs
						SET
							llm_temperature = 1.2,
							llm_top_p = 0.95,
							humanizer_degree = 1,
							timezone_offset = 0,
							message_fetch_limit = 80,
							server_memteaching_enabled = true,
							attribute_memteaching_enabled = false,
							sampledialogue_memteaching_enabled = false,
							self_teaching_enabled = true,
							web_search_enabled = true,
							personal_memories_enabled = true,
							emoji_usage_enabled = true,
							sticker_usage_enabled = true,
							imagegen_enabled = true,
							self_debug_enabled = false
						WHERE tomori_id = ${mainTomoriId}
						RETURNING tomori_config_id
					`;
        }
      }

      if (!updatedRows.length) {
        await replyInfoEmbed(responseInteraction, locale, {
          titleKey: "commands.data.delete.no_server_data_title",
          descriptionKey: "commands.data.delete.no_server_data_description",
          color: ColorCode.WARN,
        });
        return;
      }

      invalidateTomoriStateCache(serverDiscId);
      await replyInfoEmbed(responseInteraction, locale, {
        titleKey: "commands.data.delete.success_server_config_title",
        descriptionKey:
          "commands.data.delete.success_server_config_description",
        color: ColorCode.SUCCESS,
      });
      return;
    }

    await replyInfoEmbed(responseInteraction, locale, {
      titleKey: "general.errors.invalid_option_title",
      descriptionKey: "general.errors.invalid_option_description",
      color: ColorCode.ERROR,
    });
  } catch (error) {
    const context: ErrorContext = {
      userId: userData.user_id,
      errorType: "CommandExecutionError",
      metadata: {
        command: "data delete",
        deleteType,
        userDiscordId: interaction.user.id,
        guildDiscordId: interaction.guild?.id,
      },
    };

    await log.error(
      `Error executing /data delete for user ${userData.user_disc_id}`,
      error as Error,
      context,
    );

    if (responseInteraction.deferred || responseInteraction.replied) {
      await replyInfoEmbed(responseInteraction, locale, {
        titleKey: "general.errors.unknown_error_title",
        descriptionKey: "general.errors.unknown_error_description",
        color: ColorCode.ERROR,
      });
    } else {
      await replyInfoEmbed(responseInteraction, locale, {
        titleKey: "general.errors.unknown_error_title",
        descriptionKey: "general.errors.unknown_error_description",
        color: ColorCode.ERROR,
        flags: MessageFlags.Ephemeral,
      });
    }
  }
}
