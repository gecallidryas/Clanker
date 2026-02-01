# Femboi Bot Features

This document is the canonical, detailed feature inventory for this repository. It is expected to stay in sync with the codebase.

## System summary
- Multi-cog Discord bot with per-guild configuration, persistent storage, and AI-driven chat.
- Persona system with multiple modes, per-mode prompts, and webhook-based display customization.
- Per-guild SQLite databases plus a global stats database.

## Feature catalog (by subsystem)

### Core runtime (discord_bot/main.py)
- Loads environment variables from `discord_bot/.env` plus optional `.env.femmy` overrides.
- Requires `DISCORD_TOKEN` and `ENCRYPTION_KEY` at startup; configurable `COMMAND_PREFIX` and `BOT_MODE` lock.
- Auto-discovers and loads all cogs in `discord_bot/cogs` at startup.
- Initializes databases and syncs slash commands on startup.
- Enforces guild-only commands (blocks prefix and slash commands in DMs).
- Sets bot presence based on the current mode profile for the first guild.
- Tracks command usage metrics.
- Provides a standalone `!sync` command for on-demand slash sync.

### AI chat and conversation (discord_bot/cogs/ai_brain.py)
- Responds when mentioned, when a mode-specific trigger word is used, or while in an active conversation window.
- Maintains per-channel rolling context (last 20 messages within 30 minutes).
- Tracks message attribution for reply context (chain memory).
- Active conversation continuation for up to 3 messages within a 5 minute window.
- Injects user facts (including mentioned users) into prompts.
- Applies affection level gating to tone and compliance.
- Enforces gender-role guidance in prompts based on configured role-to-gender mappings.
- Supports strict name preferences when a user has a strict alias.
- Adds wellbeing check prompt once per day for Oneesan mode (20:00-23:00 local time when timezone is set; otherwise UTC).
- Supports custom emoji policies and server emoji lists in prompts.
- Uses per-user rate limiting for AI responses.
- Multi-modal context injection:
  - Auto-describes attached images (up to 3, 10 MB each) and adds descriptions to the prompt.
  - Auto-describes attached videos (up to 1, 20 MB) via Gemini File API and adds descriptions to the prompt.
- Provider selection:
  - Default: Gemini.
  - Uncensored (evil) mode: OpenRouter when enabled and allowed by affection level; falls back to Gemini if needed.
- Agentic action execution (role management and moderation) via structured JSON responses when user has configured staff permissions; logs to mod-log channel.
- Natural-language admin configuration via `admin_action` JSON for starboard, welcome, automod, and basic config actions, with confirmation prompts if required fields are missing.

### Vision analysis (discord_bot/cogs/vision.py)
- Explicit image analysis via `!describe` or `/describe` with optional question prompt.
- Supports image attachments on the current message or a replied message.
- Enforces supported formats and size limits (10 MB).
- Uses per-user AI rate limiting.

### Personality, modes, and presentation
- Mode registry with profiles in `discord_bot/modes/*` and prompts in `discord_bot/prompts/*`.
- Mode profiles include:
  - `mode_default`
  - `mode_femboy`
  - `mode_tsundere`
  - `mode_oneesan`
- Each mode defines:
  - Display name and description
  - Aliases
  - Trigger words
  - Prompt file and evil prompt file
  - Mention reactions
  - Switch message
  - Optional emoji prefix and activity string
- Mode switching with permission checks; optional global lock via `BOT_MODE`.
- Persona manager uses webhooks to send messages with mode-specific display names and avatars from `discord_bot/data/personas.json`.

### Affection and mood (discord_bot/cogs/affection.py, discord_bot/utils/sentiment.py)
- Per-mode affection tracking with levels and thresholds.
- Affection changes from direct mentions (sentiment analysis) and explicit actions (headpat/hug).
- Mood system per guild with hourly decay and interaction-based boosts.
- Sentiment analysis uses keyword heuristics and Gemini fallback.

### Memory and personalization (discord_bot/cogs/memories.py)
- User timezone storage (IANA names and common abbreviations).
- Personal facts:
  - `!remember` / `/remember` to store facts.
  - Automatic fact reconciliation using Gemini summarization when possible.
  - `!forget` / `/forget` clears facts.
- Aliases and lookup:
  - `!aka` / `/aka` to add aliases.
  - `!aliases` / `/aliases` list aliases.
  - `!whois` / `/whois` resolves alias to user.
- Cross-user facts via `!aboutuser` / `/aboutuser`.
- Birthdays:
  - View, set, and list upcoming birthdays (`!birthday`, `/birthday`).
