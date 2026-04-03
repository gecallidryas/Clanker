import {
  PermissionFlagsBits,
  type Message,
  type GuildMember,
} from "discord.js";
import { sql } from "@/utils/db/client";
import { CooldownType, type TomoriConfigRow } from "@/types/db/schema";
import { log } from "@/utils/misc/logger";
import { getCachedWhitelistStatus } from "@/utils/cache/channelWhitelistCache";

/**
 * Result of a cooldown check operation
 */
export interface CooldownCheckResult {
  isOnCooldown: boolean;
  remainingSeconds: number;
  cooldownType: CooldownType;
}

/**
 * Checks if a user is exempt from cooldowns based on type and permissions.
 * Server managers (users with ManageGuild permission) are exempt from cooldown types 1-3.
 * Only type 4 (STRICT_SERVER_WIDE) has no exemptions.
 * @param member - Guild member to check
 * @param cooldownType - The cooldown type configured
 * @returns True if the user is exempt from the cooldown
 */
export function isExemptFromCooldown(
  member: GuildMember | null,
  cooldownType: CooldownType,
): boolean {
  // Type 0 (OFF) has no cooldown, so exemption is irrelevant
  // Type 4 (STRICT_SERVER_WIDE) has no exemptions - everyone must wait
  if (
    cooldownType === CooldownType.OFF ||
    cooldownType === CooldownType.STRICT_SERVER_WIDE
  ) {
    return false;
  }

  // Types 1-3 (PER_USER, PER_CHANNEL, SERVER_WIDE) exempt server managers
  if (member?.permissions.has(PermissionFlagsBits.ManageGuild)) {
    return true;
  }

  return false;
}

/**
 * Checks if a message trigger is on cooldown.
 * @param message - The Discord message that triggered the bot
 * @param config - The Tomori config containing cooldown settings
 * @returns CooldownCheckResult with cooldown status and remaining time
 */
