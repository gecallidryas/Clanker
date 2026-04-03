import {
  MessageFlags,
  type ChatInputCommandInteraction,
  type Client,
  type SlashCommandSubcommandBuilder,
} from "discord.js";
import { localizer } from "../../../utils/text/localizer";
import { ColorCode } from "../../../utils/misc/logger";
import { replyInfoEmbed } from "../../../utils/discord/interactionHelper";
import type { UserRow } from "../../../types/db/schema";

// Configure the subcommand
export const configureSubcommand = (
  subcommand: SlashCommandSubcommandBuilder,
) =>
  subcommand
    .setName("help")
    .setDescription(
      localizer("en-US", "commands.config.apikey.help.description"),
    );

/**
 * Displays setup instructions for the Custom provider (OpenAI-compatible endpoints).
 * Explains the endpoint URL format, model name requirement, and optional Bearer token.
 *
 * @param _client - Discord client instance (unused)
 * @param interaction - Command interaction
 * @param _userData - User data from database (unused)
 * @param locale - Locale of the interaction
 */
export async function execute(
  _client: Client,
  interaction: ChatInputCommandInteraction,
  _userData: UserRow,
  locale: string,
): Promise<void> {
  await replyInfoEmbed(
    interaction,
    locale,
    {
      titleKey: "commands.config.apikey.help.title",
      descriptionKey: "commands.config.apikey.help.body",
      color: ColorCode.INFO,
    },
    MessageFlags.Ephemeral,
  );
}
