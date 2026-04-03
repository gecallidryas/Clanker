import { PermissionFlagsBits, type GuildMember } from "discord.js";
import { sql } from "@/utils/db/client";
import { CooldownType } from "@/types/db/schema";
import type { WhitelistBlockReason } from "@/types/misc/channelWhitelist";
import { log } from "@/utils/misc/logger";
import { getCachedWhitelistStatus } from "@/utils/cache/channelWhitelistCache";

/**
 * Result of a cooldown check operation
 */
export interface CooldownCheckResult {
  isOnCooldown: boolean;
  remainingSeconds: number;
  cooldownType: CooldownType;
  /** True when whitelist restrictions block this trigger */
  blockedByWhitelist?: boolean;
  /** Which whitelist rule blocked the trigger when blockedByWhitelist is true */
  whitelistBlockReason?: WhitelistBlockReason;
}

/**
 * Checks if a user is exempt from cooldowns based on type and permissions.
 * Server managers (users with ManageGuild permission) are exempt from cooldown types 1-3.
 * Only type 4 (STRICT_SERVER_WIDE) has no exemptions.
 *
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
 * Checks if a cooldown is active for the given scope.
 * Works for both message triggers and slash commands.
 *
 * @param serverId - Discord server/guild ID
 * @param userId - Discord user ID
 * @param channelId - Discord channel ID
 * @param cooldownType - The type of cooldown configured
 * @param member - Guild member (for exemption check)
 * @returns CooldownCheckResult with cooldown status and remaining time
 */