export async function checkMessageTriggerCooldown(
  message: Message,
  config: TomoriConfigRow,
): Promise<CooldownCheckResult> {
  // 1. Check whitelist status FIRST (before checking cooldown type)
  const serverDiscId = message.guildId ?? message.author.id;
  const memberRoleDiscIds = message.member
    ? message.member.roles.cache.map((role) => role.id)
    : undefined;

  // Get parent channel ID if this is a thread (threads inherit whitelist from parent)
  const isThread =
    "isThread" in message.channel &&
    typeof message.channel.isThread === "function" &&
    message.channel.isThread();
  const parentChannelId = isThread ? message.channel.parent?.id : undefined;

  const whitelistStatus = await getCachedWhitelistStatus(
    serverDiscId,
    message.channelId,
    memberRoleDiscIds,
    parentChannelId,
  );

  // 2. Block if whitelist policy disallows this trigger
  if (!whitelistStatus.isTriggerAllowed) {
    return {
      isOnCooldown: true,
      remainingSeconds: 999999,
      cooldownType: CooldownType.OFF,
    };
  }

  // 3. Determine which cooldown settings to use
  // If a channel-specific override exists, use it; otherwise inherit the global settings
  const cooldownType = whitelistStatus.hasChannelCooldownOverride
    ? (whitelistStatus.channelCooldownType ??
      config.cooldown_type ??
      CooldownType.OFF)
    : (config.cooldown_type ?? CooldownType.OFF);

  // Diagnostic logging for whitelist-based cooldowns
  if (whitelistStatus.isChannelWhitelisted) {
    if (whitelistStatus.hasChannelCooldownOverride) {
      log.info(
        `[Cooldown Check] Channel ${message.channelId} is whitelisted - using channel-specific cooldown type ${cooldownType}, length ${whitelistStatus.channelCooldownLength}s`,
      );
    } else {
      log.info(
        `[Cooldown Check] Channel ${message.channelId} is whitelisted - inheriting global cooldown type ${cooldownType}`,
      );
    }
  } else {
    log.info(
      `[Cooldown Check] Channel ${message.channelId} NOT whitelisted - using global cooldown type ${cooldownType}`,
    );
  }

  // If cooldowns are off, not on cooldown
  if (cooldownType === CooldownType.OFF) {
    log.info(`[Cooldown Check] Cooldown type is OFF - skipping cooldown check`);
    return {
      isOnCooldown: false,
      remainingSeconds: 0,
      cooldownType,
    };
  }

  // Check if user is exempt from this cooldown type
  // Can be disabled for testing with DISABLE_COOLDOWN_EXEMPTIONS=true
  const disableExemptions = process.env.DISABLE_COOLDOWN_EXEMPTIONS === "true";

  log.info(
    `[Cooldown Check] DISABLE_COOLDOWN_EXEMPTIONS = ${process.env.DISABLE_COOLDOWN_EXEMPTIONS} (parsed as: ${disableExemptions})`,
  );

  const member = message.member;
  const isExempt =
    !disableExemptions && isExemptFromCooldown(member, cooldownType);

  if (isExempt) {
    log.info(
      `[Cooldown Check] User ${message.author.id} is EXEMPT from cooldown type ${cooldownType} (has ManageGuild permission)`,
    );
    return {
      isOnCooldown: false,
      remainingSeconds: 0,
      cooldownType,
    };
  }

  if (
    disableExemptions &&
    member?.permissions.has(PermissionFlagsBits.ManageGuild)
  ) {
    log.warn(
      `[Cooldown Check] User ${message.author.id} WOULD BE EXEMPT but exemptions are DISABLED for testing`,
    );
  }

  log.info(
    `[Cooldown Check] User ${message.author.id} is NOT exempt - proceeding to database check`,
  );

  // Determine which identifiers to populate based on cooldown type
  const userDiscIdParam =
    cooldownType === CooldownType.PER_USER ? message.author.id : null;
  const channelDiscIdParam =
    cooldownType === CooldownType.PER_CHANNEL ? message.channelId : null;

  try {
    // Check if cooldown exists and is still active
    const now = Date.now();

    log.info(
      `[Cooldown Check] Querying database - type: ${cooldownType}, server: ${serverDiscId}, user: ${userDiscIdParam}, channel: ${channelDiscIdParam}, now: ${now}`,
    );

    const [cooldown] = await sql`
			SELECT expiry_time
			FROM cooldowns
			WHERE cooldown_type = ${cooldownType}
			AND server_disc_id = ${serverDiscId}
			AND (${userDiscIdParam}::TEXT IS NULL OR user_disc_id = ${userDiscIdParam})
			AND (${channelDiscIdParam}::TEXT IS NULL OR channel_disc_id = ${channelDiscIdParam})
			AND expiry_time > ${now}
		`;

    if (!cooldown) {
      log.info(
        `[Cooldown Check] No active cooldown found for type ${cooldownType} in server ${serverDiscId}`,
      );
      return {
        isOnCooldown: false,
        remainingSeconds: 0,
        cooldownType,
      };
    }

    const remainingMs = Number(cooldown.expiry_time) - now;
    const remainingSeconds = Math.ceil(remainingMs / 1000);

    log.info(
      `[Cooldown Check] FOUND active cooldown - ${remainingSeconds}s remaining (expires: ${cooldown.expiry_time})`,
    );

    return {
      isOnCooldown: true,
      remainingSeconds,
      cooldownType,
    };
  } catch (error) {
    // Log error but fail-open to prevent blocking legitimate users
    log.warn("Failed to check message trigger cooldown", {
      cooldownType,
      serverDiscId,
      userDiscId: userDiscIdParam,
      channelDiscId: channelDiscIdParam,
      error: error instanceof Error ? error.message : "Unknown error",
    });
    return {
      isOnCooldown: false,
      remainingSeconds: 0,
      cooldownType,
    };
  }
}

/**
 * Sets the cooldown after a successful message trigger response.
 * @param message - The Discord message that triggered the bot
 * @param config - The Tomori config containing cooldown settings
 */
