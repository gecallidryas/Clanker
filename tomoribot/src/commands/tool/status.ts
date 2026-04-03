import type { SlashCommandSubcommandBuilder } from "discord.js";
import {
  type ChatInputCommandInteraction,
  type ButtonInteraction,
  type Client,
  MessageFlags,
  TextChannel,
} from "discord.js";
import {
  replyInfoEmbed,
  replyPaginatedStatusPages,
  replyPaginatedPersonaChoicesV2,
} from "../../utils/discord/interactionHelper";
import { ColorCode, log } from "../../utils/misc/logger";
import { localizer } from "../../utils/text/localizer";
import { getCachedTomoriState } from "../../utils/cache/tomoriStateCache";
import {
  getUserReminderCount,
  getBraveApiKeyStatus,
  getBlacklistedMemberIds,
  loadPersonalMemoriesForUserLineage,
  loadAllPersonasForServer,
  getServerRandomTriggers,
  getAllChannelLlmOverridesForServer,
} from "../../utils/db/dbRead";
import { getAllWhitelistChannels } from "../../utils/db/channelWhitelist";
import { getAllWhitelistRoles } from "@/utils/db/roleWhitelist";
import { getQuotaConfig } from "@/utils/quota/imageQuotaManager";
import { getTextQuotaConfig } from "@/utils/quota/textQuotaManager";
import type {
  UserRow,
  ChannelWhitelistRow,
  RoleWhitelistRow,
  RandomTriggerRow,
  LlmRow,
  TomoriConfigRow,
} from "../../types/db/schema";
import type { SummaryEmbedOptions } from "../../types/discord/embed";
import { CooldownType, PrivacyLevel, type TomoriState } from "../../types/db/schema";
import { formatBooleanLocalized } from "@/utils/text/stringHelper";
import { getMemoryLimits } from "@/utils/db/memoryLimits";
import { DEFAULT_SYSTEM_PROMPT } from "@/utils/text/contextBuilder";
import { formatLlmDisplayLabel } from "@/utils/provider/modelDisplay";

// Constants
const MAX_ITEMS_DISPLAY = 5; // Max channel/member items before switching to count-only
const MEMORY_TRUNCATE_LENGTH = 100; // Max chars per memory snippet
const ATTRIBUTE_TRUNCATE_LENGTH = 200; // Max chars per attribute snippet
const DIALOGUE_TRUNCATE_LENGTH = 140; // Max chars per sample dialogue side
const MAX_PROMPT_PREVIEW = Number.parseInt(
  process.env.SYSPROMPT_SHOW_MAX_PREVIEW || "3800",
  10,
); // Max chars shown for system/persona prompts

/**
 * Returns a user-friendly label for a privacy level.
 * @param locale - User locale
 * @param level - Privacy level value
 * @returns Localized privacy label
 */
function getPrivacyLevelLabel(locale: string, level: PrivacyLevel): string {
  switch (level) {
    case PrivacyLevel.MINIMAL:
      return localizer(locale, "commands.personal.privacy.choice_minimal");
    case PrivacyLevel.PARTIAL:
      return localizer(locale, "commands.personal.privacy.choice_partial");
    case PrivacyLevel.FULL:
      return localizer(locale, "commands.personal.privacy.choice_full");
    default:
      return localizer(locale, "commands.personal.privacy.choice_minimal");
  }
}

/**
 * Returns a localized label for a CooldownType value.
 * Reuses the choice labels defined in commands.server.cooldown.
 * @param locale - User locale
 * @param type - CooldownType enum value
 * @returns Localized cooldown type label
 */
function getCooldownTypeLabel(locale: string, type: CooldownType): string {
  switch (type) {
    case CooldownType.OFF:
      return localizer(
        locale,
        "commands.server.cooldown.triggers.type.choice_off",
      );
    case CooldownType.PER_USER:
      return localizer(
        locale,
        "commands.server.cooldown.triggers.type.choice_per_user",
      );
    case CooldownType.PER_CHANNEL:
      return localizer(
        locale,
        "commands.server.cooldown.triggers.type.choice_per_channel",
      );
    case CooldownType.SERVER_WIDE:
      return localizer(
        locale,
        "commands.server.cooldown.triggers.type.choice_server_wide",
      );
    case CooldownType.STRICT_SERVER_WIDE:
      return localizer(
        locale,
        "commands.server.cooldown.triggers.type.choice_strict_server_wide",
      );
    default:
      return localizer(
        locale,
        "commands.server.cooldown.triggers.type.choice_off",
      );
  }
}

function truncateText(input: string, maxLength: number): string {
  return input.length > maxLength
    ? `${input.substring(0, maxLength)}...`
    : input;
}

function formatQuotaLimitValue(locale: string, limit: number): string {
  return limit === 0
    ? localizer(locale, "commands.tool.status.field_quota_unlimited")
    : String(limit);
}

/**
 * Formats an array of strings as a numbered list, truncating each item.
 * All items are included (nothing omitted).
 * @param items - Array of strings to format
 * @param locale - User locale
 * @param truncateLength - Max chars per item before truncation
 * @returns Formatted numbered list, or localized "None" if empty
 */
function formatNumberedList(
  items: string[],
  locale: string,
  truncateLength: number,
): string {
  if (items.length === 0) {
    return localizer(locale, "commands.choices.none");
  }
  return items
    .map((item, index) => {
      return `${index + 1}. ${truncateText(item, truncateLength)}`;
    })
    .join("\n");
}

/**
 * Formats an array of strings as a bullet list, truncating each item.
 * All items are included (nothing omitted).
 * @param items - Array of strings to format
 * @param locale - User locale
 * @param truncateLength - Max chars per item before truncation
 * @returns Formatted bullet list, or localized "None" if empty
 */
function formatBulletList(
  items: string[],
  locale: string,
  truncateLength: number,
): string {
  if (items.length === 0) {
    return localizer(locale, "commands.choices.none");
  }
  return items
    .map((item) => {
      return `• ${truncateText(item, truncateLength)}`;
    })
    .join("\n");
}

