# Femboi Bot Features

This document is the canonical, detailed feature inventory for this repository. It is expected to stay in sync with the codebase.

## System summary
- Multi-cog Discord bot with per-guild configuration, persistent storage, and AI-driven chat.
- Persona system with multiple modes, per-mode prompts, server-specific avatars, and custom personas per guild.
- Per-guild SQLite databases plus a global stats database.
- Tool registry with per-guild feature-flag gating and a tool-call pipeline for AI actions.
- Optional Postgres + pgvector for document RAG storage.
- URL safety checks with allow/block lists and a usage dashboard for metrics.

## Feature catalog (by subsystem)

### Core runtime (discord_bot/main.py)
- Loads environment variables from `discord_bot/.env` plus optional `.env.femmy` overrides.
- Requires `DISCORD_TOKEN` and `ENCRYPTION_KEY` at startup; configurable `COMMAND_PREFIX` and `BOT_MODE` lock.
- Auto-discovers and loads all cogs in `discord_bot/cogs` at startup.
- Initializes databases and syncs slash commands on startup.
- Initializes Postgres pgvector schema when `ACTIVATE_LOCAL_RAG` is enabled.
- Enforces guild-only commands (blocks prefix and slash commands in DMs).
- Sets bot presence to Playing: Clanking with humans.
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
- Optional custom OpenAI-compatible endpoint for standard (censored) responses when enabled per guild.
- Agentic action execution (role management and moderation) via structured JSON responses when user has configured staff permissions; logs to mod-log channel.
- Natural-language admin configuration via `admin_action` JSON for starboard, welcome, automod, and basic config actions, with confirmation prompts if required fields are missing.
- Tool pipeline:
  - Injects per-guild tool list and tool-call JSON instructions into prompts.
  - Parses tool calls, executes gated tools, and feeds tool results back into the response pipeline.
  - Injects RAG document context into prompts when local RAG is enabled.

### Vision analysis (discord_bot/cogs/vision.py)
- Explicit image analysis via `!describe` or `/describe` with optional question prompt.
- Supports image attachments on the current message or a replied message.
- Enforces supported formats and size limits (10 MB).
- Uses per-user AI rate limiting.

### Tooling and web intelligence
- Tool registry with per-guild feature flags and tool-call JSON envelope (`{"tool": "...", "args": {...}}`).
- Web search tools:
  - DuckDuckGo search (no key required).
  - Brave Search (optional per-guild key).
  - URL fetch and text extraction via trafilatura.
- Media/expression tools:
  - Image generation via Replicate or OpenRouter image models.
  - Sticker selection and emoji reactions from guild assets.
  - Media context expansion from recent history.
  - GIF replies via Tenor search (`send_gif`) when enabled.
  - Dev-only GIF inspection (frame counts/durations) gated by `GIF_ANALYSIS_ENABLED`.
- Content tools:
  - YouTube metadata + transcript retrieval.
  - Pin message tool with permission checks.
  - Profile picture analysis via Gemini Vision.

### Internationalization (discord_bot/utils/i18n.py)
- Locale JSON files in `discord_bot/locales/` with helper `t(key, locale, **vars)`.
- Fallbacks to English when keys are missing; helpers for interaction/guild locale.
- Used for selected tool/admin responses (English and Japanese provided).

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
  - Bio text and banner file
  - Optional emoji prefix and activity string
- Mode switching with permission checks; optional global lock via `BOT_MODE`.
- Server-specific bot avatars are applied per guild; mode changes can auto-update the server avatar.
- On joining a new guild, the bot sets its server avatar to the guild icon if no custom avatar override exists.
- Admins can reset avatars via `/avatar reset` (rate-limited to 2 updates per 5 minutes). Mode changes auto-apply mode avatars.
- Custom personas can be created per guild with their own bio, prompts, and avatar/banner URLs, then activated with `!mode` or `/mode`.
- `!modes` and `/modes` include custom personas for the current guild.
- Deleting an active custom persona reverts the guild back to `mode_default` and clears the server avatar override.
- Evil mode can use separate avatar images per mode when available.

