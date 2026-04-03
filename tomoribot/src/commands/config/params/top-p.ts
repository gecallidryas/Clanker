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

// Neutral value: 1.0 = full probability distribution (disabled)
const TOP_P_MIN = 0.0;
const TOP_P_MAX = 1.0;
const TOP_P_DEFAULT = 0.95;

// Configure the subcommand
export const configureSubcommand = (
  subcommand: SlashCommandSubcommandBuilder,
) =>
  subcommand
    .setName("top-p")
    .setDescription(
      localizer("en-US", "commands.config.params.top-p.description"),
    )
    .addNumberOption((option) =>
      option
        .setName("value")
        .setDescription(
          localizer("en-US", "commands.config.params.top-p.value_description"),
        )
        .setMinValue(TOP_P_MIN)
        .setMaxValue(TOP_P_MAX)
        .setRequired(true),
    );

/**
 * Sets the top-P (nucleus sampling) threshold for Tomori's LLM
 * Lower values restrict sampling to the most probable tokens
 * Neutral/disabled at 1.0 (full distribution)
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
    const newValue = interaction.options.getNumber("value", true);

    // 4. Additional validation (Discord already handles min/max, but just in case)
    if (newValue < TOP_P_MIN || newValue > TOP_P_MAX) {
      await replyInfoEmbed(interaction, locale, {
        titleKey: "commands.config.params.top-p.invalid_value_title",
        descriptionKey:
          "commands.config.params.top-p.invalid_value_description",
        descriptionVars: {
          min: TOP_P_MIN.toFixed(1),
          max: TOP_P_MAX.toFixed(1),
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
    const currentValue = tomoriState.config.llm_top_p ?? TOP_P_DEFAULT;
    if (Math.abs(newValue - currentValue) < 0.001) {
      await replyInfoEmbed(interaction, locale, {
        titleKey: "commands.config.params.top-p.already_set_title",
        descriptionKey: "commands.config.params.top-p.already_set_description",
        descriptionVars: {
          top_p: newValue.toFixed(2),
        },
        color: ColorCode.WARN,
      });
      return;
    }

    // 7. Update the config in the database
    const [updatedRow] = await sql`
            UPDATE tomori_configs
            SET llm_top_p = ${newValue}
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
          command: "config params top-p",
          guildId: interaction.guild?.id,
          newValue,
          validationErrors: validatedConfig.success
            ? null
            : validatedConfig.error.flatten(),
        },
      };
      await log.error(
        "Failed to update or validate llm_top_p config",
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
      titleKey: "commands.config.params.top-p.success_title",
      descriptionKey: "commands.config.params.top-p.success_description",
      descriptionVars: {
        top_p: newValue.toFixed(2),
        previous_top_p: currentValue.toFixed(2),
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
        command: "config params top-p",
        guildId: interaction.guild?.id,
        executorDiscordId: interaction.user.id,
        valueAttempted: interaction.options.getNumber("value"),
      },
    };
    await log.error(
      `Error executing /config params top-p for user ${userData.user_disc_id}`,
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