export async function setMessageTriggerCooldown(
  message: Message,
  config: TomoriConfigRow,
): Promise<void> {
  // 1. Check whitelist status FIRST to determine which settings to use
  const serverDiscId = message.guildId ?? message.author.id;
  const memberRoleDiscIds = message.member
    ? message.member.roles.cache.map((role) => role.id)
    : undefined;

  // Get parent channel ID if this is a thread (threads inherit whitelist from parent)
  const isThread =
    "isThread" in message.channel &&
    typeof message.channel.isThread === "function" &&
    message.channel.isThread();
  const parentChannelId = isThread ? message.channel.parent?.id : undefined;

  const whitelistStatus = await getCachedWhitelistStatus(
    serverDiscId,
    message.channelId,
    memberRoleDiscIds,
    parentChannelId,
  );

  // 2. Determine which cooldown settings to use
  // If a channel-specific override exists, use it; otherwise inherit the global settings
  const cooldownType = whitelistStatus.hasChannelCooldownOverride
    ? (whitelistStatus.channelCooldownType ??
      config.cooldown_type ??
      CooldownType.OFF)
    : (config.cooldown_type ?? CooldownType.OFF);

  const cooldownLengthSeconds = whitelistStatus.hasChannelCooldownOverride
    ? (whitelistStatus.channelCooldownLength ?? config.cooldown_length ?? 5)
    : (config.cooldown_length ?? 5);

  // Diagnostic logging for whitelist-based cooldowns
  if (whitelistStatus.isChannelWhitelisted) {
    if (whitelistStatus.hasChannelCooldownOverride) {
      log.info(
        `[Cooldown Set] Channel ${message.channelId} is whitelisted - setting cooldown type ${cooldownType}, length ${cooldownLengthSeconds}s`,
      );
    } else {
      log.info(
        `[Cooldown Set] Channel ${message.channelId} is whitelisted - inheriting global cooldown type ${cooldownType}, length ${cooldownLengthSeconds}s`,
      );
    }
  }

  // If cooldowns are off, nothing to set
  if (cooldownType === CooldownType.OFF) {
    return;
  }

  // Get cooldown duration in milliseconds
  const cooldownDurationMs = cooldownLengthSeconds * 1000;
  const expiryTime = Date.now() + cooldownDurationMs;

  // Determine which identifiers to populate based on cooldown type
  const userDiscIdParam =
    cooldownType === CooldownType.PER_USER ? message.author.id : null;
  const channelDiscIdParam =
    cooldownType === CooldownType.PER_CHANNEL ? message.channelId : null;

  try {
    await sql`
			INSERT INTO cooldowns (
				cooldown_type,
				server_disc_id,
				user_disc_id,
				channel_disc_id,
				expiry_time
			)
			VALUES (
				${cooldownType},
				${serverDiscId},
				${userDiscIdParam},
				${channelDiscIdParam},
				${expiryTime}
			)
			ON CONFLICT (cooldown_type, COALESCE(server_disc_id, ''), COALESCE(user_disc_id, ''), COALESCE(channel_disc_id, ''), COALESCE(command_category, ''))
			DO UPDATE SET expiry_time = ${expiryTime}
		`;

    log.info(
      `[Cooldown Set] Successfully set cooldown - type: ${cooldownType}, server: ${serverDiscId}, user: ${userDiscIdParam}, channel: ${channelDiscIdParam}, expires in ${cooldownLengthSeconds}s (expiryTime: ${expiryTime})`,
    );

    // Verify the cooldown was written by reading it back
    const [verification] = await sql`
			SELECT expiry_time FROM cooldowns
			WHERE cooldown_type = ${cooldownType}
			AND server_disc_id = ${serverDiscId}
			AND (${userDiscIdParam}::TEXT IS NULL OR user_disc_id = ${userDiscIdParam})
			AND (${channelDiscIdParam}::TEXT IS NULL OR channel_disc_id = ${channelDiscIdParam})
		`;

    if (verification) {
      log.info(
        `[Cooldown Set] VERIFIED - Cooldown exists in database with expiry_time: ${verification.expiry_time}`,
      );
    } else {
      log.error(
        `[Cooldown Set] VERIFICATION FAILED - Cooldown not found in database after insert!`,
      );
    }
  } catch (error) {
    // Log but don't throw - cooldown failures shouldn't break message handling
    log.warn("Failed to set message trigger cooldown", {
      cooldownType,
      serverDiscId,
      userDiscId: userDiscIdParam,
      channelDiscId: channelDiscIdParam,
      error: error instanceof Error ? error.message : "Unknown error",
    });
  }
}

/**
 * Gets the locale key for the cooldown type footer text.
 * @param cooldownType - The cooldown type
 * @returns The locale key for the footer text
 */
export function getCooldownTypeFooterKey(cooldownType: CooldownType): string {
  switch (cooldownType) {
    case CooldownType.PER_USER:
      return "general.message_cooldown_footer_per_user";
    case CooldownType.PER_CHANNEL:
      return "general.message_cooldown_footer_per_channel";
    case CooldownType.SERVER_WIDE:
      return "general.message_cooldown_footer_server_wide";
    case CooldownType.STRICT_SERVER_WIDE:
      return "general.message_cooldown_footer_strict";
    default:
      return "general.message_cooldown_footer_per_user";
  }
}
