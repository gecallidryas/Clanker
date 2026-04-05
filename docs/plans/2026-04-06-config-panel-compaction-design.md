# Config Panel Compaction Design

**Date:** 2026-04-06

**Goal:** Compact the noisy `/config` slash-command surface so high-volume settings areas route through the Discord-native config panel, while preserving a small set of subgroup entry commands that open the relevant panel section.

## Summary

The bot currently exposes a large number of direct `/config` mutator and view commands even though `discord_bot/cogs/config.py` already contains panel-based UX for AI settings, capability toggles, URL safety, provider keys and models, and custom endpoint configuration. That duplication makes the command tree hard to browse and increases doc maintenance.

This cleanup should keep the config panel as the primary admin surface while preserving discoverability through compact subgroup entry commands. The desired pattern is:

- `/config panel` stays as the main entrypoint
- `/config ai manage` opens the AI panel
- `/config toggle manage` opens the capability toggle panel
- `/config url_safety manage` opens the URL safety panel
- `/config custom_endpoint manage` opens the provider/model panel focused on endpoint-related work
- `/config keys manage` opens the provider/model panel
- `/config model manage` opens the provider/model panel
- `/config auth`, `/config password *`, and `/config env *` remain as direct setup/auth flows

Existing top-level groups that are already compact should stay as-is:

- `/autorole manage`
- `/welcome manage`
- `/staff manage`
- `/modlog manage`

## Desired UX

### Panel-first configuration

Admins should stop memorizing one-off commands such as:

- `/config ai cooldown`
- `/config ai thought_level`
- `/config toggle web_search`
- `/config url_safety allowlist`
- `/config custom_endpoint set`
- `/config model view`

Instead, they should use the relevant compact entry command and complete the edit inside the panel or modal flow it opens.

### Discoverability without clutter

Subgroups should remain visible in Discord so admins can still browse:

- `/config ai`
- `/config toggle`
- `/config url_safety`
- `/config custom_endpoint`
- `/config keys`
- `/config model`

But each should expose only `manage`, which routes to the existing panel section rather than duplicating the edit logic in slash handlers.

## Architecture

### Command registration

Trim the decorators in `discord_bot/cogs/config.py` so the command tree only exposes the compact `manage` entry commands for the targeted `/config` subgroups. Reuse the existing panel helpers:

- `_send_ai_panel(...)`
- `_send_capabilities_panel(...)`
- `_send_url_safety_panel(...)`
- `_send_provider_panel(...)`

This avoids maintaining two separate admin UX paths for the same stored settings.

### Provider grouping

Keys, models, and custom endpoint configuration already live together conceptually and in the provider panel. The direct subgroup entry commands should therefore route to the same provider panel rather than creating separate duplicate flows.

### Documentation source of truth

The slash command inventory in `discord_bot/docs/slash-commands.md` should match the registered command tree exactly. New docs under `discord_bot/docs/guide/` should explain:

- how to use the config panel
- what each setting does
- where each feature lives in code

## Risks

- Discord users who rely on direct `/config` mutators may be surprised if docs/help are not updated in the same patch.
- The panel entry commands must still feel discoverable after granular commands are removed.
- Feature docs need to reflect the real implementation, not stale command names.

## Testing

Add or update tests to cover:

- only `manage` is exposed for the compacted `/config` subgroup trees
- `/config panel`, `/config auth`, `/config password *`, and `/config env *` remain available
- existing compact top-level manage groups still behave as expected

Verification should also include a docs sanity check so removed commands no longer appear in the slash-command guide.
