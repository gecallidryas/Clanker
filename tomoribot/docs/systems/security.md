# 13. Security & Privacy

This document describes TomoriBot's current (2026) security and privacy behavior based on the active codebase.

## Security Surface

TomoriBot's security model combines:
- Secret loading and environment isolation
- Encryption-at-rest for provider/API credentials
- Key versioning and rotation support
- Provider API key failover/round-robin controls
- SQL injection protections
- Runtime anti-abuse guards (cooldowns, quotas, memory/flood guards)
- User privacy controls (global levels + per-server blacklist)

## Secrets Management

Primary files:
- `src/utils/security/secretsManager.ts`
- `src/index.ts`

Behavior:
- Non-production (or `TEST_PRODUCTION=true`): secrets load from `.env`.
- Production (`RUN_ENV=production`): secrets load from AWS Secrets Manager (`tomoribot/production`, region from `AWS_REGION`, default `us-east-1`).
- Required secrets are validated at startup:
  - `DISCORD_TOKEN`
  - `POSTGRES_HOST`, `POSTGRES_PORT`, `POSTGRES_USER`, `POSTGRES_PASSWORD`, `POSTGRES_DB`
  - `CRYPTO_SECRET`
- After loading, secrets are mapped to `process.env` and `keyManager.initialize()` is called.

Key takeaway: encryption key initialization happens only after secrets are loaded.

## API Key Encryption at Rest

Primary files:
- `src/utils/security/crypto.ts`
- `src/utils/security/keyManager.ts`
- `src/db/schema.sql`

Current implementation:
- API keys are encrypted/decrypted via PostgreSQL `pgcrypto` (`pgp_sym_encrypt` / `pgp_sym_decrypt`).
- Encrypted values are stored as `BYTEA`.
- Each encrypted row stores `key_version` to support multi-version decryption.

Main encrypted storage locations:
- `tomori_configs.api_key` + `tomori_configs.key_version`
- `opt_api_keys.api_key` + `opt_api_keys.key_version`
- `api_key_rotation.api_key` + `api_key_rotation.key_version` (except main-key pointer rows)

## Key Versioning and Rotation

Primary files/scripts:
- `src/utils/security/keyManager.ts`
- `scripts/auditKeyVersions.ts` (`bun run audit-keys`)
- `scripts/rotateAllKeys.ts` (`bun run rotate-keys`)

Environment key model:
- Legacy: `CRYPTO_SECRET` (treated as version 1 when needed)
- Versioned: `CRYPTO_SECRET_V1`, `CRYPTO_SECRET_V2`, ...
- Optional override: `CRYPTO_SECRET_CURRENT`
- If no explicit current version is set, highest available version is used for new writes.

Rotation behavior:
- New encryptions use current version.
- Existing rows remain decryptable using their stored `key_version`.
- Optional API keys also perform lazy rotation on read when an older version is encountered.
- Full forced migration is available via `bun run rotate-keys`.

Recommended workflow:
1. Add new key version to environment/secrets.
2. Restart bot (new writes use new version).
3. Run `bun run audit-keys`.
4. Run `bun run rotate-keys` if immediate migration is needed.
5. Remove old key versions only after audit shows no remaining usage.

## Provider API Key Pool (Failover / Load Balancing)

Primary file:
- `src/utils/security/keyRotation.ts`

`api_key_rotation` provides provider-specific key pools per server:
- Round-robin-like selection (ordered by `usage_count`)
- Temporary cooldown on errored keys
  - `rate_limit`: 60s
  - `api_error`: 5min
- Main key pointer support (`is_main_key_pointer=true`) so `tomori_configs.api_key` can participate in the pool
- Success/error recording updates counters and cooldown metadata

This is separate from encryption key version rotation. It controls runtime provider key usage and failover.

## Privacy Model

Primary files:
- `src/commands/personal/privacy.ts`
- `src/events/messageCreate/tomoriChat.ts`
- `src/utils/text/contextBuilder.ts`
- `src/utils/db/dbRead.ts`
- `src/db/schema.sql` (`users.privacy_level`, `personalization_blacklist`)

### Global privacy levels (`/personal privacy`)

`users.privacy_level` values:
- `0` (`MINIMAL`): full personalization context (including status/roles/personal memories when allowed).
- `1` (`PARTIAL`): reduced personalization; level-0-only enrichments (status/roles/personal memories) are excluded.
- `2` (`FULL`): strongest privacy posture.

Current runtime effects for `FULL`:
- Message-based chat trigger flow silently ignores the user in `messageCreate` (non-manual trigger path).
- Messages from level-2 users are filtered out of conversation history context.

### Per-server blacklist (`/server blacklist`)

`personalization_blacklist` is server-scoped and keyed by `(server_id, user_disc_id)`.

Blacklisted users:
- Are excluded from personalization behavior in that server.
- Are not globally opted out.
- Can still exist and interact; blacklist controls personalization scope rather than account existence.

## Data Export and Deletion (Current Behavior)

Primary files:
- `src/commands/data/export.ts`
- `src/commands/data/delete.ts`
- `src/utils/db/dataExport.ts`

Export is granular by type (JSON file via DM), including:
- persona personal memories
- persona server memories
- personal settings
- server config
- global personal memories

Delete is also type-scoped and requires confirmation choice:
- persona personal memories
- persona server memories
- personal settings reset
- server config reset
- global personal memories

Important: current `/data delete` does not implement a blanket user-row/account hard delete path in this command implementation.

## SQL Injection Protections

Primary files:
- `src/utils/db/client.ts`
- `src/utils/db/sqlSecurity.ts`

Protections in place:
- Parameterized Bun SQL template queries are used for values.
- Dynamic UPDATE field names are validated against explicit allowlists (`validateUserFields`, `validateTomoriFields`, `validateTomoriConfigFields`).

## Runtime Guardrails and Anti-Abuse Controls

Primary files:
- `src/db/schema.sql` (`cooldowns`, `cleanup_expired_cooldowns()`)
- `src/utils/db/cooldownManager.ts`
- `src/utils/db/messageCooldown.ts`
- `src/utils/security/rateLimiter.ts`
- `src/utils/security/safeDownload.ts`

Controls include:
- Command and message cooldown system (see `docs/systems/cooldown-system.md`)
- Production-only message concurrency limits per user/server
- Daily in-memory quotas for persona/import/document/avatar operations
- Stream flood guard (`MAX_FLUSH_COUNT`)
- Memory pressure guard with warning/critical modes and emergency cooldown
- Safe attachment download with max size + timeout + response validation

## Operational Checklist

- Keep `.env` and secret material out of version control.
- Prefer versioned encryption keys (`CRYPTO_SECRET_V*`) even if starting with one version.
- Run `bun run audit-keys` before removing old key versions.
- Use `bun run rotate-keys --dry-run` before forced migration.
- When changing privacy or blacklist behavior in code, verify matching cache invalidation paths (user cache / blacklist cache).

## Related Docs

- `docs/systems/database-schema.md`
- `docs/systems/caching.md`
- `docs/systems/cooldown-system.md`
- `docs/ai/rag.md` (document memory gating and limits)
