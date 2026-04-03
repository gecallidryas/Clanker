/**
 * Reminder Tool
 * Allows the AI to set reminders for users, causing TomoriBot to mention them at the specified time
 */

import { log } from "../../utils/misc/logger";
import {
  BaseTool,
  type ToolContext,
  type ToolResult,
  type ToolParameterSchema,
} from "../../types/tool/interfaces";
import {
  validateFutureTime,
  formatTimeRemaining,
} from "../../utils/text/stringHelper";
import {
  parseTimeWithOffset,
  formatUTCOffset,
  formatTimeWithOffset,
} from "../../utils/text/timezoneHelper";
import {
  isBridgeUserId,
  isMatrixBridgeWebhookUsername,
} from "../../utils/bridge";
import { resolveBridgeUserId } from "../../utils/matrix";

/**
 * Tool for creating scheduled tasks that trigger messages at specific times
 */
export class ReminderTool extends BaseTool {
  name = "create_task";
  description =
    "Create a scheduled task in a Discord channel. Use this for both user reminders and self tasks: a reminder is just a task that notifies a target user. IMPORTANT: Always set 'repetition_interval_hours' - use 0 for one-time tasks, or 1+ for recurring tasks (e.g., 24 for daily tasks). Use 'self_reminder' for tasks you should execute yourself on a schedule (for example daily summaries or periodic reports). For instant, one-time messages in other channels, use cross_channel_message instead as it sends immediately without scheduling. You can specify time in two ways: (1) Use relative time parameters like 'minutes_from_now', 'hours_from_now', 'days_from_now', 'months_from_now' for natural requests like 'in 2 hours' or 'tomorrow'. Multiple relative parameters add up. (2) Use absolute 'reminder_time' in YYYY-MM-DD_HH:MM format using the server's configured timezone (set via /config timezone) for specific dates/times. If both are provided, absolute time takes priority. If you omit all time parameters, the task defaults to 1 minute from now.";
  category = "utility" as const;

  parameters: ToolParameterSchema = {
    type: "object",
    properties: {
      reminder_purpose: {
        type: "string",
        description:
          "What the task is for. IMPORTANT: Be very descriptive and detailed (2-4 sentences) because you might not remember the context after a long time. Include WHAT the task is about, WHY it was set, and any relevant details from the conversation. The more context you provide now, the more helpful the task will be later, but do NOT include user/channel IDs or any meta information in this content.",
      },
      target_user_nickname: {
        type: "string",
        description:
          "Nickname of the Discord user this task should notify, as you see them in the current conversation or their user profile information.",
      },
      target_user_discord_id: {
        type: "string",
        description:
          "Discord ID of the user this task should notify (e.g., '123456789012345678'). This ID should be obtained from the user's information visible in the context.",
      },
      reminder_time: {
        type: "string",
        description:
          "OPTIONAL: Absolute time to trigger the task in YYYY-MM-DD_HH:MM format (e.g., '2025-09-05_15:30') using the server's configured timezone. Times are interpreted using the server's timezone setting from /config timezone. Use this for specific dates/times. If provided, this takes priority over 'from now' parameters.",
      },
      minutes_from_now: {
        type: "number",
        description:
          "OPTIONAL: Minutes from the current time to schedule the task. Can be combined with other 'from now' parameters.",
      },
      hours_from_now: {
        type: "number",
        description:
          "OPTIONAL: Hours from the current time to schedule the task. Can be combined with other 'from now' parameters.",
      },
      days_from_now: {
        type: "number",
        description:
          "OPTIONAL: Days from the current time to schedule the task. Can be combined with other 'from now' parameters.",
      },
      months_from_now: {
        type: "number",
        description:
          "OPTIONAL: Months from the current time to schedule the task. Can be combined with other 'from now' parameters. Uses calendar months (30.44 days average).",
      },
      repetition_interval_hours: {
        type: "number",
        description:
          "REQUIRED: Set to 0 for one-time tasks. Set to 1 or higher to make the task recurring (repeats every X hours after the first trigger). Example: 24 for daily tasks, 168 for weekly tasks.",
      },
      self_reminder: {
        type: "boolean",
        description:
          "OPTIONAL: Set to true when this is a task for you to execute yourself. This disables user mentions and focuses the prompt on the task.",
      },
      channel_id: {
        type: "string",
        description:
          "OPTIONAL: Discord channel ID where this task should trigger. Useful for cross-channel tasks. The channel must exist in the current server. If omitted, the current channel is used.",
      },
    },
    required: [
      "reminder_purpose",
      "target_user_nickname",
      "target_user_discord_id",
      "repetition_interval_hours",
    ],
  };

