import type {
  ChatInputCommandInteraction,
  Client,
  SlashCommandSubcommandBuilder,
} from "discord.js";
import { getCachedTomoriState } from "@/utils/cache/tomoriStateCache";
import {
  getAllWhitelistChannels,
  removeChannelWhitelist,
} from "@/utils/db/channelWhitelist";
import {
  getAllWhitelistRoles,
  removeRoleWhitelist,
} from "@/utils/db/roleWhitelist";
import { invalidateWhitelistCache } from "@/utils/cache/channelWhitelistCache";
import { localizer } from "@/utils/text/localizer";
import { log, ColorCode } from "@/utils/misc/logger";
import {
  replyInfoEmbed,
  promptWithRawModal,
} from "@/utils/discord/interactionHelper";
import type {
  ErrorContext,
  RoleWhitelistRow,
  UserRow,
} from "@/types/db/schema";
import type {
  CheckboxGroupOption,
  ModalCheckboxGroupField,
} from "@/types/discord/modal";
import { CooldownType } from "@/types/db/schema";

/**
 * Modal custom ID for channel whitelist removal
 */
const MODAL_CUSTOM_ID = "server_whitelist_remove_modal";
const CHANNEL_CHECKBOX_ID_PREFIX = "channel_checkbox_group";
const ROLE_CHECKBOX_ID_PREFIX = "role_checkbox_group";
const MAX_OPTIONS_PER_GROUP = 10;
const MAX_GROUPS_PER_MODAL = 5;
const MAX_ENTRIES_PER_MODAL = MAX_OPTIONS_PER_GROUP * MAX_GROUPS_PER_MODAL;

/**
 * Configure the /server whitelist remove subcommand
 * Allows server managers to remove channels and roles from the whitelist
 */
export const configureSubcommand = (
  subcommand: SlashCommandSubcommandBuilder,
) =>
  subcommand
    .setName("remove")
    .setDescription(
      localizer("en-US", "commands.server.whitelist.remove.description"),
    );

/**
 * Execute the /server whitelist remove command
 * Shows a modal with all whitelisted channels and roles as checkboxes (all checked by default)
 * Unchecked entries will be removed from the whitelist
 */
