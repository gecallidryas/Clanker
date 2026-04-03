import type {
  Client,
  ChatInputCommandInteraction,
  TextChannel,
  UserSelectMenuInteraction,
} from "discord.js";
import {
  MessageFlags,
  type SlashCommandSubcommandBuilder,
  EmbedBuilder,
  ChannelType,
  ActionRowBuilder,
  UserSelectMenuBuilder,
  ComponentType,
} from "discord.js";
import { localizer } from "@/utils/text/localizer";
import { ColorCode, log } from "@/utils/misc/logger";
import {
  replyInfoEmbed,
  promptWithPaginatedModal,
  safeSelectOptionText,
} from "@/utils/discord/interactionHelper";
import { loadAllPersonasForServer, loadTomoriState } from "@/utils/db/dbRead";
import {
  getOrCreateWebhook,
  resolvePersonaWebhookIdentity,
  sendWebhookMessageWithIdentity,
} from "@/utils/discord/webhookManager";
import type { SelectOption } from "@/types/discord/modal";
import type { UserRow } from "@/types/db/schema";
import tomoriChat from "@/events/messageCreate/tomoriChat";
import {
  checkMessageTriggerCooldownWithWhitelist,
  setMessageTriggerCooldownWithWhitelist,
} from "@/utils/db/cooldownManager";
import { CooldownType } from "@/types/db/schema";
import { getCooldownTypeFooterKey } from "@/utils/db/messageCooldown";
import { sendCooldownDM } from "@/utils/discord/cooldownDM";

/**
 * Configures the /bot impersonate subcommand
 * @param subcommand - The slash command subcommand builder
 * @returns Configured subcommand builder
 */
export const configureSubcommand = (
  subcommand: SlashCommandSubcommandBuilder,
) => {
  return subcommand
    .setName("impersonate")
    .setDescription(localizer("en-US", "commands.bot.impersonate.description"))
    .addStringOption((option) =>
      option
        .setName("target")
        .setDescription(
          localizer("en-US", "commands.bot.impersonate.target_description"),
        )
        .setRequired(true)
        .addChoices(
          {
            name: localizer("en-US", "commands.bot.impersonate.target_persona"),
            value: "persona",
          },
          {
            name: localizer("en-US", "commands.bot.impersonate.target_user"),
            value: "user",
          },
          {
            name: localizer("en-US", "commands.bot.impersonate.target_system"),
            value: "system",
          },
        ),
    );
};

/**
 * Handles user-target impersonation - prompt for a user, then run user impersonation flow
 * @param client - Discord client
 * @param interaction - Command interaction
 * @param locale - User's locale
 */
async function handleTargetUserImpersonation(
  client: Client,
  interaction: ChatInputCommandInteraction,
  locale: string,
): Promise<void> {
  const userSelect = new UserSelectMenuBuilder()
    .setCustomId("impersonate_target_user_select")
    .setPlaceholder(
      localizer(locale, "commands.bot.impersonate.user_select_placeholder"),
    )
    .setMinValues(1)
    .setMaxValues(1);

  const selectEmbed = new EmbedBuilder()
    .setTitle(localizer(locale, "commands.bot.impersonate.user_select_title"))
    .setDescription(
      localizer(locale, "commands.bot.impersonate.user_select_description"),
    )
    .setColor(ColorCode.INFO);

  await interaction.reply({
    embeds: [selectEmbed],
    components: [
      new ActionRowBuilder<UserSelectMenuBuilder>().addComponents(userSelect),
    ],
    flags: MessageFlags.Ephemeral,
  });

  const promptMessage = await interaction.fetchReply();
  let userSelectInteraction: UserSelectMenuInteraction;

  try {
    userSelectInteraction = await promptMessage.awaitMessageComponent({
      componentType: ComponentType.UserSelect,
      filter: (i: UserSelectMenuInteraction) =>
        i.user.id === interaction.user.id,
      time: 60_000,
    });
  } catch (_error) {
    log.warn(
      `[/bot impersonate user] User select prompt timed out for user ${interaction.user.id}`,
    );
    await replyInfoEmbed(interaction, locale, {
      titleKey: "general.interaction.timeout_title",
      descriptionKey: "general.interaction.timeout_description",
      color: ColorCode.WARN,
    });
    return;
  }

  await userSelectInteraction.deferUpdate();
  await interaction.editReply({ components: [] });

  const selectedUserId = userSelectInteraction.values[0];
  const selectedUser = userSelectInteraction.users.get(selectedUserId);
  const selectedMember = interaction.guild?.members.cache.get(selectedUserId);
  const selectedDisplayName =
    selectedMember?.displayName ||
    selectedUser?.displayName ||
    selectedUser?.username ||
    "User";

  await handleUserImpersonation(
    client,
    interaction,
    locale,
    selectedUserId,
    selectedDisplayName,
    "user",
  );
}