export async function checkCooldown(
  serverId: string,
  userId: string,
  channelId: string,
  cooldownType: CooldownType,
  member: GuildMember | null = null,
): Promise<CooldownCheckResult> {
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

  const isExempt =
    !disableExemptions && isExemptFromCooldown(member, cooldownType);

  if (isExempt) {
    log.info(
      `[Cooldown Check] User ${userId} is EXEMPT from cooldown type ${cooldownType} (has ManageGuild permission)`,
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
      `[Cooldown Check] User ${userId} WOULD BE EXEMPT but exemptions are DISABLED for testing`,
    );
  }

  log.info(
    `[Cooldown Check] User ${userId} is NOT exempt - proceeding to database check`,
  );

  // Determine which identifiers to populate based on cooldown type
  const userDiscIdParam =
    cooldownType === CooldownType.PER_USER ? userId : null;
  const channelDiscIdParam =
    cooldownType === CooldownType.PER_CHANNEL ? channelId : null;

  try {
    // Check if cooldown exists and is still active
    const now = Date.now();

    log.info(
      `[Cooldown Check] Querying database - type: ${cooldownType}, server: ${serverId}, user: ${userDiscIdParam}, channel: ${channelDiscIdParam}, now: ${now}`,
    );

    const [cooldown] = await sql`
			SELECT expiry_time
			FROM cooldowns
			WHERE cooldown_type = ${cooldownType}
			AND server_disc_id = ${serverId}
			AND (${userDiscIdParam}::TEXT IS NULL OR user_disc_id = ${userDiscIdParam})
			AND (${channelDiscIdParam}::TEXT IS NULL OR channel_disc_id = ${channelDiscIdParam})
			AND expiry_time > ${now}
		`;

    if (!cooldown) {
      log.info(
        `[Cooldown Check] No active cooldown found for type ${cooldownType} in server ${serverId}`,
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
    log.warn("Failed to check cooldown", {
      cooldownType,
      serverId,
      userId: userDiscIdParam,
      channelId: channelDiscIdParam,
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
 * Sets a cooldown for the given scope after a successful response.
 * Works for both message triggers and slash commands.
 *
 * @param serverId - Discord server/guild ID
 * @param userId - Discord user ID
 * @param channelId - Discord channel ID
 * @param cooldownType - The type of cooldown configured
 * @param cooldownLengthSeconds - Duration of the cooldown in seconds
 */
export async function setCooldown(
  serverId: string,
  userId: string,
  channelId: string,
  cooldownType: CooldownType,
  cooldownLengthSeconds: number,
): Promise<void> {
  // If cooldowns are off, nothing to set
  if (cooldownType === CooldownType.OFF) {
    return;
  }

  // Get cooldown duration in milliseconds
  const cooldownDurationMs = cooldownLengthSeconds * 1000;
  const expiryTime = Date.now() + cooldownDurationMs;

  // Determine which identifiers to populate based on cooldown type
  const userDiscIdParam =
    cooldownType === CooldownType.PER_USER ? userId : null;
  const channelDiscIdParam =
    cooldownType === CooldownType.PER_CHANNEL ? channelId : null;

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
				${serverId},
				${userDiscIdParam},
				${channelDiscIdParam},
				${expiryTime}
			)
			ON CONFLICT (cooldown_type, COALESCE(server_disc_id, ''), COALESCE(user_disc_id, ''), COALESCE(channel_disc_id, ''), COALESCE(command_category, ''))
			DO UPDATE SET expiry_time = ${expiryTime}
		`;

    log.info(
      `[Cooldown Set] Successfully set cooldown - type: ${cooldownType}, server: ${serverId}, user: ${userDiscIdParam}, channel: ${channelDiscIdParam}, expires in ${cooldownLengthSeconds}s (expiryTime: ${expiryTime})`,
    );

    // Verify the cooldown was written by reading it back
    const [verification] = await sql`
			SELECT expiry_time FROM cooldowns
			WHERE cooldown_type = ${cooldownType}
			AND server_disc_id = ${serverId}
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
    log.warn("Failed to set cooldown", {
      cooldownType,
      serverId,
      userId: userDiscIdParam,
      channelId: channelDiscIdParam,
      error: error instanceof Error ? error.message : "Unknown error",
    });
  }
}

/**
 * Checks cooldown for message triggers with whitelist awareness.
 * This is a convenience wrapper around checkCooldown that handles whitelist logic.
 *
 * @param serverId - Discord server/guild ID
 * @param userId - Discord user ID
 * @param channelId - Discord channel ID
 * @param globalCooldownType - Global cooldown type from config
 * @param member - Guild member (for exemption check)
 * @returns CooldownCheckResult with cooldown status and remaining time
 */
export async function checkMessageTriggerCooldownWithWhitelist(
  serverId: string,
  userId: string,
  channelId: string,
  globalCooldownType: CooldownType,
  member: GuildMember | null = null,
): Promise<CooldownCheckResult> {
  // 1. Check whitelist status FIRST (before checking cooldown type)
  const memberRoleDiscIds = member
    ? member.roles.cache.map((role) => role.id)
    : undefined;

  // Get parent channel ID if this is a thread (threads inherit whitelist from parent)
  const channel = member?.guild.channels.cache.get(channelId);
  const isThread =
    channel &&
    "isThread" in channel &&
    typeof channel.isThread === "function" &&
    channel.isThread();
  const parentChannelId = isThread && "parent" in channel ? channel.parent?.id : undefined;

  const whitelistStatus = await getCachedWhitelistStatus(
    serverId,
    channelId,
    memberRoleDiscIds,
    parentChannelId,
  );

  // 2. Block if whitelist policy disallows this trigger
  if (!whitelistStatus.isTriggerAllowed) {
    return {
      isOnCooldown: true,
      remainingSeconds: 0,
      cooldownType: CooldownType.OFF,
      blockedByWhitelist: true,
      whitelistBlockReason: whitelistStatus.blockReason,
    };
  }

  // 3. Determine which cooldown settings to use
  // If a channel-specific override exists, use it; otherwise inherit the global settings
  const effectiveCooldownType = whitelistStatus.hasChannelCooldownOverride
    ? (whitelistStatus.channelCooldownType ?? globalCooldownType)
    : globalCooldownType;

  // Diagnostic logging for whitelist-based cooldowns
  if (whitelistStatus.isChannelWhitelisted) {
    if (whitelistStatus.hasChannelCooldownOverride) {
      log.info(
        `[Cooldown Check] Channel ${channelId} is whitelisted - using channel-specific cooldown type ${effectiveCooldownType}, length ${whitelistStatus.channelCooldownLength}s`,
      );
    } else {
      log.info(
        `[Cooldown Check] Channel ${channelId} is whitelisted - inheriting global cooldown type ${effectiveCooldownType}`,
      );
    }
  } else {
    log.info(
      `[Cooldown Check] Channel ${channelId} NOT whitelisted - using global cooldown type ${effectiveCooldownType}`,
    );
  }

  // 4. Check cooldown using shared function
  return checkCooldown(
    serverId,
    userId,
    channelId,
    effectiveCooldownType,
    member,
  );
}

/**
 * Sets cooldown for message triggers with whitelist awareness.
 * This is a convenience wrapper around setCooldown that handles whitelist logic.
 *
 * @param serverId - Discord server/guild ID
 * @param userId - Discord user ID
 * @param channelId - Discord channel ID
 * @param globalCooldownType - Global cooldown type from config
 * @param globalCooldownLength - Global cooldown length from config
 */
export async function setMessageTriggerCooldownWithWhitelist(
  serverId: string,
  userId: string,
  channelId: string,
  globalCooldownType: CooldownType,
  globalCooldownLength: number,
  member: GuildMember | null = null,
): Promise<void> {
  // 1. Check whitelist status FIRST to determine which settings to use
  const memberRoleDiscIds = member
    ? member.roles.cache.map((role) => role.id)
    : undefined;

  // Get parent channel ID if this is a thread (threads inherit whitelist from parent)
  const channel = member?.guild.channels.cache.get(channelId);
  const isThread =
    channel &&
    "isThread" in channel &&
    typeof channel.isThread === "function" &&
    channel.isThread();
  const parentChannelId = isThread && "parent" in channel ? channel.parent?.id : undefined;

  const whitelistStatus = await getCachedWhitelistStatus(
    serverId,
    channelId,
    memberRoleDiscIds,
    parentChannelId,
  );

  // 2. Determine which cooldown settings to use
  // If a channel-specific override exists, use it; otherwise inherit the global settings
  const effectiveCooldownType = whitelistStatus.hasChannelCooldownOverride
    ? (whitelistStatus.channelCooldownType ?? globalCooldownType)
    : globalCooldownType;

  const effectiveCooldownLength = whitelistStatus.hasChannelCooldownOverride
    ? (whitelistStatus.channelCooldownLength ?? globalCooldownLength)
    : globalCooldownLength;

  // Diagnostic logging for whitelist-based cooldowns
  if (whitelistStatus.isChannelWhitelisted) {
    if (whitelistStatus.hasChannelCooldownOverride) {
      log.info(
        `[Cooldown Set] Channel ${channelId} is whitelisted - setting cooldown type ${effectiveCooldownType}, length ${effectiveCooldownLength}s`,
      );
    } else {
      log.info(
        `[Cooldown Set] Channel ${channelId} is whitelisted - inheriting global cooldown type ${effectiveCooldownType}, length ${effectiveCooldownLength}s`,
      );
    }
  }

  // 3. Set cooldown using shared function
  await setCooldown(
    serverId,
    userId,
    channelId,
    effectiveCooldownType,
    effectiveCooldownLength,
  );
}
