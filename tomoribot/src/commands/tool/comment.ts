import type { Client, ChatInputCommandInteraction } from "discord.js";
import {
  MessageFlags,
  type SlashCommandSubcommandBuilder,
  EmbedBuilder,
  ChannelType,
} from "discord.js";
import { localizer } from "@/utils/text/localizer";
import { ColorCode } from "@/utils/misc/logger";
import {
  replyInfoEmbed,
  promptWithPaginatedModal,
} from "@/utils/discord/interactionHelper";
import type { UserRow } from "@/types/db/schema";

/**
 * Configures the /tool comment subcommand
 * @param subcommand - The slash command subcommand builder
 * @returns Configured subcommand builder
 */
export const configureSubcommand = (
  subcommand: SlashCommandSubcommandBuilder,
) => {
  return subcommand
    .setName("comment")
    .setDescription(localizer("en-US", "commands.tool.comment.description"));
};

/**
 * Executes the /tool comment command
 * Sends an embed with user input text and a footer showing who created the comment
 * @param client - Discord client
 * @param interaction - Command interaction
 * @param userData - User data from database (unused)
 * @param locale - User's locale
 */
export async function execute(
  _client: Client,
  interaction: ChatInputCommandInteraction,
  _userData: UserRow,
  locale: string,
): Promise<void> {
  // 1. Fast validation
  if (!interaction.guild || !interaction.channel) {
    await replyInfoEmbed(interaction, locale, {
      titleKey: "general.errors.guild_only_title",
      descriptionKey: "general.errors.guild_only_description",
      color: ColorCode.WARN,
      flags: MessageFlags.Ephemeral,
    });
    return;
  }

  // Narrow channel type to TextChannel
  if (interaction.channel.type !== ChannelType.GuildText) {
    await replyInfoEmbed(interaction, locale, {
      titleKey: "commands.tool.comment.invalid_channel_title",
      descriptionKey: "commands.tool.comment.invalid_channel_description",
      color: ColorCode.WARN,
      flags: MessageFlags.Ephemeral,
    });
    return;
  }

  const channel = interaction.channel;

  // 2. Show modal for comment content
  // DO NOT defer before modal - Pattern 3
  const modalResult = await promptWithPaginatedModal(interaction, locale, {
    modalCustomId: "tool_comment_modal",
    modalTitleKey: "commands.tool.comment.modal_title",
    components: [
      {
        customId: "comment_content",
        labelKey: "commands.tool.comment.content_label",
        placeholder: localizer(
          locale,
          "commands.tool.comment.content_placeholder",
        ),
        required: true,
        minLength: 1,
        maxLength: 4000,
        style: 2, // TextInputStyle.Paragraph
      },
    ],
  });

  // 3. Process modal submission
  if (
    modalResult.outcome !== "submit" ||
    !modalResult.values ||
    !modalResult.interaction
  ) {
    return;
  }

  // Ensure submission is deferred
  if (!modalResult.interaction.deferred && !modalResult.interaction.replied) {
    await modalResult.interaction.deferReply({ flags: MessageFlags.Ephemeral });
  }

  const rawContent = modalResult.values.comment_content || "";

  // 4. Resolve :emojiName: patterns into Discord custom emoji syntax if found in guild
  const commentContent = rawContent.replace(/:(\w+):/g, (match, name) => {
    const emoji = interaction.guild?.emojis.cache.find(
      (e) => e.name === name,
    );
    if (!emoji) return match;
    // Animated emojis use <a:name:id>, static use <:name:id>
    return emoji.animated ? `<a:${emoji.name}:${emoji.id}>` : `<:${emoji.name}:${emoji.id}>`;
  });

  // 5. Create embed with comment content
  const embed = new EmbedBuilder()
    .setDescription(commentContent)
    .setColor(ColorCode.INFO);

  // 6. Add footer showing who created the comment (with profile picture)
  const memberAvatarUrl = interaction.member
    ? (interaction.member as import("discord.js").GuildMember).displayAvatarURL(
        {
          size: 64,
          extension: "png",
          forceStatic: true,
        },
      )
    : interaction.user.displayAvatarURL({
        size: 64,
        extension: "png",
        forceStatic: true,
      });

  embed.setFooter({
    text: localizer(locale, "commands.tool.comment.footer", {
      user: interaction.user.username,
    }),
    iconURL: memberAvatarUrl,
  });

  // 7. Send as public message in the channel
  await channel.send({
    embeds: [embed],
  });

  // 8. Send confirmation to user
  await replyInfoEmbed(modalResult.interaction, locale, {
    titleKey: "commands.tool.comment.success_title",
    descriptionKey: "commands.tool.comment.success_description",
    color: ColorCode.SUCCESS,
  });
}
