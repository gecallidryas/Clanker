import { sql } from "@/utils/db/client";
import { log } from "@/utils/misc/logger";
import type { SQL } from "bun";
import type {
  ImageQuotaConfigRow,
  ImageQuotaRow,
  ServerwideQuotaRow,
} from "@/types/db/schema";
import {
  imageQuotaConfigSchema,
  imageQuotaSchema,
  serverwideQuotaSchema,
} from "@/types/db/schema";

/**
 * Result of quota check operations
 */
export interface QuotaCheckResult {
  allowed: boolean; // Whether user can generate image
  reason?: "user_quota_exceeded" | "serverwide_quota_exceeded" | "disabled"; // Reason if denied
  userRemaining?: number; // User's remaining quota for the day
  serverwideRemaining?: number; // Server's remaining quota for the period
  resetTime?: Date; // When the quota resets (for error messages)
}

/**
 * Get or create server's quota configuration
 * Creates default config if not exists (10 daily user quota, unlimited serverwide)
 */
export async function getQuotaConfig(
  serverId: number,
): Promise<ImageQuotaConfigRow> {
  try {
    // 1. Try to fetch existing config
    const [existing] = await sql<
      ImageQuotaConfigRow[]
    >`SELECT * FROM image_quota_configs WHERE server_id = ${serverId}`;

    if (existing) {
      return imageQuotaConfigSchema.parse(existing);
    }

    // 2. Create default config if not exists
    const [newConfig] = await sql<ImageQuotaConfigRow[]>`
			INSERT INTO image_quota_configs (server_id, daily_user_quota, serverwide_quota, serverwide_quota_resets_in, enabled)
			VALUES (${serverId}, 10, 0, 365, true)
			RETURNING *
		`;

    log.info("Created default image quota config");

    return imageQuotaConfigSchema.parse(newConfig);
  } catch (error) {
    log.error("Failed to get quota config", error);
    // Return safe defaults on error
    return {
      server_id: serverId,
      daily_user_quota: 10,
      serverwide_quota: 0,
      serverwide_quota_resets_in: 365,
      enabled: true,
    };
  }
}

/**
 * Check if user can generate an image based on daily quota
 * Returns remaining quota and whether generation is allowed
 */
export async function checkUserDailyQuota(
  serverId: number,
  userDiscId: string,
  config: ImageQuotaConfigRow,
): Promise<QuotaCheckResult> {
  // 1. If daily user quota is 0 (unlimited), allow
  if (config.daily_user_quota === 0) {
    return { allowed: true };
  }

  try {
    // 2. Get current date in YYYY-MM-DD format (server's local date)
    const today = new Date().toISOString().split("T")[0];

    // 3. Get or create user's quota record for today
    const [userQuota] = await sql<ImageQuotaRow[]>`
			INSERT INTO image_quotas (server_id, user_disc_id, usage_count, quota_date)
			VALUES (${serverId}, ${userDiscId}, 0, ${today}::date)
			ON CONFLICT (server_id, user_disc_id, quota_date)
			DO UPDATE SET server_id = EXCLUDED.server_id
			RETURNING *
		`;

    const parsedQuota = imageQuotaSchema.parse(userQuota);

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
    log.error("Failed to check user daily quota", error);
    // On error, allow (fail-open to prevent blocking legitimate usage)
    return { allowed: true };
  }
}

/**
 * Check if server has remaining server-wide quota
 * Returns remaining quota and whether generation is allowed
 */