/**
 * Handles persona impersonation - user sends messages as bot personas
 * @param client - Discord client
 * @param interaction - Command interaction
 * @param locale - User's locale
 */
async function handlePersonaImpersonation(
  _client: Client,
  interaction: ChatInputCommandInteraction,
  locale: string,
): Promise<void> {
  if (!interaction.guild || !interaction.channel) {
    await replyInfoEmbed(interaction, locale, {
      titleKey: "commands.bot.impersonate.missing_permissions_title",
      descriptionKey:
        "commands.bot.impersonate.missing_permissions_description",
      color: ColorCode.WARN,
      flags: MessageFlags.Ephemeral,
    });
    return;
  }

  // Narrow channel type to TextChannel
  if (interaction.channel.type !== ChannelType.GuildText) {
    await replyInfoEmbed(interaction, locale, {
      titleKey: "commands.bot.impersonate.missing_permissions_title",
      descriptionKey:
        "commands.bot.impersonate.missing_permissions_description",
      color: ColorCode.WARN,
      flags: MessageFlags.Ephemeral,
    });
    return;
  }

  const serverId = interaction.guild.id;
  const channel = interaction.channel as TextChannel;

  // 1. Load all personas (main + alters) - keep this under 3 seconds
  const allPersonas = await loadAllPersonasForServer(serverId);
  if (!allPersonas || allPersonas.length === 0) {
    await replyInfoEmbed(interaction, locale, {
      titleKey: "commands.bot.impersonate.no_personas_title",
      descriptionKey: "commands.bot.impersonate.no_personas_description",
      color: ColorCode.WARN,
      flags: MessageFlags.Ephemeral,
    });
    return;
  }

  // 2. Build select options for modal
  const personaSelectOptions: SelectOption[] = allPersonas.map(
    (persona, index) => ({
      label: safeSelectOptionText(persona.tomori_nickname),
      value: index.toString(), // Use index to avoid ID truncation issues
      description: persona.is_alter ? "Alter Persona" : "Main Persona",
    }),
  );

  // 3. Show modal with persona select + message text area
  // DO NOT defer before modal - Pattern 3
  const modalResult = await promptWithPaginatedModal(interaction, locale, {
    modalCustomId: "impersonate_persona_modal",
    modalTitleKey: "commands.bot.impersonate.persona_modal_title",
    components: [
      {
        customId: "persona_select",
        labelKey: "commands.bot.impersonate.persona_select_label",
        placeholder: localizer(
          locale,
          "commands.bot.impersonate.persona_select_placeholder",
        ),
        required: true,
        options: personaSelectOptions,
      },
      {
        customId: "message_content",
        labelKey: "commands.bot.impersonate.persona_message_label",
        placeholder: localizer(
          locale,
          "commands.bot.impersonate.persona_message_placeholder",
        ),
        required: true,
        minLength: 1,
        maxLength: 2000,
        style: 2, // TextInputStyle.Paragraph
      },
    ],
  });

  // 4. Process modal submission
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

  const selectedIndex = Number.parseInt(
    modalResult.values.persona_select || "0",
    10,
  );
  const messageContent = modalResult.values.message_content || "";

  const selectedPersona = allPersonas[selectedIndex];
  if (!selectedPersona || !selectedPersona.tomori_id) {
    log.error(
      `Selected persona at index ${selectedIndex} not found in persona list`,
    );
    await replyInfoEmbed(modalResult.interaction, locale, {
      titleKey: "general.errors.unknown_error_title",
      descriptionKey: "general.errors.unknown_error_description",
      color: ColorCode.ERROR,
      flags: MessageFlags.Ephemeral,
    });
    return;
  }

  try {
    // 5. Check hide_impersonation_embeds permission
    const tomoriState = allPersonas[0]; // Main persona has config
    const shouldHideEmbed =
      tomoriState?.config?.hide_impersonation_embeds ?? false;

    // 6. Build impersonation notice embed if needed
    const embeds: EmbedBuilder[] = [];
    if (!shouldHideEmbed) {
      const invokerAvatarUrl = interaction.member
        ? (
            interaction.member as import("discord.js").GuildMember
          ).displayAvatarURL({
            size: 64,
            extension: "png",
            forceStatic: true,
          })
        : interaction.user.displayAvatarURL({
            size: 64,
            extension: "png",
            forceStatic: true,
          });

      const noticeEmbed = new EmbedBuilder()
        .setDescription(
          localizer(
            locale,
            "commands.bot.impersonate.persona_impersonation_notice_description",
          ),
        )
        .setFooter({
          text: localizer(
            locale,
            "commands.bot.impersonate.persona_impersonation_notice_footer",
            { user: interaction.user.username },
          ),
          iconURL: invokerAvatarUrl,
        })
        .setColor(ColorCode.INFO);
      embeds.push(noticeEmbed);
    }

    // 7. Send message based on persona type
    if (!selectedPersona.is_alter) {
      // Main persona: Send as bot directly with embeds
      await channel.send({
        content: messageContent,
        embeds,
      });
    } else {
      // Alter persona: Send via webhook with embeds
      const { webhook, errorReason } = await getOrCreateWebhook(channel);
      if (!webhook) {
        await replyInfoEmbed(modalResult.interaction, locale, {
          titleKey: "commands.bot.impersonate.webhook_error_title",
          descriptionKey: "commands.bot.impersonate.webhook_error_description",
          descriptionVars: { error: errorReason || "Failed to create webhook" },
          color: ColorCode.ERROR,
        });
        return;
      }

      const identity = await resolvePersonaWebhookIdentity(
        selectedPersona,
        interaction.guild,
      );
      await sendWebhookMessageWithIdentity(
        webhook,
        {
          content: messageContent,
          embeds,
        },
        identity,
      );
    }

    // 8. Send success confirmation to user
    await replyInfoEmbed(modalResult.interaction, locale, {
      titleKey: "commands.bot.impersonate.persona_success_title",
      descriptionKey: "commands.bot.impersonate.persona_success_description",
      descriptionVars: { persona: selectedPersona.tomori_nickname },
      color: ColorCode.SUCCESS,
    });
  } catch (error) {
    log.error("Failed to send impersonated message", {
      error,
      personaId: selectedPersona.tomori_id,
      serverId,
    });
    await replyInfoEmbed(modalResult.interaction, locale, {
      titleKey: "commands.bot.impersonate.webhook_error_title",
      descriptionKey: "commands.bot.impersonate.webhook_error_description",
      descriptionVars: {
        error: error instanceof Error ? error.message : "Unknown error",
      },
      color: ColorCode.ERROR,
    });
  }
}

