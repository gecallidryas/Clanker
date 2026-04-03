import { sql } from "@/utils/db/client";
import { log } from "@/utils/misc/logger";
import type { SQL } from "bun";
import type {
  TextQuotaConfigRow,
  TextQuotaRow,
  TextServerwideQuotaRow,
} from "@/types/db/schema";
import {
  textQuotaConfigSchema,
  textQuotaSchema,
  textServerwideQuotaSchema,
} from "@/types/db/schema";

/**
 * Result of text quota check operations
 */
export interface TextQuotaCheckResult {
  allowed: boolean; // Whether user can trigger text generation
  reason?: "user_quota_exceeded" | "serverwide_quota_exceeded" | "disabled"; // Reason if denied
  userRemaining?: number; // User's remaining quota for the day
  serverwideRemaining?: number; // Server's remaining quota for the period
  resetTime?: Date; // When the quota resets (for error messages)
}

/**
 * Get or create server's text quota configuration
 * Creates default config if not exists (unlimited by default)
 */
export async function getTextQuotaConfig(
  serverId: number,
): Promise<TextQuotaConfigRow> {
  try {
    // 1. Try to fetch existing config
    const [existing] = await sql<
      TextQuotaConfigRow[]
    >`SELECT * FROM text_quota_configs WHERE server_id = ${serverId}`;

    if (existing) {
      return textQuotaConfigSchema.parse(existing);
    }

    // 2. Create default config if not exists
    const [newConfig] = await sql<TextQuotaConfigRow[]>`
			INSERT INTO text_quota_configs (server_id, daily_user_quota, serverwide_quota, serverwide_quota_resets_in, enabled)
			VALUES (${serverId}, 0, 0, 365, true)
			RETURNING *
		`;

    log.info("Created default text quota config");

    return textQuotaConfigSchema.parse(newConfig);
  } catch (error) {
    log.error("Failed to get text quota config", error);
    // Return safe defaults on error
    return {
      server_id: serverId,
      daily_user_quota: 0,
      serverwide_quota: 0,
      serverwide_quota_resets_in: 365,
      enabled: true,
    };
  }
}

/**
 * Check if user can trigger text generation based on daily quota
 * Returns remaining quota and whether trigger is allowed
 */
export async function checkUserDailyTextQuota(
  serverId: number,
  userDiscId: string,
  config: TextQuotaConfigRow,
): Promise<TextQuotaCheckResult> {
  // 1. If daily user quota is 0 (unlimited), allow
  if (config.daily_user_quota === 0) {
    return { allowed: true };
  }

  try {
    // 2. Get current date in YYYY-MM-DD format (server's local date)
    const today = new Date().toISOString().split("T")[0];

    // 3. Get or create user's quota record for today
    const [userQuota] = await sql<TextQuotaRow[]>`
			INSERT INTO text_quotas (server_id, user_disc_id, usage_count, quota_date)
			VALUES (${serverId}, ${userDiscId}, 0, ${today}::date)
			ON CONFLICT (server_id, user_disc_id, quota_date)
			DO UPDATE SET server_id = EXCLUDED.server_id
			RETURNING *
		`;

    const parsedQuota = textQuotaSchema.parse(userQuota);

    // 4. Check if user has exceeded their daily quota
    const remaining = config.daily_user_quota - parsedQuota.usage_count;

    if (remaining <= 0) {
      // Calculate midnight tonight for reset time
      const resetTime = new Date();
      resetTime.setHours(24, 0, 0, 0); // Next midnight

      return {
        allowed: false,
        reason: "user_quota_exceeded",
        userRemaining: 0,
        resetTime,
      };
    }

    // 5. User has remaining quota
    return {
      allowed: true,
      userRemaining: remaining,
    };
  } catch (error) {
    log.error("Failed to check user daily text quota", error);
    // On error, allow (fail-open to prevent blocking legitimate usage)
    return { allowed: true };
  }
}

/**
 * Check if server has remaining server-wide text quota
 * Returns remaining quota and whether trigger is allowed
 */
