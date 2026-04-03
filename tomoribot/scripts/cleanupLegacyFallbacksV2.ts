import { sql } from "bun";
import { config } from "dotenv";
import { log } from "../src/utils/misc/logger";

config();

type ScriptOptions = {
  apply: boolean;
  finalCutover: boolean;
  yes: boolean;
};

type CleanupMetrics = {
  tomoriConfigsTotal: number;
  tomoriConfigsNullServerId: number;
  tomoriConfigDuplicateServers: number;
  serverMemoriesNullTomori: number;
  personaConfigsMissing: number;
  globalPersonalMemories: number;
  usersWithLegacyPersonalArray: number | null;
  userPersonalMemoriesColumnPresent: boolean;
  legacyTriggerColumnsPresent: {
    tomoriConfigsTriggerWords: boolean;
    tomorisAlterTriggers: boolean;
  };
};

function parseOptions(): ScriptOptions {
  const args = new Set(process.argv.slice(2));
  return {
    apply: args.has("--apply"),
    finalCutover: args.has("--final-cutover"),
    yes: args.has("--yes"),
  };
}

function ensureDatabaseUrl(): void {
  if (process.env.DATABASE_URL) {
    return;
  }

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

async function confirmWithUser(): Promise<boolean> {
  return await new Promise<boolean>((resolve) => {
    process.stdin.resume();
    process.stdin.once("data", (data) => {
      const response = data.toString().trim();
      process.stdin.pause();
      resolve(response === "CLEANUP");
    });
  });
}

async function columnExists(table: string, column: string): Promise<boolean> {
  const [row] = await sql<{ exists: boolean }>`
		SELECT EXISTS (
			SELECT 1
			FROM information_schema.columns
			WHERE table_schema = 'public'
			  AND table_name = ${table}
			  AND column_name = ${column}
		) AS exists
	`;
  return Boolean(row?.exists);
}

async function fetchInt(
  query: Promise<Array<{ value: number }>>,
): Promise<number> {
  const [row] = await query;
  return Number(row?.value ?? 0);
}

async function fetchMetrics(): Promise<CleanupMetrics> {
  const userPersonalMemoriesColumnPresent = await columnExists(
    "users",
    "personal_memories",
  );
  const tomoriConfigsTriggerWords = await columnExists(
    "tomori_configs",
    "trigger_words",
  );
  const tomorisAlterTriggers = await columnExists("tomoris", "alter_triggers");

  const tomoriConfigsTotal = await fetchInt(
    sql<{ value: number }>`
			SELECT COUNT(*)::int AS value
			FROM tomori_configs
		`,
  );
  const tomoriConfigsNullServerId = await fetchInt(
    sql<{ value: number }>`
			SELECT COUNT(*)::int AS value
			FROM tomori_configs
			WHERE server_id IS NULL
		`,
  );
  const tomoriConfigDuplicateServers = await fetchInt(
    sql<{ value: number }>`
			SELECT COUNT(*)::int AS value
			FROM (
				SELECT server_id
				FROM tomori_configs
				WHERE server_id IS NOT NULL
				GROUP BY server_id
				HAVING COUNT(*) > 1
			) d
		`,
  );
  const serverMemoriesNullTomori = await fetchInt(
    sql<{ value: number }>`
			SELECT COUNT(*)::int AS value
			FROM server_memories
			WHERE tomori_id IS NULL
		`,
  );
  const personaConfigsMissing = await fetchInt(
    sql<{ value: number }>`
			SELECT COUNT(*)::int AS value
			FROM tomoris t
			LEFT JOIN persona_configs pc ON pc.tomori_id = t.tomori_id
			WHERE pc.tomori_id IS NULL
		`,
  );
  const globalPersonalMemories = await fetchInt(
    sql<{ value: number }>`
			SELECT COUNT(*)::int AS value
			FROM personal_memories
			WHERE persona_lineage_id = 0
		`,
  );

  let usersWithLegacyPersonalArray: number | null = null;
  if (userPersonalMemoriesColumnPresent) {
    usersWithLegacyPersonalArray = await fetchInt(
      sql<{ value: number }>`
				SELECT COUNT(*)::int AS value
				FROM users
				WHERE COALESCE(array_length(personal_memories, 1), 0) > 0
			`,
    );
  }

  return {
    tomoriConfigsTotal,
    tomoriConfigsNullServerId,
    tomoriConfigDuplicateServers,
    serverMemoriesNullTomori,
    personaConfigsMissing,
    globalPersonalMemories,
    usersWithLegacyPersonalArray,
    userPersonalMemoriesColumnPresent,
    legacyTriggerColumnsPresent: {
      tomoriConfigsTriggerWords,
      tomorisAlterTriggers,
    },
  };
}

function printMetrics(label: string, metrics: CleanupMetrics): void {
  log.section(`Legacy Cleanup Metrics (${label})`);
  log.info(`tomori_configs_total=${metrics.tomoriConfigsTotal}`);
  log.info(
    `tomori_configs_null_server_id=${metrics.tomoriConfigsNullServerId}`,
  );
  log.info(
    `tomori_configs_duplicate_servers=${metrics.tomoriConfigDuplicateServers}`,
  );
  log.info(`server_memories_null_tomori=${metrics.serverMemoriesNullTomori}`);
  log.info(`persona_configs_missing=${metrics.personaConfigsMissing}`);
  log.info(`global_personal_memories=${metrics.globalPersonalMemories}`);
  log.info(
    `users_personal_memories_column_present=${metrics.userPersonalMemoriesColumnPresent}`,
  );
  log.info(
    `users_with_legacy_personal_array=${metrics.usersWithLegacyPersonalArray ?? "N/A"}`,
  );
  log.info(
    `legacy_trigger_columns_present=tomori_configs.trigger_words:${metrics.legacyTriggerColumnsPresent.tomoriConfigsTriggerWords},tomoris.alter_triggers:${metrics.legacyTriggerColumnsPresent.tomorisAlterTriggers}`,
  );
}

async function runBaseCleanup(): Promise<void> {
  await sql.transaction(async (tx) => {
    // 1) Backfill tomori_configs.server_id from legacy tomori_id linkage (main personas only).
    await tx`
			UPDATE tomori_configs tc
			SET server_id = t.server_id
			FROM tomoris t
			WHERE tc.server_id IS NULL
			  AND tc.tomori_id = t.tomori_id
			  AND t.is_alter = false
		`;

    // 2) Deduplicate server-scoped config rows, keeping the most recently updated row per server.
    await tx`
			WITH ranked AS (
				SELECT
					tomori_config_id,
					ROW_NUMBER() OVER (
						PARTITION BY server_id
						ORDER BY updated_at DESC NULLS LAST, tomori_config_id DESC
					) AS rn
				FROM tomori_configs
				WHERE server_id IS NOT NULL
			)
			DELETE FROM tomori_configs tc
			USING ranked r
			WHERE tc.tomori_config_id = r.tomori_config_id
			  AND r.rn > 1
		`;

    // 3) Remove any orphan legacy config rows that still have NULL server_id.
    await tx`
			DELETE FROM tomori_configs
			WHERE server_id IS NULL
		`;

    // 4) Enforce non-null server linkage for configs.
    await tx`
			ALTER TABLE tomori_configs
			ALTER COLUMN server_id SET NOT NULL
		`;

    // 5) Ensure one config row per server.
    await tx`
			DROP INDEX IF EXISTS idx_tomori_configs_server_id_unique
		`;
    await tx`
			CREATE UNIQUE INDEX IF NOT EXISTS idx_tomori_configs_server_id_unique
			ON tomori_configs(server_id)
		`;

    // 6) Backfill legacy server memories to a preferred persona per server.
    await tx`
			WITH preferred AS (
				SELECT DISTINCT ON (server_id)
					server_id,
					tomori_id
				FROM tomoris
				ORDER BY server_id, is_alter ASC, updated_at DESC NULLS LAST, tomori_id DESC
			)
			UPDATE server_memories sm
			SET tomori_id = preferred.tomori_id
			FROM preferred
			WHERE sm.server_id = preferred.server_id
			  AND sm.tomori_id IS NULL
		`;

    const [remainingNullServerMemories] = await tx<{ count: number }>`
			SELECT COUNT(*)::int AS count
			FROM server_memories
			WHERE tomori_id IS NULL
		`;
    if (Number(remainingNullServerMemories?.count ?? 0) > 0) {
      throw new Error(
        "Cannot enforce server_memories.tomori_id NOT NULL: unresolved NULL rows remain.",
      );
    }

    // 7) Remove legacy nullable behavior now that backfill is complete.
    await tx`
			ALTER TABLE server_memories
			ALTER COLUMN tomori_id SET NOT NULL
		`;
  });
}

async function runFinalCutoverCleanup(): Promise<void> {
  await sql.transaction(async (tx) => {
    // 1) Ensure persona_configs exists for every persona before dropping legacy trigger columns.
    await tx`
			INSERT INTO persona_configs (tomori_id, trigger_words)
			SELECT
				t.tomori_id,
				CASE
					WHEN t.is_alter THEN COALESCE(t.alter_triggers, ARRAY[]::TEXT[])
					ELSE COALESCE(tc.trigger_words, ARRAY[]::TEXT[])
				END AS trigger_words
			FROM tomoris t
			LEFT JOIN tomori_configs tc ON tc.server_id = t.server_id
			WHERE NOT EXISTS (
				SELECT 1
				FROM persona_configs pc
				WHERE pc.tomori_id = t.tomori_id
			)
		`;

    // 2) Migrate any remaining users.personal_memories into global lineage before dropping column.
    const [usersPersonalMemoriesExists] = await tx<{ exists: boolean }>`
			SELECT EXISTS (
				SELECT 1
				FROM information_schema.columns
				WHERE table_schema = 'public'
				  AND table_name = 'users'
				  AND column_name = 'personal_memories'
			) AS exists
		`;

    if (usersPersonalMemoriesExists?.exists) {
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
				WHERE legacy_memory <> ''
				  AND NOT EXISTS (
					SELECT 1
					FROM personal_memories pm
					WHERE pm.user_id = u.user_id
					  AND pm.persona_lineage_id = 0
					  AND pm.content = legacy_memory
				)
			`;

      await tx`
				ALTER TABLE users
				DROP COLUMN IF EXISTS personal_memories
			`;
    }

    // 3) Drop legacy trigger-word fallback columns.
    await tx`
			ALTER TABLE tomori_configs
			DROP COLUMN IF EXISTS trigger_words
		`;
    await tx`
			ALTER TABLE tomoris
			DROP COLUMN IF EXISTS alter_triggers
		`;
  });
}

async function run(): Promise<void> {
  ensureDatabaseUrl();
  const options = parseOptions();

  log.section("Legacy Fallback Cleanup v2");
  log.info(
    `mode=${options.apply ? "apply" : "dry-run"}, final_cutover=${options.finalCutover}`,
  );

  const before = await fetchMetrics();
  printMetrics("before", before);

  if (!options.apply) {
    log.info("Dry-run only. No changes applied.");
    log.info("Run with `--apply` to execute cleanup.");
    log.info(
      "Add `--final-cutover` to also drop legacy columns after code fallback is removed.",
    );
    return;
  }

  if (!options.yes) {
    log.warn(
      "This will mutate production data/schema. Make sure you have a backup.",
    );
    log.info("Type `CLEANUP` (all caps) to continue:");
    const confirmed = await confirmWithUser();
    if (!confirmed) {
      log.info("Cleanup aborted. Database unchanged.");
      return;
    }
  }

  await runBaseCleanup();

  if (options.finalCutover) {
    log.warn(
      "Running final cutover cleanup: dropping legacy columns. Ensure fallback code is already removed.",
    );
    await runFinalCutoverCleanup();
  }

  const after = await fetchMetrics();
  printMetrics("after", after);

  log.success("Legacy fallback cleanup completed.");
}

run()
  .catch((error) => {
    log.error("Legacy fallback cleanup failed.", error);
    process.exit(1);
  })
  .finally(() => {
    process.exit(0);
  });
