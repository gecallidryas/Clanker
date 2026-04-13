# `/persona impersonate` Workflow Reference

## Purpose

`/persona impersonate` lets staff generate an inactive custom persona from a real guild member's recent visible server messages.

Entry point:

- Command: `/persona impersonate member:@user name:<optional>`
- Handler: `discord_bot/cogs/persona.py`
- Helper pipeline: `discord_bot/utils/persona_impersonation.py`

This feature extends the existing custom persona system instead of introducing a separate runtime-only impersonation mode.

## What It Does

The command:

- requires `Manage Guild`
- scans up to `1000` visible messages from the target member across readable guild text channels
- filters low-signal messages before generation
- requires at least `100` usable messages after filtering
- sends a structured prompt through the guild `GEMINI_PROFILE_KEY` path
- generates persona fields and persona-local sample dialogue
- copies the target member avatar into custom persona assets when possible
- saves the result as a normal inactive custom persona
- does not activate the persona automatically

## Generated Persona Fields

The Gemini payload is parsed into:

- `bio`
- `aliases`
- `normal_prompt`
- `evil_prompt`
- `sample_dialogues`

The saved bio also gets a provenance note showing that it was generated from the target member's message history.

## Command Workflow

1. Staff member runs `/persona impersonate`.
2. The bot verifies the command is running in a guild.
3. The bot enforces `Manage Guild`.
4. The bot collects visible target-member messages from readable text channels.
5. The bot filters commands, duplicates, filler, empty content, and other low-signal lines.
6. The bot rejects the request if fewer than `100` usable messages remain.
7. The bot builds a style-analysis prompt and calls `generate_guild_gemini_profile_text(...)`.
8. The bot parses the returned JSON payload.
9. The bot resolves a collision-safe custom persona name.
10. The bot copies the target avatar into `data/avatars/custom/` if possible.
11. The bot saves the persona row and extracted persona traits.
12. The bot replies ephemerally with the saved persona name and counts.

## Storage Model

The generated persona is stored in the normal `custom_personas` table through `create_custom_persona(...)`.

Relevant fields:

- `name`
- `mode_key`
- `bio`
- `avatar_path`
- `normal_prompt`
- `evil_prompt`
- `aliases`
- `sample_dialogues_json`

`sample_dialogues_json` stores persona-local example lines so the impersonated persona does not overwrite guild-global `/teach sampledialogue` data.

## Prompt Builder Integration

When a custom persona is active, the AI prompt builder now checks that persona row first for `sample_dialogues_json`.

Behavior:

- if persona-local sample dialogue exists, the `SAMPLE DIALOGUES` prompt section uses it
- otherwise the prompt builder falls back to guild-global `get_sample_dialogues(...)`

This keeps impersonated speech examples attached to the specific custom persona that generated them.

## Name Collision Rules

The base persona name is:

- the optional `name` argument when supplied
- otherwise the target member display name

If that name already exists, the helper chooses:

- `Name (impersonated)`
- then `Name (impersonated 2)`
- and so on

The command should not fail solely because the initial display name collides.

## Failure Handling

Failure paths are ephemeral and do not claim success.

Handled cases:

- guild-only enforcement
- missing `Manage Guild`
- fewer than `100` usable messages
- missing `GEMINI_PROFILE_KEY`
- Gemini rejection or invalid JSON payload
- avatar copy failure with persona save fallback
- DB uniqueness failure during final save

## Key Files

- `discord_bot/cogs/persona.py`
- `discord_bot/cogs/ai_brain.py`
- `discord_bot/utils/persona_impersonation.py`
- `discord_bot/utils/db_handler.py`
- `discord_bot/tests/test_persona_impersonation_storage.py`
- `discord_bot/tests/test_persona_impersonation_helpers.py`
- `discord_bot/tests/test_persona_impersonate_command.py`
- `discord_bot/tests/test_persona_prompt_dialogues.py`
