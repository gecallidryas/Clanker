/**
 * SillyTavern Preset Database Utilities
 * CRUD operations for st_presets and st_preset_nodes tables.
 * Presets are scoped per server_id; multiple presets per server are allowed.
 */

import { sql } from "@/utils/db/client";
import type { StPresetRow, StPresetNodeRow } from "@/types/db/schema";
import { log } from "@/utils/misc/logger";
import { invalidateStPresetCache } from "@/utils/cache/stPresetCache";

// ─── Preset-Level Operations ─────────────────────────────────────────

/**
 * Insert a new ST preset with its parsed nodes in a single transaction.
 * If a preset with the same name already exists for this server, the
 * insert fails (unique constraint on server_id + preset_name).
 *
 * @param serverId - Internal server_id (FK to servers table)
 * @param presetName - Display name for the preset (from filename or JSON metadata)
 * @param rawJson - The full raw SillyTavern preset JSON object
 * @param nodes - Parsed toggleable nodes to insert (order matters)
 * @returns The inserted preset row, or null on failure
 */
export async function insertPresetWithNodes(
	serverId: number,
	presetName: string,
	rawJson: unknown,
	nodes: Omit<StPresetNodeRow, "node_id" | "preset_id">[],
): Promise<StPresetRow | null> {
	try {
		// 1. Use a transaction to ensure atomicity (preset + all nodes or nothing)
		const result = await sql.begin(async (tx) => {
			// 2. Remove any existing preset with the same name for this server.
			//    The FK cascade on st_preset_nodes deletes old nodes automatically.
			await tx`
				DELETE FROM st_presets
				WHERE server_id = ${serverId} AND preset_name = ${presetName}
			`;

			// 3. Insert the preset metadata + raw JSON
			const [preset] = await tx`
				INSERT INTO st_presets (server_id, preset_name, raw_json)
				VALUES (${serverId}, ${presetName}, ${JSON.stringify(rawJson)})
				RETURNING *
			`;

			// 4. Insert each node with a reference to the new preset_id
			for (const node of nodes) {
				await tx`
					INSERT INTO st_preset_nodes (
						preset_id, identifier, name, role, content,
						is_marker, is_enabled, node_order,
						injection_position, injection_depth, injection_order
					)
					VALUES (
						${preset.preset_id},
						${node.identifier},
						${node.name},
						${node.role},
						${node.content},
						${node.is_marker},
						${node.is_enabled},
						${node.node_order},
						${node.injection_position},
						${node.injection_depth},
						${node.injection_order}
					)
				`;
			}

			return preset;
		});

		log.success(`[StPresetDb] Inserted preset "${presetName}" with ${nodes.length} nodes for server ${serverId}`);
		// Invalidate cache after successful write
		invalidateStPresetCache(serverId);
		return result as StPresetRow;
	} catch (error) {
		log.error(`[StPresetDb] Failed to insert preset "${presetName}" for server ${serverId}`, error);
		return null;
	}
}

// ─── Preset Query Operations ─────────────────────────────────────────

/**
 * Load all ST presets for a server (metadata only, no nodes).
 *
 * @param serverId - Internal server_id
 * @returns Array of preset rows ordered by creation date
 */
export async function loadPresetsForServer(
	serverId: number,
): Promise<StPresetRow[]> {
	try {
		const rows = await sql`
			SELECT preset_id, server_id, preset_name, is_active, created_at, updated_at
			FROM st_presets
			WHERE server_id = ${serverId}
			ORDER BY created_at ASC
		`;
		return rows as StPresetRow[];
	} catch (error) {
		log.error(`[StPresetDb] Failed to load presets for server ${serverId}`, error);
		return [];
	}
}

/**
 * Load a single preset by ID (with raw JSON).
 *
 * @param presetId - The preset_id to load
 * @returns The preset row or null if not found
 */
export async function loadPresetById(
	presetId: number,
): Promise<StPresetRow | null> {
	try {
		const [row] = await sql`
			SELECT * FROM st_presets WHERE preset_id = ${presetId}
		`;
		return (row as StPresetRow) ?? null;
	} catch (error) {
		log.error(`[StPresetDb] Failed to load preset ${presetId}`, error);
		return null;
	}
}

/**
 * Load the currently active preset for a server, if any.
 *
 * @param serverId - Internal server_id
 * @returns The active preset row or null
 */
export async function loadActivePreset(
	serverId: number,
): Promise<StPresetRow | null> {
	try {
		const [row] = await sql`
			SELECT * FROM st_presets
			WHERE server_id = ${serverId} AND is_active = true
			LIMIT 1
		`;
		return (row as StPresetRow) ?? null;
	} catch (error) {
		log.error(`[StPresetDb] Failed to load active preset for server ${serverId}`, error);
		return null;
	}
}

