import type {
  ChatInputCommandInteraction,
  Client,
  SlashCommandSubcommandBuilder,
} from "discord.js";
import { MessageFlags } from "discord.js";
import type { UserRow } from "@/types/db/schema";
import type { ErrorContext } from "@/types/db/schema";
import type { SummaryEmbedOptions } from "@/types/discord/embed";
import { localizer } from "@/utils/text/localizer";
import { log, ColorCode } from "@/utils/misc/logger";
import { replySummaryEmbed } from "@/utils/discord/interactionHelper";
import { commandRegistry } from "@/utils/discord/commandRegistry";

/**
 * Configure the /help apikey subcommand
 * Provider-specific instructions for getting and setting up API keys
 */
export const configureSubcommand = (
  subcommand: SlashCommandSubcommandBuilder,
) =>
  subcommand
    .setName("apikey")
    .setDescription(localizer("en-US", "commands.help.apikey.description"))
    .addStringOption((option) =>
      option
        .setName("provider")
        .setDescription(
          localizer("en-US", "commands.help.apikey.provider_description"),
        )
        .setRequired(true)
        .addChoices(
          {
            name: localizer(
              "en-US",
              "commands.help.apikey.provider_choice_brave",
            ),
            value: "brave",
          },
          {
            name: localizer(
              "en-US",
              "commands.help.apikey.provider_choice_google",
            ),
            value: "google",
          },
          {
            name: localizer(
              "en-US",
              "commands.help.apikey.provider_choice_deepseek",
            ),
            value: "deepseek",
          },
          {
            name: localizer(
              "en-US",
              "commands.help.apikey.provider_choice_nvidia",
            ),
            value: "nvidia",
          },
          {
            name: localizer(
              "en-US",
              "commands.help.apikey.provider_choice_novelai",
            ),
            value: "novelai",
          },
          {
            name: localizer(
              "en-US",
              "commands.help.apikey.provider_choice_openrouter",
            ),
            value: "openrouter",
          },
          {
            name: localizer(
              "en-US",
              "commands.help.apikey.provider_choice_zai",
            ),
            value: "zai",
          },
          {
            name: localizer(
              "en-US",
              "commands.help.apikey.provider_choice_vertex",
            ),
            value: "vertex",
          },
          {
            name: localizer(
              "en-US",
              "commands.help.apikey.provider_choice_elevenlabs",
            ),
            value: "elevenlabs",
          },
        ),
    );