export async function checkServerwideQuota(
  serverId: number,
  config: ImageQuotaConfigRow,
): Promise<QuotaCheckResult> {
  // 1. If serverwide quota is 0 (unlimited), allow
  if (config.serverwide_quota === 0) {
    return { allowed: true };
  }

  try {
    // 2. Get or create server-wide quota record
    const [serverwideQuota] = await sql<ServerwideQuotaRow[]>`
			INSERT INTO serverwide_quotas (
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

    const parsedQuota = serverwideQuotaSchema.parse(serverwideQuota);

    // 3. Check if quota period has expired (needs reset)
    const now = new Date();
    const periodEnd = new Date(parsedQuota.quota_period_end);

    if (now >= periodEnd) {
      // Reset the server-wide quota
      const [resetQuota] = await sql<ServerwideQuotaRow[]>`
				UPDATE serverwide_quotas
				SET
					usage_count = 0,
					quota_period_start = CURRENT_TIMESTAMP,
					quota_period_end = CURRENT_TIMESTAMP + (${config.serverwide_quota_resets_in} || ' days')::interval
				WHERE server_id = ${serverId}
				RETURNING *
			`;

      const parsedResetQuota = serverwideQuotaSchema.parse(resetQuota);

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
    log.error("Failed to check serverwide quota", error);
    // On error, allow (fail-open to prevent blocking legitimate usage)
    return { allowed: true };
  }
}

/**
 * Check all quotas (user daily + server-wide)
 * Returns combined result indicating if generation is allowed
 */
export async function checkImageQuota(
  serverId: number,
  userDiscId: string,
): Promise<QuotaCheckResult> {
  try {
    // 1. Get quota configuration
    const config = await getQuotaConfig(serverId);

    // 2. If quota system is disabled, allow all
    if (!config.enabled) {
      return { allowed: true };
    }

    // 3. Check user daily quota first (most common limit)
    const userCheck = await checkUserDailyQuota(serverId, userDiscId, config);
    if (!userCheck.allowed) {
      return userCheck;
    }

    // 4. Check server-wide quota
    const serverwideCheck = await checkServerwideQuota(serverId, config);
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
    log.error("Failed to check image quota", error);
    // On error, allow (fail-open to prevent blocking legitimate usage)
    return { allowed: true };
  }
}

/**
 * Increment both user daily and server-wide quotas after successful image generation
 * Should only be called AFTER image generation succeeds
 */
export async function incrementImageQuota(
  serverId: number,
  userDiscId: string,
): Promise<void> {
  try {
    const today = new Date().toISOString().split("T")[0];

    // 1. Increment user's daily quota (using transaction for consistency)
    await sql.begin(async (tx: SQL) => {
      // Increment user quota
      await tx`
				INSERT INTO image_quotas (server_id, user_disc_id, usage_count, quota_date)
				VALUES (${serverId}, ${userDiscId}, 1, ${today}::date)
				ON CONFLICT (server_id, user_disc_id, quota_date)
				DO UPDATE SET usage_count = image_quotas.usage_count + 1
			`;

      // Increment server-wide quota
      await tx`
				UPDATE serverwide_quotas
				SET usage_count = usage_count + 1
				WHERE server_id = ${serverId}
			`;
    });

    log.info("Incremented image quotas");
  } catch (error) {
    log.error("Failed to increment image quota", error);
    // Don't throw - quota increment failure shouldn't block user
  }
}

/**
 * Clean up old user quota records (older than 7 days)
 * Should be called periodically (e.g., on startup or via cron)
 */
export async function cleanupOldImageQuotas(): Promise<number> {
  try {
    const result = await sql<{ cleanup_old_image_quotas: number }[]>`
			SELECT cleanup_old_image_quotas() AS cleanup_old_image_quotas
		`;

    const deletedCount = result[0]?.cleanup_old_image_quotas || 0;

    if (deletedCount > 0) {
      log.info("Cleaned up old image quota records");
    }

    return deletedCount;
  } catch (error) {
    log.error("Failed to cleanup old image quotas", error);
    return 0;
  }
}

/**
 * Manually reset server-wide quota (admin override)
 * Creates new quota period starting now
 */
export async function resetServerwideQuota(serverId: number): Promise<void> {
  try {
    const config = await getQuotaConfig(serverId);

    await sql`
			UPDATE serverwide_quotas
			SET
				usage_count = 0,
				quota_period_start = CURRENT_TIMESTAMP,
				quota_period_end = CURRENT_TIMESTAMP + (${config.serverwide_quota_resets_in} || ' days')::interval
			WHERE server_id = ${serverId}
		`;

    log.info("Manually reset serverwide quota");
  } catch (error) {
    log.error("Failed to reset serverwide quota", error);
    throw error;
  }
}