// ─── Node-Level Operations ───────────────────────────────────────────

/**
 * Load all toggleable (non-marker, non-comment-only) nodes for a preset,
 * ordered by node_order. These are the nodes shown in the toggle UI.
 *
 * @param presetId - The preset_id to load nodes for
 * @returns Array of node rows in prompt_order sequence
 */
export async function loadToggleableNodes(
	presetId: number,
): Promise<StPresetNodeRow[]> {
	try {
		const rows = await sql`
			SELECT * FROM st_preset_nodes
			WHERE preset_id = ${presetId}
			  AND is_marker = false
			ORDER BY node_order ASC
		`;
		return rows as StPresetNodeRow[];
	} catch (error) {
		log.error(`[StPresetDb] Failed to load toggleable nodes for preset ${presetId}`, error);
		return [];
	}
}

/**
 * Load ALL nodes for a preset (including markers), ordered by node_order.
 * Used by the context builder when assembling the full prompt.
 *
 * @param presetId - The preset_id to load nodes for
 * @returns Array of all node rows in prompt_order sequence
 */
export async function loadAllNodes(
	presetId: number,
): Promise<StPresetNodeRow[]> {
	try {
		const rows = await sql`
			SELECT * FROM st_preset_nodes
			WHERE preset_id = ${presetId}
			ORDER BY node_order ASC
		`;
		return rows as StPresetNodeRow[];
	} catch (error) {
		log.error(`[StPresetDb] Failed to load all nodes for preset ${presetId}`, error);
		return [];
	}
}

/**
 * Batch-update enabled states for multiple nodes in a single transaction.
 * Accepts a map of identifier → is_enabled for all nodes in the preset.
 *
 * @param presetId - The preset_id owning these nodes
 * @param enabledMap - Map of node identifier → desired enabled state
 * @param serverId - Internal server_id for cache invalidation (required to keep preset cache consistent)
 * @returns True if the update succeeded
 */
export async function updateNodeEnabledStates(
	presetId: number,
	enabledMap: Map<string, boolean>,
	serverId: number,
): Promise<boolean> {
	try {
		await sql.begin(async (tx) => {
			for (const [identifier, isEnabled] of enabledMap) {
				await tx`
					UPDATE st_preset_nodes
					SET is_enabled = ${isEnabled}
					WHERE preset_id = ${presetId} AND identifier = ${identifier}
				`;
			}
		});

		log.info(`[StPresetDb] Updated ${enabledMap.size} node states for preset ${presetId}`);
		// Invalidate cache after successful toggle (node states affect context assembly)
		invalidateStPresetCache(serverId);
		return true;
	} catch (error) {
		log.error(`[StPresetDb] Failed to update node states for preset ${presetId}`, error);
		return false;
	}
}

// ─── Preset Management ───────────────────────────────────────────────

/**
 * Delete a preset and all its nodes (CASCADE handles node cleanup).
 *
 * @param presetId - The preset_id to delete
 * @param serverId - Internal server_id for cache invalidation (required to keep preset cache consistent)
 * @returns True if a row was deleted
 */
export async function deletePreset(
	presetId: number,
	serverId: number,
): Promise<boolean> {
	try {
		const result = await sql`
			DELETE FROM st_presets WHERE preset_id = ${presetId}
		`;
		const deleted = (result as unknown[]).length > 0 || (result as { count?: number }).count === 1;
		if (deleted) {
			log.success(`[StPresetDb] Deleted preset ${presetId}`);
			// Invalidate cache after successful delete
			invalidateStPresetCache(serverId);
		}
		return deleted;
	} catch (error) {
		log.error(`[StPresetDb] Failed to delete preset ${presetId}`, error);
		return false;
	}
}

/**
 * Set a preset as active and deactivate all others for the same server.
 * Uses a transaction to ensure only one preset is active at a time.
 *
 * @param serverId - Internal server_id
 * @param presetId - The preset_id to activate
 * @returns True if the activation succeeded
 */
export async function setActivePreset(
	serverId: number,
	presetId: number,
): Promise<boolean> {
	try {
		await sql.begin(async (tx) => {
			// 1. Deactivate all presets for this server
			await tx`
				UPDATE st_presets SET is_active = false
				WHERE server_id = ${serverId}
			`;
			// 2. Activate the target preset
			await tx`
				UPDATE st_presets SET is_active = true
				WHERE preset_id = ${presetId} AND server_id = ${serverId}
			`;
		});

		log.success(`[StPresetDb] Activated preset ${presetId} for server ${serverId}`);
		// Invalidate cache after successful activation change
		invalidateStPresetCache(serverId);
		return true;
	} catch (error) {
		log.error(`[StPresetDb] Failed to activate preset ${presetId} for server ${serverId}`, error);
		return false;
	}
}
