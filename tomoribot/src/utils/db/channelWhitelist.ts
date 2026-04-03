import { sql } from "@/utils/db/client";
import type { ChannelWhitelistRow, CooldownType } from "@/types/db/schema";
import type { WhitelistCheckResult } from "@/types/misc/channelWhitelist";
import { log } from "@/utils/misc/logger";

/**
 * Check whitelist status (channel + role) and get channel cooldown settings.
 * @param serverDiscId - Discord server ID (snowflake) or user ID for DMs
 * @param channelDiscId - Discord channel ID (snowflake)
 * @param memberRoleDiscIds - Optional role IDs for the triggering member
 * @param parentChannelDiscId - Optional parent channel ID for threads; threads inherit whitelist from parent if not explicitly whitelisted
 * @returns WhitelistCheckResult with whitelist status and settings
 */
export async function checkChannelWhitelist(
  serverDiscId: string,
  channelDiscId: string,
  memberRoleDiscIds?: string[],
  parentChannelDiscId?: string,
): Promise<WhitelistCheckResult> {
  const fallbackResult: WhitelistCheckResult = {
    hasActiveWhitelist: false,
    hasActiveChannelWhitelist: false,
    isChannelWhitelisted: false,
    hasActiveRoleWhitelist: false,
    isRoleWhitelisted: false,
    isTriggerAllowed: true,
    hasChannelCooldownOverride: false,
  };

  try {
    // 1. Get server database ID
    const [serverRow] = await sql`
			SELECT server_id FROM servers WHERE server_disc_id = ${serverDiscId}
		`;

    if (!serverRow) {
      // Server not in database - no whitelist
      return fallbackResult;
    }

    const serverId = serverRow.server_id as number;

    // 2. Check if server has channel whitelist entries
    const [countRow] = await sql`
			SELECT COUNT(*) as count FROM channel_whitelist WHERE server_id = ${serverId}
		`;

    const channelWhitelistCount = Number.parseInt(countRow?.count as string, 10);
    const hasActiveChannelWhitelist = channelWhitelistCount > 0;

    // 3. Check if specific channel is whitelisted
    // For threads: first check the thread itself, then fall back to parent channel
    const [channelRow] = hasActiveChannelWhitelist
      ? await sql<Array<{ cooldown_type: CooldownType | null; cooldown_length: number | null }>>`
			SELECT cooldown_type, cooldown_length
			FROM channel_whitelist
			WHERE server_id = ${serverId} AND channel_disc_id = ${channelDiscId}
		`
      : [null];

    // 3a. If channel not whitelisted and this is a thread (parent provided), check parent channel
    let [parentChannelRow] = [null as { cooldown_type: CooldownType | null; cooldown_length: number | null } | null];
    if (!channelRow && parentChannelDiscId && hasActiveChannelWhitelist) {
      [parentChannelRow] = await sql<Array<{ cooldown_type: CooldownType | null; cooldown_length: number | null }>>`
				SELECT cooldown_type, cooldown_length
				FROM channel_whitelist
				WHERE server_id = ${serverId} AND channel_disc_id = ${parentChannelDiscId}
			`;
    }

    const isChannelWhitelisted = Boolean(channelRow || parentChannelRow);
    const effectiveChannelRow = channelRow || parentChannelRow;

    const hasChannelCooldownOverride =
      isChannelWhitelisted &&
      effectiveChannelRow?.cooldown_type !== null &&
      effectiveChannelRow?.cooldown_length !== null;

    if (
      isChannelWhitelisted &&
      !hasChannelCooldownOverride &&
      !(effectiveChannelRow?.cooldown_type === null && effectiveChannelRow?.cooldown_length === null)
    ) {
      log.warn("Channel whitelist row has partial cooldown override; falling back to global cooldown", {
        metadata: {
          serverDiscId,
          channelDiscId,
          parentChannelDiscId,
          cooldownType: effectiveChannelRow?.cooldown_type ?? null,
          cooldownLength: effectiveChannelRow?.cooldown_length ?? null,
        },
      });
    }

    // 4. Load role whitelist entries for this server
    const roleRows = await sql<Array<{ role_disc_id: string }>>`
			SELECT role_disc_id
			FROM role_whitelist
			WHERE server_id = ${serverId}
		`;
    const hasActiveRoleWhitelist = roleRows.length > 0;

    // 5. Role whitelist check (fail-open if role data is unavailable)
    let isRoleWhitelisted = false;
    if (hasActiveRoleWhitelist) {
      if (memberRoleDiscIds === undefined) {
        isRoleWhitelisted = true;
      } else if (memberRoleDiscIds.length > 0) {
        const memberRoles = new Set(memberRoleDiscIds);
        isRoleWhitelisted = roleRows.some((row) =>
          memberRoles.has(row.role_disc_id),
        );
      } else {
        isRoleWhitelisted = false;
      }
    }

    const isChannelAllowed =
      !hasActiveChannelWhitelist || isChannelWhitelisted;
    const isRoleAllowed = !hasActiveRoleWhitelist || isRoleWhitelisted;
    const isTriggerAllowed = isChannelAllowed && isRoleAllowed;
    const hasActiveWhitelist =
      hasActiveChannelWhitelist || hasActiveRoleWhitelist;

    let blockReason: WhitelistCheckResult["blockReason"];
    if (!isTriggerAllowed) {
      const blockedByChannel =
        hasActiveChannelWhitelist && !isChannelWhitelisted;
      const blockedByRole = hasActiveRoleWhitelist && !isRoleWhitelisted;
      if (blockedByChannel && blockedByRole) {
        blockReason = "channel_and_role";
      } else if (blockedByRole) {
        blockReason = "role";
      } else {
        blockReason = "channel";
      }
    }

    return {
      hasActiveWhitelist,
      hasActiveChannelWhitelist,
      isChannelWhitelisted,
      hasActiveRoleWhitelist,
      isRoleWhitelisted,
      isTriggerAllowed,
      blockReason,
      hasChannelCooldownOverride,
      channelCooldownType: hasChannelCooldownOverride
        ? (effectiveChannelRow?.cooldown_type as CooldownType)
        : undefined,
      channelCooldownLength: hasChannelCooldownOverride
        ? (effectiveChannelRow?.cooldown_length as number)
        : undefined,
    };
  } catch (error) {
    log.warn("Failed to check channel whitelist, failing open", {
      errorType: "ChannelWhitelistCheckError",
      metadata: { serverDiscId, channelDiscId, memberRoleDiscIds, error },
    });

    // Fail open - no whitelist enforcement on error
    return fallbackResult;
  }
}