/**
 * Handles user impersonation - bot mimics the user through webhook
 * @param client - Discord client
 * @param interaction - Command interaction
 * @param locale - User's locale
 */
async function handleUserImpersonation(
  client: Client,
  interaction: ChatInputCommandInteraction,
  locale: string,
  impersonatedUserId: string = interaction.user.id,
  impersonatedDisplayName?: string,
  invokedTarget: "me" | "user" = "me",
): Promise<void> {
  if (!interaction.guild || !interaction.channel) {
    await replyInfoEmbed(interaction, locale, {
      titleKey: "commands.bot.impersonate.missing_permissions_title",
      descriptionKey:
        "commands.bot.impersonate.missing_permissions_description",
      color: ColorCode.WARN,
      flags: MessageFlags.Ephemeral,
    });
    return;
  }

  // Narrow channel type to TextChannel
  if (interaction.channel.type !== ChannelType.GuildText) {
    await replyInfoEmbed(interaction, locale, {
      titleKey: "commands.bot.impersonate.missing_permissions_title",
      descriptionKey:
        "commands.bot.impersonate.missing_permissions_description",
      color: ColorCode.WARN,
      flags: MessageFlags.Ephemeral,
    });
    return;
  }

  const channel = interaction.channel as TextChannel;
  const commandTarget = invokedTarget;
  const cooldownActiveKey =
    invokedTarget === "me"
      ? "commands.bot.impersonate.cooldown_active"
      : "commands.bot.impersonate.cooldown_active_user";
  const channelWhitelistKey =
    invokedTarget === "me"
      ? "commands.bot.impersonate.channel_not_whitelisted"
      : "commands.bot.impersonate.channel_not_whitelisted_user";

  log.info(
    `[/bot impersonate ${commandTarget}] Command invoked by user ${interaction.user.id} (${interaction.user.username}) in channel ${interaction.channel.id} targeting ${impersonatedUserId}`,
  );

  // 1. Defer the interaction immediately (Pattern 2 - async work ahead)
  if (!interaction.deferred && !interaction.replied) {
    await interaction.deferReply({ flags: MessageFlags.Ephemeral });
  }

  try {
    // 2. Load tomori state for cooldown configuration
    const tomoriState = await loadTomoriState(interaction.guild.id);
    if (!tomoriState) {
      await replyInfoEmbed(interaction, locale, {
        titleKey: "general.errors.unknown_error_title",
        descriptionKey: "general.errors.unknown_error_description",
        color: ColorCode.ERROR,
      });
      return;
    }

    // 3. Check cooldown (shares cooldown pool with message triggers and /bot respond)
    // Uses whitelist-aware version to respect per-channel cooldown overrides
    const cooldownType = tomoriState.config.cooldown_type ?? CooldownType.OFF;
    const cooldownLength = tomoriState.config.cooldown_length ?? 5;

    log.info(
      `[/bot impersonate ${commandTarget}] Checking cooldown - globalType: ${cooldownType}, globalLength: ${cooldownLength}s, guild: ${interaction.guild.id}, user: ${interaction.user.id}, channel: ${interaction.channel.id}`,
    );

    const cooldownResult = await checkMessageTriggerCooldownWithWhitelist(
      interaction.guild.id,
      interaction.user.id,
      interaction.channel.id,
      cooldownType,
      interaction.member as import("discord.js").GuildMember | null,
    );

    log.info(
      `[/bot impersonate ${commandTarget}] Cooldown check result: ${cooldownResult.isOnCooldown ? "ON COOLDOWN" : "NOT ON COOLDOWN"}, remaining: ${cooldownResult.remainingSeconds}s`,
    );

    if (cooldownResult.isOnCooldown) {
      // If blocked by whitelist, show a specific "not whitelisted" message instead of cooldown
      if (cooldownResult.blockedByWhitelist) {
        await replyInfoEmbed(interaction, locale, {
          titleKey: "general.message_cooldown_title",
          descriptionKey: channelWhitelistKey,
          color: ColorCode.WARN,
        });
        return;
      }

      // Show cooldown warning via DM (with ephemeral fallback)
      const footerKey = getCooldownTypeFooterKey(cooldownResult.cooldownType);
      await sendCooldownDM(
        interaction.user,
        locale,
        "general.message_cooldown_title",
        cooldownActiveKey,
        {
          seconds: cooldownResult.remainingSeconds.toString(),
          botName: tomoriState.tomori_nickname,
        },
        footerKey,
        interaction,
        MessageFlags.Ephemeral,
      );
      return;
    }

    // 4. Get the latest message in the channel to use as a "passport"
    // Same pattern as /bot respond - no placeholder message needed
    const messages = await channel.messages.fetch({ limit: 1 });
    const latestMessage = messages.first();

    if (!latestMessage) {
      await replyInfoEmbed(interaction, locale, {
        titleKey: "commands.bot.impersonate.no_messages_title",
        descriptionKey: "commands.bot.impersonate.no_messages_description",
        color: ColorCode.WARN,
      });
      return;
    }

    const member = interaction.guild.members.cache.get(impersonatedUserId);
    const displayName =
      impersonatedDisplayName ||
      member?.displayName ||
      member?.user.displayName ||
      "User";

    // 5. Show public impersonation notice if enabled in permissions
    if (!(tomoriState.config.hide_impersonation_embeds ?? false)) {
      try {
        const invokerAvatarUrl = interaction.member
          ? (
              interaction.member as import("discord.js").GuildMember
            ).displayAvatarURL({
              size: 64,
              extension: "png",
              forceStatic: true,
            })
          : interaction.user.displayAvatarURL({
              size: 64,
              extension: "png",
              forceStatic: true,
            });

        const noticeEmbed = new EmbedBuilder()
          .setDescription(
            localizer(
              locale,
              "commands.bot.impersonate.user_impersonation_notice_description",
            ),
          )
          .setFooter({
            text: localizer(
              locale,
              "commands.bot.impersonate.user_impersonation_notice_footer",
              { user: interaction.user.username, target: displayName },
            ),
            iconURL: invokerAvatarUrl,
          })
          .setColor(ColorCode.INFO);

        const impersonatedUser =
          member?.user ||
          (await client.users.fetch(impersonatedUserId).catch(() => null));
        const impersonatedAvatarUrl =
          member?.displayAvatarURL({
            size: 1024,
            extension: "png",
            forceStatic: true,
          }) ||
          impersonatedUser?.displayAvatarURL({
            size: 1024,
            extension: "png",
            forceStatic: true,
          });

        const { webhook } = await getOrCreateWebhook(channel);
        if (webhook) {
          await webhook.send({
            embeds: [noticeEmbed],
            username: displayName,
            avatarURL: impersonatedAvatarUrl,
          });
        } else {
          log.warn(
            "Skipping user impersonation notice embed because no webhook was available",
            {
              channelId: interaction.channel.id,
              guildId: interaction.guild.id,
              impersonatedUserId,
            },
          );
        }
      } catch (noticeError) {
        log.warn("Failed to send user impersonation notice embed", {
          noticeError,
          channelId: interaction.channel.id,
          guildId: interaction.guild.id,
        });
      }
    }

    // 6. Call tomoriChat with user impersonation enabled
    // tomoriChat will handle everything: context building, refresh embeds, provider call, webhook, etc.
    await tomoriChat(
      client,
      latestMessage,
      false, // Not from queue
      true, // isManuallyTriggered - bypasses bot author check
      undefined, // No forced reasoning
      undefined, // No reasoning query
      undefined, // No LLM override
      false, // Not a stop response
      0, // No retry count
      false, // Don't skip lock
      undefined, // No reminder recipient
      undefined, // No reminder data
      undefined, // No selected persona
      false, // Not a persona job
      true, // isUserImpersonation - enables role reversal
      impersonatedUserId, // impersonatedUserId - the user to mimic
      "user", // textQuotaSource
      interaction.id, // textQuotaTriggerKey
      interaction.user.id, // textQuotaUserDiscId
      undefined, // manualSystemPrompt
      undefined, // manualPrefill
      undefined, // naiContinuationPrefill
      undefined, // emptyResponseFinishReason
      undefined, // injectedContextItems
      undefined, // forcedMentions
      {
        userDiscId: interaction.user.id,
        username: interaction.user.username,
        locale,
        member: interaction.member as import("discord.js").GuildMember | null,
      },
    );

    // 7. Set cooldown after successful response (shares cooldown pool with message triggers and /bot respond)
    // Uses whitelist-aware version to respect per-channel cooldown overrides
    log.info(
      `[/bot impersonate ${commandTarget}] Setting cooldown - globalType: ${cooldownType}, globalLength: ${cooldownLength}s`,
    );
    await setMessageTriggerCooldownWithWhitelist(
      interaction.guild.id,
      interaction.user.id,
      interaction.channel.id,
      cooldownType,
      cooldownLength,
      interaction.member as import("discord.js").GuildMember | null,
    );
    log.info(`[/bot impersonate ${commandTarget}] Cooldown set successfully`);

    // 8. Send success confirmation

    await interaction.editReply({
      embeds: [
        new EmbedBuilder()
          .setTitle(
            localizer(locale, "commands.bot.impersonate.me_success_title"),
          )
          .setDescription(
            localizer(
              locale,
              "commands.bot.impersonate.me_success_description",
              { user: displayName },
            ),
          )
          .setColor(ColorCode.SUCCESS),
      ],
    });
  } catch (error) {
    log.error("Failed to handle user impersonation", {
      error,
      userId: interaction.user.id,
      impersonatedUserId,
      guildId: interaction.guild?.id,
    });

    // Check if interaction is still valid before replying
    if (interaction.deferred || interaction.replied) {
      const isTimeoutError =
        error instanceof Error && /timed?\s*out|timeout/i.test(error.message);
      const description = isTimeoutError
        ? localizer(locale, "genai.error_stream_timeout_description")
        : localizer(locale, "genai.generic_error_description", {
            error_message:
              error instanceof Error ? error.message : "Unknown error",
          });
      await interaction.editReply({
        embeds: [
          new EmbedBuilder()
            .setTitle(
              localizer(
                locale,
                isTimeoutError
                  ? "genai.error_stream_timeout_title"
                  : "genai.generic_error_title",
              ),
            )
            .setDescription(description)
            .setColor(ColorCode.ERROR),
        ],
      });
    }
  }
}

