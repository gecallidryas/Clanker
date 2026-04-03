import {
  MessageFlags,
  type ChatInputCommandInteraction,
  type Client,
  type SlashCommandSubcommandBuilder,
} from "discord.js";
import {
  getCachedTomoriState,
  invalidateTomoriStateCache,
} from "../../../utils/cache/tomoriStateCache";
import { localizer } from "../../../utils/text/localizer";
import { log, ColorCode } from "../../../utils/misc/logger";
import { replyInfoEmbed } from "../../../utils/discord/interactionHelper";
import {
  type UserRow,
  type ErrorContext,
  tomoriConfigSchema,
} from "../../../types/db/schema";
import { sql } from "@/utils/db/client";

// Neutral value: 0.0 = no penalty applied
const PRESENCE_PENALTY_MIN = -2.0;
const PRESENCE_PENALTY_INPUT_MAX = 2.0;
const PRESENCE_PENALTY_STORED_MAX = 1.99;
const PRESENCE_PENALTY_DEFAULT = 0.0;

// Configure the subcommand
export const configureSubcommand = (
  subcommand: SlashCommandSubcommandBuilder,
) =>
  subcommand
    .setName("presence-penalty")
    .setDescription(
      localizer("en-US", "commands.config.params.presence-penalty.description"),
    )
    .addNumberOption((option) =>
      option
        .setName("value")
        .setDescription(
          localizer(
            "en-US",
            "commands.config.params.presence-penalty.value_description",
          ),
        )
        .setMinValue(PRESENCE_PENALTY_MIN)
        .setMaxValue(PRESENCE_PENALTY_INPUT_MAX)
        .setRequired(true),
    );

function normalizePresencePenalty(value: number): number {
	return Math.max(
		PRESENCE_PENALTY_MIN,
		Math.min(PRESENCE_PENALTY_STORED_MAX, value),
	);
}

/**
 * Sets the presence penalty for Tomori's LLM
 * Positive values penalize tokens that have appeared at all in the output so far
 * Applied by OpenRouter and NovelAI.
 * Google support is behind an explicit provider flag and compatible-model guard.
 * Neutral at 0.0 (no penalty)
 * @param _client - Discord client instance
 * @param interaction - Command interaction
 * @param userData - User data from database
 * @param locale - Locale of the interaction
 */
