# 26. Coding Standards and Conventions

This document captures coding rules that should stay stable across features and refactors.

## Formatting and Style

- Use tabs for indentation (Biome project setting).
- Use double quotes for strings.
- Run `bun run lint` after edits.

## TypeScript and Validation

- Keep TypeScript strict; avoid `any`.
- Prefer explicit shared types under `src/types/`.
- Use Zod/runtime validation for untrusted external input.
- Add concise JSDoc for exported/public functions when behavior is non-obvious.

## File Organization and Imports

- Use `camelCase` file names.
- Use `@/*` path aliases for `src/*` imports.
- Use `node:` protocol for Node built-ins (`node:path`, `node:fs`, etc.).

## Configuration and Magic Numbers

- Do not hardcode operational limits/timeouts/thresholds in feature logic.
- Use env vars with fallback defaults, for example:

```ts
const VALUE = Number.parseInt(process.env.CONFIG_VAR || "10", 10);
```

- Add new env vars to `.env.example` with a clear comment.

## Database and Migrations

- Use Bun SQL template literals for queries.
- Keep schema migrations idempotent (`IF NOT EXISTS`, helper functions, guarded blocks).
- For DB model details, see `docs/systems/database-schema.md`.

## Cache-Safe Write Pattern

If a write affects cached reads:

1. perform DB write successfully
2. then invalidate affected cache key(s)

Do not invalidate before failed writes, and do not manually mutate cached objects.
See `docs/systems/caching.md` for exact cache map and invalidation APIs.

## Logging and Error Handling

- Use `log` from `src/utils/misc/logger.ts`.
- Include useful context metadata (`errorType`, IDs, action context).
- Treat startup-critical failures differently from recoverable runtime failures.

## Discord Command Rules

- Slash commands only (no legacy prefix command surface).
- All user-facing text must be localized via `localizer()`.
- Follow interaction timing patterns in `docs/systems/command-system.md`.

## Final Quality Gate

Before finishing implementation work:

```bash
bun run check
bun run lint
```

When locale keys/command metadata changed:

```bash
bun run check-locales
```