- User profile analysis:
  - `/analyze` runs AI-driven personality summary using message history and saved facts.

### Reminders (discord_bot/cogs/reminders.py)
- Natural language time parsing for reminders (minutes/hours/days/weeks, tomorrow, next week).
- Per-user reminder limits (25 max).
- Reminder list, cancel, and background delivery loop.
- Reminder responses are persona-aware.

### Scheduling and automation (discord_bot/cogs/scheduler.py)
- Disboard bump detection and reminders (2 hours after last bump).
- Configurable bump reminder channel and toggles (prefix and slash commands).
- Meal check reminders for Oneesan mode at 22:00 local time (based on user timezone).

### Moderation and safety
- Automod keyword rules with configurable actions (delete, timeout, kick, ban) via `/automod`.
- Spam detection with configurable thresholds and timeouts.
- Mod log channel support for automod and agentic actions.
- Timeout logging via `discord_bot/cogs/logger.py`.
- Staff role permission levels for agentic actions (`/config staff`).
- Gender role mappings for pronoun guidance (`/admin setgenderrole`).

### Starboard (discord_bot/cogs/starboard.py)
- Configurable starboard channel, threshold, and emoji triggers (single emoji, multiple list, or ANY).
- Optional self-star allowance.
- Ignore/unignore channels.
- Updates starboard entries on reaction add/remove.
- Marks starboard entries when the original message is deleted.

### Utilities (discord_bot/cogs/utilities.py)
- Custom help system with category layout.
- Bot stats (uptime, servers, users, memory usage, messages, images).
- Cog reload (owner only).
- Translation via Gemini (`!translate`, `/translate`).
- Summarization of recent messages (`!tldr`, `/tldr`).
- Ping and about commands.
- AI embed generator (`/generate_embed`).

### Configuration and admin (discord_bot/cogs/config.py, discord_bot/cogs/admin.py)
- Guild admin password and auth sessions (15 minute session window).
- Encrypted per-guild API key storage for:
  - Gemini general
  - Gemini translate
  - Gemini summarize
  - OpenRouter
- Model selection for Gemini and OpenRouter (with recommended lists).
- Env upload and example delivery for guild-specific configuration.
- Feature toggles (evil mode, autorole, welcome) via `/config toggle`.
- Staff roles and permission levels via `/config staff`.
- Mod log channel via `/config modlog`.
- Auto-role configuration via `/config autorole`.
- Welcome messages:
  - Channel, enable/disable
  - Custom template
  - DM welcome message and toggle
- Admin user management:
  - Reset user data (facts, affection, aliases)
  - View full user profile
  - Set/delete facts
  - Set affection points by mode
  - Slash command sync and clearing
  - Gender role mapping

### Emoji systems (discord_bot/utils/app_emojis.py, discord_bot/utils/emoji_manager.py)
- Application emoji fetching and caching.
- Emoji prefix filters for mode-specific emoji lists.
- Emoji replacement of `:name:` tokens in AI responses.
- Config-driven custom emoji availability and usage rules (`discord_bot/data/emoji_config.json`).
- General emoji list for unrestricted usage.
- Emoji assets are not bundled; emojis are referenced by ID in config.

### Data and persistence (discord_bot/utils/db_handler.py)
- Per-guild SQLite databases stored in `discord_bot/data/`.
- Global SQLite database for stats and guild registry (`data/global.db` by default).
- Tables (per-guild unless noted):
  - global: `bot_stats`, `guild_registry`
  - users and profiles: `users`, `user_profiles`
  - memory: `user_facts`, `user_aliases`, `pending_facts`
  - relationships: `user_affection_by_mode`, `bot_mood`, `wellbeing_checks`
  - reminders: `reminders`
  - server settings: `server_config`, `guild_config`
  - auth/audit: `guild_admin_auth`, `guild_auth_sessions`, `guild_config_audit`
  - moderation: `staff_roles`, `gender_roles`, `automod_rules`, `mod_log_channel_id` (in `guild_config`)
  - starboard: `starboard_settings`, `starboard_entries`, `starboard_ignored_channels`
- `starboard_settings` fields include `channel_id`, `emoji_trigger`, `emoji_triggers`, `emoji_mode`, `threshold`, `allow_self_star`, `enabled`.
- Built-in migrations for new columns and tables.

### Deployment and ops
- Deployment scripts in `deploy/` with a systemd service template.
- `scripts/split_db.py` migrates a legacy monolithic DB into per-guild DBs plus a global stats DB.
- Logging to `discord_bot/logs/femmy.log` with rotation.

