# Config Panel Guide

## Overview

The bot now uses a panel-first config UX. Instead of many one-off `/config` commands, you open the main panel or a compact subgroup entry command and complete the change from the Discord-native UI.

Primary entrypoints:

- `/config panel`
- `/config ai manage`
- `/config toggle manage`
- `/config url_safety manage`
- `/config keys manage`
- `/config model manage`
- `/config custom_endpoint manage`

Setup and auth entrypoints that still stay direct:

- `/config auth`
- `/config password set`
- `/config password change`
- `/config password reset`
- `/config env example`
- `/config env upload`

## Recommended Setup Flow

1. Set a config password with `/config password set`.
2. Authenticate with `/config auth` before high-risk edits.
3. Download the template with `/config env example` if you need to upload provider secrets in bulk.
4. Upload the guild-specific env file with `/config env upload`.
5. Open `/config panel` and finish server-specific tuning from the panel sections.

## What Each Entry Command Opens

### `/config panel`

Main landing surface implemented in `discord_bot/cogs/config.py`. It links to:

- Capabilities
- AI Settings
- Providers and Models
- Welcome
- Autorole
- URL Safety
- Mod Log
- Staff

### `/config ai manage`

Opens the AI settings panel in `discord_bot/cogs/config.py`. Use it for:

- reply cooldown and scope
- self-reply limit
- auto-channel threshold
- whitelist and auto-channel routing
- streaming behavior
- thought/debug logging

### `/config toggle manage`

Opens the capabilities panel in `discord_bot/cogs/config.py`. Use it for:

- tool and media toggles such as web search, image generation, stickers, GIFs, YouTube, profile peek, and RAG
- learning and memory toggles such as self-teaching and pin message
- evil mode via the panel action

### `/config url_safety manage`

Opens the URL safety panel in `discord_bot/cogs/config.py`. Use it for:

- warn vs delete action
- allowlist patterns
- blocklist patterns

### `/config keys manage`, `/config model manage`, `/config custom_endpoint manage`

These all route into the provider/model panel in `discord_bot/cogs/config.py`. Use that panel for:

- masked provider secret overview
- Gemini and OpenRouter model selection
- custom endpoint URL, key, model, and capability edits

## Related Top-Level Manage Commands

These stayed compact already and still open panel-driven workflows:

- `/welcome manage`
- `/autorole manage`
- `/staff manage`
- `/modlog manage`

## Authentication Rules

Low-risk edits require Manage Server in most panel flows. High-risk edits such as secret changes, destructive removals, staff role changes, and mod-log routing require:

- Administrator permission
- a configured config password
- an active config auth session

Auth handling lives in:

- `discord_bot/utils/auth.py`
- `discord_bot/utils/admin_panel_logic.py`
- `discord_bot/cogs/config.py`

## Code References

- Panel command tree: `discord_bot/cogs/config.py`
- Shared admin panel widgets: `discord_bot/utils/config_panel_ui.py`
- Native panel implementation helpers: `discord_bot/utils/native_config_panel.py`
- Stored guild config state: `discord_bot/utils/db_handler.py`