### Affection and mood (discord_bot/cogs/affection.py, discord_bot/utils/sentiment.py)
- Per-mode affection tracking with levels and thresholds.
- Affection changes from bot-directed messages (sentiment analysis) and explicit actions (headpat/hug), with mode-specific deltas and rate limits (1 per hour, 3 per day) outside default mode.
- Neutral sentiment does not award affection points.
- Default mode uses fixed hug/pat responses and does not change affection.
- Mood system per guild with hourly decay and interaction-based boosts.
- Sentiment analysis uses keyword heuristics and Gemini fallback.
- One-time trait rewards are tracked per user and persona when keyword triggers are detected.

### Memory and personalization (discord_bot/cogs/memories.py)
- User timezone storage (IANA names and common abbreviations).
- Personal facts:
  - `!remember` / `/remember` to store facts.
  - Automatic fact reconciliation using Gemini summarization when possible.
  - `!forget` / `/forget` clears facts (supports personal, short_term, long_term, server, and document scopes).
- Aliases and lookup:
  - `!aka` / `/aka` to add aliases.
  - `!aliases` / `/aliases` list aliases.
  - `!whois` / `/whois` resolves alias to user.
- Cross-user facts via `!aboutuser` / `/aboutuser`.
- Birthdays:
  - View, set, and list upcoming birthdays (`!birthday`, `/birthday`).
- User profile analysis:
  - `/analyze` runs AI-driven personality summary using message history and saved facts.
- Teaching system (`discord_bot/cogs/teach.py`):
  - `/teach memory personal` and `/teach memory server` to store personal or server memories.
  - `/teach attribute` to store persona attributes.
  - `/teach sampledialogue` to store sample dialogue lines.
  - `/teach document` to upload documents for RAG (Postgres + pgvector).
  - `/personal privacy` to opt out of personal memory.
- Self-teaching tools can store short-term and long-term memories when enabled per guild.

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
- Optional URL safety checks with allow/block regex lists and warn/delete actions.
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
- Help output is generated from a centralized command inventory, with mode-specific intros and admin filtering.
- Bot stats (uptime, servers, users, memory usage, messages, images).
- Usage dashboard (`/usage`) with global and per-guild metrics.
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
- `/config env example` sends the warning text plus a multi-part guild.env template when it exceeds message length.
- Feature toggles via `/config toggle`:
  - evil, autorole, welcome
  - web_search, image_gen, stickers, emojis, pin_message, self_teaching, youtube, profile_peek, rag, gif_responses, url_safety
- Quick toggle UI panel via `/config ui`.
- URL safety configuration via `/config url_safety` (view, action, allowlist, blocklist, clear).
- Staff roles and permission levels via `/config staff`.
- Mod log channel via `/config modlog`.
- Auto-role configuration via `/config autorole`.
- Welcome messages:
  - Channel, enable/disable
  - Custom template
  - DM welcome message and toggle
- Custom endpoint configuration via `/config custom_endpoint`.
- Tool availability overview via `/tools status`.
- Admin user management:
  - Reset user data (facts, affection, aliases)
  - View full user profile
  - Set/delete facts
  - Set affection points by mode
  - Slash command sync and clearing
  - Gender role mapping
- Server avatar management via `/avatar reset` (rate-limited to 2 updates per 5 minutes). Mode changes auto-apply mode avatars.
- Custom persona management via `/persona` subcommands (create, list, preview, edit, delete).

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
  - global: `bot_stats`, `guild_registry`, `guild_stats`
  - users and profiles: `users`, `user_profiles`
  - memory: `user_facts`, `user_aliases`, `pending_facts`, `persona_attributes`, `sample_dialogues`
  - relationships: `user_affection_by_mode`, `bot_mood`, `wellbeing_checks`, `interaction_cooldowns`
  - affection traits: `persona_traits`, `user_trait_history`
  - reminders: `reminders`
  - server settings: `server_config`, `guild_config`, `guild_avatar_config`
  - custom personas: `custom_personas`
  - auth/audit: `guild_admin_auth`, `guild_auth_sessions`, `guild_config_audit`
  - moderation: `staff_roles`, `gender_roles`, `automod_rules`, `mod_log_channel_id` (in `guild_config`)
  - starboard: `starboard_settings`, `starboard_entries`, `starboard_ignored_channels`
