/**
 * Migration: Add voice_message_enabled column to tomori_configs
 *
 * Adds a boolean flag for controlling whether Tomori can send ElevenLabs
 * TTS voice messages. Defaults to true (enabled) for all existing rows.
 *
 * Usage: bun scripts/addVoiceMessagePermission.ts
 */

import { sql } from "@/utils/db/client";
import { log } from "@/utils/misc/logger";

async function addVoiceMessagePermissionColumn(): Promise<void> {
	try {
		log.info("Starting migration: Add voice_message_enabled column...");

		await sql`
      ALTER TABLE tomori_configs
      ADD COLUMN IF NOT EXISTS voice_message_enabled BOOLEAN NOT NULL DEFAULT true;
    `;
		log.info("✓ Added voice_message_enabled column (default: true)");

		log.success("Migration completed: voice_message_enabled column added");
	} catch (error) {
		if (error instanceof Error && error.message.includes("already exists")) {
			log.warn("Column already exists, skipping...");
		} else {
			log.error(
				"Failed to add voice_message_enabled column",
				error as Error,
			);
			throw error;
		}
	}
}

// Run migration
addVoiceMessagePermissionColumn()
	.then(() => {
		log.info("Migration finished successfully");
		process.exit(0);
	})
	.catch((error) => {
		log.error("Migration failed", error as Error);
		process.exit(1);
	});
