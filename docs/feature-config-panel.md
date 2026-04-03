# `/config panel` Workflow Reference

## Purpose

`/config panel` is the primary Discord-native admin surface for server configuration. It consolidates the most important guild settings into one entry point instead of forcing admins to remember many granular slash commands.

Entry point:

- Command: `/config panel`
- Handler: `discord_bot/cogs/config.py`
- Main launcher: `Config.config_panel()` -> `Config._open_config_panel()`

## What It Covers

The panel routes admins into these sections:

- Capabilities
- AI Settings
- Providers
- Welcome
- Autorole
- URL Safety
- Modlog
- Staff

The section dispatch is handled by `Config._handle_config_panel_action()` in `discord_bot/cogs/config.py`.

## High-Level Workflow

1. Admin runs `/config panel`.
2. The bot loads current guild config with `get_guild_config(guild_id)`.
3. The bot renders an ephemeral `ActionMenuView`.
4. The selected section opens a second panel or modal.
5. The chosen action writes updates through `update_guild_config(...)` or a focused helper such as `set_welcome_channel_id(...)`.
6. The bot records the change with `add_guild_config_audit(...)`.

All panel responses are ephemeral and invoker-locked through the admin view helpers, so only the original admin can keep using the open panel.

## Capabilities Workflow

### User Flow

1. Open `/config panel`.
2. Choose `Capabilities`.
3. Choose a feature group such as AI tools, expression/media, memory/learning, or conversation.
4. Select one or more flags.
5. Enable or disable the selected flags in bulk.

### Implementation Flow

- Launcher: `Config._send_capabilities_panel()`
- Group panel: `Config._send_feature_group_panel()`
- UI: `ActionMenuView` and `FeatureGroupView` in `discord_bot/utils/config_panel_ui.py`
- Persistence: `update_guild_config(...)`
- Diffing: `diff_toggle_states(...)` in `discord_bot/utils/admin_panel_logic.py`
- Audit action: `capabilities_save`

The config panel groups are backed by `FEATURE_GROUPS` and `CONFIG_TOGGLE_OPTIONS` in `discord_bot/cogs/config.py`.

## AI Settings Workflow

### User Flow

From `AI Settings`, admins can edit:

- Reply policy
- Streaming controls
- AI channel whitelist
- AI auto channels
- Thought/debug logs

The current AI settings summary also displays persona runtime state:

- `ai_multi_persona_enabled`
- `ai_triggered_persona_limit`
- `ai_persona_webhooks_enabled`

Important implementation note:

- these fields are stored in guild config and consumed by the AI runtime
- they appear in the AI settings summaries and in `/config ai view`
- the current `AI Settings` action menu does not expose a dedicated editor for them

### Reply Policy

The reply policy modal updates:

- `ai_reply_cooldown_seconds`
- `ai_reply_cooldown_type`
- `ai_self_reply_limit`
- `ai_auto_threshold`

This is saved in `Config._save_ai_reply_policy()` and audited as `ai_settings_save`.

### Streaming

The streaming modal updates:

- `ai_streaming_enabled`
- `ai_stream_min_flush_chars`
- `ai_stream_stall_seconds`
- `ai_stream_min_interval_seconds`
- `ai_stream_max_total_chars`

This is saved in `Config._save_ai_streaming_settings()` and audited as `ai_settings_save`.

### Channel Whitelist and Auto Channels

These panels use bulk list editing instead of separate add/remove commands.

Implementation pieces:

- Panel builder: `Config._send_ai_channel_list_panel()`
- List editing UI: `ChannelListEditorView`
- Reconciliation helper: `reconcile_id_lists(...)`
- Config fields:
  - `ai_channel_whitelist`
  - `ai_auto_channels`

### Thought and Debug Logs

This flow manages:

- `ai_thought_log_level`
- `ai_thought_log_allow_mod_log`
- `ai_thought_channel_id`

Implementation pieces:

- Panel builder: `Config._send_ai_thought_logs_panel()`
- Modal save: `Config._save_ai_thought_logs()`
- Channel selection: `Config._set_thought_channel()`

### Runtime Meaning

These settings are consumed by the AI runtime in `discord_bot/cogs/ai_brain.py` to decide:

- whether the bot should answer
- how cooldown is enforced
- how much self-reply chaining is allowed
- whether streaming is active
- where thought/debug output is routed

Separate persona-runtime fields also affect:

- multi-persona queue fanout
- triggered persona job limit
- webhook identity sending

## Provider and Model Workflow

### User Flow