- `starboard_settings` fields include `channel_id`, `emoji_trigger`, `emoji_triggers`, `emoji_mode`, `threshold`, `allow_self_star`, `enabled`.
- `guild_config` includes `gemini_profile_key` for profile analysis.
- `guild_config` includes `gemini_key_type` for Gemini key rotation mode.
- `guild_config` includes Brave/Replicate/Tenor keys, image provider settings, tool feature flags, URL safety settings, and custom endpoint fields.
- `user_facts` includes `source`, `learned_from_user_id`, and `memory_type` for memory tracking.
- `user_profiles` includes `personal_memory_opt_out`.
- Built-in migrations for new columns and tables.
- Custom persona assets are stored under `discord_bot/data/avatars/custom/` by guild.
- Optional Postgres RAG store (when `ACTIVATE_LOCAL_RAG` is enabled):
  - `documents` and `document_chunks` with pgvector embeddings.

### Deployment and ops
- Deployment scripts in `deploy/` with a systemd service template.
- `scripts/split_db.py` migrates a legacy monolithic DB into per-guild DBs plus a global stats DB.
- Logging to `discord_bot/logs/femmy.log` with rotation.

### Tests
- Unit tests for API key manager, mode registry, image downloader, persona DB helpers, affection traits, tool parsing/flags, web search/fetch, image generation, expression tools, YouTube tool, pin tool, profile peek, RAG helpers, and i18n in `tests/`.

## Commands

### Prefix commands
- Admin: `!admin` (group: reset, view, setfact, delfact, setaffection, sync, clearglobal, clearguild)
- Affection: `!affection`, `!mood`, `!headpat`, `!hug`
- Memory: `!set_timezone`, `!remember`, `!forget`, `!myinfo`, `!aka`, `!aliases`, `!whois`, `!aboutuser`, `!birthday`
- Reminders: `!remind` (group: list, cancel), `!reminders`
- Scheduler: `!setbump`, `!clearbump`
- Social: `!mode`, `!modes`, `!currentmode`, `!evil`
- Utilities: `!help`, `!stats`, `!usage`, `!reload`, `!translate`, `!tldr`, `!ping`, `!about`
- Vision: `!describe`
- Core: `!sync` (from main.py)

### Slash commands
- Admin: `/admin reset`, `/admin view`, `/admin setfact`, `/admin delfact`, `/admin affection`, `/admin model`, `/admin clearglobal`, `/admin clearguild`
- Avatar: `/avatar reset`
- Persona: `/persona create`, `/persona list`, `/persona preview`, `/persona edit`, `/persona delete`
- Affection: `/affection`, `/mood`, `/headpat`, `/hug`
- Automod: `/automod add`, `/automod remove`, `/automod list`, `/automod spam`
- Config: `/config auth`, `/config password set|change|reset`, `/config keys view|set|clear`, `/config model view|set`, `/config env example|upload`, `/config toggle evil|autorole|welcome|web_search|image_gen|stickers|emojis|pin_message|self_teaching|youtube|profile_peek|rag|gif_responses|url_safety`, `/config url_safety view|action|allowlist|blocklist|clear`, `/config ui`, `/config staff add|remove|list`, `/config modlog set|clear|view`, `/config autorole set|clear|view`, `/config welcome channel|clear|test|set_message|view_message|clear_message|set_dm_message|clear_dm_message|toggle_dm`, `/config custom_endpoint view|set`
- Memory: `/timezone`, `/remember`, `/forget`, `/myinfo`, `/aka`, `/aliases`, `/whois`, `/aboutuser`, `/birthday`, `/analyze`
- Teach: `/teach memory personal`, `/teach memory server`, `/teach attribute`, `/teach sampledialogue`, `/teach document`, `/personal privacy`
- Reminders: `/remind`, `/reminders`, `/remindcancel`
- Scheduler: `/bumpchannel`, `/bumpstart`, `/bumpstop`
- Social: `/evil`, `/mode`, `/modes`, `/currentmode`
- Starboard: `/starboard setup`, `/starboard toggle`, `/starboard ignore`, `/starboard unignore`, `/starboard ignored`
- Utilities: `/help`, `/stats`, `/usage`, `/reload`, `/translate`, `/generate_embed`, `/tldr`, `/ping`, `/about`
- Tools: `/tools status`
- Media: `/generate image`
- Vision: `/describe`
- Misc: `/setgenderrole` (admin)

