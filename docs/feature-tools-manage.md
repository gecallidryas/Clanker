# `/tools manage` Workflow Reference

## Purpose

`/tools manage` is the primary bulk tool-capability surface. It exists to flip grouped capability flags quickly without mixing those changes with operational commands like `/tools refresh`.

Entry point:

- Command: `/tools manage`
- Handler: `discord_bot/cogs/tools_admin.py`
- Command method: `ToolsAdmin.tools_manage_command()`

## What `/tools manage` Actually Does

The panel edits grouped feature flags only. It does not directly:

- clear short-term memory
- change tool policy rules
- manage raw debug capture
- clear quarantine
- register or approve MCP servers/tools

Those stay as separate `/tools ...` subcommands because they are operational or security-sensitive workflows, not simple persistent configuration.

## Tool Groups

The main groups are defined in `TOOL_GROUPS` inside `discord_bot/cogs/tools_admin.py`:

- `ai_tools`
- `discovery`
- `media`
- `memory`

Each group maps to one or more guild config flags such as:

- `web_search_enabled`
- `rag_enabled`
- `image_gen_enabled`
- `gif_responses_enabled`
- `youtube_enabled`
- `profile_peek_enabled`
- `sticker_usage_enabled`
- `emoji_usage_enabled`
- `pin_message_enabled`
- `self_teaching_enabled`

## User Workflow

1. Admin runs `/tools manage`.
2. The bot reads guild config with `get_guild_config(guild_id)`.
3. The bot renders an overview embed showing group coverage and enabled counts.
4. The admin selects a group from an `ActionMenuView`.
5. The bot opens a `FeatureGroupView` for that group.
6. The admin selects one or more flags and clicks `Enable Selected` or `Disable Selected`.
7. The bot computes a diff, persists only changed values, and writes an audit entry.

## Implementation Flow

### Panel Opening

- Overview builder: `ToolsAdmin._overview_embed()`
- Selector UI: `ActionMenuView`
- Group opener: `ToolsAdmin._send_feature_group_panel()`

### Group Editing

- Options builder: `ToolsAdmin._feature_options()`
- Group embed builder: `ToolsAdmin._group_embed()`
- Save path: `ToolsAdmin._apply_group_changes()`
- Change diffing: `diff_toggle_states(...)`

### Persistence

Changed values are written through:

- `update_guild_config(guild_id, proposed)`

Audit is written through:

- `add_guild_config_audit(...)`
- action name: `tools_manage_save`
- category: `tools_config`

## Relationship to Runtime Tool Availability

The panel does not decide tool use by itself. It sets config flags that feed later runtime evaluation.

The runtime decision path is:

1. Guild flags are loaded from `server_config`.
2. A `ToolTurnContext` is built.
3. `compute_tool_availability_decisions(...)` evaluates the current turn.
4. Policy rules, quarantine state, discovery state, and config flags all contribute to the final allowed or denied result.

You can see that status path in:

- `ToolsAdmin.tools_status()`
- `ToolsAdmin.tools_inspect()`

## Why `/tools refresh` Is Separate

`/tools refresh` is intentionally not part of the bulk panel.

Behavior:

- clears short-term channel memory
- sets a new prompt boundary marker
- is treated as an operational reset

Implementation:

- Command: `ToolsAdmin.tools_refresh()`
- AI integration: `AIBrain.clear_channel_memory_boundary(...)`

That separation matches the feature spec in `docs/FEATURES.md`: management is configuration, refresh is operational.

## Adjacent Advanced Tool Workflows

These are part of the broader tools admin surface, but not part of `/tools manage` itself.

### Policy

Commands under `/tools policy` let admins allow or deny categories or specific tools.

Relevant methods:

- `tools_policy_set_category`
- `tools_policy_clear_category`
- `tools_policy_set_tool`
- `tools_policy_clear_tool`

### Debug Capture

Commands under `/tools debug` let admins temporarily enable raw capture of tool args and results for debugging.

Relevant methods:

- `tools_debug_raw_capture_status`
- `tools_debug_raw_capture_enable`
- `tools_debug_raw_capture_disable`

Persistence is handled by the global tables:

- `tool_debug_capture`
- `tool_debug_capture_settings`

### Quarantine

Commands under `/tools quarantine` inspect and clear failure-driven quarantine state.

Relevant methods:

- `tools_quarantine_status`
- `tools_quarantine_clear`

Persistence is handled by:

- `tool_quarantine_policy`
- `tool_quarantine_state`

### MCP Registration and Approval

Commands under `/tools mcp` manage MCP server registration, discovery, health, and approval.

Relevant methods include:

- `tools_mcp_list_registrations`
- `tools_mcp_health`
- `tools_mcp_list_tools`
- `tools_mcp_register_global`
- `tools_mcp_register_guild`
- `tools_mcp_discover_global`
- `tools_mcp_discover_guild`
- `tools_mcp_approve_global`
- `tools_mcp_approve_guild`

Persistence is handled by global tables:

- `mcp_server_registrations`
- `mcp_discovered_tools`
- `mcp_server_health`

## Key Files

- `discord_bot/cogs/tools_admin.py`
- `discord_bot/utils/config_panel_ui.py`
- `discord_bot/tools/availability.py`
- `discord_bot/tools/policy_engine.py`
- `discord_bot/tools/quarantine.py`
- `discord_bot/tools/audit.py`
- `discord_bot/tools/mcp/control_plane.py`
- `discord_bot/utils/db_handler.py`