/**
 * Execute the /help apikey command
 * Displays provider-specific API key setup instructions
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
  try {
    const provider = interaction.options.getString("provider", true);

    // Get command mentions for cross-references
    const configBraveapiSetMention = commandRegistry.getCommandMention(
      "config",
      "braveapi",
      "set",
    );
    const configSetupMention = commandRegistry.getCommandMention(
      "config",
      "setup",
    );
    const configApikeySetMention = commandRegistry.getCommandMention(
      "config",
      "apikey",
      "set",
    );
    const configModelMention = commandRegistry.getCommandMention(
      "config",
      "model",
      "text",
    );
    const configModelEmbeddingMention = commandRegistry.getCommandMention(
      "config",
      "model",
      "embedding",
    );
    const configModelImageMention = commandRegistry.getCommandMention(
      "config",
      "model",
      "image",
    );
    const supportServerMention = commandRegistry.getCommandMention(
      "support",
      "discord",
    );
    const optionalkeyElevenlabsSetMention = commandRegistry.getCommandMention(
      "optionalkey",
      "elevenlabs",
      "set",
    );
    const optionalkeyElevenlabsRemoveMention = commandRegistry.getCommandMention(
      "optionalkey",
      "elevenlabs",
      "remove",
    );
    const configVoiceElevenlabsMention = commandRegistry.getCommandMention(
      "config",
      "voice",
      "elevenlabs",
    );

    // Build options based on provider
    let embedOptions: SummaryEmbedOptions;

    switch (provider) {
      case "brave":
        embedOptions = {
          titleKey: "commands.help.apikey.brave_title",
          descriptionKey: "commands.help.apikey.brave_description",
          color: ColorCode.INFO,
          fields: [
            {
              nameKey: "commands.help.apikey.brave_getting_key_title",
              value: localizer(
                locale,
                "commands.help.apikey.brave_getting_key_description",
                {
                  configBraveapiSet: configBraveapiSetMention,
                },
              ),
              inline: false,
            },
            {
              nameKey: "commands.help.apikey.brave_important_title",
              value: localizer(
                locale,
                "commands.help.apikey.brave_important_description",
              ),
              inline: false,
            },
          ],
          footerKey: "commands.help.apikey.brave_footer",
        };
        break;

      case "google":
        embedOptions = {
          titleKey: "commands.help.apikey.google_title",
          descriptionKey: "commands.help.apikey.google_description",
          color: ColorCode.INFO,
          fields: [
            {
              nameKey: "commands.help.apikey.google_getting_key_title",
              value: localizer(
                locale,
                "commands.help.apikey.google_getting_key_description",
                {
                  configSetup: configSetupMention,
                  configApikeySet: configApikeySetMention,
                },
              ),
              inline: false,
            },
          ],
          footerKey: "commands.help.apikey.google_footer",
          footerVars: {
            configModel: configModelMention,
          },
        };
        break;

      case "deepseek":
        embedOptions = {
          titleKey: "commands.help.apikey.deepseek_title",
          descriptionKey: "commands.help.apikey.deepseek_description",
          color: ColorCode.INFO,
          fields: [
            {
              nameKey: "commands.help.apikey.deepseek_getting_key_title",
              value: localizer(
                locale,
                "commands.help.apikey.deepseek_getting_key_description",
                {
                  configSetup: configSetupMention,
                  configApikeySet: configApikeySetMention,
                },
              ),
              inline: false,
            },
            {
              nameKey: "commands.help.apikey.deepseek_model_notes_title",
              value: localizer(
                locale,
                "commands.help.apikey.deepseek_model_notes_description",
              ),
              inline: false,
            },
          ],
          footerKey: "commands.help.apikey.deepseek_footer",
          footerVars: {
            configModel: configModelMention,
          },
        };
        break;

      case "nvidia":
        embedOptions = {
          titleKey: "commands.help.apikey.nvidia_title",
          descriptionKey: "commands.help.apikey.nvidia_description",
          color: ColorCode.INFO,
          fields: [
            {
              nameKey: "commands.help.apikey.nvidia_getting_key_title",
              value: localizer(
                locale,
                "commands.help.apikey.nvidia_getting_key_description",
                {
                  configSetup: configSetupMention,
                  configApikeySet: configApikeySetMention,
                },
              ),
              inline: false,
            },
            {
              nameKey: "commands.help.apikey.nvidia_model_notes_title",
              value: localizer(
                locale,
                "commands.help.apikey.nvidia_model_notes_description",
              ),
              inline: false,
            },
          ],
          footerKey: "commands.help.apikey.nvidia_footer",
          footerVars: {
            configModel: configModelMention,
            configModelEmbedding: configModelEmbeddingMention,
            configModelImage: configModelImageMention,
          },
        };
        break;

      case "novelai":
        embedOptions = {
          titleKey: "commands.help.apikey.novelai_title",
          descriptionKey: "commands.help.apikey.novelai_description",
          color: ColorCode.INFO,
          fields: [
            {
              nameKey: "commands.help.apikey.novelai_getting_key_title",
              value: localizer(
                locale,
                "commands.help.apikey.novelai_getting_key_description",
                {
                  configSetup: configSetupMention,
                  configApikeySet: configApikeySetMention,
                },
              ),
              inline: false,
            },
          ],
          footerKey: "commands.help.apikey.novelai_footer",
          footerVars: {
            configModel: configModelMention,
          },
        };
        break;

      case "openrouter":
        embedOptions = {
          titleKey: "commands.help.apikey.openrouter_title",
          descriptionKey: "commands.help.apikey.openrouter_description",
          color: ColorCode.INFO,
          fields: [
            {
              nameKey: "commands.help.apikey.openrouter_getting_key_title",
              value: localizer(
                locale,
                "commands.help.apikey.openrouter_getting_key_description",
                {
                  configSetup: configSetupMention,
                  configApikeySet: configApikeySetMention,
                },
              ),
              inline: false,
            },
            {
              nameKey: "commands.help.apikey.openrouter_model_selection_title",
              value: localizer(
                locale,
                "commands.help.apikey.openrouter_model_selection_description",
                {
                  supportServer: supportServerMention,
                },
              ),
              inline: false,
            },
            {
              nameKey: "commands.help.apikey.openrouter_pricing_title",
              value: localizer(
                locale,
                "commands.help.apikey.openrouter_pricing_description",
              ),
              inline: false,
            },
            {
              nameKey: "commands.help.apikey.openrouter_settings_title",
              value: localizer(
                locale,
                "commands.help.apikey.openrouter_settings_description",
              ),
              inline: false,
            },
          ],
          footerKey: "commands.help.apikey.openrouter_footer",
          footerVars: {
            configModel: configModelMention,
          },
        };
        break;

      case "zai":
        embedOptions = {
          titleKey: "commands.help.apikey.zai_title",
          descriptionKey: "commands.help.apikey.zai_description",
          color: ColorCode.INFO,
          fields: [
            {
              nameKey: "commands.help.apikey.zai_general_endpoint_title",
              value: localizer(
                locale,
                "commands.help.apikey.zai_general_endpoint_description",
              ),
              inline: false,
            },
            {
              nameKey: "commands.help.apikey.zai_coding_endpoint_title",
              value: localizer(
                locale,
                "commands.help.apikey.zai_coding_endpoint_description",
              ),
              inline: false,
            },
            {
              nameKey: "commands.help.apikey.zai_getting_key_title",
              value: localizer(
                locale,
                "commands.help.apikey.zai_getting_key_description",
                {
                  configSetup: configSetupMention,
                  configApikeySet: configApikeySetMention,
                },
              ),
              inline: false,
            },
            {
              nameKey: "commands.help.apikey.zai_model_notes_title",
              value: localizer(
                locale,
                "commands.help.apikey.zai_model_notes_description",
              ),
              inline: false,
            },
          ],
          footerKey: "commands.help.apikey.zai_footer",
          footerVars: {
            configModel: configModelMention,
          },
        };
        break;

      case "vertex":
        embedOptions = {
          titleKey: "commands.help.apikey.vertex_title",
          descriptionKey: "commands.help.apikey.vertex_description",
          color: ColorCode.INFO,
          fields: [
            {
              nameKey: "commands.help.apikey.vertex_getting_key_title",
              value: localizer(
                locale,
                "commands.help.apikey.vertex_getting_key_description",
                {
                  configSetup: configSetupMention,
                  configApikeySet: configApikeySetMention,
                },
              ),
              inline: false,
            },
            {
              nameKey: "commands.help.apikey.vertex_important_title",
              value: localizer(
                locale,
                "commands.help.apikey.vertex_important_description",
              ),
              inline: false,
            },
          ],
          footerKey: "commands.help.apikey.vertex_footer",
          footerVars: {
            configModel: configModelMention,
          },
        };
        break;

      case "elevenlabs":
        embedOptions = {
          titleKey: "commands.help.elevenlabs.title",
          descriptionKey: "commands.help.elevenlabs.description",
          color: ColorCode.INFO,
          fields: [
            {
              nameKey: "commands.help.elevenlabs.what_is_title",
              value: localizer(locale, "commands.help.elevenlabs.what_is_description"),
              inline: false,
            },
            {
              nameKey: "commands.help.elevenlabs.getting_key_title",
              value: localizer(
                locale,
                "commands.help.elevenlabs.getting_key_description",
                { optionalkeyElevenlabsSet: optionalkeyElevenlabsSetMention },
              ),
              inline: false,
            },
            {
              nameKey: "commands.help.elevenlabs.free_voices_title",
              value: localizer(
                locale,
                "commands.help.elevenlabs.free_voices_description",
                { configVoiceElevenlabs: configVoiceElevenlabsMention },
              ),
              inline: false,
            },
            {
              nameKey: "commands.help.elevenlabs.choosing_voice_title",
              value: localizer(
                locale,
                "commands.help.elevenlabs.choosing_voice_description",
                { configVoiceElevenlabs: configVoiceElevenlabsMention },
              ),
              inline: false,
            },
            {
              nameKey: "commands.help.elevenlabs.important_notes_title",
              value: localizer(
                locale,
                "commands.help.elevenlabs.important_notes_description",
                { optionalkeyElevenlabsRemove: optionalkeyElevenlabsRemoveMention },
              ),
              inline: false,
            },
          ],
          footerKey: "commands.help.elevenlabs.footer",
          footerVars: {
            optionalkeyElevenlabsRemove: optionalkeyElevenlabsRemoveMention,
          },
        };
        break;

      default:
        // Should never happen due to choices validation
        throw new Error(`Unknown provider: ${provider}`);
    }

    // Use replySummaryEmbed to show provider-specific guide
    await replySummaryEmbed(
      interaction,
      locale,
      embedOptions,
      MessageFlags.Ephemeral,
    );
  } catch (error) {
    // Log error with context
    const context: ErrorContext = {
      userId: userData.user_id,
      errorType: "CommandExecutionError",
      metadata: {
        commandName: "/help apikey",
        guildDiscordId: interaction.guild?.id,
      },
    };
    await log.error(
      "Error executing /help apikey command",
      error as Error,
      context,
    );

    // Inform user of error (ephemeral)
    const errorMessage = localizer(
      locale,
      "general.errors.unknown_error_description",
    );
    try {
      if (interaction.replied || interaction.deferred) {
        await interaction.followUp({
          content: errorMessage,
          flags: MessageFlags.Ephemeral,
        });
      } else {
        await interaction.reply({
          content: errorMessage,
          flags: MessageFlags.Ephemeral,
        });
      }
    } catch (replyError) {
      // Log if even the error reply fails
      log.error(
        "Failed to send error reply for /help apikey",
        replyError,
        context,
      );
    }
  }
}
