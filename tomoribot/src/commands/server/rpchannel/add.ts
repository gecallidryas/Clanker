import {
  ChannelType,
  MessageFlags,
  type ChatInputCommandInteraction,
  type Client,
  type SlashCommandSubcommandBuilder,
} from "discord.js";
import { sql } from "@/utils/db/client";
import {
  getCachedTomoriState,
  invalidateTomoriStateCache,
} from "../../../utils/cache/tomoriStateCache";
import { tomoriConfigSchema } from "../../../types/db/schema";
import { localizer } from "../../../utils/text/localizer";
import { log, ColorCode } from "../../../utils/misc/logger";
import { replyInfoEmbed } from "../../../utils/discord/interactionHelper";
import type { UserRow, ErrorContext } from "../../../types/db/schema";

/**
 * Configures the `/server rpchannel add` subcommand.
 * @param subcommand - The subcommand builder to configure
 * @returns The configured subcommand builder
 */
export const configureSubcommand = (
  subcommand: SlashCommandSubcommandBuilder,
) =>
  subcommand
    .setName("add")
    .setDescription(
      localizer("en-US", "commands.server.rpchannel.add.description"),
    )
    .addChannelOption((option) =>
      option
        .setName("channel")
        .setDescription(
          localizer(
            "en-US",
            "commands.server.rpchannel.add.channel_description",
          ),
        )
        .addChannelTypes(ChannelType.GuildText)
        .setRequired(true),
    );

/**
 * Adds a channel to the RP channel list, permanently suppressing emojis and stickers there.
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
  // Ensure command is run in a guild
  if (!interaction.guild || !interaction.channel) {
    await replyInfoEmbed(interaction, userData.language_pref, {
      titleKey: "general.errors.guild_only_title",
      descriptionKey: "general.errors.guild_only_description",
      color: ColorCode.ERROR,
    });
    return;
  }

  // 1. Defer before async work to avoid 3-second interaction timeout
  await interaction.deferReply({ flags: MessageFlags.Ephemeral });

  try {
    const channel = interaction.options.getChannel("channel", true);

    // 2. Load the current Tomori state for this server
    const tomoriState = await getCachedTomoriState(interaction.guild.id);
    if (!tomoriState) {
      await replyInfoEmbed(interaction, locale, {
        titleKey: "general.errors.tomori_not_setup_title",
        descriptionKey: "general.errors.tomori_not_setup_description",
        color: ColorCode.ERROR,
      });
      return;
    }

    // 3. Check if the channel is already in the RP channel list
    const currentChannels = tomoriState.config.rp_channel_ids || [];
    if (currentChannels.includes(channel.id)) {
      await replyInfoEmbed(interaction, locale, {
        titleKey: "commands.server.rpchannel.add.already_added_title",
        descriptionKey:
          "commands.server.rpchannel.add.already_added_description",
        descriptionVars: {
          channel_name: channel.name ?? "UNDEFINED_CH",
        },
        color: ColorCode.WARN,
      });
      return;
    }

    // 4. Build the updated channel array and convert to PostgreSQL array literal
    const updatedChannels = [...currentChannels, channel.id];
    const channelsArrayLiteral = `{${updatedChannels
      .map((id) => `"${id.replace(/(["\\])/g, "\\$1")}"`)
      .join(",")}}`;

    // 5. Persist to database
    const [updatedRow] = await sql`
      UPDATE tomori_configs
      SET rp_channel_ids = ${channelsArrayLiteral}::text[]
      WHERE server_id = ${tomoriState.server_id}
      RETURNING *
    `;

    if (!updatedRow) {
      const context: ErrorContext = {
        tomoriId: tomoriState.tomori_id,
        errorType: "CommandExecutionError",
        metadata: {
          command: "server rpchannel add",
          guildId: interaction.guild.id,
          channelId: channel.id,
        },
      };
      await log.error(
        "Failed to update rp_channel_ids config",
        new Error("Database update failed"),
        context,
      );
      await replyInfoEmbed(interaction, locale, {
        titleKey: "general.errors.update_failed_title",
        descriptionKey: "general.errors.update_failed_description",
        color: ColorCode.ERROR,
      });
      return;
    }

    // 6. Validate the returned row shape
    const validatedConfig = tomoriConfigSchema.safeParse(updatedRow);
    if (!validatedConfig.success) {
      const context: ErrorContext = {
        tomoriId: tomoriState.tomori_id,
        errorType: "SchemaValidationError",
        metadata: {
          command: "server rpchannel add",
          validationErrors: validatedConfig.error.flatten(),
        },
      };
      await log.error(
        "Failed to validate updated config after rpchannel add",
        validatedConfig.error,
        context,
      );
      await replyInfoEmbed(interaction, locale, {
        titleKey: "general.errors.update_failed_title",
        descriptionKey: "general.errors.update_failed_description",
        color: ColorCode.ERROR,
      });
      return;
    }

    // 7. Invalidate cache so next message gets fresh config
    invalidateTomoriStateCache(interaction.guild.id);

    await replyInfoEmbed(interaction, locale, {
      titleKey: "commands.server.rpchannel.add.success_title",
      descriptionKey: "commands.server.rpchannel.add.success_description",
      descriptionVars: {
        channel_name: channel.name ?? "UNDEFINED_CH",
      },
      color: ColorCode.SUCCESS,
    });
  } catch (error) {
    const context: ErrorContext = {
      errorType: "CommandExecutionError",
      metadata: {
        command: "server rpchannel add",
        guildId: interaction.guild.id,
      },
    };
    await log.error("Error in /server rpchannel add command", error, context);
    await replyInfoEmbed(interaction, locale, {
      titleKey: "general.errors.unknown_error_title",
      descriptionKey: "general.errors.unknown_error_description",
      color: ColorCode.ERROR,
    });
  }
}