export async function execute(
  _client: Client,
  interaction: ChatInputCommandInteraction,
  user: UserRow,
  locale: string,
): Promise<void> {
  const errorContext: ErrorContext = {
    userId: user.user_id,
    serverId: null,
    tomoriId: null,
  };

  try {
    // 1. Validate guild context
    if (!interaction.guild || !interaction.guildId) {
      await replyInfoEmbed(interaction, locale, {
        color: ColorCode.ERROR,
        titleKey: "general.errors.guild_only_title",
        descriptionKey: "general.errors.guild_only_description",
      });
      return;
    }

    // 2. Get Tomori state for server
    const tomoriState = await getCachedTomoriState(interaction.guildId);
    if (!tomoriState) {
      await replyInfoEmbed(interaction, locale, {
        color: ColorCode.ERROR,
        titleKey: "general.errors.tomori_not_setup_title",
        descriptionKey: "general.errors.tomori_not_setup_description",
      });
      return;
    }

    errorContext.serverId = tomoriState.server_id;
    errorContext.tomoriId = tomoriState.tomori_id;

    // 3. Get all whitelisted channels and roles for this server
    const [whitelistChannels, whitelistRoles] = await Promise.all([
      getAllWhitelistChannels(tomoriState.server_id),
      getAllWhitelistRoles(tomoriState.server_id),
    ]);

    // 4. Check if there are any whitelisted entries
    if (whitelistChannels.length === 0 && whitelistRoles.length === 0) {
      await replyInfoEmbed(interaction, locale, {
        color: ColorCode.WARN,
        titleKey: "commands.server.whitelist.remove.no_entries_title",
        descriptionKey:
          "commands.server.whitelist.remove.no_entries_description",
      });
      return;
    }

    // 5. Discord checkbox groups allow at most 10 options each and 5 groups per modal
    const channelGroupCount = Math.ceil(
      whitelistChannels.length / MAX_OPTIONS_PER_GROUP,
    );
    const roleGroupCount = Math.ceil(
      whitelistRoles.length / MAX_OPTIONS_PER_GROUP,
    );
    const totalGroupCount = channelGroupCount + roleGroupCount;

    if (totalGroupCount > MAX_GROUPS_PER_MODAL) {
      await replyInfoEmbed(interaction, locale, {
        color: ColorCode.WARN,
        titleKey: "commands.server.whitelist.remove.too_many_entries_title",
        descriptionKey:
          "commands.server.whitelist.remove.too_many_entries_description",
        descriptionVars: {
          channel_count: whitelistChannels.length.toString(),
          role_count: whitelistRoles.length.toString(),
          max_entries: MAX_ENTRIES_PER_MODAL.toString(),
          max_groups: MAX_GROUPS_PER_MODAL.toString(),
        },
      });
      return;
    }

    // 6. Build checkbox groups by chunking whitelisted channels and roles into groups of 10
    const checkboxGroups: ModalCheckboxGroupField[] = [];

    for (let i = 0; i < whitelistChannels.length; i += MAX_OPTIONS_PER_GROUP) {
      const chunk = whitelistChannels.slice(i, i + MAX_OPTIONS_PER_GROUP);
      const groupIndex = Math.floor(i / MAX_OPTIONS_PER_GROUP);
      const options: CheckboxGroupOption[] = [];

      for (const entry of chunk) {
        try {
          const channel = await interaction.guild.channels.fetch(
            entry.channel_disc_id,
          );
          const description = getWhitelistChannelSummary(entry, locale);

          options.push({
            label: channel?.name ?? entry.channel_disc_id,
            value: entry.channel_disc_id,
            description: description.substring(0, 100),
            default: true,
          });
        } catch (error) {
          log.warn("Failed to fetch channel for whitelist remove", error);

          const description = getWhitelistChannelSummary(entry, locale);

          options.push({
            label: `Unknown (${entry.channel_disc_id.substring(0, 10)}...)`,
            value: entry.channel_disc_id,
            description: description.substring(0, 100),
            default: true,
          });
        }
      }

      checkboxGroups.push({
        kind: "checkboxGroup" as const,
        customId: `${CHANNEL_CHECKBOX_ID_PREFIX}_${groupIndex}`,
        labelKey:
          groupIndex === 0
            ? "commands.server.whitelist.remove.checkbox_label"
            : "commands.server.whitelist.remove.checkbox_label_continued",
        descriptionKey:
          groupIndex === 0
            ? "commands.server.whitelist.remove.checkbox_description"
            : undefined,
        minValues: 0,
        required: false,
        options,
      });
    }

    for (let i = 0; i < whitelistRoles.length; i += MAX_OPTIONS_PER_GROUP) {
      const chunk = whitelistRoles.slice(i, i + MAX_OPTIONS_PER_GROUP);
      const groupIndex = Math.floor(i / MAX_OPTIONS_PER_GROUP);
      const options = await buildRoleCheckboxOptions(interaction, chunk);

      checkboxGroups.push({
        kind: "checkboxGroup" as const,
        customId: `${ROLE_CHECKBOX_ID_PREFIX}_${groupIndex}`,
        labelKey:
          groupIndex === 0
            ? "commands.server.whitelist.remove.role_checkbox_label"
            : "commands.server.whitelist.remove.role_checkbox_label_continued",
        descriptionKey:
          groupIndex === 0
            ? "commands.server.whitelist.remove.role_checkbox_description"
            : undefined,
        minValues: 0,
        required: false,
        options,
      });
    }

    // 7. Show the modal with checkbox groups for whitelist removal
    const modalResult = await promptWithRawModal(interaction, locale, {
      modalCustomId: MODAL_CUSTOM_ID,
      modalTitleKey: "commands.server.whitelist.remove.modal_title",
      components: checkboxGroups,
    });

    // 8. Handle modal outcome
    if (modalResult.outcome !== "submit") {
      log.info(
        `Whitelist removal modal ${modalResult.outcome} for user ${user.user_id}`,
      );
      return;
    }

    // 9. Extract checked entry IDs from all checkbox groups in the modal
    const modalSubmitInteraction = modalResult.interaction;
    const checkedChannelIds = new Set<string>();
    const checkedRoleIds = new Set<string>();

    for (let groupIndex = 0; groupIndex < channelGroupCount; groupIndex++) {
      const groupValues =
        modalResult.multiValues?.[
          `${CHANNEL_CHECKBOX_ID_PREFIX}_${groupIndex}`
        ] ?? [];
      for (const channelId of groupValues) {
        checkedChannelIds.add(channelId);
      }
    }

    for (let groupIndex = 0; groupIndex < roleGroupCount; groupIndex++) {
      const groupValues =
        modalResult.multiValues?.[
          `${ROLE_CHECKBOX_ID_PREFIX}_${groupIndex}`
        ] ?? [];
      for (const roleId of groupValues) {
        checkedRoleIds.add(roleId);
      }
    }

    if (!modalSubmitInteraction) {
      log.error("Modal result unexpectedly missing interaction");
      return;
    }

    // 10. Find entries to remove (those NOT checked in the modal)
    const channelsToRemove: string[] = [];
    for (const entry of whitelistChannels) {
      if (!checkedChannelIds.has(entry.channel_disc_id)) {
        channelsToRemove.push(entry.channel_disc_id);
      }
    }

    const rolesToRemove: string[] = [];
    for (const entry of whitelistRoles) {
      if (!checkedRoleIds.has(entry.role_disc_id)) {
        rolesToRemove.push(entry.role_disc_id);
      }
    }

    // 11. If no entries selected for removal, inform user
    if (channelsToRemove.length === 0 && rolesToRemove.length === 0) {
      await replyInfoEmbed(modalSubmitInteraction, locale, {
        color: ColorCode.INFO,
        titleKey: "commands.server.whitelist.remove.no_removals_title",
        descriptionKey:
          "commands.server.whitelist.remove.no_removals_description",
      });
      return;
    }

    // 12. Remove all unchecked entries from the whitelist
    const [channelResults, roleResults] = await Promise.all([
      Promise.all(
        channelsToRemove.map((channelId) =>
          removeChannelWhitelist(tomoriState.server_id, channelId),
        ),
      ),
      Promise.all(
        rolesToRemove.map((roleId) =>
          removeRoleWhitelist(tomoriState.server_id, roleId),
        ),
      ),
    ]);

    const failedRemovals =
      channelResults.filter((result) => !result).length +
      roleResults.filter((result) => !result).length;

    if (failedRemovals > 0) {
      await replyInfoEmbed(modalSubmitInteraction, locale, {
        color: ColorCode.ERROR,
        titleKey: "general.errors.unknown_error_title",
        descriptionKey: "general.errors.unknown_error_description",
      });
      return;
    }

    // 13. Invalidate whitelist cache for this server
    invalidateWhitelistCache(interaction.guildId);

    // 14. Get names for success message
    const removedChannelNames: string[] = [];
    for (const channelId of channelsToRemove) {
      try {
        const channel = await interaction.guild.channels.fetch(channelId);
        removedChannelNames.push(channel?.name ?? channelId);
      } catch {
        removedChannelNames.push(channelId);
      }
    }

    const removedRoleNames: string[] = [];
    for (const roleId of rolesToRemove) {
      try {
        const role = await interaction.guild.roles.fetch(roleId);
        removedRoleNames.push(role ? `<@&${role.id}>` : roleId);
      } catch {
        removedRoleNames.push(roleId);
      }
    }

    // 15. Send success message
    await replyInfoEmbed(
      modalSubmitInteraction,
      locale,
      {
        color: ColorCode.SUCCESS,
        titleKey: "commands.server.whitelist.remove.success_title",
        descriptionKey: "commands.server.whitelist.remove.success_description",
        descriptionVars: {
          channels_removed:
            removedChannelNames.length > 0
              ? formatRemovedNames(removedChannelNames)
              : localizer(locale, "general.none"),
          roles_removed:
            removedRoleNames.length > 0
              ? formatRemovedNames(removedRoleNames)
              : localizer(locale, "general.none"),
        },
      },
      undefined,
    );

    log.info(
      `Whitelist entries removed in server ${interaction.guildId}: channels=[${channelsToRemove.join(", ")}], roles=[${rolesToRemove.join(", ")}]`,
    );
  } catch (error) {
    log.error(
      "Error executing /server whitelist remove command",
      error,
      errorContext,
    );

    if (!interaction.replied && !interaction.deferred) {
      await replyInfoEmbed(interaction, locale, {
        color: ColorCode.ERROR,
        titleKey: "general.errors.unknown_error_title",
        descriptionKey: "general.errors.unknown_error_description",
      });
    }
  }
}