export async function checkServerwideTextQuota(
  serverId: number,
  config: TextQuotaConfigRow,
): Promise<TextQuotaCheckResult> {
  // 1. If serverwide quota is 0 (unlimited), allow
  if (config.serverwide_quota === 0) {
    return { allowed: true };
  }

  try {
    // 2. Get or create server-wide quota record
    const [serverwideQuota] = await sql<TextServerwideQuotaRow[]>`
			INSERT INTO text_serverwide_quotas (
				server_id,
				usage_count,
				quota_period_start,
				quota_period_end
			)
			VALUES (
				${serverId},
				0,
				CURRENT_TIMESTAMP,
				CURRENT_TIMESTAMP + (${config.serverwide_quota_resets_in} || ' days')::interval
			)
			ON CONFLICT (server_id)
			DO UPDATE SET server_id = EXCLUDED.server_id
			RETURNING *
		`;

    const parsedQuota = textServerwideQuotaSchema.parse(serverwideQuota);

    // 3. Check if quota period has expired (needs reset)
    const now = new Date();
    const periodEnd = new Date(parsedQuota.quota_period_end);

    if (now >= periodEnd) {
      // Reset the server-wide quota
      const [resetQuota] = await sql<TextServerwideQuotaRow[]>`
				UPDATE text_serverwide_quotas
				SET
					usage_count = 0,
					quota_period_start = CURRENT_TIMESTAMP,
					quota_period_end = CURRENT_TIMESTAMP + (${config.serverwide_quota_resets_in} || ' days')::interval
				WHERE server_id = ${serverId}
				RETURNING *
			`;

      const parsedResetQuota = textServerwideQuotaSchema.parse(resetQuota);

      return {
        allowed: true,
        serverwideRemaining: config.serverwide_quota,
        resetTime: new Date(parsedResetQuota.quota_period_end),
      };
    }

    // 4. Check if server has exceeded its quota
    const remaining = config.serverwide_quota - parsedQuota.usage_count;

    if (remaining <= 0) {
      return {
        allowed: false,
        reason: "serverwide_quota_exceeded",
        serverwideRemaining: 0,
        resetTime: periodEnd,
      };
    }

    // 5. Server has remaining quota
    return {
      allowed: true,
      serverwideRemaining: remaining,
      resetTime: periodEnd,
    };
  } catch (error) {
    log.error("Failed to check serverwide text quota", error);
    // On error, allow (fail-open to prevent blocking legitimate usage)
    return { allowed: true };
  }
}

/**
 * Check all text quotas (user daily + server-wide)
 * Returns combined result indicating if trigger is allowed
 */
export async function checkTextQuota(
  serverId: number,
  userDiscId: string,
): Promise<TextQuotaCheckResult> {
  try {
    // 1. Get quota configuration
    const config = await getTextQuotaConfig(serverId);

    // 2. If quota system is disabled, allow all
    if (!config.enabled) {
      return { allowed: true };
    }

    // 3. Check user daily quota first (most common limit)
    const userCheck = await checkUserDailyTextQuota(serverId, userDiscId, config);
    if (!userCheck.allowed) {
      return userCheck;
    }

    // 4. Check server-wide quota
    const serverwideCheck = await checkServerwideTextQuota(serverId, config);
    if (!serverwideCheck.allowed) {
      return serverwideCheck;
    }

    // 5. Both checks passed, combine remaining counts
    return {
      allowed: true,
      userRemaining: userCheck.userRemaining,
      serverwideRemaining: serverwideCheck.serverwideRemaining,
      resetTime: serverwideCheck.resetTime,
    };
  } catch (error) {
    log.error("Failed to check text quota", error);
    // On error, allow (fail-open to prevent blocking legitimate usage)
    return { allowed: true };
  }
}

/**
 * Increment both user daily and server-wide text quotas after successful generation
 * Should only be called AFTER a text response succeeds
 */
export async function incrementTextQuota(
  serverId: number,
  userDiscId: string,
): Promise<void> {
  try {
    const today = new Date().toISOString().split("T")[0];

    // 1. Increment user's daily quota (using transaction for consistency)
    await sql.begin(async (tx: SQL) => {
      // Increment user quota
      await tx`
				INSERT INTO text_quotas (server_id, user_disc_id, usage_count, quota_date)
				VALUES (${serverId}, ${userDiscId}, 1, ${today}::date)
				ON CONFLICT (server_id, user_disc_id, quota_date)
				DO UPDATE SET usage_count = text_quotas.usage_count + 1
			`;

      // Increment server-wide quota
      await tx`
				UPDATE text_serverwide_quotas
				SET usage_count = usage_count + 1
				WHERE server_id = ${serverId}
			`;
    });

    log.info("Incremented text quotas");
  } catch (error) {
    log.error("Failed to increment text quota", error);
    // Don't throw - quota increment failure shouldn't block user
  }
}

/**
 * Clean up old user text quota records (older than 7 days)
 * Should be called periodically (e.g., on startup or via cron)
 */
export async function cleanupOldTextQuotas(): Promise<number> {
  try {
    const result = await sql<{ cleanup_old_text_quotas: number }[]>`
			SELECT cleanup_old_text_quotas() AS cleanup_old_text_quotas
		`;

    const deletedCount = result[0]?.cleanup_old_text_quotas || 0;

    if (deletedCount > 0) {
      log.info("Cleaned up old text quota records");
    }

    return deletedCount;
  } catch (error) {
    log.error("Failed to cleanup old text quotas", error);
    return 0;
  }
}

/**
 * Manually reset server-wide text quota (admin override)
 * Creates new quota period starting now
 */
export async function resetTextServerwideQuota(serverId: number): Promise<void> {
  try {
    const config = await getTextQuotaConfig(serverId);

    await sql`
			UPDATE text_serverwide_quotas
			SET
				usage_count = 0,
				quota_period_start = CURRENT_TIMESTAMP,
				quota_period_end = CURRENT_TIMESTAMP + (${config.serverwide_quota_resets_in} || ' days')::interval
			WHERE server_id = ${serverId}
		`;

    log.info("Manually reset text serverwide quota");
  } catch (error) {
    log.error("Failed to reset text serverwide quota", error);
    throw error;
  }
}
