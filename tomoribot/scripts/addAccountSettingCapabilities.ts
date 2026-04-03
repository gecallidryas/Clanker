/**
 * Migration: Add account-setting capability caching columns to tomori_configs
 *
 * Adds three columns for storing the detected OpenRouter model and its capabilities
 * when users select account-setting as their model:
 * - account_setting_actual_model (text) - The real model name detected
 * - account_setting_capabilities (jsonb) - Cached capabilities (hasTools, seesImages, etc.)
 * - account_setting_capabilities_fetched_at (timestamp) - When capabilities were last fetched
 *
 * Usage: bun scripts/addAccountSettingCapabilities.ts
 */

import { sql } from "@/utils/db/client";
import { log } from "@/utils/misc/logger";

async function addAccountSettingCapabilityColumns(): Promise<void> {
  try {
    log.info("Starting migration: Add account-setting capability caching...");

    // Add account_setting_actual_model column
    await sql`
      ALTER TABLE tomori_configs
      ADD COLUMN IF NOT EXISTS account_setting_actual_model TEXT;
    `;
    log.info("✓ Added account_setting_actual_model column");

    // Add account_setting_capabilities column (JSONB with default structure)
    await sql`
      ALTER TABLE tomori_configs
      ADD COLUMN IF NOT EXISTS account_setting_capabilities JSONB;
    `;
    log.info("✓ Added account_setting_capabilities column");

    // Add account_setting_capabilities_fetched_at column
    await sql`
      ALTER TABLE tomori_configs
      ADD COLUMN IF NOT EXISTS account_setting_capabilities_fetched_at TIMESTAMP;
    `;
    log.info("✓ Added account_setting_capabilities_fetched_at column");

    log.success(
      "Migration completed: account-setting capability caching columns added",
    );
  } catch (error) {
    if (error instanceof Error && error.message.includes("already exists")) {
      log.warn("Columns already exist, skipping...");
    } else {
      log.error("Failed to add account-setting capability columns", error as Error);
      throw error;
    }
  }
}

// Run migration
addAccountSettingCapabilityColumns()
  .then(() => {
    log.info("Migration finished successfully");
    process.exit(0);
  })
  .catch((error) => {
    log.error("Migration failed", error as Error);
    process.exit(1);
  });
