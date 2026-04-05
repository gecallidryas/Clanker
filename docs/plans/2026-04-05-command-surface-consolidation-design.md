# Command Surface Consolidation Design

**Date:** 2026-04-05

**Goal:** Remove redundant mode/persona/stats commands, fold stats into `about`, and make slash-command thinking placeholders reflect the active bot mode instead of the default bot identity.

## Summary

The bot currently exposes overlapping entrypoints for persona and mode management across prefix commands, slash commands, and the newer `/persona manage` panel. It also uses deferred slash responses that show Discord's default bot identity while commands are processing, which clashes with the active guild persona when the bot is operating as Femmy, Yumi, or a custom persona.

This change consolidates the user-facing command surface around:

- `about` for both identity and runtime stats
- `/persona manage` for persona and presentation administration
- explicit mode-aware placeholder responses for long-running slash commands

## Command Changes

### Keep

- `!about` and `/about`
- `!evil` and `/evil`
- `/persona manage`
- `/persona edit`
- `/persona delete`

### Remove

- `!stats` and `/stats`
- `!currentmode` and `/currentmode`
- `!mode` and `/mode`
- `!modes` and `/modes`
- `/persona create`
- `/persona list`
- `/persona preview`

## About And Stats Consolidation

`about` will become the single information surface for:

- active mode identity and bio
- feature summary
- uptime
- server count
- user count
- processed message count
- analyzed image count
- memory usage
- current guild mode

The old stats embed builder logic should be reused instead of duplicated so prefix and slash variants stay aligned.

## Mode-Aware Thinking Placeholder

Discord's deferred slash "thinking" state is not mode-aware. For commands that currently call `interaction.response.defer(thinking=True)`, the bot should send an immediate placeholder message like `"Yumi is thinking..."` or `"Femmy is thinking..."`, then edit that original response into the final embed or content.

The display name should resolve as:

- `Clanker` for `mode_default`
- `Femmy` for `mode_femboy` and `mode_tsundere`
- `Yumi` for `mode_oneesan`
- custom persona name for `custom_*` modes

This helper should support both normal and ephemeral slash responses so other cogs can reuse it.

## Persona And Mode Consolidation

The new admin flow already lives under `/persona manage`, so the older slash entrypoints should be removed completely rather than kept as deprecation shims. Any reusable creation/edit helpers should stay on the Persona cog so the manage panel remains the single entry surface without losing existing modal logic.

Where text still says "run `/persona create` again", update it to point users back to `/persona manage`.

## Testing

Add focused tests around:

- mode display-name resolution for built-in and custom personas
- the consolidated about embed containing runtime stats
- manage-panel actions continuing to reuse the Persona cog modal helpers after legacy slash subcommands are removed

## Risks

- Removing commands can break habits for existing users, so docs/help text must be updated in the same change.
- Replacing deferred responses with editable placeholder messages must preserve ephemeral behavior and followup semantics.
- The social cog currently contains duplicate `/mode` slash registration; cleanup should remove that duplication rather than carrying it forward.
