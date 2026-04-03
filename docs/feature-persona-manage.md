# `/persona manage` Workflow Reference

## Purpose

`/persona manage` is the primary admin surface for presentation mode and custom persona lifecycle management.

Entry point:

- Command: `/persona manage`
- Handler: `discord_bot/cogs/persona.py`
- Launcher: `open_persona_manage_panel(...)` in `discord_bot/utils/persona_panel_ui.py`

## What It Covers

The panel unifies these workflows:

- built-in persona selection
- custom persona selection
- active persona activation
- evil-mode toggling
- persona previewing
- custom persona creation
- custom persona detail editing
- custom persona prompt editing
- persona duplication
- persona deletion with safe fallback

## Panel Workflow

1. Admin runs `/persona manage`.
2. The bot loads current state with `load_persona_panel_state(guild_id)`.
3. The state includes:
   - current active mode
   - current evil-mode state
   - built-in persona entries
   - guild custom persona entries
4. The bot renders a `PersonaManageView`.
5. The admin selects a persona and triggers an action with panel buttons.
6. The bot writes state changes to guild config or persona tables and records an audit event.

## State Model

The panel merges two persona sources:

- built-in personas from `modes/`
- custom personas from the guild database

Built-in persona metadata comes from:

- `modes.get_all_modes()`
- `modes.get_mode_profile()`

Custom persona metadata comes from:

- `get_guild_custom_personas(guild_id)`
- `get_custom_persona_by_mode_key(...)`
- `get_custom_persona_by_name(...)`

## Activation Workflow

### User Flow

1. Select a persona from the dropdown.
2. Click `Activate`.

### Implementation Flow

- UI action: `PersonaManageView.activate_selected()`
- Runtime setter: `activate_persona_mode(...)`
- Persistence:
  - `set_server_mode(guild_id, mode_key)`
  - sometimes `set_evil_mode(guild_id, False)` when falling back to default
  - `set_guild_avatar_path(guild_id, None)` when leaving a custom persona

The activation path also calls `_apply_social_profile(...)` so social or profile presentation is updated to match the selected mode.

Audit action:

- `persona_activate`

## Evil-Mode Workflow

### User Flow

1. Open `/persona manage`.
2. Click `Enable Evil` or `Disable Evil`.

### Implementation Flow

- UI action: `PersonaManageView.toggle_evil()`
- Runtime setter: `set_persona_evil_mode(...)`
- Persistence: `set_evil_mode(guild_id, enabled)`
- Follow-up: `_apply_social_profile(...)`

Important constraint:

- `mode_default` cannot stay in evil mode. The database layer forces evil mode off for the default mode.

Audit action:

- `persona_toggle_evil`

## Preview Workflow

Preview is read-only and returns an embed with:

- display name
- group
- mode key
- whether an evil prompt exists
- aliases when present

Implementation:

- UI action: `PersonaManageView.preview_selected()`
- Embed builder: `build_persona_preview_embed(...)`

## Custom Persona Creation Workflow

There are two creation paths in the repo:

- the main slash-command modal chain in `discord_bot/cogs/persona.py`
- the panel-side fallback modal in `discord_bot/utils/persona_panel_ui.py`

The current panel prefers the slash-command style flow by delegating to `Persona._open_basic_modal(...)` when the cog is available.

### Step-by-Step Flow

1. Admin clicks `Create` in the panel.
2. The panel calls the cog helper `_open_basic_modal(...)`.
3. Step 1 collects:
   - name
   - bio
   - avatar URL
   - banner URL
   - aliases
4. The cog validates:
   - name presence
   - slug safety
   - duplicate names
   - guild persona limit
   - rate limit
   - URL scheme
5. Step 2 collects the normal prompt.
6. Step 3 collects the evil prompt.
7. Final confirmation downloads assets, creates the persona row, extracts traits, and records creation.

### Key Constraints

- max personas per guild: `5`
- max creations per hour per user: `3`
- pending modal TTL: `300` seconds

### Persistence

Creation eventually calls:

- `create_custom_persona(...)`
- `upsert_persona_traits(...)`

Asset files are written into:

- `discord_bot/data/avatars/custom/`

## Custom Persona Edit Workflow

### Detail Editing

Detail editing updates:

- name
- bio
- aliases
- optional avatar and banner replacement

Panel path:

