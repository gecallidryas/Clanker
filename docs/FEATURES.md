# Femmy Bot Feature Reference

This file is the feature index for the current Discord admin UX in `discord_bot/`.
Every feature listed here is backed by a focused workflow document under `docs/`.

## Primary Admin Surfaces

### `/config panel`

Primary guild configuration surface for capabilities, AI reply behavior, providers and models, welcome flows, autorole, staff routing, mod-log routing, and URL safety.

Detailed reference: [feature-config-panel.md](./feature-config-panel.md)

### `/tools manage`

Primary bulk tool-capability surface. This handles grouped feature flags only. Operational actions such as `/tools refresh` stay outside the panel.

Detailed reference: [feature-tools-manage.md](./feature-tools-manage.md)

### `/persona manage`

Primary persona and presentation surface. This covers activation, evil-mode toggling, previewing, and custom persona lifecycle actions.

Detailed reference: [feature-persona-manage.md](./feature-persona-manage.md)

### `/persona impersonate`

Staff-only persona generation surface. This creates an inactive custom persona from a member's recent visible messages, persona-local sample dialogues, and current avatar.

Detailed reference: [feature-persona-impersonation.md](./feature-persona-impersonation.md)

## Configuration Areas

### Capabilities and Tools

Bulk grouped toggles replace one-off flag edits for most tool and capability settings.

Detailed reference:
- [feature-config-panel.md](./feature-config-panel.md)
- [feature-tools-manage.md](./feature-tools-manage.md)

### AI Reply Settings

Reply policy, routing, streaming, and thought/debug logging are managed directly from the config panel. Persona runtime state for multi-persona queueing and webhook identity is also stored in guild config and surfaced by the AI settings summaries.

The AI reply runtime also coalesces same-user split messages into one turn after the first fragment triggers the bot, so later fragments in that short debounce window do not need to repeat the mention.

Detailed reference: [feature-config-panel.md](./feature-config-panel.md)

### Providers and Models

Masked secret state, model routing, image/media provider settings, and custom endpoint configuration are managed from the provider section of the config panel.

Detailed reference: [feature-config-panel.md](./feature-config-panel.md)

### Welcome and Autorole

Welcome channel/message settings, DM welcomes, and autorole configuration live under the server settings portion of the config panel.

Detailed reference: [feature-config-panel.md](./feature-config-panel.md)

### Staff and Modlog

High-risk server routing for staff access and moderation logging is managed from the config panel with password-backed authentication.

Detailed reference:
- [feature-config-panel.md](./feature-config-panel.md)
- [feature-security-audit.md](./feature-security-audit.md)

## Persona and Presentation

- Built-in and custom personas are managed from the same panel.
- Active mode switching and evil-mode switching are part of the same workflow.
- Multi-persona queueing can fan out triggered personas into queued follow-up jobs.
- Persona webhook identity can be enabled independently from queue execution.
- Custom personas support create, edit, preview, duplicate, and delete flows.
- Staff can generate inactive custom personas from member message history with `/persona impersonate`.
- Deleting the active custom persona falls back to `mode_default`.

Detailed reference:
- [feature-persona-manage.md](./feature-persona-manage.md)
- [feature-persona-impersonation.md](./feature-persona-impersonation.md)

## Security and Audit

- High-risk actions use risk-based auth instead of requiring auth for every change.
- Passwords create short-lived guild auth sessions.
- Secrets, destructive actions, staff-role changes, mod-log routing, and custom-persona deletion are authenticated paths.
- Guild config changes are written to normalized audit records with structured detail payloads.

Detailed reference: [feature-security-audit.md](./feature-security-audit.md)

## Transitional Commands

Older granular slash commands still exist as migration shims in several places. Where those remain, responses point admins back to `/config panel`, `/tools manage`, or `/persona manage`.

Detailed reference: [feature-transitional-commands.md](./feature-transitional-commands.md)

## Maintenance Notes

### Gemini-Backed Web Search Verification

- Refresh the Gemini grounding fixture with `python scripts/capture_gemini_grounding.py --output tests/fixtures/gemini_grounding_response.json` whenever the live response shape changes.
- The canonical fixture refresh command now refuses to overwrite `tests/fixtures/gemini_grounding_response.json` with synthetic sample data; without credentials, capture to a temporary path if you only need a local parser sample.
- Run the live contract test only when you want to verify the real provider path: set `RUN_LIVE_GEMINI_GROUNDING=1` and provide `GEMINI_API_KEY` or one of the numbered `GEMINI_API_KEY_1..10` values.
- The parser is expected to skip empty or malformed Gemini metadata, normalize usable grounding chunks into `title`/`url`/`snippet` records, and fall back to Brave or DuckDuckGo when Gemini does not return usable results.
- Use [`plans/2026-04-14-gemini-grounding-verification.md`](./plans/2026-04-14-gemini-grounding-verification.md) as the operator workflow for fixture refreshes, live checks, and Gemini triage.

## Source of Truth

The documentation in this directory is based on the live implementation in:

- `discord_bot/cogs/config.py`
- `discord_bot/cogs/tools_admin.py`
- `discord_bot/cogs/persona.py`
- `discord_bot/cogs/ai_brain.py`
- `discord_bot/utils/persona_panel_ui.py`
- `discord_bot/utils/config_panel_ui.py`
- `discord_bot/utils/admin_panel_logic.py`
- `discord_bot/utils/auth.py`
- `discord_bot/utils/db_handler.py`
- `discord_bot/utils/persona_queue.py`
- `discord_bot/utils/webhook_identity.py`
