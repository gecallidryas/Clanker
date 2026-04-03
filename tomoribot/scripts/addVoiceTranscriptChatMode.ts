/**
 * Migration: Add voice_transcript_chat_mode column to tomori_configs
 *
 * Adds a boolean flag for controlling whether voice transcripts are posted
 * as visible chat messages (via user-impersonation webhook) rather than
 * stored in the internal in-memory cache. Defaults to false (disabled).
 *
 * Usage: bun scripts/addVoiceTranscriptChatMode.ts
 */

import { sql } from "@/utils/db/client";
import { log } from "@/utils/misc/logger";

async function addVoiceTranscriptChatModeColumn(): Promise<void> {
	try {
		log.info("Starting migration: Add voice_transcript_chat_mode column...");

		await sql`
      ALTER TABLE tomori_configs
      ADD COLUMN IF NOT EXISTS voice_transcript_chat_mode BOOLEAN NOT NULL DEFAULT false;
    `;
		log.info("✓ Added voice_transcript_chat_mode column (default: false)");

		log.success("Migration completed: voice_transcript_chat_mode column added");
	} catch (error) {
		if (error instanceof Error && error.message.includes("already exists")) {
			log.warn("Column already exists, skipping...");
		} else {
			log.error(
				"Failed to add voice_transcript_chat_mode column",
				error as Error,
			);
			throw error;
		}
	}
}

// Run migration
addVoiceTranscriptChatModeColumn()
	.then(() => {
		log.info("Migration finished successfully");
		process.exit(0);
	})
	.catch((error) => {
		log.error("Migration failed", error as Error);
		process.exit(1);
	});