/**
 * Formats sample dialogue pairs as a numbered list with truncation on each side.
 * @param dialoguesIn - User/input dialogue examples
 * @param dialoguesOut - Persona/output dialogue examples
 * @param locale - User locale
 * @param truncateLength - Max chars per dialogue side before truncation
 * @returns Formatted list, or localized "None" if empty
 */
function formatSampleDialogues(
  dialoguesIn: string[],
  dialoguesOut: string[],
  locale: string,
  truncateLength: number,
): string {
  const pairCount = Math.max(dialoguesIn.length, dialoguesOut.length);
  if (pairCount === 0) {
    return localizer(locale, "commands.choices.none");
  }

  return Array.from({ length: pairCount }, (_, index) => {
    const input = truncateText(
      dialoguesIn[index] ?? localizer(locale, "commands.choices.none"),
      truncateLength,
    );
    const output = truncateText(
      dialoguesOut[index] ?? localizer(locale, "commands.choices.none"),
      truncateLength,
    );
    return `${index + 1}. ${input} -> ${output}`;
  }).join("\n");
}

/**
 * Resolves a Discord channel ID to a channel mention string.
 * Falls back to a raw snowflake mention if the fetch fails.
 * @param client - Discord client for channel fetch
 * @param id - Discord channel snowflake ID
 * @param locale - User locale (for unknown channel label)
 * @returns Resolved channel mention string
 */
async function resolveChannelMention(
  client: Client,
  id: string,
  locale: string,
): Promise<string> {
  try {
    const channel = await client.channels.fetch(id);
    return channel instanceof TextChannel ? channel.toString() : `<#${id}>`;
  } catch {
    return `*<${localizer(locale, "commands.tool.status.unknown_channel")} ${id}>*`;
  }
}

/**
 * Formats a list of channel IDs as mentions, collapsing to a count if over the max.
 * @param client - Discord client
 * @param ids - Array of channel Discord IDs
 * @param locale - User locale
 * @returns Formatted channel list string, or localized "None" if empty
 */
async function formatChannelList(
  client: Client,
  ids: string[],
  locale: string,
): Promise<string> {
  if (ids.length === 0) {
    return localizer(locale, "commands.choices.none");
  }
  const mentions = await Promise.all(
    ids.map((id) => resolveChannelMention(client, id, locale)),
  );
  return mentions.length <= MAX_ITEMS_DISPLAY
    ? mentions.join(", ")
    : localizer(locale, "commands.tool.status.item_count", {
        count: mentions.length,
      });
}

/**
 * Formats the channel whitelist as a numbered list.
 * Shows each whitelisted channel with its per-channel cooldown type and duration.
 * When no entries exist, shows an "all channels allowed" message instead.
 * @param client - Discord client for channel mentions
 * @param entries - Array of whitelist rows from the database
 * @param locale - User locale
 * @returns Formatted whitelist string
 */
async function formatWhitelistEntries(
  client: Client,
  entries: ChannelWhitelistRow[],
  locale: string,
): Promise<string> {
  // 1. No entries = whitelist is inactive (all channels can trigger)
  if (entries.length === 0) {
    return localizer(locale, "commands.tool.status.whitelist_all_allowed");
  }

  // 2. Resolve each channel mention and build formatted lines
  const lines = await Promise.all(
    entries.map(async (entry, index) => {
      const mention = await resolveChannelMention(
        client,
        entry.channel_disc_id,
        locale,
      );
      if (entry.cooldown_type === null || entry.cooldown_length === null) {
        return `${index + 1}. ${mention} (${localizer(locale, "commands.choices.inherit_global")})`;
      }

      const cooldownType = entry.cooldown_type;
      const typeLabel = getCooldownTypeLabel(locale, cooldownType);

      // 3. Include duration only when a real cooldown is set
      const detail =
        cooldownType === CooldownType.OFF
          ? typeLabel
          : `${typeLabel}, ${entry.cooldown_length}s`;

      return `${index + 1}. ${mention} (${detail})`;
    }),
  );

  return lines.join("\n");
}

/**
 * Formats the role whitelist as a numbered list.
 * When no entries exist, shows an "all roles allowed" message instead.
 * @param entries - Array of role whitelist rows from the database
 * @param locale - User locale
 * @returns Formatted role whitelist string
 */
function formatWhitelistRolesEntries(
  entries: RoleWhitelistRow[],
  locale: string,
): string {
  if (entries.length === 0) {
    return localizer(locale, "commands.tool.status.whitelist_roles_all_allowed");
  }

  return entries
    .map((entry, index) => {
      return `${index + 1}. <@&${entry.role_disc_id}>`;
    })
    .join("\n");
}

/**
 * Formats the list of random triggers as a numbered list.
 * Each entry shows channel, persona name, timer interval, and trigger probability.
 * @param client - Discord client for channel mentions
 * @param triggers - Array of random trigger rows from the database
 * @param personaNameMap - Map of tomori_id to persona nickname for name resolution
 * @param locale - User locale
 * @returns Formatted random trigger list string, or localized "None" if empty
 */
async function formatRandomTriggers(
  client: Client,
  triggers: RandomTriggerRow[],
  personaNameMap: Map<number, string>,
  locale: string,
): Promise<string> {
  if (triggers.length === 0) {
    return localizer(locale, "commands.choices.none");
  }

  const lines = await Promise.all(
    triggers.map(async (trigger, index) => {
      // 1. Resolve the channel mention
      const mention = await resolveChannelMention(
        client,
        trigger.channel_disc_id,
        locale,
      );

      // 2. Resolve persona name (null tomori_id = random persona selection)
      const personaName =
        trigger.tomori_id != null
          ? (personaNameMap.get(trigger.tomori_id) ?? `ID:${trigger.tomori_id}`)
          : localizer(
              locale,
              "commands.tool.status.random_trigger_persona_random",
            );
      const offsetSegment =
        trigger.random_offset_range != null && trigger.random_offset_range > 0
          ? ` +/-${trigger.random_offset_range}h`
          : "";

      // 3. Format: "N. #channel · Persona · Xh · Y%"
      return `${index + 1}. ${mention} · ${personaName} · ${trigger.timer_hours}h${offsetSegment} · ${trigger.chance_percent}%`;
    }),
  );

  return lines.join("\n");
}

