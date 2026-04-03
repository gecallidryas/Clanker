import { sql } from "@/utils/db/client";
import type { GuildMcpServerRow } from "@/types/db/schema";
import { log } from "@/utils/misc/logger";
import { keyManager } from "@/utils/security/keyManager";

/**
 * Load all guild MCP server registrations for a given server.
 * Returns enabled and disabled rows so callers can filter as needed.
 *
 * @param serverId - Internal server_id (FK to servers table)
 * @returns Array of GuildMcpServerRow (may be empty)
 */
export async function loadGuildMcpServers(
	serverId: number,
): Promise<GuildMcpServerRow[]> {
	try {
		const rows = await sql`
			SELECT guild_mcp_id, server_id, name, url, auth_token, key_version,
			       is_enabled, server_type, created_at, updated_at
			FROM guild_mcp_servers
			WHERE server_id = ${serverId}
			ORDER BY created_at ASC
		`;

		return rows as GuildMcpServerRow[];
	} catch (error) {
		log.error(`[GuildMcpDb] Failed to load MCP servers for server ${serverId}`, error);
		return [];
	}
}

/**
 * Insert a new guild MCP server registration.
 * The auth token is PGP-encrypted before storage using the current encryption key.
 *
 * @param serverId - Internal server_id
 * @param name - Unique server name within the guild (alphanumeric + hyphens)
 * @param url - Remote MCP server URL (HTTPS required in production)
 * @param rawAuthToken - Optional bearer token (plaintext — will be encrypted)
 * @param serverType - Optional server type for deduplicating default tools ('web_search' | 'url_fetcher')
 * @returns The inserted row, or null on failure (e.g., duplicate name)
 */
export async function insertGuildMcpServer(
	serverId: number,
	name: string,
	url: string,
	rawAuthToken?: string,
	serverType?: string | null,
): Promise<GuildMcpServerRow | null> {
	try {
		const currentKey = keyManager.getCurrentKey();
		const currentVersion = keyManager.getCurrentVersion();

		let row: GuildMcpServerRow;

		if (rawAuthToken) {
			// Encrypt the auth token inline using pgp_sym_encrypt (same pattern as opt_api_keys)
			const [result] = await sql`
				INSERT INTO guild_mcp_servers (server_id, name, url, auth_token, key_version, server_type)
				VALUES (
					${serverId},
					${name},
					${url},
					pgp_sym_encrypt(${rawAuthToken.trim()}, ${currentKey}, 'compress-algo=1, cipher-algo=aes256'),
					${currentVersion},
					${serverType ?? null}
				)
				RETURNING *
			`;
			row = result as GuildMcpServerRow;
		} else {
			// No auth token — insert without encryption
			const [result] = await sql`
				INSERT INTO guild_mcp_servers (server_id, name, url, server_type)
				VALUES (${serverId}, ${name}, ${url}, ${serverType ?? null})
				RETURNING *
			`;
			row = result as GuildMcpServerRow;
		}

		log.success(`[GuildMcpDb] Registered MCP server "${name}" for server ${serverId}`);
		return row;
	} catch (error) {
		// Unique constraint violation on (server_id, name) is expected when name already exists
		const errorMessage = error instanceof Error ? error.message : String(error);
		if (errorMessage.includes("unique") || errorMessage.includes("duplicate")) {
			log.warn(`[GuildMcpDb] Duplicate MCP server name "${name}" for server ${serverId}`);
		} else {
			log.error(`[GuildMcpDb] Failed to insert MCP server "${name}" for server ${serverId}`, error);
		}
		return null;
	}
}

/**
 * Delete a guild MCP server registration by name.
 *
 * @param serverId - Internal server_id
 * @param name - Server name to delete
 * @returns True if a row was deleted, false if not found
 */
export async function deleteGuildMcpServer(
	serverId: number,
	name: string,
): Promise<boolean> {
	try {
		const result = await sql`
			DELETE FROM guild_mcp_servers
			WHERE server_id = ${serverId} AND name = ${name}
		`;

		const deleted = result.count > 0;
		if (deleted) {
			log.success(`[GuildMcpDb] Deleted MCP server "${name}" for server ${serverId}`);
		}
		return deleted;
	} catch (error) {
		log.error(`[GuildMcpDb] Failed to delete MCP server "${name}" for server ${serverId}`, error);
		return false;
	}
}