### Tests
- Unit tests for API key manager and mode registry in `tests/`.

## Commands

### Prefix commands
- Admin: `!admin` (group: reset, view, setfact, delfact, setaffection, sync, clearglobal, clearguild)
- Affection: `!affection`, `!mood`, `!headpat`, `!hug`
- Memory: `!set_timezone`, `!remember`, `!forget`, `!myinfo`, `!aka`, `!aliases`, `!whois`, `!aboutuser`, `!birthday`
- Reminders: `!remind` (group: list, cancel), `!reminders`
- Scheduler: `!setbump`, `!clearbump`
- Social: `!mode`, `!modes`, `!currentmode`, `!evil`
- Utilities: `!help`, `!stats`, `!reload`, `!translate`, `!tldr`, `!ping`, `!about`
- Vision: `!describe`
- Core: `!sync` (from main.py)

### Slash commands
- Admin: `/admin reset`, `/admin view`, `/admin setfact`, `/admin delfact`, `/admin affection`, `/admin model`, `/admin clearglobal`, `/admin clearguild`
- Affection: `/affection`, `/mood`, `/headpat`, `/hug`
- Automod: `/automod add`, `/automod remove`, `/automod list`, `/automod spam`
- Config: `/config auth`, `/config password set|change|reset`, `/config keys view|set|clear`, `/config model view|set`, `/config env example|upload`, `/config toggle evil|autorole|welcome`, `/config staff add|remove|list`, `/config modlog set|clear|view`, `/config autorole set|clear|view`, `/config welcome channel|clear|test|set_message|view_message|clear_message|set_dm_message|clear_dm_message|toggle_dm`
- Memory: `/timezone`, `/remember`, `/forget`, `/myinfo`, `/aka`, `/aliases`, `/whois`, `/aboutuser`, `/birthday`, `/analyze`
- Reminders: `/remind`, `/reminders`, `/remindcancel`
- Scheduler: `/bumpchannel`, `/bumpstart`, `/bumpstop`
- Social: `/evil`, `/mode`, `/modes`, `/currentmode`
- Starboard: `/starboard setup`, `/starboard toggle`, `/starboard ignore`, `/starboard unignore`, `/starboard ignored`
- Utilities: `/help`, `/stats`, `/reload`, `/translate`, `/generate_embed`, `/tldr`, `/ping`, `/about`
- Vision: `/describe`
- Misc: `/setgenderrole` (admin)

## Configuration and secrets
- Bot-level configuration: `discord_bot/.env` (see `discord_bot/.env.example`).
- Guild-level configuration: upload `discord_bot/guild.env.example` via `/config env upload`.
- Per-guild API keys are stored encrypted using `ENCRYPTION_KEY`.

## Folder skeleton (top level)

```
/ (repo root)
  .agent/
    workflows/
      webhook_standard_mod.md
  deploy/
    deploy.sh
    update.sh
    setup_yumi.sh
    femmy-bot.service
    README.md
  discord_bot/
    cogs/
      admin.py
      affection.py
      ai_brain.py
      automod.py
      config.py
      logger.py
      memories.py
      reminders.py
      scheduler.py
      social.py
      starboard.py
      utilities.py
      vision.py
      __init__.py
    data/
      emoji_config.json
      personas.json
    modes/
      default.py
      femboy.py
      oneesan.py
      tsundere.py
      registry.py
      __init__.py
    prompts/
      default.txt
      femboy.txt
      femboy_evil.txt
      oneesan.txt
      oneesan_evil.txt
      tsundere.txt
      tsundere_evil.txt
    utils/
      admin_actions.py
      api_manager.py
      app_emojis.py
      auth.py
      db_handler.py
      emoji_manager.py
      encryption.py
      guild_ai.py
      logger.py
      persona_manager.py
      rate_limiter.py
      sentiment.py
      __init__.py
    .env
    .env.example
    guild.env.example
    main.py
    requirements.txt
  scripts/
    split_db.py
  tests/
    test_api_manager.py
    test_mode_registry.py
  AGENTS.md
  FEATURES.md
  emojilist.md
  application.commands
  implementation_plan.md
  implementation_plan2.md
  implementation4.md
  implementation5.md
  implementationfix1.md
  improvement.md
  Improvement3.md
  plan.md
  apidbrefactor.md
  task.md
```

## Notes
- On Windows, `FEATURES.md` and `features.md` refer to the same file; this repository uses `FEATURES.md` as the canonical filename for the detailed features doc.
- Emoji assets are not bundled; emoji IDs in `discord_bot/data/emoji_config.json` are the source of truth.
```
