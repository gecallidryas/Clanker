import { sql } from "bun";
import { config } from "dotenv";
import { log } from "../src/utils/misc/logger";

config();

if (!process.env.DATABASE_URL) {
  const host = process.env.POSTGRES_HOST || "localhost";
  const port = process.env.POSTGRES_PORT || "5432";
  const user = process.env.POSTGRES_USER || "postgres";
  const password = process.env.POSTGRES_PASSWORD;
  const database = process.env.POSTGRES_DB || "tomodb";

  if (!password) {
    log.error("POSTGRES_PASSWORD environment variable not found.");
    process.exit(1);
  }

  process.env.DATABASE_URL = `postgresql://${user}:${password}@${host}:${port}/${database}`;
}

async function fetchMetrics(label: string): Promise<void> {
  const [row] = await sql<{
    tomoris_without_lineage: number;
    persona_configs_total: number;
    server_memories_without_tomori: number;
    personal_memories_global_scope: number;
    users_with_legacy_array: number;
  }>`
		SELECT
			(SELECT COUNT(*)::int FROM tomoris WHERE persona_lineage_id IS NULL) AS tomoris_without_lineage,
			(SELECT COUNT(*)::int FROM persona_configs) AS persona_configs_total,
			(SELECT COUNT(*)::int FROM server_memories WHERE tomori_id IS NULL) AS server_memories_without_tomori,
			(SELECT COUNT(*)::int FROM personal_memories WHERE persona_lineage_id = 0) AS personal_memories_global_scope,
			(
				SELECT COUNT(*)::int
				FROM users
				WHERE COALESCE(array_length(personal_memories, 1), 0) > 0
			) AS users_with_legacy_array
	`;

  log.info(`[${label}] tomoris_without_lineage=${row.tomoris_without_lineage}`);
  log.info(`[${label}] persona_configs_total=${row.persona_configs_total}`);
  log.info(
    `[${label}] server_memories_without_tomori=${row.server_memories_without_tomori}`,
  );
  log.info(
    `[${label}] personal_memories_global_scope=${row.personal_memories_global_scope}`,
  );
  log.info(`[${label}] users_with_legacy_array=${row.users_with_legacy_array}`);
}

async function runMigration(): Promise<void> {
  log.section("Persona Lineage + Memory Backfill v2");
  await fetchMetrics("before");

  await sql.transaction(async (tx) => {
    // 1) Backfill missing lineage IDs on existing personas.
    await tx`
			UPDATE tomoris
			SET persona_lineage_id = nextval('persona_lineage_id_seq')
			WHERE persona_lineage_id IS NULL
		`;

    // 2) Backfill persona_configs trigger words from legacy locations.
    await tx`
			INSERT INTO persona_configs (tomori_id, trigger_words)
			SELECT
				t.tomori_id,
				CASE
					WHEN t.is_alter THEN COALESCE(t.alter_triggers, ARRAY[]::TEXT[])
					ELSE COALESCE(tc_server.trigger_words, tc_legacy.trigger_words, ARRAY[]::TEXT[])
				END AS trigger_words
			FROM tomoris t
			LEFT JOIN LATERAL (
				SELECT trigger_words
				FROM tomori_configs
				WHERE server_id = t.server_id
				ORDER BY updated_at DESC NULLS LAST, tomori_config_id DESC
				LIMIT 1
			) tc_server ON true
			LEFT JOIN LATERAL (
				SELECT trigger_words
				FROM tomori_configs
				WHERE tomori_id = t.tomori_id
				ORDER BY updated_at DESC NULLS LAST, tomori_config_id DESC
				LIMIT 1
			) tc_legacy ON true
			ON CONFLICT (tomori_id) DO NOTHING
		`;

    // 3) Backfill server_memories.tomori_id to each server's current main persona.
    await tx`
			UPDATE server_memories sm
			SET tomori_id = main.tomori_id
			FROM (
				SELECT DISTINCT ON (server_id)
					server_id,
					tomori_id
				FROM tomoris
				WHERE is_alter = false
				ORDER BY server_id, updated_at DESC NULLS LAST, tomori_id DESC
			) main
			WHERE sm.server_id = main.server_id
			  AND sm.tomori_id IS NULL
		`;

    // 4) Backfill users.personal_memories into global personal namespace (lineage 0).
    await tx`
			INSERT INTO personal_memories (user_id, persona_lineage_id, content, created_at, updated_at)
			SELECT
				u.user_id,
				0::BIGINT,
				legacy_memory,
				COALESCE(u.updated_at, CURRENT_TIMESTAMP),
				COALESCE(u.updated_at, CURRENT_TIMESTAMP)
			FROM users u
			CROSS JOIN LATERAL unnest(COALESCE(u.personal_memories, ARRAY[]::TEXT[])) AS legacy_memory
			WHERE NOT EXISTS (
				SELECT 1
				FROM personal_memories pm
				WHERE pm.user_id = u.user_id
				  AND pm.persona_lineage_id = 0
				  AND pm.content = legacy_memory
			)
		`;
  });

  await fetchMetrics("after");
  log.success("Migration/backfill completed.");
}

runMigration()
  .catch((error) => {
    log.error("Migration/backfill failed.", error);
    process.exit(1);
  })
  .finally(() => {
    process.exit(0);
  });