/**
 * Formats the list of channel-level LLM overrides as a numbered list.
 * Each entry shows channel mention and the model codename + provider.
 * @param client - Discord client for channel mentions
 * @param overrides - Array of channel override objects from the database
 * @param locale - User locale
 * @returns Formatted channel LLM override list string, or localized "None" if empty
 */
async function formatChannelLlmOverrides(
  client: Client,
  overrides: { channelDiscId: string; llm: LlmRow }[],
  locale: string,
  customModelName?: string | null,
): Promise<string> {
  if (overrides.length === 0) {
    return localizer(locale, "commands.choices.none");
  }

  const lines = await Promise.all(
    overrides.map(async (entry, index) => {
      // 1. Resolve channel mention
      const mention = await resolveChannelMention(
        client,
        entry.channelDiscId,
        locale,
      );
      // 2. Format: "N. #channel → model (provider)"
      return `${index + 1}. ${mention} → ${formatLlmDisplayLabel(entry.llm, customModelName)}`;
    }),
  );

  return lines.join("\n");
}

/**
 * Formats the list of persona-level LLM overrides as a numbered list.
 * Only includes personas that have an explicit model override set.
 * @param personas - Array of all TomoriState personas for the server
 * @param locale - User locale
 * @returns Formatted persona LLM override list string, or localized "None" if empty
 */
function formatPersonaLlmOverrides(
  personas: TomoriState[],
  locale: string,
  customModelName?: string | null,
): string {
  // 1. Filter to personas with an explicit override, narrowing the type so llm is non-optional
  const overrides = personas.filter(
    (p): p is TomoriState & { persona_llm: LlmRow } => p.persona_llm != null,
  );

  if (overrides.length === 0) {
    return localizer(locale, "commands.choices.none");
  }

  // 2. Format: "N. Persona Name → `model` (provider)"
  return overrides
    .map((p, index) => {
      return `${index + 1}. **${p.tomori_nickname}** → ${formatLlmDisplayLabel(p.persona_llm, customModelName)}`;
    })
    .join("\n");
}

/**
 * Formats welcome channel configuration as a single-line string.
 * Shows channel mention with associated persona if configured.
 * When no welcome channel is set, shows a localized "None" message.
 * @param client - Discord client for channel mentions
 * @param config - TomoriState config containing welcome_channel_disc_id and welcome_persona_id
 * @param personaNameMap - Map of persona IDs to nicknames
 * @param locale - User locale
 * @returns Formatted welcome channel string
 */
async function formatWelcomeChannel(
  client: Client,
  config: TomoriConfigRow,
  personaNameMap: Map<number, string>,
  locale: string,
): Promise<string> {
  const welcomeChannelId = config.welcome_channel_disc_id;

  if (!welcomeChannelId) {
    return localizer(locale, "commands.choices.none");
  }

  // 1. Resolve channel mention
  const channelMention = await resolveChannelMention(
    client,
    welcomeChannelId,
    locale,
  );

  // 2. Resolve persona name (null welcome_persona_id = random persona selection)
  const personaName = config.welcome_persona_id != null
    ? (personaNameMap.get(config.welcome_persona_id) ?? `ID:${config.welcome_persona_id}`)
    : localizer(
        locale,
        "commands.tool.status.random_trigger_persona_random",
      );

  // 3. Format: "#channel · Persona"
  return `${channelMention} · ${personaName}`;
}

/**
 * Configures the 'status' subcommand with scope options.
 */
export const configureSubcommand = (
  subcommand: SlashCommandSubcommandBuilder,
) =>
  subcommand
    .setName("status")
    .setDescription(localizer("en-US", "commands.tool.status.description"))
    .addStringOption((option) =>
      option
        .setName("scope")
        .setDescription(
          localizer("en-US", "commands.tool.status.scope_description"),
        )
        .setRequired(true)
        .addChoices(
          {
            name: localizer(
              "en-US",
              "commands.tool.status.scope_choice_personal",
            ),
            value: "personal",
          },
          {
            name: localizer(
              "en-US",
              "commands.tool.status.scope_choice_server",
            ),
            value: "server",
          },
          {
            name: localizer(
              "en-US",
              "commands.tool.status.scope_choice_persona",
            ),
            value: "persona",
          },
        ),
    );

/**
 * Executes the 'status' command.
 * Displays paginated status pages for the selected scope (personal, server, or persona).
 * @param client - The Discord client instance
 * @param interaction - The chat input command interaction
 * @param userData - The user data row from the database
 * @param locale - The user's preferred locale
 */
