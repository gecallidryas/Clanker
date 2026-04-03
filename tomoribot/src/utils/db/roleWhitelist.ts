import { sql } from "@/utils/db/client";
import type { RoleWhitelistRow } from "@/types/db/schema";

/**
 * Add a role to the whitelist for a server.
 * @param serverId - Database server ID
 * @param roleDiscId - Discord role ID (snowflake)
 * @returns The upserted role whitelist row
 */
export async function upsertRoleWhitelist(
  serverId: number,
  roleDiscId: string,
): Promise<RoleWhitelistRow> {
  const [result] = await sql`
		INSERT INTO role_whitelist (server_id, role_disc_id)
		VALUES (${serverId}, ${roleDiscId})
		ON CONFLICT (server_id, role_disc_id)
		DO UPDATE SET updated_at = CURRENT_TIMESTAMP
		RETURNING *
	`;

  if (!result) {
    throw new Error("Failed to upsert role whitelist");
  }

  return result as RoleWhitelistRow;
}

/**
 * Remove a role from the whitelist.
 * @param serverId - Database server ID
 * @param roleDiscId - Discord role ID (snowflake)
 * @returns True if a row was deleted, false if not found
 */
export async function removeRoleWhitelist(
  serverId: number,
  roleDiscId: string,
): Promise<boolean> {
  const result = await sql`
		DELETE FROM role_whitelist
		WHERE server_id = ${serverId} AND role_disc_id = ${roleDiscId}
	`;

  return result.count > 0;
}

/**
 * Get all whitelisted roles for a server.
 * @param serverId - Database server ID
 * @returns Array of role whitelist rows
 */
export async function getAllWhitelistRoles(
  serverId: number,
): Promise<RoleWhitelistRow[]> {
  const result = await sql`
		SELECT * FROM role_whitelist
		WHERE server_id = ${serverId}
		ORDER BY created_at ASC
	`;

  return result as RoleWhitelistRow[];
}

/**
 * Check whether a role is currently whitelisted.
 * @param serverId - Database server ID
 * @param roleDiscId - Discord role ID (snowflake)
 * @returns True if the role is whitelisted
 */
export async function isRoleWhitelisted(
  serverId: number,
  roleDiscId: string,
): Promise<boolean> {
  const [row] = await sql`
		SELECT 1
		FROM role_whitelist
		WHERE server_id = ${serverId} AND role_disc_id = ${roleDiscId}
		LIMIT 1
	`;

  return Boolean(row);
}