export async function execute(
  _client: Client,
  interaction: ChatInputCommandInteraction,
  userData: UserRow,
  locale: string,
): Promise<void> {
  // 1. Ensure command is run in a guild
  if (!interaction.guild || !interaction.channel) {
    await replyInfoEmbed(interaction, userData.language_pref, {
      titleKey: "general.errors.guild_only_title",
      descriptionKey: "general.errors.guild_only_description",
      color: ColorCode.ERROR,
    });
    return;
  }

  // 2. Defer the interaction before async work to prevent timeout
  await interaction.deferReply({ flags: MessageFlags.Ephemeral });

  try {
    // 3. Get the value from options
    const requestedValue = interaction.options.getNumber("value", true);
    const newValue = normalizePresencePenalty(requestedValue);

    // 4. Additional validation (Discord already handles min/max, but just in case)
    if (
      requestedValue < PRESENCE_PENALTY_MIN ||
      requestedValue > PRESENCE_PENALTY_INPUT_MAX
    ) {
      await replyInfoEmbed(interaction, locale, {
        titleKey: "commands.config.params.presence-penalty.invalid_value_title",
        descriptionKey:
          "commands.config.params.presence-penalty.invalid_value_description",
        descriptionVars: {
          min: PRESENCE_PENALTY_MIN.toFixed(1),
          max: PRESENCE_PENALTY_INPUT_MAX.toFixed(1),
        },
        color: ColorCode.ERROR,
      });
      return;
    }

    // 5. Load the Tomori state for this server
    const tomoriState = await getCachedTomoriState(interaction.guild.id);
    if (!tomoriState) {
      await replyInfoEmbed(interaction, locale, {
        titleKey: "general.errors.tomori_not_setup_title",
        descriptionKey: "general.errors.tomori_not_setup_description",
        color: ColorCode.ERROR,
      });
      return;
    }

    // 6. Check if the value is already set to the same value
    const currentValue =
      tomoriState.config.llm_presence_penalty ?? PRESENCE_PENALTY_DEFAULT;
    if (Math.abs(newValue - currentValue) < 0.001) {
      await replyInfoEmbed(interaction, locale, {
        titleKey: "commands.config.params.presence-penalty.already_set_title",
        descriptionKey:
          "commands.config.params.presence-penalty.already_set_description",
        descriptionVars: {
          presence_penalty: newValue.toFixed(2),
        },
        color: ColorCode.WARN,
      });
      return;
    }

    // 7. Update the config in the database
    const [updatedRow] = await sql`
            UPDATE tomori_configs
            SET llm_presence_penalty = ${newValue}
            WHERE server_id = ${tomoriState.server_id}
            RETURNING *
        `;

    // 8. Validate the returned data
    const validatedConfig = tomoriConfigSchema.safeParse(updatedRow);

    if (!validatedConfig.success || !updatedRow) {
      const context: ErrorContext = {
        tomoriId: tomoriState.tomori_id,
        serverId: tomoriState.server_id,
        userId: userData.user_id,
        errorType: "DatabaseUpdateError",
        metadata: {
          command: "config params presence-penalty",
          guildId: interaction.guild?.id,
          requestedValue,
          normalizedValue: newValue,
          validationErrors: validatedConfig.success
            ? null
            : validatedConfig.error.flatten(),
        },
      };
      await log.error(
        "Failed to update or validate llm_presence_penalty config",
        validatedConfig.success
          ? new Error("Database update returned no rows or unexpected data")
          : new Error("Updated config data failed validation"),
        context,
      );

      await replyInfoEmbed(interaction, locale, {
        titleKey: "general.errors.update_failed_title",
        descriptionKey: "general.errors.update_failed_description",
        color: ColorCode.ERROR,
      });
      return;
    }

    // 9. Invalidate cache so next message gets fresh config
    invalidateTomoriStateCache(interaction.guild.id);

    // 10. Success message
    await replyInfoEmbed(interaction, locale, {
      titleKey: "commands.config.params.presence-penalty.success_title",
      descriptionKey:
        "commands.config.params.presence-penalty.success_description",
      descriptionVars: {
        presence_penalty: newValue.toFixed(2),
        previous_presence_penalty: currentValue.toFixed(2),
      },
      color: ColorCode.SUCCESS,
    });
  } catch (error) {
    // 11. Log error with context
    let serverIdForError: number | null = null;
    let tomoriIdForError: number | null = null;
    if (interaction.guild?.id) {
      const state = await getCachedTomoriState(interaction.guild.id);
      serverIdForError = state?.server_id ?? null;
      tomoriIdForError = state?.tomori_id ?? null;
    }

    const context: ErrorContext = {
      userId: userData.user_id,
      serverId: serverIdForError,
      tomoriId: tomoriIdForError,
      errorType: "CommandExecutionError",
      metadata: {
        command: "config params presence-penalty",
        guildId: interaction.guild?.id,
        executorDiscordId: interaction.user.id,
        valueAttempted: interaction.options.getNumber("value"),
        normalizedValue:
          interaction.options.getNumber("value") === null
            ? null
            : normalizePresencePenalty(
                interaction.options.getNumber("value", true),
              ),
      },
    };
    await log.error(
      `Error executing /config params presence-penalty for user ${userData.user_disc_id}`,
      error as Error,
      context,
    );

    if (interaction.deferred && !interaction.replied) {
      await interaction.followUp({
        content: localizer(locale, "general.errors.unknown_error_description"),
        flags: MessageFlags.Ephemeral,
      });
    }
  }
}