/**
 * Count the number of guild MCP server registrations for a server.
 * Used to enforce MAX_MCP_SERVERS_PER_GUILD limit before inserts.
 *
 * @param serverId - Internal server_id
 * @returns Count of registered MCP servers
 */
export async function countGuildMcpServers(
	serverId: number,
): Promise<number> {
	try {
		const [row] = await sql`
			SELECT COUNT(*) AS count FROM guild_mcp_servers
			WHERE server_id = ${serverId}
		`;

		return Number.parseInt(row?.count as string, 10) || 0;
	} catch (error) {
		log.error(`[GuildMcpDb] Failed to count MCP servers for server ${serverId}`, error);
		return 0;
	}
}

/**
 * Toggle the is_enabled flag for a guild MCP server.
 *
 * @param serverId - Internal server_id
 * @param name - Server name to toggle
 * @param enabled - New enabled state
 * @returns True if a row was updated, false if not found
 */
export async function updateGuildMcpServerEnabled(
	serverId: number,
	name: string,
	enabled: boolean,
): Promise<boolean> {
	try {
		const result = await sql`
			UPDATE guild_mcp_servers
			SET is_enabled = ${enabled}
			WHERE server_id = ${serverId} AND name = ${name}
		`;

		const updated = result.count > 0;
		if (updated) {
			log.success(`[GuildMcpDb] ${enabled ? "Enabled" : "Disabled"} MCP server "${name}" for server ${serverId}`);
		}
		return updated;
	} catch (error) {
		log.error(`[GuildMcpDb] Failed to update MCP server enabled state for "${name}" on server ${serverId}`, error);
		return false;
	}
}

/**
 * Decrypt and return the auth token for a guild MCP server.
 * Performs lazy key rotation if the token was encrypted with an older key version.
 *
 * @param row - GuildMcpServerRow with encrypted auth_token
 * @returns Decrypted auth token string, or null if no token is stored
 */
export async function decryptGuildMcpAuthToken(
	row: GuildMcpServerRow,
): Promise<string | null> {
	if (!row.auth_token) {
		return null;
	}

	try {
		const keyVersion = row.key_version || 1;
		const key = keyManager.getKey(keyVersion);

		const [result] = await sql`
			SELECT pgp_sym_decrypt(${row.auth_token}, ${key}) AS decrypted_token
		`;

		if (!result?.decrypted_token) {
			log.warn(`[GuildMcpDb] Decryption returned empty for MCP server "${row.name}"`);
			return null;
		}

		const decryptedToken = result.decrypted_token.toString();

		// Lazy rotation: re-encrypt with current key version if outdated
		const currentVersion = keyManager.getCurrentVersion();
		if (keyVersion !== currentVersion) {
			log.info(`[GuildMcpDb] Rotating auth token for "${row.name}" from key v${keyVersion} to v${currentVersion}`);
			const currentKey = keyManager.getCurrentKey();

			await sql`
				UPDATE guild_mcp_servers
				SET auth_token = pgp_sym_encrypt(${decryptedToken}, ${currentKey}, 'compress-algo=1, cipher-algo=aes256'),
				    key_version = ${currentVersion}
				WHERE guild_mcp_id = ${row.guild_mcp_id}
			`;

			log.success(`[GuildMcpDb] Key rotation completed for MCP server "${row.name}"`);
		}

		return decryptedToken;
	} catch (error) {
		log.error(`[GuildMcpDb] Failed to decrypt auth token for MCP server "${row.name}"`, error);
		return null;
	}
}

/**
 * Load all enabled guild MCP servers across ALL guilds.
 * Used during dev/local startup for eager connection initialization.
 *
 * @returns Array of GuildMcpServerRow (enabled only)
 */
export async function loadAllEnabledGuildMcpServers(): Promise<GuildMcpServerRow[]> {
	try {
		const rows = await sql`
			SELECT guild_mcp_id, server_id, name, url, auth_token, key_version,
			       is_enabled, server_type, created_at, updated_at
			FROM guild_mcp_servers
			WHERE is_enabled = true
			ORDER BY server_id ASC, created_at ASC
		`;

		return rows as GuildMcpServerRow[];
	} catch (error) {
		log.error("[GuildMcpDb] Failed to load all enabled guild MCP servers", error);
		return [];
	}
}
