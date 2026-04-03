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

// Define constants at the top (Rule #20)
const TEMPERATURE_MIN = 0;
const TEMPERATURE_INPUT_MAX = 2.0;
const TEMPERATURE_STORED_MAX = 1.99;
const TEMPERATURE_DEFAULT = 1.0;

// Configure the subcommand
export const configureSubcommand = (
  subcommand: SlashCommandSubcommandBuilder,
) =>
  subcommand
    .setName("temperature")
    .setDescription(
      localizer("en-US", "commands.config.params.temperature.description"),
    )
    .addNumberOption((option) =>
      option
        .setName("value")
        .setDescription(
          localizer(
            "en-US",
            "commands.config.params.temperature.value_description",
          ),
        )
        .setMinValue(TEMPERATURE_MIN)
        .setMaxValue(TEMPERATURE_INPUT_MAX)
        .setRequired(true),
    );

/**
 * Clamp temperature to DB-safe range.
 * Some providers (e.g. Google Gemini) reject exact 2.0, so cap at 1.99.
 */
function normalizeTemperature(value: number): number {
  return Math.max(TEMPERATURE_MIN, Math.min(TEMPERATURE_STORED_MAX, value));
}

/**
 * Sets the temperature parameter for Tomori's LLM
 * Higher values make output more random, lower values make it more deterministic
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

  // 1.5. Defer the interaction before async work to prevent timeout
  await interaction.deferReply({ flags: MessageFlags.Ephemeral });

  try {
    // 2. Get the temperature value from options and normalize for storage
    const rawValue = interaction.options.getNumber("value", true);
    const temperatureValue = normalizeTemperature(rawValue);

    // 3. Additional validation (Discord already handles min/max, but just in case)
    if (
      rawValue < TEMPERATURE_MIN ||
      rawValue > TEMPERATURE_INPUT_MAX
    ) {
      await replyInfoEmbed(interaction, locale, {
        titleKey: "commands.config.params.temperature.invalid_value_title",
        descriptionKey:
          "commands.config.params.temperature.invalid_value_description",
        descriptionVars: {
          min: TEMPERATURE_MIN.toFixed(1),
          max: TEMPERATURE_INPUT_MAX.toFixed(1),
        },
        color: ColorCode.ERROR,
      });
      return;
    }

    // 4. Load the Tomori state for this server
    const tomoriState = await getCachedTomoriState(interaction.guild.id);
    if (!tomoriState) {
      await replyInfoEmbed(interaction, locale, {
        titleKey: "general.errors.tomori_not_setup_title",
        descriptionKey: "general.errors.tomori_not_setup_description",
        color: ColorCode.ERROR,
      });
      return;
    }

    // 5. Check if this is the same as the current temperature
    const currentTemperature =
      tomoriState.config.llm_temperature ?? TEMPERATURE_DEFAULT;
    if (Math.abs(temperatureValue - currentTemperature) < 0.01) {
      await replyInfoEmbed(interaction, locale, {
        titleKey: "commands.config.params.temperature.already_set_title",
        descriptionKey:
          "commands.config.params.temperature.already_set_description",
        descriptionVars: {
          temperature: temperatureValue.toFixed(1),
        },
        color: ColorCode.WARN,
      });
      return;
    }

    // 6. Update the config in the database
    const [updatedRow] = await sql`
            UPDATE tomori_configs
            SET llm_temperature = ${temperatureValue}
            WHERE server_id = ${tomoriState.server_id}
            RETURNING *
        `;

    // 7. Validate the returned data
    const validatedConfig = tomoriConfigSchema.safeParse(updatedRow);

    if (!validatedConfig.success || !updatedRow) {
      const context: ErrorContext = {
        tomoriId: tomoriState.tomori_id,
        serverId: tomoriState.server_id,
        userId: userData.user_id,
        errorType: "DatabaseUpdateError",
        metadata: {
          command: "config params temperature",
          guildId: interaction.guild?.id,
          temperatureValue,
          validationErrors: validatedConfig.success
            ? null
            : validatedConfig.error.flatten(),
        },
      };
      await log.error(
        "Failed to update or validate llm_temperature config",
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

    // 8. Invalidate cache so next message gets fresh config
    invalidateTomoriStateCache(interaction.guild.id);

    // 9. Success message
    await replyInfoEmbed(interaction, locale, {
      titleKey: "commands.config.params.temperature.success_title",
      descriptionKey: "commands.config.params.temperature.success_description",
      descriptionVars: {
        temperature: temperatureValue.toFixed(1),
        previous_temperature: currentTemperature.toFixed(1),
      },
      color: ColorCode.SUCCESS,
    });
  } catch (error) {
    // 10. Log error with context
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
        command: "config params temperature",
        guildId: interaction.guild?.id,
        executorDiscordId: interaction.user.id,
        valueAttempted: interaction.options.getNumber("value"),
      },
    };
    await log.error(
      `Error executing /config params temperature for user ${userData.user_disc_id}`,
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
