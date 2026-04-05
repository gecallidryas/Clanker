# Command And Admin Surface Consolidation

**Date:** 2026-04-06

## Summary

This implementation consolidated the bot's public command surface so overlapping slash and prefix entrypoints were removed in favor of:

- a single `about` surface for bot info and stats
- `/persona manage` for persona and presentation administration
- `/autorole manage` for autorole administration
- normal chat with the bot for natural-language role/category/channel create and delete requests

## What Changed

### 1. Merged stats into `about`

`!stats` and `/stats` were removed. Runtime stats now appear inside `!about` and `/about`, including:

- uptime
- server count
- user count
- processed message count
- analyzed image count
- memory usage
- current guild mode

### 2. Added mode-aware slash thinking placeholders

Long-running slash commands no longer rely on the generic Discord thinking state alone. They now send a mode-aware placeholder such as:

- `Clanker is thinking...`
- `Femmy is thinking...`
- `Yumi is thinking...`
- `{custom persona name} is thinking...`

This applies to the affected long-running slash flows in utilities, memories, teach, and image generation.

### 3. Removed redundant mode and persona commands

The following were removed from the public command surface:

- `!mode`, `/mode`
- `!modes`, `/modes`
- `!currentmode`, `/currentmode`
- `/persona create`
- `/persona list`
- `/persona preview`

The intended replacements are:

- `/persona manage` for persona/presentation administration
- `about` for bot identity and runtime information

### 4. Simplified autorole management

The following were removed:

- `/autorole set`
- `/autorole clear`
- `/autorole view`

Autorole is now managed through:

- `/autorole manage`

### 5. Removed direct structure-management slash commands

The following slash commands were removed:

- `/manage create_category`
- `/manage create_text_channel`
- `/manage create_voice_channel`
- `/manage create_role`
- `/manage delete_category`
- `/manage delete_channel`
- `/manage delete_role`

These actions are now expected to be handled through the bot's existing normal-chat AI admin-action flow. Example requests:

- "create a text channel called announcements under Updates"
- "make a role called Event Ping"
- "delete the category old tickets"

## Files Updated

Primary code and docs touched during this work:

- `discord_bot/cogs/utilities.py`
- `discord_bot/cogs/social.py`
- `discord_bot/cogs/persona.py`
- `discord_bot/cogs/memories.py`
- `discord_bot/cogs/teach.py`
- `discord_bot/cogs/imagegen.py`
- `discord_bot/cogs/config.py`
- `discord_bot/cogs/ai_brain.py`
- `discord_bot/utils/interaction_status.py`
- `discord_bot/docs/slash-commands.md`

## Verification

The following checks were used while implementing this work:

```bash
python3 -m unittest tests.test_interaction_status
python3 -m unittest tests.test_persona_manage_create
python3 -m unittest tests.test_admin_surface_consolidation
python3 -m py_compile cogs/utilities.py cogs/social.py cogs/persona.py cogs/memories.py cogs/teach.py cogs/imagegen.py utils/interaction_status.py cogs/config.py cogs/ai_brain.py
```

## Notes

- This documentation summarizes implemented behavior, not just planned work.
- Detailed design and implementation plans still live under `docs/plans/`.
