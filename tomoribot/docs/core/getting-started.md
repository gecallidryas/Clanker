# 2. Getting Started with TomoriBot Development

This guide sets up TomoriBot locally with Bun + PostgreSQL.

## Prerequisites

- Bun
- PostgreSQL
- A Discord bot application with:
  - `bot` and `applications.commands` scopes
  - Privileged intents enabled in Discord Developer Portal:
    - `Server Members Intent`
    - `Message Content Intent`
  - `Presence Intent` is optional (used only outside production)

## 1. Install Dependencies

```bash
bun install
```

## 2. Create Local Environment File

```bash
cp .env.example .env
```

Minimum required values for local development:

```env
DISCORD_TOKEN=...
CRYPTO_SECRET=...
POSTGRES_HOST=localhost
POSTGRES_PORT=5432
POSTGRES_USER=...
POSTGRES_PASSWORD=...
POSTGRES_DB=tomodb
RUN_ENV=development
```

Notes:

- Runtime uses `RUN_ENV` (not `NODE_ENV`) for production/dev branching.
- In production mode (`RUN_ENV=production`), secrets are fetched from AWS Secrets Manager (`tomoribot/production`) unless `TEST_PRODUCTION=true`.

## 3. Prepare PostgreSQL

Create a DB/user, then ensure `.env` credentials match.

## 4. Start the Bot

```bash
bun run dev
```

Expected startup stages include:

- secrets loading
- encryption key manager init
- schema + seed verification
- tool registry init
- locale init
- cache warmup
- event handler setup
- Discord login

## 5. First-Time Discord Setup

Run in your test server:

```text
/config setup
```

Then set your provider key:

```text
/config apikey set provider:google key:...
```

Also supported:

- `provider:openrouter`
- `provider:novelai`

`custom` provider (self-hosted endpoint) is intended for non-production environments.

## Common Development Commands

```bash
bun run dev
bun run build
bun run start
bun run lint
bun run check
bun run seed-db
bun run nuke-db
bun run backup-db
bun run purge-commands
bun run check-locales
bun run check-limits
```

## Quick Health Checks

- `/tool ping`
- `/tool status`
- Mention the bot or use trigger words in chat

## Troubleshooting

- Command registration issues: run `/tool refresh`
- Type errors: `bun run check`
- Formatting/lint: `bun run lint`
- Locales mismatch: `bun run check-locales`