- `PersonaManageView.edit_details()`
- usually delegates to `Persona._open_edit_modal_by_mode_key(...)`

Cog path:

- staged edit state is stored in `PendingPersonaEdit`
- updated values are written with `update_custom_persona(...)`

### Prompt Editing

Prompt editing updates:

- `normal_prompt`
- `evil_prompt`

Implementation:

- panel modal: `PersonaPromptsModal`
- writer: `update_persona_prompts(...)`
- traits refresh: `upsert_persona_traits(...)`

## Duplicate Workflow

### User Flow

1. Select a custom persona.
2. Click `Duplicate`.
3. Choose a new name.

### Implementation Flow

- UI action: `PersonaManageView.duplicate_persona()`
- helper: `duplicate_custom_persona(...)`
- underlying operation: create a new persona using the source persona's bio, aliases, normal prompt, and evil prompt

Audit action:

- `persona_duplicate`

## Delete Workflow

### User Flow

1. Select a custom persona.
2. Click `Delete`.
3. Authenticate if required.
4. The persona is deleted and the panel refreshes.

### Implementation Flow

- UI action: `PersonaManageView.delete_persona()`
- auth prompt: `AuthPromptView`
- delete helper: `delete_persona_with_fallback(...)`

### Safe Fallback Behavior

If the deleted persona is currently active:

1. The bot switches the guild back to `mode_default`.
2. Evil mode is disabled.
3. Custom avatar state is cleared.
4. Social or profile presentation is refreshed.
5. The persona row is deleted.
6. Persona traits are deleted.
7. Persona avatar and banner files are removed from disk.

This is the implementation behind the feature statement that deleting the active custom persona should safely fall back to the default mode.

Audit actions involved:

- `persona_activate` for the fallback to default
- `persona_delete` for the destructive delete

## Multi-Persona Queue Runtime

The persona admin surface and AI runtime are coupled through guild config.

Relevant config fields in `server_config`:

- `ai_multi_persona_enabled`
- `ai_triggered_persona_limit`
- `ai_active_personas`
- `ai_persona_webhooks_enabled`

### Active Persona Storage

Active personas are stored as a JSON list in `ai_active_personas`.

Helpers:

- `get_active_persona_modes(guild_id)`
- `set_active_persona_modes(guild_id, mode_keys)`
- `sanitize_active_persona_modes(guild_id, mode_keys)`

The DB layer automatically removes invalid or deleted custom persona keys from this list and falls back to the current primary mode if the list becomes empty.

### Job Selection

When a message is processed in `discord_bot/cogs/ai_brain.py`:

1. The bot loads the primary mode.
2. The bot resolves the stored active persona list.
3. The bot resolves triggered persona mode keys from message content.
4. `_build_persona_jobs(...)` decides whether to fan out.

Behavior:

- If multi-persona is off, the bot runs only the primary mode.
- If multi-persona is on, the bot selects triggered personas that are also in the active persona list.
- Selection is capped by `ai_triggered_persona_limit`.

### Queue Execution

Extra persona jobs are stored as `PersonaInvocationJob` instances and queued by `PersonaQueueManager`.

Queue behavior:

- per-channel deque
- only one drain task per channel at a time
- queued jobs run sequentially after the primary reply

Implementation files:

- `discord_bot/cogs/ai_brain.py`
- `discord_bot/utils/persona_queue.py`

## Persona Webhook Identity Runtime

If `ai_persona_webhooks_enabled` is true, the AI runtime builds a webhook identity for the current persona before sending the reply.

Implementation:

- `build_persona_webhook_context(...)`
- `resolve_persona_webhook_identity(...)`
- `ChannelWebhookIdentityManager`

Behavior:

- built-in personas use the mode display name and built-in avatar assets
- evil mode switches to evil avatar variants when available
- custom personas use the custom persona name and stored avatar file
- webhooks are cached per channel
- thread replies target the parent webhook channel and pass the thread object back into send

This means webhook identity is presentation-only. It can be enabled or disabled independently from whether multi-persona queueing is active.

## Key Files

- `discord_bot/cogs/persona.py`
- `discord_bot/utils/persona_panel_ui.py`
- `discord_bot/cogs/ai_brain.py`
- `discord_bot/utils/persona_queue.py`
- `discord_bot/utils/webhook_identity.py`
- `discord_bot/utils/db_handler.py`
- `discord_bot/modes/registry.py`