  /**
   * Check if reminder tool is available for the given provider
   * @param _provider - LLM provider name (unused)
   * @returns True if provider supports reminder functionality
   */
  isAvailableFor(_provider: string): boolean {
    // Reminder functionality works with all providers
    return true;
  }

  /**
   * Execute reminder creation
   * @param args - Arguments containing reminder details
   * @param context - Tool execution context
   * @returns Promise resolving to tool result
   */
  async execute(
    args: Record<string, unknown>,
    context: ToolContext,
  ): Promise<ToolResult> {
    // Validate parameters
    const validation = this.validateParameters(args);
    if (!validation.isValid) {
      return {
        success: false,
        error: `Invalid parameters: ${validation.errors?.join(", ") || `Missing required parameters: ${validation.missingParams?.join(", ")}`}`,
        data: {
          status: "reminder_creation_failed_invalid_args",
          reason: `Invalid parameters: ${validation.errors?.join(", ") || `Missing required parameters: ${validation.missingParams?.join(", ")}`}`,
        },
      };
    }

    // Extract arguments
    const reminderPurposeArg = args.reminder_purpose as string;
    let targetUserNicknameArg = args.target_user_nickname as string;
    let targetUserDiscordIdArg = args.target_user_discord_id as string;
    let reminderTimeArg = args.reminder_time as string | undefined;
    const minutesFromNowArg = args.minutes_from_now as number | undefined;
    const hoursFromNowArg = args.hours_from_now as number | undefined;
    const daysFromNowArg = args.days_from_now as number | undefined;
    const monthsFromNowArg = args.months_from_now as number | undefined;
    let repetitionIntervalHoursArg = args.repetition_interval_hours as
      | number
      | undefined;
    const selfReminderArg = args.self_reminder as boolean | undefined;
    const requestedChannelIdArg = args.channel_id as string | undefined;

    // NovelAI GLM recovery: resolve missing or garbled user/channel params from context.
    // GLM frequently omits target_user_nickname and generates slightly wrong Discord IDs
    // (e.g., last few digits off). When the model is clearly trying to target the message
    // author, resolve from context instead of failing.
    if (context.message?.author && selfReminderArg !== true) {
      const authorId = context.message.author.id;
      const guildMember = context.message.guild?.members.cache.get(authorId);
      const authorDisplayName =
        guildMember?.displayName ?? context.message.author.username;

      // 1. Fuzzy-match Discord ID: if the provided ID doesn't match any cached guild member,
      //    search ALL cached members for the closest snowflake ID within a tolerance of 1000.
      //    GLM often gets IDs wrong by a few digits due to floating-point precision loss
      //    on large snowflake IDs (which exceed Number.MAX_SAFE_INTEGER).
      //    Skip fuzzy-match entirely for Matrix user IDs (@user:host) — BigInt parsing would fail.
      if (targetUserDiscordIdArg && !isBridgeUserId(targetUserDiscordIdArg)) {
        const guild = context.message.guild;
        if (guild) {
          const exactMember = guild.members.cache.get(targetUserDiscordIdArg);
          if (!exactMember) {
            try {
              const garbledId = BigInt(targetUserDiscordIdArg);
              let closestMemberId: string | null = null;
              let smallestDiff = BigInt(1000); // threshold: < 1000

              // Scan all cached guild members for the closest matching ID
              for (const [memberId] of guild.members.cache) {
                const diff =
                  garbledId > BigInt(memberId)
                    ? garbledId - BigInt(memberId)
                    : BigInt(memberId) - garbledId;
                if (diff > 0n && diff < smallestDiff) {
                  smallestDiff = diff;
                  closestMemberId = memberId;
                }
              }

              if (closestMemberId) {
                log.info(
                  `Reminder tool: Correcting garbled Discord ID "${targetUserDiscordIdArg}" → "${closestMemberId}" (diff: ${smallestDiff}, fuzzy-matched from guild members cache)`,
                );
                targetUserDiscordIdArg = closestMemberId;
              }
            } catch {
              // BigInt parsing failed — ID contains non-numeric characters, skip fuzzy match
            }
          }
        }
      }

      // 2. Auto-fill missing target_user_nickname from context
      if (
        !targetUserNicknameArg?.trim() &&
        targetUserDiscordIdArg === authorId
      ) {
        log.info(
          `Reminder tool: Auto-filling missing target_user_nickname with "${authorDisplayName}" (message author)`,
        );
        targetUserNicknameArg = authorDisplayName;
      }

      // 3. Auto-fill missing target_user_discord_id if nickname matches the author
      if (!targetUserDiscordIdArg?.trim() && targetUserNicknameArg?.trim()) {
        const providedLower = targetUserNicknameArg.toLowerCase();
        const authorNameLower = authorDisplayName.toLowerCase();
        const authorUsernameLower =
          context.message.author.username.toLowerCase();
        if (
          providedLower === authorNameLower ||
          providedLower === authorUsernameLower
        ) {
          log.info(
            `Reminder tool: Auto-filling missing target_user_discord_id with "${authorId}" (nickname "${targetUserNicknameArg}" matches message author)`,
          );
          targetUserDiscordIdArg = authorId;
        }
      }
    }

    // Matrix ID recovery: LLMs occasionally drop or mangle the Matrix user ID.
    // resolveBridgeUserId() handles both failure modes (missing "@" prefix and plain
    // display name) and is a no-op for valid bridge IDs and Discord snowflakes.
    targetUserDiscordIdArg = resolveBridgeUserId(targetUserDiscordIdArg);

    // NovelAI GLM recovery: normalize absolute time format.
    // GLM may output "2025-09-05 15:30" (space), "2025-09-05T15:30" (ISO), or
    // "2025/09/05_15:30" (slashes) instead of the expected "YYYY-MM-DD_HH:MM" format.
    // Normalize common variants before parseTimeWithOffset rejects them.
    if (reminderTimeArg && typeof reminderTimeArg === "string") {
      let normalized = reminderTimeArg.trim();
      // 1. Replace slash date separators with dashes (2025/09/05 → 2025-09-05)
      normalized = normalized.replace(/^(\d{4})\/(\d{2})\/(\d{2})/, "$1-$2-$3");
      // 2. Replace space or T between date and time with underscore
      normalized = normalized.replace(
        /^(\d{4}-\d{2}-\d{2})[T ](\d{2}:\d{2})/,
        "$1_$2",
      );
      if (normalized !== reminderTimeArg) {
        log.info(
          `Reminder tool: Normalized time format "${reminderTimeArg}" → "${normalized}"`,
        );
        reminderTimeArg = normalized;
      }
    }

    // NovelAI GLM recovery: default repetition_interval_hours to 0 (one-time) when missing.
    // GLM frequently omits this required parameter for simple "remind me in X" requests.
    // Only for NovelAI — other providers have retries and should be required to explicitly
    // set this so the model is "conscious" of whether the reminder is one-time or recurring.
    if (
      context.provider === "novelai" &&
      typeof repetitionIntervalHoursArg !== "number"
    ) {
      log.info(
        "Reminder tool: Auto-filling missing repetition_interval_hours with 0 (one-time reminder)",
      );
      repetitionIntervalHoursArg = 0;
    }

    // Import database functions and utilities
    const { loadUserRow } = await import("../../utils/db/dbRead");
    const { addReminder } = await import("../../utils/db/dbWrite");
    const { sendStandardEmbed } = await import(
      "../../utils/discord/embedHelper"
    );
    const { ColorCode } = await import("../../utils/misc/logger");

    // Get server and user context
    const tomoriState = context.tomoriState;
    const resolvedUserId = context.message?.author?.id || context.userId;

    // Matrix relay messages arrive via Discord webhook (author = webhook bot).
    // The webhook bot has no users table record, so loadUserRow returns null.
    // Detect this case so we can relax the requestingUserRow guard below and
    // store created_by_user_id = null (the column is nullable for this reason).
    const isMatrixRelayRequester =
      !!context.message?.webhookId &&
      isMatrixBridgeWebhookUsername(context.message?.author?.username ?? "");

    const requestingUserRow = resolvedUserId
      ? await loadUserRow(resolvedUserId)
      : null;
    const channelId = context.channel.id;

    if (
      !tomoriState ||
      // Allow null requestingUserRow for Matrix relay webhooks — they have no
      // users table entry, so created_by_user_id will be stored as null
      (!requestingUserRow && !isMatrixRelayRequester) ||
      (requestingUserRow && !requestingUserRow.user_id) ||
      !tomoriState.server_id ||
      !resolvedUserId
    ) {
      // Log which specific value is missing for diagnostics
      const missing = [
        !tomoriState && "tomoriState",
        !requestingUserRow && !isMatrixRelayRequester && "requestingUserRow",
        requestingUserRow &&
          !requestingUserRow.user_id &&
          "requestingUserRow.user_id",
        tomoriState && !tomoriState.server_id && "tomoriState.server_id",
        !resolvedUserId && "resolvedUserId",
      ].filter(Boolean);
      log.error(
        `Critical state missing before handling create_task: [${missing.join(", ")}]`,
      );
      return {
        success: false,
        error: "Internal bot error: Critical state information is missing",
        data: {
          status: "reminder_creation_failed_internal_error",
          reason: "Internal bot error: Critical state information is missing",
        },
      };
    }

    const personaNickname =
      context.personaUsername ||
      tomoriState.tomori_nickname ||
      context.client.user?.username ||
      "TomoriBot";

    // Validate reminder purpose
    if (typeof reminderPurposeArg !== "string" || !reminderPurposeArg.trim()) {
      return {
        success: false,
        error:
          "The 'reminder_purpose' argument was missing, empty, or not a string",
        data: {
          status: "reminder_creation_failed_invalid_args",
          reason:
            "The 'reminder_purpose' argument was missing, empty, or not a string",
        },
      };
    }

    // Validate target user nickname
    const botUserId = context.client.user?.id;
    const isSelfReminder =
      selfReminderArg === true ||
      (typeof targetUserDiscordIdArg === "string" &&
        !!botUserId &&
        targetUserDiscordIdArg.trim() === botUserId);

    if (!isSelfReminder) {
      if (
        typeof targetUserNicknameArg !== "string" ||
        !targetUserNicknameArg.trim()
      ) {
        return {
          success: false,
          error:
            "The 'target_user_nickname' argument was missing, empty, or not a string",
          data: {
            status: "reminder_creation_failed_invalid_args",
            reason:
              "The 'target_user_nickname' argument was missing, empty, or not a string",
          },
        };
      }

      // Validate target user Discord ID
      if (
        typeof targetUserDiscordIdArg !== "string" ||
        !targetUserDiscordIdArg.trim()
      ) {
        return {
          success: false,
          error:
            "The 'target_user_discord_id' argument was missing, empty, or not a string",
          data: {
            status: "reminder_creation_failed_invalid_args",
            reason:
              "The 'target_user_discord_id' argument was missing, empty, or not a string",
          },
        };
      }
    } else if (!botUserId) {
      return {
        success: false,
        error: "Tomori bot user ID is not available to create a self reminder",
        data: {
          status: "reminder_creation_failed_internal_error",
          reason: "Tomori bot user ID is missing.",
        },
      };
    }

    // Validate repetition interval (0 = one-time, 1+ = recurring)
    let repetitionIntervalHours: number | null = null;
    if (typeof repetitionIntervalHoursArg === "number") {
      if (
        !Number.isFinite(repetitionIntervalHoursArg) ||
        !Number.isInteger(repetitionIntervalHoursArg) ||
        repetitionIntervalHoursArg < 0
      ) {
        return {
          success: false,
          error:
            "The 'repetition_interval_hours' must be 0 (for one-time) or an integer >= 1 (for recurring)",
          data: {
            status: "reminder_creation_failed_invalid_repeat_interval",
            reason:
              "The 'repetition_interval_hours' must be 0 or an integer >= 1.",
          },
        };
      }
      // Only set repetitionIntervalHours if it's > 0 (recurring)
      repetitionIntervalHours =
        repetitionIntervalHoursArg > 0 ? repetitionIntervalHoursArg : null;
    }

    // Resolve and validate target channel (optional override)
    let resolvedChannelId = channelId;
    if (typeof requestedChannelIdArg === "string") {
      const trimmedChannelId = requestedChannelIdArg.trim();
      if (!trimmedChannelId) {
        return {
          success: false,
          error: "The 'channel_id' argument was empty or invalid",
          data: {
            status: "reminder_creation_failed_invalid_channel",
            reason: "The 'channel_id' argument was empty or invalid.",
          },
        };
      }

      // If channel_id is provided in a DM context, only allow the current channel
      if (!context.guildId) {
        if (trimmedChannelId !== channelId) {
          return {
            success: false,
            error: "Channel overrides are not supported in DMs",
            data: {
              status: "reminder_creation_failed_invalid_channel",
              reason:
                "Channel overrides are not supported in DMs. Use the current channel.",
            },
          };
        }
      } else {
        let targetChannel = await context.client.channels
          .fetch(trimmedChannelId)
          .catch(() => null);

        // GLM fuzzy recovery: if exact channel ID not found, search all guild
        // channels for the closest snowflake ID within a tolerance of 1000.
        // GLM loses precision on large snowflake IDs due to float rounding.
        if (!targetChannel && context.guildId) {
          try {
            const garbledId = BigInt(trimmedChannelId);
            const guild = await context.client.guilds
              .fetch(context.guildId)
              .catch(() => null);
            if (guild) {
              let closestChannelId: string | null = null;
              let smallestDiff = BigInt(1000); // threshold: < 1000

              // Scan all cached guild channels for the closest matching ID
              for (const [chId] of guild.channels.cache) {
                const diff =
                  garbledId > BigInt(chId)
                    ? garbledId - BigInt(chId)
                    : BigInt(chId) - garbledId;
                if (diff > 0n && diff < smallestDiff) {
                  smallestDiff = diff;
                  closestChannelId = chId;
                }
              }

              if (closestChannelId) {
                log.info(
                  `Reminder tool: Correcting garbled channel ID "${trimmedChannelId}" → "${closestChannelId}" (diff: ${smallestDiff}, fuzzy-matched from guild channels cache)`,
                );
                targetChannel = await context.client.channels
                  .fetch(closestChannelId)
                  .catch(() => null);
              }
            }
          } catch {
            // BigInt parsing failed, skip fuzzy match
          }
        }

        if (!targetChannel || targetChannel.isDMBased()) {
          return {
            success: false,
            error: `Channel with ID '${trimmedChannelId}' was not found in this server`,
            data: {
              status: "reminder_creation_failed_invalid_channel",
              reason: `Channel not found in server: ${trimmedChannelId}`,
            },
          };
        }

        if (
          !("guildId" in targetChannel) ||
          targetChannel.guildId !== context.guildId
        ) {
          return {
            success: false,
            error: `Channel with ID '${trimmedChannelId}' was not found in this server`,
            data: {
              status: "reminder_creation_failed_invalid_channel",
              reason: `Channel not found in server: ${trimmedChannelId}`,
            },
          };
        }

        if (!targetChannel.isTextBased()) {
          return {
            success: false,
            error: "The specified channel is not a text-based server channel",
            data: {
              status: "reminder_creation_failed_invalid_channel",
              reason:
                "The specified channel is not a text-based server channel.",
            },
          };
        }
      }

      resolvedChannelId = trimmedChannelId;
    }

    // Determine which time method to use and calculate the final reminder time
    let finalReminderTime: Date | null = null;
    let timeCalculationMethod = "";

    // Get the server's configured timezone offset (default to 0/UTC if not set)
    const timezoneOffset = tomoriState.config.timezone_offset ?? 0;

    if (
      reminderTimeArg &&
      typeof reminderTimeArg === "string" &&
      reminderTimeArg.trim()
    ) {
      // Method 1: Absolute time provided - parse in server's configured timezone
      timeCalculationMethod = "absolute";
      finalReminderTime = parseTimeWithOffset(
        reminderTimeArg.trim(),
        timezoneOffset,
      );
      if (!finalReminderTime) {
        return {
          success: false,
          error: `Invalid reminder time format. Please use YYYY-MM-DD_HH:MM format (e.g., '2025-09-05_15:30') in the server's configured timezone (${formatUTCOffset(timezoneOffset)}). The provided format '${reminderTimeArg}' is invalid.`,
          data: {
            status: "reminder_creation_failed_invalid_time_format",
            reason: `Invalid reminder time format: '${reminderTimeArg}'. Expected YYYY-MM-DD_HH:MM format in ${formatUTCOffset(timezoneOffset)}.`,
            provided_time: reminderTimeArg,
            server_timezone: formatUTCOffset(timezoneOffset),
          },
        };
      }
    } else {
      // Method 2: Relative time parameters - calculate from current time
      const hasRelativeParams =
        (typeof minutesFromNowArg === "number" && minutesFromNowArg > 0) ||
        (typeof hoursFromNowArg === "number" && hoursFromNowArg > 0) ||
        (typeof daysFromNowArg === "number" && daysFromNowArg > 0) ||
        (typeof monthsFromNowArg === "number" && monthsFromNowArg > 0);

      // Default to 1 minute if no time parameters provided (immediate message use case)
      let effectiveMinutesFromNow = minutesFromNowArg;
      if (!hasRelativeParams) {
        effectiveMinutesFromNow = 1;
        log.info(
          "No time parameters provided for reminder - defaulting to 1 minute from now",
        );
      }

      // Calculate relative time by adding all "from now" parameters
      timeCalculationMethod = "relative";
      const currentTime = new Date();
      let totalMilliseconds = 0;

      // Add each time component (convert to milliseconds)
      if (
        typeof effectiveMinutesFromNow === "number" &&
        effectiveMinutesFromNow > 0
      ) {
        totalMilliseconds += effectiveMinutesFromNow * 60 * 1000;
      }
      if (typeof hoursFromNowArg === "number" && hoursFromNowArg > 0) {
        totalMilliseconds += hoursFromNowArg * 60 * 60 * 1000;
      }
      if (typeof daysFromNowArg === "number" && daysFromNowArg > 0) {
        totalMilliseconds += daysFromNowArg * 24 * 60 * 60 * 1000;
      }
      if (typeof monthsFromNowArg === "number" && monthsFromNowArg > 0) {
        // Use average month length (30.44 days) for consistency
        totalMilliseconds += monthsFromNowArg * 30.44 * 24 * 60 * 60 * 1000;
      }

      finalReminderTime = new Date(currentTime.getTime() + totalMilliseconds);
    }

    const reminderPurpose = reminderPurposeArg.trim();
    const targetUserNickname = targetUserNicknameArg?.trim();
    const targetUserDiscordId = targetUserDiscordIdArg?.trim();

    // Validate that the calculated time is in the future (both absolute and relative times)
    if (!finalReminderTime || !validateFutureTime(finalReminderTime)) {
      const timeDisplay =
        timeCalculationMethod === "absolute"
          ? reminderTimeArg
          : `calculated from relative parameters (${[
              minutesFromNowArg && `${minutesFromNowArg} minutes`,
              hoursFromNowArg && `${hoursFromNowArg} hours`,
              daysFromNowArg && `${daysFromNowArg} days`,
              monthsFromNowArg && `${monthsFromNowArg} months`,
            ]
              .filter(Boolean)
              .join(", ")})`;

      return {
        success: false,
        error: `The reminder time must be in the future. The ${timeCalculationMethod} time ${timeDisplay} results in a past time or is too close to the current time.`,
        data: {
          status: "reminder_creation_failed_past_time",
          reason: `The ${timeCalculationMethod} time calculation resulted in a past time.`,
          calculated_time: finalReminderTime?.toISOString() || "invalid",
          current_utc_time: new Date().toISOString(),
          time_method: timeCalculationMethod,
        },
      };
    }

    try {
      let actualNicknameInDB = targetUserNickname || "Tomori";
      let resolvedTargetUserId = targetUserDiscordId || "";

      if (isSelfReminder) {
        resolvedTargetUserId = botUserId as string;
        actualNicknameInDB =
          tomoriState.tomori_nickname ||
          context.client.user?.username ||
          "Tomori";
      } else if (isBridgeUserId(resolvedTargetUserId)) {
        // Matrix users have no users table record — their ID is "@user:host" format.
        // Trust the AI-provided nickname directly (verified by the context builder
        // which injects their display name from matrixDisplayNameToId).
        actualNicknameInDB = targetUserNickname;
        log.info(
          `Reminder: Target is a Matrix user (${resolvedTargetUserId}), skipping DB lookup and using provided nickname "${actualNicknameInDB}"`,
        );
      } else {
        // Load target user to verify they exist
        const targetUserRow = await loadUserRow(resolvedTargetUserId);

        if (!targetUserRow || !targetUserRow.user_id) {
          log.warn(
            `Reminder: Target user with Discord ID ${resolvedTargetUserId} not found`,
          );
          return {
            success: false,
            error: `The user with Discord ID '${resolvedTargetUserId}' was not found in TomoriBot's records`,
            data: {
              status: "reminder_creation_failed_user_not_found",
              target_user_discord_id: resolvedTargetUserId,
              reason: `The user with Discord ID '${resolvedTargetUserId}' was not found in TomoriBot's records. TomoriBot can only create reminders for users she knows.`,
            },
          };
        }

        // Verify nickname as "two-factor" check
        actualNicknameInDB = targetUserRow.user_nickname;
        const guildMember =
          context.message?.guild?.members.cache.get(resolvedTargetUserId);
        const guildDisplayName = guildMember?.displayName?.toLowerCase();
        const discordUsername = guildMember?.user?.username?.toLowerCase();

        // Allow if LLM-provided nickname matches ANY of:
        // 1. Database nickname
        // 2. Current guild display name
        // 3. Discord username (bulletproof fallback)
        const providedNicknameLower = (targetUserNickname || "").toLowerCase();
        const dbNicknameLower = actualNicknameInDB.toLowerCase();
        const nicknameValid =
          dbNicknameLower === providedNicknameLower ||
          providedNicknameLower === guildDisplayName ||
          dbNicknameLower === guildDisplayName ||
          providedNicknameLower === discordUsername;

        if (!nicknameValid) {
          log.warn(
            `Reminder: Nickname mismatch for target user ${resolvedTargetUserId}. LLM provided: '${targetUserNickname}', DB has: '${actualNicknameInDB}', Guild display: '${guildMember?.displayName}', Discord username '${guildMember?.user?.username}'.`,
          );
          return {
            success: false,
            error: `The provided nickname '${targetUserNickname}' does not match the records for user ID '${resolvedTargetUserId}'`,
            data: {
              status: "reminder_creation_failed_nickname_mismatch",
              target_user_discord_id: resolvedTargetUserId,
              provided_nickname: targetUserNickname,
              actual_nickname: actualNicknameInDB,
              guild_display_name: guildMember?.displayName,
              discord_username: guildMember?.user?.username,
              reason: `The provided nickname '${targetUserNickname}' does not match the records for user ID '${resolvedTargetUserId}' (TomoriBot knows them as '${actualNicknameInDB}', guild shows '${guildMember?.displayName}', Discord username '${guildMember?.user?.username}'). Please ensure the Discord ID and nickname correspond to the same user.`,
            },
          };
        }
      }

      // Create the reminder in the database
      const dbResult = await addReminder({
        server_id: tomoriState.server_id,
        channel_disc_id: resolvedChannelId,
        user_discord_id: resolvedTargetUserId,
        user_nickname: actualNicknameInDB, // Use the verified nickname from DB
        reminder_purpose: reminderPurpose,
        reminder_time: finalReminderTime,
        repetition_interval_hours: repetitionIntervalHours,
        self_reminder: isSelfReminder,
        created_by_user_id: requestingUserRow?.user_id ?? null,
        persona_id: context.tomoriState.tomori_id ?? null,
      });

      if (dbResult) {
        log.success(
          `Reminder created (ID: ${dbResult.reminder_id}): "${reminderPurpose}" for ${actualNicknameInDB} (${resolvedTargetUserId}) at ${finalReminderTime.toISOString()}`,
        );

        // Calculate time remaining for user-friendly display
        const timeRemainingMs = finalReminderTime.getTime() - Date.now();
        const timeRemainingStr = formatTimeRemaining(timeRemainingMs);

        // Send confirmation embed to the channel
        // Format the reminder time in the server's configured timezone
        const formattedReminderTime = formatTimeWithOffset(
          finalReminderTime,
          timezoneOffset,
          {
            year: "numeric",
            month: "long",
            day: "numeric",
            hour: "2-digit",
            minute: "2-digit",
          },
        );

        const useRecurringTaskEmbed =
          isSelfReminder && repetitionIntervalHours !== null;
        const useOneTimeTaskEmbed =
          isSelfReminder && repetitionIntervalHours === null;
        const reminderPurposeText =
          reminderPurpose.length > 200
            ? `${reminderPurpose.substring(0, 197)}...`
            : reminderPurpose;
        const reminderTimeText = `${formattedReminderTime} (${formatUTCOffset(timezoneOffset)})`;
        const baseDescriptionVars = {
          user_nickname: actualNicknameInDB,
          reminder_purpose: reminderPurposeText,
          reminder_time: reminderTimeText,
        };
        const descriptionVars = useRecurringTaskEmbed
          ? {
              ...baseDescriptionVars,
              repetition_interval_hours: repetitionIntervalHours as number,
            }
          : baseDescriptionVars;

        await sendStandardEmbed(
          context.channel,
          context.locale,
          {
            color: useRecurringTaskEmbed ? ColorCode.INFO : ColorCode.SUCCESS,
            titleKey: useRecurringTaskEmbed
              ? "reminders.recurring_task_set_title"
              : useOneTimeTaskEmbed
                ? "reminders.task_set_title"
                : "reminders.reminder_set_title",
            titleVars: {
              persona_nickname: personaNickname,
            },
            descriptionKey: useRecurringTaskEmbed
              ? "reminders.recurring_task_set_description"
              : useOneTimeTaskEmbed
                ? "reminders.task_set_description"
                : "reminders.reminder_set_description",
            descriptionVars,
            footerKey: useRecurringTaskEmbed
              ? "reminders.recurring_task_set_footer"
              : repetitionIntervalHours
                ? "reminders.reminder_set_footer_recurring"
                : useOneTimeTaskEmbed
                  ? "reminders.task_set_footer"
                  : "reminders.reminder_set_footer",
            footerVars: repetitionIntervalHours
              ? {
                  time_remaining: timeRemainingStr,
                  repetition_interval_hours: repetitionIntervalHours,
                }
              : {
                  time_remaining: timeRemainingStr,
                },
          },
          {
            webhook: context.webhook,
            personaUsername: context.personaUsername,
            personaAvatarUrl: context.personaAvatarUrl,
          },
        );

        return {
          success: true,
          message: `Reminder successfully set for ${actualNicknameInDB}`,
          data: {
            status: "reminder_created_successfully",
            reminder_id: dbResult.reminder_id,
            target_user_nickname: actualNicknameInDB,
            target_user_discord_id: resolvedTargetUserId,
            reminder_purpose: reminderPurpose,
            reminder_time: finalReminderTime.toISOString(),
            repetition_interval_hours: repetitionIntervalHours,
            channel_id: resolvedChannelId,
            self_reminder: isSelfReminder,
            time_remaining_ms: timeRemainingMs,
            time_remaining_text: timeRemainingStr,
          },
        };
      }

      log.error("Failed to create reminder (DB error)");
      return {
        success: false,
        error: "Database operation failed to create reminder",
        data: {
          status: "reminder_creation_failed_db_error",
          reason: "Database operation failed to create reminder",
        },
      };
    } catch (error) {
      log.error("Error during reminder creation", error as Error);
      return {
        success: false,
        error: "Error occurred while creating reminder",
        data: {
          status: "reminder_creation_failed_error",
          reason: error instanceof Error ? error.message : "Unknown error",
        },
      };
    }
  }
}