export async function execute(
  client: Client,
  interaction: ChatInputCommandInteraction,
  userData: UserRow,
  locale: string,
): Promise<void> {
  const serverDiscId = interaction.guildId ?? interaction.user.id;
  const scope = interaction.options.getString("scope", true);
  const limits = getMemoryLimits();

  try {
    switch (scope) {
      case "personal": {
        // 1. Load global personal memories (lineage 0 only)
        let globalPersonalMemoryList: string[] = [];
        if (userData.user_id) {
          const personalMemoryRows = await loadPersonalMemoriesForUserLineage(
            userData.user_id,
            0,
            false,
          );
          globalPersonalMemoryList = personalMemoryRows.map(
            (row) => row.content,
          );
        }

        // 2. Format global personal memories (all shown, 100-char truncation each)
        const globalPersonalMemoriesValue = formatNumberedList(
          globalPersonalMemoryList,
          locale,
          MEMORY_TRUNCATE_LENGTH,
        );
        const globalPersonalMemoriesCount = globalPersonalMemoryList.length;

        // 3. Get the user's active reminder count
        const reminderCount = await getUserReminderCount(interaction.user.id);
        const rawImpersonationPrompt = userData.impersonation_prompt?.trim() ?? null;
        const impersonationPromptValue = rawImpersonationPrompt
          ? `\`\`\`\n${
              rawImpersonationPrompt.length > MAX_PROMPT_PREVIEW
                ? `${rawImpersonationPrompt.slice(0, MAX_PROMPT_PREVIEW)}...`
                : rawImpersonationPrompt
            }\n\`\`\``
          : localizer(
              locale,
              "commands.tool.status.field_impersonation_prompt_not_set",
            );

        // 4. Build the single personal status page
        const personalPage: SummaryEmbedOptions = {
          titleKey: "commands.tool.status.personal_title",
          descriptionKey: "commands.tool.status.personal_description",
          color: ColorCode.INFO,
          footerKey:
            "commands.tool.status.export_footer_global_personal_memories",
          fields: [
            {
              nameKey: "commands.tool.status.field_user_nickname",
              value: userData.user_nickname,
              inline: true,
            },
            {
              nameKey: "commands.tool.status.field_language_pref",
              value: userData.language_pref,
              inline: true,
            },
            {
              nameKey: "commands.tool.status.field_privacy",
              value: getPrivacyLevelLabel(
                locale,
                userData.privacy_level ?? PrivacyLevel.MINIMAL,
              ),
              inline: true,
            },
            {
              nameKey: "commands.tool.status.field_impersonation_prompt",
              value: impersonationPromptValue,
              inline: false,
            },
            {
              nameKey: "commands.tool.status.field_reminders_count",
              value: String(reminderCount),
              inline: true,
            },
            {
              nameKey:
                "commands.tool.status.field_global_personal_memories_with_count",
              nameVars: {
                current: globalPersonalMemoriesCount,
                max: limits.maxPersonalMemories,
              },
              value: globalPersonalMemoriesValue,
              inline: false,
            },
          ],
        };

        await replyPaginatedStatusPages(
          interaction,
          locale,
          [personalPage],
          MessageFlags.Ephemeral,
        );
        break;
      }

      case "server": {
        // 1. Load Tomori state for this server
        const tomoriState = await getCachedTomoriState(serverDiscId);

        if (!tomoriState) {
          await replyInfoEmbed(interaction, locale, {
            titleKey: "general.errors.tomori_not_setup_title",
            descriptionKey: "general.errors.tomori_not_setup_description",
            color: ColorCode.ERROR,
          });
          return;
        }

        const config = tomoriState.config;
        const llm = tomoriState.llm;

        // 2. Load all supporting data in parallel
        const [
          braveApiKeySet,
          blacklistedMemberIds,
          whitelistChannels,
          whitelistRoles,
          randomTriggers,
          allPersonas,
          channelLlmOverrides,
          imageQuotaConfig,
          textQuotaConfig,
        ] = await Promise.all([
          getBraveApiKeyStatus(tomoriState.server_id),
          getBlacklistedMemberIds(tomoriState.server_id),
          getAllWhitelistChannels(tomoriState.server_id),
          getAllWhitelistRoles(tomoriState.server_id),
          getServerRandomTriggers(tomoriState.server_id),
          loadAllPersonasForServer(serverDiscId),
          getAllChannelLlmOverridesForServer(tomoriState.server_id),
          getQuotaConfig(tomoriState.server_id),
          getTextQuotaConfig(tomoriState.server_id),
        ]);

        // 3. Build a persona name map for random trigger display (tomori_id -> nickname)
        const personaNameMap = new Map<number, string>();
        for (const persona of allPersonas) {
          if (persona.tomori_id) {
            personaNameMap.set(persona.tomori_id, persona.tomori_nickname);
          }
        }

        // 4. Format timezone (UTC+08:00 style)
        const timezoneOffset = config.timezone_offset;
        const timezoneSign = timezoneOffset >= 0 ? "+" : "-";
        const timezoneHours = Math.abs(timezoneOffset)
          .toString()
          .padStart(2, "0");
        const timezoneValue = `UTC${timezoneSign}${timezoneHours}:00`;

        // 5. Format cooldown type and duration
        const cooldownType = config.cooldown_type ?? CooldownType.OFF;
        const cooldownTypeLabel = getCooldownTypeLabel(locale, cooldownType);
        const cooldownLengthValue =
          cooldownType === CooldownType.OFF
            ? localizer(locale, "commands.choices.disabled")
            : localizer(
                locale,
                "commands.tool.status.field_cooldown_length_value",
                { seconds: config.cooldown_length },
              );
        const autochThresholdMax =
          config.autoch_threshold_max > 0
            ? Math.max(config.autoch_threshold_max, config.autoch_threshold)
            : config.autoch_threshold;
        const autochModeValue =
          config.autoch_threshold === 0
            ? localizer(locale, "commands.choices.always")
            : autochThresholdMax > config.autoch_threshold
              ? `${config.autoch_threshold}-${autochThresholdMax}`
              : String(config.autoch_threshold);

        // 6. Format blacklisted members
        const blacklistedCount = blacklistedMemberIds.length;
        const blacklistedValue =
          blacklistedCount === 0
            ? localizer(locale, "commands.choices.none")
            : blacklistedCount <= MAX_ITEMS_DISPLAY
              ? blacklistedMemberIds.map((id) => `<@${id}>`).join(", ")
              : localizer(
                  locale,
                  "commands.tool.status.field_blacklisted_members_with_count",
                  { current: blacklistedCount },
                );

        // 7. Format channel lists (auto-chat, RP, welcome, whitelist, random triggers, channel model overrides)
        const [
          autoChannelsValue,
          rpChannelsValue,
          welcomeChannelValue,
          thoughtLogChannelValue,
          whitelistValue,
          whitelistRolesValue,
          randomTriggersValue,
          channelLlmOverridesValue,
        ] = await Promise.all([
          formatChannelList(client, config.autoch_disc_ids, locale),
          formatChannelList(client, config.rp_channel_ids, locale),
          formatWelcomeChannel(client, config, personaNameMap, locale),
          formatChannelList(
            client,
            config.thought_log_channel_disc_id
              ? [config.thought_log_channel_disc_id]
              : [],
            locale,
          ),
          formatWhitelistEntries(client, whitelistChannels, locale),
          formatWhitelistRolesEntries(whitelistRoles, locale),
          formatRandomTriggers(client, randomTriggers, personaNameMap, locale),
          formatChannelLlmOverrides(
            client,
            channelLlmOverrides,
            locale,
            config.custom_model_name,
          ),
        ]);

        // 8. Format system prompt preview (code block, up to MAX_PROMPT_PREVIEW chars)
        const rawSystemPrompt = config.system_prompt ?? null;
        const systemPromptText = rawSystemPrompt
          ? rawSystemPrompt.length > MAX_PROMPT_PREVIEW
            ? `${rawSystemPrompt.slice(0, MAX_PROMPT_PREVIEW)}...`
            : rawSystemPrompt
          : DEFAULT_SYSTEM_PROMPT.trim();
        const systemPromptValue = `\`\`\`\n${systemPromptText}\n\`\`\``;

        // ── Page 1: Model & Sampling ───────────────────────────────────
        const serverPage1: SummaryEmbedOptions = {
          titleKey: "commands.tool.status.server_page1_title",
          descriptionKey: "commands.tool.status.server_page1_description",
          color: ColorCode.INFO,
          fields: [
            {
              nameKey: "commands.tool.status.field_model",
              value: formatLlmDisplayLabel(llm, config.custom_model_name),
              inline: false,
            },
            {
              nameKey: "commands.tool.status.field_temperature",
              value: String(config.llm_temperature),
              inline: true,
            },
            {
              nameKey: "commands.tool.status.field_top_p",
              value: String(config.llm_top_p),
              inline: true,
            },
            {
              nameKey: "commands.tool.status.field_top_k",
              value: String(config.llm_top_k),
              inline: true,
            },
            {
              nameKey: "commands.tool.status.field_min_p",
              value: String(config.llm_min_p),
              inline: true,
            },
            {
              nameKey: "commands.tool.status.field_frequency_penalty",
              value: String(config.llm_frequency_penalty),
              inline: true,
            },
            {
              nameKey: "commands.tool.status.field_presence_penalty",
              value: String(config.llm_presence_penalty),
              inline: true,
            },
            {
              nameKey: "commands.tool.status.field_humanizer",
              value: String(config.humanizer_degree),
              inline: true,
            },
          ],
        };

        // ── Page 2: Behavior ───────────────────────────────────────────
        const serverPage2: SummaryEmbedOptions = {
          titleKey: "commands.tool.status.server_page2_title",
          descriptionKey: "commands.tool.status.server_page2_description",
          color: ColorCode.INFO,
          fields: [
            {
              nameKey: "commands.tool.status.field_timezone",
              value: timezoneValue,
              inline: true,
            },
            {
              nameKey: "commands.tool.status.field_message_fetch_limit",
              value: String(config.message_fetch_limit),
              inline: true,
            },
            {
              nameKey: "commands.tool.status.field_self_reply_limit",
              value: String(config.self_reply_limit),
              inline: true,
            },
            {
              nameKey: "commands.tool.status.field_send_message_limit",
              value: (config.send_message_limit ?? 0) > 0
                ? String(config.send_message_limit)
                : localizer(locale, "commands.choices.disabled"),
              inline: true,
            },
            {
              nameKey: "commands.tool.status.field_always_reply",
              value: config.always_reply_enabled
                ? localizer(locale, "commands.choices.enabled")
                : localizer(locale, "commands.choices.disabled"),
              inline: true,
            },
            {
              nameKey: "commands.tool.status.field_triggered_persona_limit",
              value: String(config.triggered_persona_limit),
              inline: true,
            },
            {
              nameKey: "commands.tool.status.field_cooldown_type",
              value: cooldownTypeLabel,
              inline: true,
            },
            {
              nameKey: "commands.tool.status.field_cooldown_length",
              value: cooldownLengthValue,
              inline: true,
            },
            {
              nameKey: "commands.tool.status.field_autoch_threshold",
              value: autochModeValue,
              inline: true,
            },
          ],
        };

        // ── Page 3: Channels & Automation ──────────────────────────────
        const serverPage3: SummaryEmbedOptions = {
          titleKey: "commands.tool.status.server_page3_title",
          descriptionKey: "commands.tool.status.server_page3_description",
          color: ColorCode.INFO,
          fields: [
            {
              nameKey: "commands.tool.status.field_autoch_channels",
              value: autoChannelsValue,
              inline: false,
            },
            {
              nameKey: "commands.tool.status.field_rp_channels",
              value: rpChannelsValue,
              inline: false,
            },
            {
              nameKey: "commands.tool.status.field_welcome_channel",
              value: welcomeChannelValue,
              inline: false,
            },
            {
              nameKey: "commands.tool.status.field_thought_logs_channel",
              value: thoughtLogChannelValue,
              inline: false,
            },
            {
              nameKey: "commands.tool.status.field_whitelist_channels",
              value: whitelistValue,
              inline: false,
            },
            {
              nameKey: "commands.tool.status.field_whitelist_roles",
              value: whitelistRolesValue,
              inline: false,
            },
            {
              nameKey: "commands.tool.status.field_random_triggers",
              value: randomTriggersValue,
              inline: false,
            },
          ],
        };

        // ── Page 4: Features & Moderation ─────────────────────────────
        const serverPage4: SummaryEmbedOptions = {
          titleKey: "commands.tool.status.server_page4_title",
          descriptionKey: "commands.tool.status.server_page4_description",
          color: ColorCode.INFO,
          fields: [
            {
              nameKey: "commands.tool.status.field_personalization",
              value: formatBooleanLocalized(
                config.personal_memories_enabled,
                locale,
              ),
              inline: true,
            },
            {
              nameKey: "commands.tool.status.field_self_teach",
              value: formatBooleanLocalized(
                config.self_teaching_enabled,
                locale,
              ),
              inline: true,
            },
            {
              nameKey: "commands.tool.status.field_image_generation",
              value: formatBooleanLocalized(config.imagegen_enabled, locale),
              inline: true,
            },
            {
              nameKey: "commands.tool.status.field_videogen",
              value: formatBooleanLocalized(config.videogen_enabled, locale),
              inline: true,
            },
            {
              nameKey: "commands.tool.status.field_web_search",
              value: formatBooleanLocalized(config.web_search_enabled, locale),
              inline: true,
            },
            {
              nameKey: "commands.tool.status.field_pin_message",
              value: formatBooleanLocalized(config.pin_message_enabled, locale),
              inline: true,
            },
            {
              nameKey: "commands.tool.status.field_emoji_usage",
              value: formatBooleanLocalized(config.emoji_usage_enabled, locale),
              inline: true,
            },
            {
              nameKey: "commands.tool.status.field_sticker_usage",
              value: formatBooleanLocalized(
                config.sticker_usage_enabled,
                locale,
              ),
              inline: true,
            },
            {
              nameKey: "commands.tool.status.field_api_key_set",
              value: formatBooleanLocalized(!!config.api_key, locale),
              inline: true,
            },
            {
              nameKey: "commands.tool.status.field_brave_api_key_set",
              value: formatBooleanLocalized(braveApiKeySet, locale),
              inline: true,
            },
            {
              nameKey: "commands.tool.status.field_server_memteaching",
              value: formatBooleanLocalized(
                config.server_memteaching_enabled,
                locale,
              ),
              inline: true,
            },
            {
              nameKey: "commands.tool.status.field_attribute_memteaching",
              value: formatBooleanLocalized(
                config.attribute_memteaching_enabled,
                locale,
              ),
              inline: true,
            },
            {
              nameKey: "commands.tool.status.field_sampledialogue_memteaching",
              value: formatBooleanLocalized(
                config.sampledialogue_memteaching_enabled,
                locale,
              ),
              inline: true,
            },
            {
              nameKey: "commands.tool.status.field_hide_impersonation",
              value: formatBooleanLocalized(
                config.hide_impersonation_embeds,
                locale,
              ),
              inline: true,
            },
            {
              nameKey: "commands.tool.status.field_hide_respond_embed",
              value: formatBooleanLocalized(config.hide_respond_embed, locale),
              inline: true,
            },
            {
              nameKey: "commands.tool.status.field_self_debug",
              value: formatBooleanLocalized(config.self_debug_enabled, locale),
              inline: true,
            },
            {
              nameKey: "commands.tool.status.field_uncensor_injection",
              value: formatBooleanLocalized(
                config.uncensor_injection_enabled,
                locale,
              ),
              inline: true,
            },
            {
              nameKey: "commands.tool.status.field_uncensor_unicode",
              value: formatBooleanLocalized(
                config.uncensor_unicode_space_enabled,
                locale,
              ),
              inline: true,
            },
            {
              nameKey: "commands.tool.status.field_uncensor_sanitize",
              value: formatBooleanLocalized(
                config.uncensor_sanitize_enabled,
                locale,
              ),
              inline: true,
            },
            {
              nameKey: "commands.tool.status.field_blacklisted_members",
              value: blacklistedValue,
              inline: blacklistedCount <= MAX_ITEMS_DISPLAY,
            },
          ],
        };

        // ── Page 5: System Prompt ───────────────────────────────────────
        const serverPage5: SummaryEmbedOptions = {
          titleKey: "commands.tool.status.server_page5_title",
          descriptionKey: "commands.tool.status.server_page5_description",
          color: ColorCode.INFO,
          footerKey: "commands.tool.status.export_footer_server_config",
          fields: [
            {
              nameKey: "commands.tool.status.field_system_prompt",
              value: systemPromptValue,
              inline: false,
            },
          ],
        };

        // ── Page 6: Model Overrides ─────────────────────────────────────
        const personaLlmOverridesValue = formatPersonaLlmOverrides(
          allPersonas,
          locale,
          config.custom_model_name,
        );

        const serverPage6: SummaryEmbedOptions = {
          titleKey: "commands.tool.status.server_page6_title",
          descriptionKey: "commands.tool.status.server_page6_description",
          color: ColorCode.INFO,
          fields: [
            {
              nameKey: "commands.tool.status.field_channel_llm_overrides",
              value: channelLlmOverridesValue,
              inline: false,
            },
            {
              nameKey: "commands.tool.status.field_persona_llm_overrides",
              value: personaLlmOverridesValue,
              inline: false,
            },
          ],
        };

        // ── Page 7: Quotas ──────────────────────────────────────────────
        const serverPage7: SummaryEmbedOptions = {
          titleKey: "commands.tool.status.server_page7_title",
          descriptionKey: "commands.tool.status.server_page7_description",
          color: ColorCode.INFO,
          fields: [
            {
              nameKey: "commands.tool.status.field_image_quota_enabled",
              value: formatBooleanLocalized(imageQuotaConfig.enabled, locale),
              inline: true,
            },
            {
              nameKey: "commands.tool.status.field_image_quota_daily_user",
              value: formatQuotaLimitValue(
                locale,
                imageQuotaConfig.daily_user_quota,
              ),
              inline: true,
            },
            {
              nameKey: "commands.tool.status.field_image_quota_serverwide",
              value: formatQuotaLimitValue(
                locale,
                imageQuotaConfig.serverwide_quota,
              ),
              inline: true,
            },
            {
              nameKey: "commands.tool.status.field_image_quota_reset_days",
              value: localizer(
                locale,
                "commands.tool.status.field_quota_reset_days_value",
                { days: imageQuotaConfig.serverwide_quota_resets_in },
              ),
              inline: true,
            },
            {
              nameKey: "commands.tool.status.field_text_quota_enabled",
              value: formatBooleanLocalized(textQuotaConfig.enabled, locale),
              inline: true,
            },
            {
              nameKey: "commands.tool.status.field_text_quota_daily_user",
              value: formatQuotaLimitValue(
                locale,
                textQuotaConfig.daily_user_quota,
              ),
              inline: true,
            },
            {
              nameKey: "commands.tool.status.field_text_quota_serverwide",
              value: formatQuotaLimitValue(
                locale,
                textQuotaConfig.serverwide_quota,
              ),
              inline: true,
            },
            {
              nameKey: "commands.tool.status.field_text_quota_reset_days",
              value: localizer(
                locale,
                "commands.tool.status.field_quota_reset_days_value",
                { days: textQuotaConfig.serverwide_quota_resets_in },
              ),
              inline: true,
            },
          ],
        };

        await replyPaginatedStatusPages(
          interaction,
          locale,
          [
            serverPage1,
            serverPage2,
            serverPage3,
            serverPage4,
            serverPage5,
            serverPage6,
            serverPage7,
          ],
          MessageFlags.Ephemeral,
        );
        break;
      }

      case "persona": {
        // 1. Load all personas for the picker
        const allPersonas = await loadAllPersonasForServer(serverDiscId);

        if (allPersonas.length === 0) {
          await replyInfoEmbed(interaction, locale, {
            titleKey: "general.errors.tomori_not_setup_title",
            descriptionKey: "general.errors.tomori_not_setup_description",
            color: ColorCode.ERROR,
          });
          return;
        }

        // 2. Show paginated persona picker (Pattern 4 — preserves interaction)
        const personaSelection = await replyPaginatedPersonaChoicesV2(
          interaction,
          locale,
          {
            personas: allPersonas,
            color: ColorCode.INFO,
            preserveSelectedInteraction: true,
            onSelect: async () => {},
          },
        );

        if (
          !personaSelection.success ||
          personaSelection.selectedIndex === undefined ||
          !personaSelection.interaction
        ) {
          return;
        }

        const personaInteraction: ButtonInteraction =
          personaSelection.interaction;
        const selectedPersona =
          allPersonas[personaSelection.selectedIndex] ?? null;

        if (!selectedPersona?.tomori_id) {
          await replyInfoEmbed(personaInteraction, locale, {
            titleKey: "general.errors.invalid_option_title",
            descriptionKey: "general.errors.invalid_option_description",
            color: ColorCode.ERROR,
          });
          return;
        }

        const personaName = selectedPersona.tomori_nickname;
        const personaLineageId = selectedPersona.persona_lineage_id ?? 0;

        // 3. Load persona-scoped personal memories for the requesting user
        let personaPersonalMemoryList: string[] = [];
        if (userData.user_id) {
          const personaPersonalMemoryRows =
            await loadPersonalMemoriesForUserLineage(
              userData.user_id,
              personaLineageId,
              false,
            );
          personaPersonalMemoryList = personaPersonalMemoryRows.map(
            (row) => row.content,
          );
        }

        // 4. Persona-scoped server memories are already attached to the persona state
        const personaServerMemoryList = selectedPersona.server_memories ?? [];

        // 5. Format attributes (all shown, 200-char truncation each)
        const attributesCount = selectedPersona.attribute_list.length;
        const attributesValue = formatBulletList(
          selectedPersona.attribute_list,
          locale,
          ATTRIBUTE_TRUNCATE_LENGTH,
        );

        // 6. Format sample dialogues with actual truncated content
        const dialogueCount = Math.max(
          selectedPersona.sample_dialogues_in.length,
          selectedPersona.sample_dialogues_out.length,
        );
        const sampleDialoguesValue = formatSampleDialogues(
          selectedPersona.sample_dialogues_in,
          selectedPersona.sample_dialogues_out,
          locale,
          DIALOGUE_TRUNCATE_LENGTH,
        );

        // 7. Format persona-scoped memory content
        const personaPersonalMemoriesCount = personaPersonalMemoryList.length;
        const personaPersonalMemoriesValue = formatNumberedList(
          personaPersonalMemoryList,
          locale,
          MEMORY_TRUNCATE_LENGTH,
        );
        const personaServerMemoriesCount = personaServerMemoryList.length;
        const personaServerMemoriesValue = formatNumberedList(
          personaServerMemoryList,
          locale,
          MEMORY_TRUNCATE_LENGTH,
        );

        // 8. Format alter/persona trigger words
        const alterTriggersValue =
          selectedPersona.alter_triggers.length > 0
            ? selectedPersona.alter_triggers.map((t) => `\`${t}\``).join(", ")
            : localizer(locale, "commands.choices.none");

        const personaTriggersValue =
          selectedPersona.trigger_words.length > 0
            ? selectedPersona.trigger_words.map((t) => `\`${t}\``).join(", ")
            : localizer(locale, "commands.choices.none");

        // 9. Format NAI tags
        const naiTagsValue =
          selectedPersona.nai_tags.length > 0
            ? selectedPersona.nai_tags.join(", ")
            : localizer(locale, "commands.choices.none");

        // 10. Build persona model override value
        //     Shows the persona-specific LLM if set, otherwise "Server default"
        const personaModelValue = selectedPersona.persona_llm
          ? formatLlmDisplayLabel(
              selectedPersona.persona_llm,
              selectedPersona.config.custom_model_name,
            )
          : localizer(
              locale,
              "commands.tool.status.persona_model_server_default",
            );

        // 11. Format ATTG metadata block
        //     Each field is shown individually; null fields display as "None"
        const noneLabel = localizer(locale, "commands.choices.none");
        const attgAuthor = selectedPersona.nai_attg_author ?? noneLabel;
        const attgTitle = selectedPersona.nai_attg_title ?? noneLabel;
        const attgTags = selectedPersona.nai_attg_tags ?? noneLabel;
        const attgGenre = selectedPersona.nai_attg_genre ?? noneLabel;
        const attgStars =
          selectedPersona.nai_attg_stars != null
            ? `${selectedPersona.nai_attg_stars}★`
            : noneLabel;
        const attgAllUnset =
          !selectedPersona.nai_attg_author &&
          !selectedPersona.nai_attg_title &&
          !selectedPersona.nai_attg_tags &&
          !selectedPersona.nai_attg_genre &&
          selectedPersona.nai_attg_stars == null;
        const attgValue = attgAllUnset
          ? localizer(locale, "commands.tool.status.nai_attg_not_set")
          : `Author: ${attgAuthor}\nTitle: ${attgTitle}\nTags: ${attgTags}\nGenre: ${attgGenre}\nStars: ${attgStars}`;

        // 13. Format persona prompt preview (code block, up to MAX_PROMPT_PREVIEW chars)
        const rawPersonaPrompt = selectedPersona.persona_prompt ?? null;
        const personaPromptValue = rawPersonaPrompt
          ? `\`\`\`\n${
              rawPersonaPrompt.length > MAX_PROMPT_PREVIEW
                ? `${rawPersonaPrompt.slice(0, MAX_PROMPT_PREVIEW)}...`
                : rawPersonaPrompt
            }\n\`\`\``
          : localizer(
              locale,
              "commands.tool.status.field_persona_prompt_not_set",
            );

        // ── Page 1: Identity ───────────────────────────────────────────
        const personaPage1: SummaryEmbedOptions = {
          titleKey: "commands.tool.status.persona_page1_title",
          titleVars: { persona_name: personaName },
          descriptionKey: "commands.tool.status.persona_page1_description",
          color: ColorCode.INFO,
          fields: [
            {
              nameKey: "commands.tool.status.field_nickname",
              value: personaName,
              inline: true,
            },
            {
              nameKey: "commands.tool.status.field_is_alter",
              value: formatBooleanLocalized(selectedPersona.is_alter, locale),
              inline: true,
            },
            {
              nameKey: "commands.tool.status.field_alter_triggers",
              value: alterTriggersValue,
              inline: true,
            },
            {
              nameKey: "commands.tool.status.field_persona_triggers",
              value: personaTriggersValue,
              inline: true,
            },
            {
              nameKey: "commands.tool.status.field_persona_model",
              value: personaModelValue,
              inline: true,
            },
          ],
        };

        // ── Page 2: Attributes ─────────────────────────────────────────
        const personaPage2: SummaryEmbedOptions = {
          titleKey: "commands.tool.status.persona_page2_title",
          titleVars: { persona_name: personaName },
          descriptionKey: "commands.tool.status.persona_page2_description",
          color: ColorCode.INFO,
          footerKey:
            "commands.tool.status.export_footer_persona_attributes_and_dialogues",
          fields: [
            {
              nameKey: "commands.tool.status.field_attributes_with_count",
              nameVars: {
                current: attributesCount,
                max: limits.maxAttributes,
              },
              value: attributesValue,
              inline: false,
            },
          ],
        };

        // ── Page 3: Sample Dialogues ───────────────────────────────────
        const personaPage3: SummaryEmbedOptions = {
          titleKey: "commands.tool.status.persona_page3_title",
          titleVars: { persona_name: personaName },
          descriptionKey: "commands.tool.status.persona_page3_description",
          color: ColorCode.INFO,
          footerKey:
            "commands.tool.status.export_footer_persona_attributes_and_dialogues",
          fields: [
            {
              nameKey: "commands.tool.status.field_sample_dialogues_with_count",
              nameVars: {
                current: dialogueCount,
                max: limits.maxSampleDialogues,
              },
              value: sampleDialoguesValue,
              inline: false,
            },
          ],
        };

        // ── Page 4: Memories ───────────────────────────────────────────
        const personaPage4: SummaryEmbedOptions = {
          titleKey: "commands.tool.status.persona_page4_title",
          titleVars: { persona_name: personaName },
          descriptionKey: "commands.tool.status.persona_page4_description",
          color: ColorCode.INFO,
          footerKey: "commands.tool.status.export_footer_persona_memories",
          fields: [
            {
              nameKey:
                "commands.tool.status.field_persona_personal_memories_with_count",
              nameVars: {
                current: personaPersonalMemoriesCount,
                max: limits.maxPersonalMemories,
              },
              value: personaPersonalMemoriesValue,
              inline: false,
            },
            {
              nameKey:
                "commands.tool.status.field_persona_server_memories_with_count",
              nameVars: {
                current: personaServerMemoriesCount,
                max: limits.maxServerMemories,
              },
              value: personaServerMemoriesValue,
              inline: false,
            },
          ],
        };

        // ── Page 5: Prompt & Tags ──────────────────────────────────────
        const personaPage5: SummaryEmbedOptions = {
          titleKey: "commands.tool.status.persona_page5_title",
          titleVars: { persona_name: personaName },
          descriptionKey: "commands.tool.status.persona_page5_description",
          color: ColorCode.INFO,
          fields: [
            {
              nameKey: "commands.tool.status.field_persona_prompt",
              value: personaPromptValue,
              inline: false,
            },
            {
              nameKey: "commands.tool.status.field_nai_tags",
              value: naiTagsValue,
              inline: false,
            },
            {
              nameKey: "commands.tool.status.field_nai_attg",
              value: attgValue,
              inline: false,
            },
          ],
        };

        // 14. Display paginated persona status from the preserved ButtonInteraction
        await replyPaginatedStatusPages(
          personaInteraction,
          locale,
          [
            personaPage1,
            personaPage2,
            personaPage3,
            personaPage4,
            personaPage5,
          ],
          MessageFlags.Ephemeral,
        );
        break;
      }

      default:
        log.error(`Invalid status scope received: ${scope}`);
        await replyInfoEmbed(interaction, locale, {
          titleKey: "general.errors.unknown_error_title",
          descriptionKey: "general.errors.unknown_error_description",
          color: ColorCode.ERROR,
        });
        return;
    }
  } catch (error) {
    log.error(`Error executing status command for scope ${scope}:`, error, {
      errorType: "CommandExecutionError",
      metadata: {
        commandName: "status",
        scope,
        guildDiscordId: serverDiscId,
      },
    });
    await replyInfoEmbed(interaction, locale, {
      titleKey: "general.errors.unknown_error_title",
      descriptionKey: "general.errors.unknown_error_description",
      color: ColorCode.ERROR,
    });
  }
}