## Configuration and secrets
- Bot-level configuration: `discord_bot/.env` (see `discord_bot/.env.example`).
- Guild-level configuration: upload `discord_bot/guild.env.example` via `/config env upload`; `/config env example` replies with the text template (ephemeral).
- Guild env keys include `GEMINI_PROFILE_KEY` for `/analyze` profile summaries.
- Guild env supports `GEMINI_KEY_TYPE` to control Gemini key rotation (`free` rotates every request, `paid` sticks unless a key fails).
- Guild env supports optional `BRAVE_API_KEY`, `REPLICATE_API_KEY`, `IMAGE_PROVIDER`, `IMAGE_MODEL`, and `CUSTOM_ENDPOINT_*` settings.
- Bot env supports Postgres RAG settings (`ACTIVATE_LOCAL_RAG`, `POSTGRES_*`, `RAG_*`), Tenor GIF keys, and dev flags (`GIF_ANALYSIS_ENABLED`).
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
      imagegen.py
      logger.py
      memories.py
      persona.py
      reminders.py
      scheduler.py
      social.py
      starboard.py
      teach.py
      tools_admin.py
      utilities.py
      usage.py
      vision.py
      __init__.py
    locales/
      en.json
      ja.json
    data/
      avatars/
        .gitkeep
        mode_femboy.webp
        mode_femboy_evil.webp
        mode_tsundere.webp
        mode_tsundere_evil.webp
        mode_oneesan.webp
        mode_oneesan_evil.webp
        custom/
          .gitkeep
      emoji_config.json
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
      affection_traits.py
      admin_actions.py
      api_manager.py
      app_emojis.py
      auth.py
      db_handler.py
      emoji_manager.py
      encryption.py
      expression_picker.py
      expression_tools.py
      gif_reply.py
      gif_processor.py
      guild_ai.py
      i18n.py
      image_downloader.py
      image_generation.py
      logger.py
      media_context.py
      pg_client.py
      pin_tool.py
      profile_peek.py
      rag_documents.py
      rag_embeddings.py
      rag_store.py
      rate_limiter.py
      review_capabilities.py
      server_avatar.py
      self_teaching.py
      sentiment.py
      tool_context.py
      tool_flags.py
      tool_parser.py
      tool_registry.py
      url_safety.py
      url_fetcher.py
      web_search.py
      __init__.py
    .env
    .env.example
    guild.env.example
    main.py
    requirements.txt
  docs/
    AGENTS.md
    FEATURES.md
    FEATURE_PARITY_REPORT.md
    Improvement3.md
    apidbrefactor.md
    application.commands
    emojilist.md
    freeapisafety.md
    implementation8.md
    implementation9.md
    improvement.md
    improvement7.md
    task.md
  scripts/
    split_db.py
  tests/
    test_affection_traits.py
    test_affection_traits_db.py
    test_api_manager.py
    test_expression_tools.py
    test_i18n.py
    test_image_generation.py
    test_image_downloader.py
    test_mode_registry.py
    test_persona_db.py
    test_pin_tool.py
    test_profile_peek.py
    test_rag_documents.py
    test_rag_store.py
    test_tool_parser.py
    test_tool_registry.py
    test_web_search.py
    test_youtube_tool.py
  tomoribot_reference/
```

## Notes
- On Windows, `docs/FEATURES.md` and `docs/features.md` refer to the same file; this repository uses `docs/FEATURES.md` as the canonical filename for the detailed features doc.
- Emoji assets are not bundled; emoji IDs in `discord_bot/data/emoji_config.json` are the source of truth.
```