/**
 * Handles system impersonation - user injects system prompts as embeds
 * @param interaction - Command interaction
 * @param locale - User's locale
 */
async function handleSystemImpersonation(
  interaction: ChatInputCommandInteraction,
  locale: string,
): Promise<void> {
  if (!interaction.guild || !interaction.channel) {
    await replyInfoEmbed(interaction, locale, {
      titleKey: "commands.bot.impersonate.missing_permissions_title",
      descriptionKey:
        "commands.bot.impersonate.missing_permissions_description",
      color: ColorCode.WARN,
      flags: MessageFlags.Ephemeral,
    });
    return;
  }

  // Narrow channel type to TextChannel
  if (interaction.channel.type !== ChannelType.GuildText) {
    await replyInfoEmbed(interaction, locale, {
      titleKey: "commands.bot.impersonate.missing_permissions_title",
      descriptionKey:
        "commands.bot.impersonate.missing_permissions_description",
      color: ColorCode.WARN,
      flags: MessageFlags.Ephemeral,
    });
    return;
  }

  const channel = interaction.channel as TextChannel;

  // 1. Show modal for system prompt content
  // DO NOT defer before modal - Pattern 3
  const modalResult = await promptWithPaginatedModal(interaction, locale, {
    modalCustomId: "impersonate_system_modal",
    modalTitleKey: "commands.bot.impersonate.system_modal_title",
    components: [
      {
        customId: "system_content",
        labelKey: "commands.bot.impersonate.system_content_label",
        placeholder: localizer(
          locale,
          "commands.bot.impersonate.system_content_placeholder",
        ),
        required: true,
        minLength: 1,
        maxLength: 4000,
        style: 2, // TextInputStyle.Paragraph
      },
    ],
  });

  // 2. Process modal submission
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

  const systemContent = modalResult.values.system_content || "";

  // 3. Create embed with "System Message" title (triggers detection in tomoriChat)
  const embed = new EmbedBuilder()
    .setTitle(localizer(locale, "commands.bot.impersonate.system_title"))
    .setDescription(systemContent)
    .setColor(ColorCode.SECTION);

  // Add footer showing who injected the prompt
  const invokerAvatarUrl = interaction.member
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
    text: localizer(locale, "commands.bot.impersonate.system_injected_footer", {
      user: interaction.user.username,
    }),
    iconURL: invokerAvatarUrl,
  });

  // 4. Send as public message in the channel (not ephemeral - this is the injection)
  await channel.send({
    embeds: [embed],
  });

  // 5. Send confirmation to user
  await replyInfoEmbed(modalResult.interaction, locale, {
    titleKey: "commands.bot.impersonate.system_success_title",
    descriptionKey: "commands.bot.impersonate.system_success_description",
    color: ColorCode.SUCCESS,
  });
}