async function buildRoleCheckboxOptions(
  interaction: ChatInputCommandInteraction,
  entries: RoleWhitelistRow[],
): Promise<CheckboxGroupOption[]> {
  const options: CheckboxGroupOption[] = [];

  for (const entry of entries) {
    try {
      const role = await interaction.guild?.roles.fetch(entry.role_disc_id);
      options.push({
        label: role?.name ?? entry.role_disc_id,
        value: entry.role_disc_id,
        default: true,
      });
    } catch (error) {
      log.warn("Failed to fetch role for whitelist remove", error);
      options.push({
        label: `Unknown (${entry.role_disc_id.substring(0, 10)}...)`,
        value: entry.role_disc_id,
        default: true,
      });
    }
  }

  return options;
}

/**
 * Get localized summary text for a whitelist channel's cooldown behavior.
 * @param entry - Whitelist entry to summarize
 * @param locale - The locale to use for localization
 * @returns Localized summary text
 */
function getWhitelistChannelSummary(
  entry: { cooldown_type: CooldownType | null; cooldown_length: number | null },
  locale: string,
): string {
  if (entry.cooldown_type === null || entry.cooldown_length === null) {
    return localizer(locale, "commands.choices.inherit_global");
  }

  const cooldownTypeName = getCooldownTypeName(entry.cooldown_type, locale);
  return entry.cooldown_type === CooldownType.OFF
    ? cooldownTypeName
    : `${cooldownTypeName}, ${entry.cooldown_length}s`;
}

