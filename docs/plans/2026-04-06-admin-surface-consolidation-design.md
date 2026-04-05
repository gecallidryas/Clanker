# Admin Surface Consolidation Design

**Date:** 2026-04-06

**Goal:** Remove direct slash commands for autorole set/clear/view and server structure creation/deletion, keeping `/autorole manage` as the only autorole slash surface while relying on the existing chat-based AI admin-action flow for natural-language create/delete category, channel, and role requests.

## Summary

The bot currently exposes two overlapping admin surfaces:

- direct slash commands for autorole and server structure management in `cogs/config.py`
- natural-language admin actions in normal chat through `cogs/ai_brain.py`

This makes the UX noisy and encourages users to memorize command trees for actions the bot already knows how to perform conversationally. The cleanup should simplify the public admin surface:

- `/autorole manage` remains for autorole configuration
- direct `/autorole set`, `/autorole clear`, and `/autorole view` are removed
- the entire `/manage` create/delete slash group is removed
- normal chat becomes the supported path for “create/delete role/category/channel” requests

## Desired UX

### Autorole

Users manage autorole only through:

- `/autorole manage`

That panel should continue to support:

- picking a role
- disabling autorole
- viewing current state

The direct slash subcommands become redundant and should be hard-removed.

### Structure Management

Users should no longer use:

- `/manage create_category`
- `/manage create_text_channel`
- `/manage create_voice_channel`
- `/manage create_role`
- `/manage delete_category`
- `/manage delete_channel`
- `/manage delete_role`

Instead, they should say things like:

- “create a text channel called announcements under Updates”
- “make a role called Event Ping”
- “delete the category old tickets”

The existing AI admin-action / agentic path already supports these operations and destructive confirmations. The public docs and help text should steer users toward that path instead of slash commands.

## Architecture

### Public Surface

Remove the direct slash decorators and help inventory entries in `cogs/config.py`, `cogs/utilities.py`, and `docs/slash-commands.md`.

### Behavior Source Of Truth

Keep the natural-language implementation in `cogs/ai_brain.py` as the supported execution path for structure changes. If there is any slash-only behavior worth preserving, extract it into a small shared helper instead of maintaining duplicate command handlers.

### Confirmation And Permissions

Destructive operations should continue to require confirmation through the existing pending-action flow in `ai_brain.py`. Permission checks must remain the same or stricter than the removed slash commands.

## Cleanup Areas

- Remove redundant `/autorole set`, `/autorole clear`, and `/autorole view`
- Remove the `/manage` slash group entries for category/channel/role create/delete
- Update command inventories and docs
- Update AI help text so it describes normal-chat admin management instead of removed slash commands

## Risks

- Users may still expect the removed slash commands, so docs/help text need to change in the same patch.
- The AI path must stay clearly discoverable for structure management.
- Confirmation behavior for deletes must remain intact after the slash-command removal.

## Testing

Add or update tests to cover:

- `/autorole manage` still registered while set/clear/view are gone
- `/manage ...` structure commands are no longer registered
- AI help text and command docs no longer advertise the removed commands