/**
 * Executes the /bot impersonate command
 * @param client - Discord client
 * @param interaction - Command interaction
 * @param userData - User data from database (unused)
 * @param locale - User's locale
 */
export async function execute(
  client: Client,
  interaction: ChatInputCommandInteraction,
  _userData: UserRow,
  locale: string,
): Promise<void> {
  // 1. Fast validation
  if (!interaction.guild) {
    await replyInfoEmbed(interaction, locale, {
      titleKey: "general.errors.guild_only_title",
      descriptionKey: "general.errors.guild_only_description",
      color: ColorCode.WARN,
      flags: MessageFlags.Ephemeral,
    });
    return;
  }

  // 2. Get target option
  const target = interaction.options.getString("target", true);

  // 3. Route to appropriate handler
  switch (target) {
    case "persona":
      await handlePersonaImpersonation(client, interaction, locale);
      break;
    case "user":
      await handleTargetUserImpersonation(client, interaction, locale);
      break;
    case "system":
      await handleSystemImpersonation(interaction, locale);
      break;
    default:
      log.error(`Invalid target option: ${target}`);
      await replyInfoEmbed(interaction, locale, {
        titleKey: "general.errors.unknown_error_title",
        descriptionKey: "general.errors.unknown_error_description",
        color: ColorCode.WARN,
        flags: MessageFlags.Ephemeral,
      });
  }
}