/**
 * Get localized name for a cooldown type
 * @param cooldownType - The cooldown type
 * @param locale - The locale to use for localization
 * @returns Localized cooldown type name
 */
function getCooldownTypeName(cooldownType: CooldownType, locale: string): string {
  const key = getCooldownTypeKey(cooldownType);
  return localizer(locale, `commands.config.cooldown.type.choice_${key}`);
}

/**
 * Get the locale key suffix for a cooldown type
 * @param cooldownType - The cooldown type
 * @returns The locale key suffix (e.g., "off", "per_user", "per_channel")
 */
function getCooldownTypeKey(cooldownType: CooldownType): string {
  switch (cooldownType) {
    case CooldownType.OFF:
      return "off";
    case CooldownType.PER_USER:
      return "per_user";
    case CooldownType.PER_CHANNEL:
      return "per_channel";
    case CooldownType.SERVER_WIDE:
      return "server_wide";
    case CooldownType.STRICT_SERVER_WIDE:
      return "strict_server_wide";
    default:
      return "off";
  }
}

function formatRemovedNames(names: string[]): string {
  const maxVisibleNames = 10;
  const visibleNames = names.slice(0, maxVisibleNames);
  const suffix = names.length > maxVisibleNames ? ", ..." : "";
  return `${visibleNames.join(", ")}${suffix}`;
}
