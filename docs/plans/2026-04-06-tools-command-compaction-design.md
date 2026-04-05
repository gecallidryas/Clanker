# Tools Command Compaction Design

**Date:** 2026-04-06

**Goal:** Compact the `/tools` command tree so flag-style settings stay centered on `/tools manage`, while non-panel operations move into clear subgroups instead of remaining flat.

## Summary

The current `/tools` surface mixes three different kinds of actions:

- grouped flag toggles already handled by `/tools manage`
- read-only inspection commands such as `status` and `inspect`
- operational/admin controls such as refresh, quarantine, policy, debug, and MCP registration

That flat surface is harder to browse than it needs to be. The cleanup should preserve the existing tool-management capabilities while reorganizing them into a smaller, more legible command tree.

## Desired UX

### Keep `/tools manage` as the flag surface

`/tools manage` already covers grouped flag toggles for:

- search and RAG
- media tools
- memory/self-teaching

That should stay the primary place for enable/disable style tool settings.

### Move non-panel read-only commands under `/tools info`

These commands do not belong in the flag editor and should stay command-driven:

- `/tools info status`
- `/tools info inspect`

### Move context-reset actions under `/tools context`

These are operational actions rather than settings:

- `/tools context refresh`
- `/tools context clear-guild-recency`

### Keep existing admin subgroups grouped

The following areas are already grouped well enough and should remain grouped:

- `/tools policy ...`
- `/tools debug ...`
- `/tools quarantine ...`
- `/tools mcp ...`

## Architecture

### Command registration

Modify `discord_bot/cogs/tools_admin.py` to:

- add `info_group` and `context_group` as children of `tools_group`
- move the existing flat handlers into those subgroups
- keep the existing implementation bodies and permissions intact where possible

### Docs and help inventory

Update:

- `discord_bot/cogs/utilities.py`
- `discord_bot/docs/slash-commands.md`

So the public inventory matches the real `/tools` command tree.

## Risks

- Users accustomed to `/tools status` and `/tools refresh` may need docs/help updates in the same patch.
- Operational commands must keep the same permissions after regrouping.
- `/tools manage` should remain clearly distinct from `/tools info` and `/tools context`.

## Testing

Add tests that assert:

- `/tools manage` still exists at the root
- `status` and `inspect` no longer exist at the root and now live under `/tools info`
- `refresh` and `clear-guild-recency` no longer exist at the root and now live under `/tools context`
- existing grouped areas (`policy`, `debug`, `quarantine`, `mcp`) remain present