From `Providers`, admins can:

- edit provider secrets
- edit text model routing
- edit media provider settings
- edit a custom OpenAI-compatible endpoint

### Implementation Flow

- Panel builder: `Config._send_provider_panel()`
- Secret modal: `Config._build_provider_secret_modal()`
- Model modal: `Config._build_provider_model_modal()`
- Media modal: `Config._build_media_provider_modal()`
- Endpoint modal: `Config._build_custom_endpoint_modal()`

Persisted fields include:

- `gemini_api_key`
- `openrouter_api_key`
- `brave_api_key`
- `replicate_api_key`
- `tenor_api_key`
- `gemini_model`
- `gemini_translate_model`
- `gemini_summarize_model`
- `openrouter_model`
- `openrouter_fallback_models`
- `image_provider`
- `image_model`
- `tenor_client_key`
- `custom_endpoint_url`
- `custom_model_name`
- `custom_model_capabilities`
- `custom_endpoint_enabled`
- `custom_endpoint_api_key`

Secrets are encrypted before storage and masked in the panel summary. Auth is required for secret and custom-endpoint edits.

## Welcome Workflow

### User Flow

From `Welcome`, admins can:

- set the welcome channel
- disable welcomes
- edit the welcome template
- edit the DM welcome message
- toggle DM welcomes

### Implementation Flow

- Panel builder: `Config._send_welcome_panel()`
- Channel setter: `Config._set_welcome_channel()`
- Message save: `Config._save_welcome_messages()`
- DM toggle save: `Config._save_dm_welcome_toggle()`

Persisted fields:

- `welcome_channel_id`
- `welcome_enabled`
- `welcome_message_template`
- `dm_welcome_message`
- `dm_welcome_enabled`

All writes are audited as `welcome_settings_save`.

## Autorole Workflow

### User Flow

From `Autorole`, admins can:

- select the role granted on join
- disable autorole entirely

### Implementation Flow

- Panel builder: `Config._send_autorole_panel()`
- Role picker: `SingleRolePickerView`
- Save path: `Config._set_autorole()`

Persisted fields:

- `autorole_id`
- `autorole_enabled`

All writes are audited as `autorole_settings_save`.

## URL Safety Workflow

### User Flow

From `URL Safety`, admins can:

- choose `warn` or `delete`
- replace the allowlist
- replace the blocklist
- clear the allowlist
- clear the blocklist

### Implementation Flow

- Panel builder: `Config._send_url_safety_panel()`
- Action save: `Config._save_url_safety_action()`
- Pattern save: `Config._save_url_safety_patterns()`
- Pattern clear: `Config._clear_url_safety_patterns()`

Persisted fields:

- `url_safety_action`
- `url_allowlist`
- `url_blocklist`

Important implementation note:

- The panel footer says URL safety is toggled from `Capabilities > Conversation.`
- The actual moderation behavior is configured here.
- Current code requires config-password auth for editing the action or regex lists.

## Modlog Workflow

### User Flow

From `Modlog`, admins can:

- set the moderation log channel
- disable moderation logs

### Implementation Flow

- Panel builder: `Config._send_modlog_panel()`
- Channel setter: `Config._set_modlog_channel()`
- Disable path: `Config._handle_modlog_action()`
- Persistence helper: `set_mod_log_channel_id(...)`

Persisted field:

- `mod_log_channel_id`

This is treated as a high-risk action and uses risk-based auth.

## Staff Workflow

### User Flow

From `Staff`, admins can:

- add a level-1 mod role
- add a level-2 admin role
- remove configured staff roles
- clear all staff roles through the paginated editor

### Implementation Flow

- Panel builder: `Config._send_staff_panel()`
- Add path: `Config._add_staff_role_from_panel()`
- Remove path: `Config._remove_staff_roles_from_panel()`
- Clear path: `Config._clear_staff_roles_from_panel()`
- Persistence table: `staff_roles`

Staff updates are audited as `staff_roles_update` and require auth on write paths.

## Data Model

Most panel state is stored in the guild-local `server_config` table created in `discord_bot/utils/db_handler.py`.

Related auth and audit tables:

- `guild_admin_auth`
- `guild_auth_sessions`
- `guild_config_audit`
- `staff_roles`

## Key Files

- `discord_bot/cogs/config.py`
- `discord_bot/utils/config_panel_ui.py`
- `discord_bot/utils/admin_panel_logic.py`
- `discord_bot/utils/admin_views.py`
- `discord_bot/utils/auth.py`
- `discord_bot/utils/db_handler.py`
