# Starboard And DM Welcome Fixes

**Date:** 2026-04-06

## Summary

This implementation closed two behavior bugs in the Discord bot:

- starboard entries were being kept and updated even after reaction counts dropped below the configured threshold
- DM welcome messages were being sent as embeds instead of plain text messages

## What Changed

### 1. Fixed starboard threshold reconciliation

The starboard reconcile flow in `discord_bot/cogs/starboard.py` now removes an existing starboard post when the effective reaction count falls below the configured threshold.

Before this fix:

- new messages below threshold were skipped
- existing starboard entries below threshold were still edited and retained

After this fix:

- messages below threshold with no entry are still skipped
- messages below threshold with an existing entry have that starboard message deleted
- the corresponding starboard DB record is cleared

### 2. Changed DM welcome sends to plain text

The member-join DM welcome path in `discord_bot/cogs/social.py` now sends the configured DM welcome text as a normal message:

```python
await member.send(dm_text)
```

The previous embed wrapper with title, description, and footer was removed so the DM content now matches the stored staff-authored message directly.

## Files Updated

Primary files touched during this work:

- `discord_bot/cogs/starboard.py`
- `discord_bot/cogs/social.py`
- `tests/test_starboard_reaction_counting.py`
- `tests/test_starboard_settings_parsing.py`
- `tests/test_social_welcome_dm.py`

Supporting design note:

- `docs/plans/2026-04-05-dm-welcome-plain-text-design.md`

## Verification

The following checks were run while implementing these fixes:

```bash
pytest -q tests/test_starboard_reaction_counting.py tests/test_starboard_settings_parsing.py
pytest -q tests/test_social_welcome_dm.py tests/test_config_panel.py
```

## Notes

- The starboard fix is covered by a regression test that reproduces an existing entry dropping below threshold.
- The DM welcome fix is covered by a regression test that asserts `member.send()` is called with plain text rather than `embed=...`.
