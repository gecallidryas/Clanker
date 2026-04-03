# Transitional Commands and Migration Shims

## Purpose

The current admin UX is moving toward three primary surfaces:

- `/config panel`
- `/tools manage`
- `/persona manage`

Older granular slash commands still exist in several places so existing admin habits do not break immediately. Those commands now act as migration shims or compatibility entry points.

## Migration Direction

The desired long-term pattern is:

- guild configuration goes through `/config panel`
- grouped tool flags go through `/tools manage`
- persona and presentation changes go through `/persona manage`

Legacy commands remain only where the repo still needs direct compatibility or operational one-off commands.

## Confirmed Shim Behavior in Current Code

### `/config ui`

Current behavior:

- command still exists
- it does not open a separate legacy panel
- it tells admins to use `/config panel`

Implementation:

- `discord_bot/cogs/config.py`
- `Config.config_ui()`

Response text:

- `/config ui` is now a legacy shortcut
- admins are redirected to `/config panel`

### Manage Aliases for Panel Sections

Several section-specific commands exist mainly to reopen the same panel section directly:

- `/autorole manage`
- `/welcome manage`
- `/staff manage`
- `/modlog manage`

These commands all route back into the same panel handlers used by `/config panel`.

Examples:

- `/autorole manage` -> `Config._send_autorole_panel(...)`
- `/welcome manage` -> `Config._send_welcome_panel(...)`
- `/staff manage` -> `Config._send_staff_panel(...)`
- `/modlog manage` -> `Config._send_modlog_panel(...)`

This means they are not separate configuration systems. They are compatibility entry points into the new Discord-native panel UX.

## Inline Migration Hints

Many granular commands now append a panel hint to their response.

This is handled by:

- `Config._manage_panel_hint(...)`

The helper appends text such as:

- use `/config panel`
- use `/welcome manage`
- use `/autorole manage`
- use `/staff manage`
- use `/modlog manage`

That hint appears in many existing direct command responses so admins are nudged toward the consolidated surface after a successful old-style command.

## Examples of Existing Granular Commands That Point Back to the Panel

The current config cog still includes direct commands for:

- URL safety edits
- autorole set/view/toggle
- welcome channel/message/toggle operations
- staff add/remove/list
- modlog set/clear/view

These commands still perform the write, but they also point admins back to the panel-based surface where possible.

Examples visible in `discord_bot/cogs/config.py`:

- autorole responses mention `/config panel` or `/autorole manage`
- welcome responses mention `/config panel` or `/welcome manage`
- staff list responses mention `/config panel` or `/staff manage`
- modlog view responses mention `/config panel` or `/modlog manage`
- URL safety responses mention `/config panel`

## `/tools manage` Versus Legacy Tool Commands

`/tools manage` is the preferred grouped flag editor, but the tools cog intentionally still keeps non-panel commands for:

- status
- inspect
- refresh
- policy
- debug capture
- quarantine
- MCP registration, discovery, and approval

Those are not legacy leftovers in the same way as old config toggles. They are separate because they are operational workflows, inspection paths, or privileged control-plane actions.

## `/persona manage` Versus Older Persona Commands

The persona cog still exposes direct commands such as:

- `/persona create`
- `/persona list`
- `/persona preview`
- `/persona edit`
- `/persona delete`

These remain useful as direct compatibility commands, but the code explicitly marks `/persona manage` as the primary admin surface.

You can see that in:

- `MANAGE_GUIDANCE = "Primary admin surface: \`/persona manage\`."`

That guidance is reused in create, edit, duplicate, activate, and delete responses so admins are gradually moved into the panel flow.

## Why Shims Still Exist

The remaining shims serve three practical needs:

- existing admins still remember older commands
- some commands are faster for one-off edits
- migration can happen without breaking established moderation and config workflows

The codebase is therefore in a hybrid state:

- one consolidated panel-first design
- a small compatibility layer that still works

## Key Files

- `discord_bot/cogs/config.py`
- `discord_bot/cogs/tools_admin.py`
- `discord_bot/cogs/persona.py`
- `discord_bot/utils/persona_panel_ui.py`
