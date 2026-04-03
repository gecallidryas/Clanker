# 4. Entry Point and Initialization Flow

This document reflects the current `src/index.ts` startup pipeline.

## File

- `src/index.ts`

## Startup Sequence

1. Load `.env` (`dotenv`), then load app secrets via `getAppSecrets()`.
2. Populate `process.env` from secrets (Discord, DB, crypto, optional Matrix/S3/webhook values).
3. Initialize `keyManager` after env population.
4. Construct Discord client with intents + sweepers.
5. Register process/client error handlers.
6. Initialize database:
   - run `src/db/schema.sql`
   - run `src/db/schema_rag.sql` only when RAG is enabled (`RUN_ENV=production` or `ACTIVATE_LOCAL_RAG=true`)
   - run `src/db/seed.sql`
7. Cleanup expired cooldown rows at startup (`cleanupExpiredCooldowns`).
8. Attempt optional `pg_cron` registration for hourly cooldown cleanup job.
9. Initialize tool registry (`initializeTools`).
10. Initialize localization (`initializeLocalizer`).
11. Initialize model caches:
    - LLM cache (`initializeLLMCache`)
    - OpenRouter capability cache (`initializeOpenRouterCapabilityCache`)
12. Preload preset avatar cache from DB presets.
13. Initialize Matrix client (optional; non-fatal on failure).
14. Attach all event listeners (`eventHandler(client)`).
15. Register post-ready startup hooks:
    - health tracker init
    - reminder timer init
    - memory monitor init
16. Initialize upload quota cleanup scheduler.
17. In production only, start health HTTP server on `127.0.0.1:3000/health`.
18. Call `client.login(DISCORD_TOKEN)`.

## Error Criticality

- Fatal (process exits):
  - database init failure
  - tool registry init failure
- Non-fatal (warn and continue):
  - cache warmup failures
  - pg_cron setup failures
  - matrix init failure
  - cooldown cleanup failure
  - reminder/memory monitor/quota cleanup init failures

## Discord Client Configuration Notes

- `GuildPresences` intent is only added outside production.
- Sweeper configuration is enabled for message/user cache pressure control.

## clientReady Event Work

`eventHandler` executes all handlers in `src/events/clientReady/` (sorted), including:

- command registration
- MCP server registration
- command registry initialization
- status/presence setup

Additional `client.once("clientReady")` hooks in `index.ts` initialize health tracking, reminders, and memory monitoring.

## Production Health Endpoint

`GET /health` returns:

- `200` when healthy
- `503` when unhealthy

Health is computed from:

- Discord ready state
- websocket ping threshold
- recent Discord event activity
