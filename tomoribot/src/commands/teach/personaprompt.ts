import type {
  ChatInputCommandInteraction,
  Client,
  SlashCommandSubcommandBuilder,
} from "discord.js";
import { MessageFlags, TextInputStyle } from "discord.js";
import type { UserRow, TomoriState } from "@/types/db/schema";
import { log, ColorCode } from "@/utils/misc/logger";
import {
  replyInfoEmbed,
  promptWithRawModal,
  safeSelectOptionText,
} from "@/utils/discord/interactionHelper";
import {
  getCachedTomoriState,
  invalidateTomoriStateCache,
} from "@/utils/cache/tomoriStateCache";
import { loadAllPersonasForServer } from "@/utils/db/dbRead";
import { sql } from "@/utils/db/client";
import { localizer } from "@/utils/text/localizer";
import type { SelectOption } from "@/types/discord/modal";

const MODAL_CUSTOM_ID = "teach_personaprompt_modal";
const PERSONA_SELECT_ID = "persona_select";
const PERSONA_PROMPT_INPUT_ID = "persona_prompt_input";

export const configureSubcommand = (
  subcommand: SlashCommandSubcommandBuilder,
) =>
  subcommand
    .setName("personaprompt")
    .setDescription(
      localizer("en-US", "commands.teach.personaprompt.description"),
    );

export async function execute(
  _client: Client,
  interaction: ChatInputCommandInteraction,
  _userData: UserRow,
  locale: string,
): Promise<void> {
  if (!interaction.channel) {
    await replyInfoEmbed(interaction, locale, {
      titleKey: "general.errors.channel_only_title",
      descriptionKey: "general.errors.channel_only_description",
      color: ColorCode.ERROR,
      flags: MessageFlags.Ephemeral,
    });
    return;
  }

  if (interaction.guild) {
    const hasPermission =
      interaction.memberPermissions?.has("ManageGuild") ?? false;
    if (!hasPermission) {
      await replyInfoEmbed(interaction, locale, {
        titleKey: "commands.teach.personaprompt.no_permission_title",
        descriptionKey:
          "commands.teach.personaprompt.no_permission_description",
        color: ColorCode.ERROR,
        flags: MessageFlags.Ephemeral,
      });
      return;
    }
  }

  let tomoriState: TomoriState | null = null;
  try {
    const serverDiscId = interaction.guild?.id ?? interaction.user.id;
    tomoriState = await getCachedTomoriState(serverDiscId);
    if (!tomoriState) {
      await replyInfoEmbed(interaction, locale, {
        titleKey: "general.errors.tomori_not_setup_title",
        descriptionKey: "general.errors.tomori_not_setup_description",
        color: ColorCode.ERROR,
        flags: MessageFlags.Ephemeral,
      });
      return;
    }

    const allPersonas = await loadAllPersonasForServer(serverDiscId);
    const personaSelectOptions: SelectOption[] = allPersonas
      .filter((persona) => persona.tomori_id !== undefined)
      .map((persona) => ({
        label: safeSelectOptionText(persona.tomori_nickname),
        value: persona.tomori_id?.toString() ?? "",
        description: persona.is_alter
          ? localizer(
              locale,
              "commands.teach.personaprompt.alter_persona_description",
            )
          : localizer(
              locale,
              "commands.teach.personaprompt.main_persona_description",
            ),
      }))
      .filter((option) => option.value !== "");

    if (personaSelectOptions.length === 0) {
      await replyInfoEmbed(interaction, locale, {
        titleKey: "general.errors.unknown_error_title",
        descriptionKey: "general.errors.unknown_error_description",
        color: ColorCode.ERROR,
        flags: MessageFlags.Ephemeral,
      });
      return;
    }

    const modalResult = await promptWithRawModal(interaction, locale, {
      modalCustomId: MODAL_CUSTOM_ID,
      modalTitleKey: "commands.teach.personaprompt.modal_title",
      components: [
        {
          customId: PERSONA_SELECT_ID,
          labelKey: "commands.teach.personaprompt.persona_select_label",
          descriptionKey:
            "commands.teach.personaprompt.persona_select_description",
          placeholder:
            "commands.teach.personaprompt.persona_select_placeholder",
          required: true,
          options: personaSelectOptions,
        },
        {
          customId: PERSONA_PROMPT_INPUT_ID,
          labelKey: "commands.teach.personaprompt.prompt_label",
          descriptionKey: "commands.teach.personaprompt.prompt_description",
          placeholder: "commands.teach.personaprompt.prompt_placeholder",
          style: TextInputStyle.Paragraph,
          required: true,
          maxLength: 4000,
        },
      ],
    });

    if (modalResult.outcome !== "submit") {
      log.info(
        `Teach personaprompt modal ${modalResult.outcome} for user ${interaction.user.id}`,
      );
      return;
    }

    const modalSubmitInteraction = modalResult.interaction;
    const selectedPersonaId = modalResult.values?.[PERSONA_SELECT_ID];
    const personaPrompt = modalResult.values?.[PERSONA_PROMPT_INPUT_ID]?.trim();
    if (!modalSubmitInteraction || !selectedPersonaId || !personaPrompt) {
      return;
    }

    const selectedPersona =
      allPersonas.find(
        (persona) => persona.tomori_id?.toString() === selectedPersonaId,
      ) ?? null;
    if (!selectedPersona?.tomori_id) {
      await replyInfoEmbed(modalSubmitInteraction, locale, {
        titleKey: "general.errors.invalid_option_title",
        descriptionKey: "general.errors.invalid_option_description",
        color: ColorCode.ERROR,
      });
      return;
    }

    await sql`
			INSERT INTO persona_configs (tomori_id, persona_prompt)
			VALUES (${selectedPersona.tomori_id}, ${personaPrompt})
			ON CONFLICT (tomori_id) DO UPDATE
			SET persona_prompt = EXCLUDED.persona_prompt
		`;

    invalidateTomoriStateCache(serverDiscId);

    await replyInfoEmbed(modalSubmitInteraction, locale, {
      titleKey: "commands.teach.personaprompt.success_title",
      descriptionKey: "commands.teach.personaprompt.success_description",
      descriptionVars: { persona_name: selectedPersona.tomori_nickname },
      color: ColorCode.SUCCESS,
    });
  } catch (error) {
    await log.error("Error in /teach personaprompt command", error, {
      serverId: tomoriState?.server_id,
      tomoriId: tomoriState?.tomori_id,
      errorType: "CommandExecutionError",
      metadata: {
        command: "teach personaprompt",
        guildId: interaction.guild?.id,
        userId: interaction.user.id,
      },
    });

    await replyInfoEmbed(interaction, locale, {
      titleKey: "general.errors.unknown_error_title",
      descriptionKey: "general.errors.unknown_error_description",
      color: ColorCode.ERROR,
      flags: MessageFlags.Ephemeral,
    });
  }
}
