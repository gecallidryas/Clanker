import type { CooldownType } from "@/types/db/schema";

export type WhitelistBlockReason = "channel" | "role" | "channel_and_role";

/**
 * Result of checking channel whitelist status
 * Used to determine if a channel should be allowed to trigger the bot
 * and what cooldown settings to apply
 */
export interface WhitelistCheckResult {
  /**
   * Whether this server has ANY active whitelist entries (channel or role)
   */
  hasActiveWhitelist: boolean;

  /**
   * Whether this server has any active channel whitelist entries.
   */
  hasActiveChannelWhitelist: boolean;

  /**
   * Whether the specific channel is in the whitelist
   * Only relevant if hasActiveChannelWhitelist is true
   */
  isChannelWhitelisted: boolean;

  /**
   * Whether this server has any active role whitelist entries.
   */
  hasActiveRoleWhitelist: boolean;

  /**
   * Whether the triggering member matches at least one whitelisted role.
   * Only relevant if hasActiveRoleWhitelist is true.
   */
  isRoleWhitelisted: boolean;

  /**
   * Final allow/deny decision after combining channel and role whitelist checks.
   */
  isTriggerAllowed: boolean;

  /**
   * If blocked, indicates which whitelist condition failed.
   */
  blockReason?: WhitelistBlockReason;

  /**
   * Whether this whitelisted channel has an explicit cooldown override.
   * False means the channel inherits the server-wide cooldown settings.
   */
  hasChannelCooldownOverride: boolean;

  /**
   * Channel-specific cooldown type.
   * Only set when hasChannelCooldownOverride is true.
   */
  channelCooldownType?: CooldownType;

  /**
   * Channel-specific cooldown length in seconds.
   * Only set when hasChannelCooldownOverride is true.
   * 0 = instant (no cooldown), 1-86400 = cooldown duration.
   */
  channelCooldownLength?: number;
}
