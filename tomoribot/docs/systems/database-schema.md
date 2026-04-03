# 5. Database Schema and Data Model

This document summarizes the current PostgreSQL schema used by TomoriBot.

## Schema Sources

- Main schema: `src/db/schema.sql`
- RAG schema: `src/db/schema_rag.sql` (loaded only when RAG is enabled)

## Main Tables (Current)

### Core identity/config

- `servers`
- `tomoris`
- `tomori_configs`
- `persona_configs`
- `users`

### Model registries

- `llms`
- `image_diffusion_models`
- `embedding_models`

### Presets and prompts

- `tomori_presets`
- `system_prompt_presets`

### Memory and expression data

- `server_memories`
- `personal_memories`
- `server_emojis`
- `server_stickers`

### Permissions/privacy/routing

- `personalization_blacklist`
- `channel_whitelist`
- `role_whitelist`

### Ops and reliability

- `cooldowns` (UNLOGGED)
- `reminders`
- `error_logs`
- `opt_api_keys`
- `api_key_rotation`
- `saved_provider_configs`

### Quota system

- `image_quota_configs`
- `image_quotas`
- `serverwide_quotas`
- `text_quota_configs`
- `text_quotas`
- `text_serverwide_quotas`

### Bridge integration

- `matrix_channel_links`

## Optional RAG Tables

When enabled (`RUN_ENV=production` or `ACTIVATE_LOCAL_RAG=true`):

- `documents`
- `document_chunks`

Also requires pgvector (`CREATE EXTENSION IF NOT EXISTS vector`).

## Notable Data Model Decisions

### Multi-persona

- `tomoris` now supports multiple personas per server (`is_alter` flag).
- `persona_lineage_id` supports cross-server memory identity matching.
- Persona names are constrained unique per server (case-insensitive, trimmed).

### Server config scoping

- `tomori_configs.server_id` is the primary modern scope.
- `tomori_configs.tomori_id` remains as a nullable legacy pointer.
- `tomori_configs.message_fetch_limit` stores the per-server context fetch cap (default `80`, configurable via `/config maxmsgfetch`).
- `tomori_configs.welcome_channel_disc_id` stores the single configured join-welcome channel per server.
- `tomori_configs.thought_log_channel_disc_id` stores the optional server-scoped channel where provider reasoning summaries are posted after successful streamed chat turns.
- `tomori_configs.welcome_prompt` stores the required additional greeting instruction shown in `/server welcomechannel`.
- `tomori_configs.welcome_persona_id` stores the selected welcome persona; `NULL` means random persona selection per join.
- `tomori_configs.nai_style_tags` stores server-wide NovelAI style/quality tags prepended to every `generate_image_nai` prompt.
- `tomori_configs.nai_negative_tags` stores server-wide NovelAI negative tags; an empty array falls back to the `NAI_IMAGE_NEGATIVE_PROMPT` env value.
- `tomori_configs.nai_diffusion_model_id` stores the dedicated NovelAI image-model override for `generate_image_nai`; `NULL` means follow `diffusion_model_id` only when that shared model is already a NovelAI diffusion model, otherwise use the seeded default NovelAI model.
- `tomori_configs.nai_sampler`, `nai_steps`, `nai_scale`, `nai_noise_schedule`, and `nai_cfg_rescale` store optional server overrides for NovelAI image generation params; `NULL` means use the env fallback.
- `tomori_configs.vision_llm_id` stores the dedicated vision model for non-vision chat models; `NULL` means no vision tool is available. When set, the `analyze_image` tool is exposed so non-vision models can delegate image analysis to this model.
- `tomori_configs.llm_logit_biases` stores server-wide logit-bias entries as raw text/token-ID input plus tokenizer-specific cached resolutions. Raw text stays canonical so entries can be refreshed when `llm_id` changes.

### NovelAI profile tags

- `tomoris.nai_tags` stores per-persona NovelAI character tags.
- `tomoris.nai_char_ref_url` stores the persisted persona reference image URL/path used by the `/novelai charreference` workflow.
- `users.nai_char_tags` stores per-user NovelAI character tags keyed by Discord snowflake (`users.user_disc_id`).
- `users.nai_char_ref_url` stores the persisted user reference image URL/path keyed by Discord snowflake.

### User personalization

- `users.impersonation_prompt` stores the global user-owned prompt used during `/bot impersonate` user impersonation replies.

### Memory split

- `server_memories`: shared server-level memory
- `personal_memories`: user + persona lineage scoped memory

### Cooldown storage

`cooldowns` uses explicit scope columns:

- `cooldown_type`
- `server_disc_id`
- `user_disc_id`
- `channel_disc_id`
- `command_category`
- `expiry_time`

`channel_whitelist` stores optional per-channel cooldown overrides:

- `cooldown_type` / `cooldown_length` both `NULL` -> inherit the server-wide cooldown
- `cooldown_type` / `cooldown_length` both set -> override the server-wide cooldown for that channel

### API key security

Encrypted columns are stored as `BYTEA` with key version tracking:

- `tomori_configs.api_key` + `tomori_configs.key_version`
- `opt_api_keys.api_key` + `opt_api_keys.key_version`
- `api_key_rotation.api_key` + `api_key_rotation.key_version`
- `saved_provider_configs.api_key` + `saved_provider_configs.key_version`

### Logit bias snapshot storage

- `saved_provider_configs.llm_logit_biases` mirrors `tomori_configs.llm_logit_biases` so provider snapshots can restore both the original text entries and any cached tokenizer-family resolutions.
- This keeps `/config provider switch` and `/config apikey set` compatible with text-first logit-bias UX across model changes.

## Migration Style

Schema is idempotent and startup-safe:

- `CREATE TABLE IF NOT EXISTS`
- helper functions like `add_column_if_not_exists` and `drop_column_if_exists`
- guarded `DO $$ ... $$` blocks for conditional constraint/index/column changes

### Adding Columns — Always Use `seed.sql`

`seed.sql` runs on **every startup** (via `scripts/seedDb.ts`). This means any `add_column_if_not_exists` call placed there is automatically applied to existing databases on the next restart — no separate one-off migration script needed.

**The rule:** whenever you add a column to any table, add the corresponding `add_column_if_not_exists` line to `seed.sql`. Group by table under a clearly labeled comment block (e.g. `-- Ensure all required columns exist in tomori_configs table`).

```sql
-- Ensure all required columns exist in tomori_configs table
SELECT add_column_if_not_exists('tomori_configs', 'my_new_flag', 'BOOLEAN', 'false');
```

One-off `scripts/add*.ts` migration scripts are **not necessary** for column additions and should be avoided — they require manual execution and are easily forgotten. The `seed.sql` approach is self-applying and idempotent.

## Operational Notes

- `cleanup_expired_cooldowns()` is defined in schema and used by startup cleanup + optional pg_cron.
- Quota cleanup helpers exist for old image/text quota rows (`cleanup_old_image_quotas()`, `cleanup_old_text_quotas()`).
- RAG tables are intentionally separate so local development can run without pgvector unless enabled.
