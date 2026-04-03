# Security and Audit Workflow Reference

## Purpose

The current admin UX uses risk-based authentication and normalized audit logging instead of forcing a password prompt on every config change.

The security model lives across:

- `discord_bot/utils/admin_panel_logic.py`
- `discord_bot/utils/auth.py`
- `discord_bot/utils/db_handler.py`
- `discord_bot/utils/persona_panel_ui.py`
- `discord_bot/cogs/config.py`

## Core Model

There are three moving parts:

1. Action classification
2. Guild password and short-lived auth session
3. Structured audit logging

## Risk-Based Action Classification

Action policy is defined in `ACTION_POLICIES` inside `discord_bot/utils/admin_panel_logic.py`.

Each known action can declare:

- risk level
- audit category
- whether auth is required

Examples of auth-required actions in the current implementation:

- `provider_secret_update`
- `provider_endpoint_update`
- `staff_roles_update`
- `modlog_update`
- `clear_all`
- `persona_delete`

Examples of low-risk actions:

- `tools_manage_save`
- `capabilities_save`
- `ai_settings_save`
- `welcome_settings_save`
- `autorole_settings_save`
- `persona_activate`
- `persona_toggle_evil`

## Guild Password Workflow

### Storage

The guild password state is stored in:

- table: `guild_admin_auth`

Columns include:

- `guild_id`
- `password_hash`
- `created_by`
- `password_version`
- `last_used_at`

Passwords are hashed with `bcrypt` in `discord_bot/utils/auth.py`.

### Session Workflow

Successful password verification creates or refreshes a short-lived session in:

- table: `guild_auth_sessions`

Important implementation details:

- session lifetime: `15` minutes
- sessions are scoped by `(guild_id, user_id)`
- sessions are invalidated automatically if the password version changes

Main helpers:

- `has_password(guild_id)`
- `set_password(guild_id, password, user_id)`
- `verify_and_create_session(guild_id, user_id, password)`
- `is_authenticated(guild_id, user_id)`
- `clear_session(guild_id, user_id)`
- `cleanup_expired_sessions(guild_id)`

## How Auth Gates Are Applied

### Config Panel

`discord_bot/cogs/config.py` uses:

- `_auth_status(...)`
- `_ensure_action_auth(...)`
- `ConfigAction`

This allows low-risk panels to stay frictionless while prompting only when an action crosses into a protected path.

Examples:

- editing provider secrets requires auth
- editing custom endpoint secrets requires auth
- setting or clearing modlog requires auth
- staff role changes require auth

### Persona Panel

`discord_bot/utils/persona_panel_ui.py` uses:

- `action_requires_auth("persona_delete")`
- `AuthPromptView`

Only deletion is auth-gated. Activation, preview, evil-mode toggling, duplication, and normal editing are not.

### Additional Current Behavior

Although the feature summary calls out secrets, destructive actions, staff, and modlog as the main authenticated paths, the current config implementation also requires auth for URL safety action and pattern edits.

That behavior is enforced directly inside:

- `Config._save_url_safety_action()`
- `Config._save_url_safety_patterns()`
- `Config._clear_url_safety_patterns()`

## Audit Model

### Storage

All guild config and persona admin changes are written into:

- table: `guild_config_audit`

Columns:

- `guild_id`
- `user_id`
- `action`
- `category`
- `field`
- `target_type`
- `target_id`
- `old_value`
- `new_value`
- `summary`
- `detail_json`
- `created_at`

### Audit Categories

Normalized categories include:

- `config_general`
- `config_security`
- `config_routing`
- `config_destructive`
- `persona_presentation`
- `persona_crud`
- `tools_config`

Category normalization is handled by `normalize_audit_category(...)`.

Structured detail payloads are serialized by:

- `serialize_audit_detail(...)`
- `normalize_audit_detail(...)`

### Write Path

All audit entries are written through:

- `add_guild_config_audit(...)`

This function normalizes the category and stores structured JSON detail.

### Read Path

Audit entries are read through:

- `get_guild_config_audit_entries(guild_id, limit=100)`

Old rows without normalized categories are backfilled during schema migration and normalized again on read.

### Retention

Old audit rows can be pruned with:

- `cleanup_guild_audit(guild_id, max_age_days=90)`

## Tool Debug and Operational Audit

The repo also has a separate operational audit path for tool execution.

Global tables:

- `tool_execution_log`
- `tool_debug_capture`
- `tool_debug_capture_settings`

Main writer:

- `record_tool_execution(...)` in `discord_bot/tools/audit.py`

This is separate from `guild_config_audit` because it tracks runtime tool invocations rather than guild admin config changes.

## What the Model Optimizes For

The current design balances three goals:

- fast edits for low-risk admin work
- explicit re-auth for destructive or security-sensitive changes
- enough structured audit detail to explain what changed later

That is why the panel system does not ask for a password on every toggle, but still creates strong boundaries around secrets, destructive deletes, staff routing, and moderation routing.

## Key Files

- `discord_bot/utils/admin_panel_logic.py`
- `discord_bot/utils/auth.py`
- `discord_bot/utils/db_handler.py`
- `discord_bot/tools/audit.py`
- `discord_bot/cogs/config.py`
- `discord_bot/utils/persona_panel_ui.py`