/**
 * Add or update a channel in the whitelist with optional cooldown override settings
 * @param serverId - Database server ID
 * @param channelDiscId - Discord channel ID (snowflake)
 * @param cooldownType - Cooldown type override for this channel, or null to inherit global cooldown
 * @param cooldownLength - Cooldown length override in seconds (0-86400), or null to inherit global cooldown
 * @returns The upserted channel whitelist row
 */
export async function upsertChannelWhitelist(
  serverId: number,
  channelDiscId: string,
  cooldownType: CooldownType | null,
  cooldownLength: number | null,
): Promise<ChannelWhitelistRow> {
  const [result] = await sql`
		INSERT INTO channel_whitelist (server_id, channel_disc_id, cooldown_type, cooldown_length)
		VALUES (${serverId}, ${channelDiscId}, ${cooldownType}, ${cooldownLength})
		ON CONFLICT (server_id, channel_disc_id)
		DO UPDATE SET
			cooldown_type = EXCLUDED.cooldown_type,
			cooldown_length = EXCLUDED.cooldown_length,
			updated_at = CURRENT_TIMESTAMP
		RETURNING *
	`;

  if (!result) {
    throw new Error("Failed to upsert channel whitelist");
  }

  return result as ChannelWhitelistRow;
}

/**
 * Remove a channel from the whitelist
 * @param serverId - Database server ID
 * @param channelDiscId - Discord channel ID (snowflake)
 * @returns True if a row was deleted, false if not found
 */
export async function removeChannelWhitelist(
  serverId: number,
  channelDiscId: string,
): Promise<boolean> {
  const result = await sql`
		DELETE FROM channel_whitelist
		WHERE server_id = ${serverId} AND channel_disc_id = ${channelDiscId}
	`;

  return result.count > 0;
}

/**
 * Get all whitelisted channels for a server
 * @param serverId - Database server ID
 * @returns Array of channel whitelist rows
 */
export async function getAllWhitelistChannels(
  serverId: number,
): Promise<ChannelWhitelistRow[]> {
  const result = await sql`
		SELECT * FROM channel_whitelist
		WHERE server_id = ${serverId}
		ORDER BY created_at ASC
	`;

  return result as ChannelWhitelistRow[];
}
