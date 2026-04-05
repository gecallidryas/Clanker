# Welcome Petpet Tasks 1-4

**Date:** 2026-04-06

## Summary

This checkpoint completes Tasks 1 through 4 of the welcome petpet plan and stops before any welcome-send integration behavior. The worktree now supports the `@user` template alias, contains a local petpet GIF renderer and hand assets, persists the `dm_welcome_petpet_enabled` guild setting, and exposes the DM petpet toggle in the welcome config panel.

## What Changed

### Task 1: Welcome template alias

- `discord_bot/cogs/social.py`
- `tests/test_social_welcome_dm.py`

`Social._apply_welcome_template(...)` now treats literal `@user` as an alias for `member.mention`. Focused tests cover the new alias and confirm the existing `{member}`, `{member_name}`, `{member_count}`, `{member_ordinal}`, and `{guild}` placeholders still render correctly.

### Task 2: Petpet renderer

- `discord_bot/utils/petpet.py`
- `discord_bot/assets/petpet/frame_0_delay-0.06s.gif`
- `discord_bot/assets/petpet/frame_1_delay-0.06s.gif`
- `discord_bot/assets/petpet/frame_2_delay-0.06s.gif`
- `discord_bot/assets/petpet/frame_3_delay-0.06s.gif`
- `discord_bot/assets/petpet/frame_4_delay-0.06s.gif`
- `discord_bot/assets/petpet/petpet-generator-hand-strokes-the-void.gif`
- `tests/test_petpet.py`

Added a deterministic Pillow-based petpet pipeline with:

- `prepare_image(source)`
- `load_hand_frames()`
- `render_petpet_frames(base_image, hand_frames)`
- `save_gif(frames)`
- `make_petpet(source)`

The renderer uses a fixed square crop, a fixed canvas size, and a five-frame squish/recover motion. It now loads the real hand-frame GIF assets supplied in `E:\femboibot\PETTING hand frames and base gif` and stores them under `discord_bot/assets/petpet` inside the worktree. Tests verify it accepts in-memory image bytes, returns non-empty GIF bytes, and produces multiple frames.

### Task 3: Guild config support

- `discord_bot/utils/db_handler.py`
- `tests/test_social_welcome_dm.py`

Added `dm_welcome_petpet_enabled` to the guild config schema and helper layer. `get_welcome_config(...)` now returns both `dm_welcome_enabled` and `dm_welcome_petpet_enabled`, defaulting missing values to `False`. Added getter/setter helpers for the new flag.

### Task 4: Welcome panel toggle

- `discord_bot/cogs/config.py`
- `tests/test_config_panel.py`

The welcome panel now shows a `DM petpet` status field and offers a `Toggle DM Petpet` action. The new modal persists the flag through the DB helper and confirms the new state in the response.

## Verification

Commands run in this worktree:

```bash
python -m unittest tests.test_social_welcome_dm -v
python -m unittest tests.test_petpet tests.test_social_welcome_dm.SocialWelcomeDmTests.test_get_welcome_config_defaults_dm_petpet_off tests.test_config_panel.PanelViewTests.test_welcome_manage_opens_panel tests.test_config_panel.PanelViewTests.test_welcome_dm_petpet_toggle_updates_setting -v
python -m py_compile discord_bot/cogs/social.py tests/test_social_welcome_dm.py
python -m py_compile discord_bot/utils/petpet.py discord_bot/utils/db_handler.py discord_bot/cogs/config.py tests/test_petpet.py tests/test_social_welcome_dm.py tests/test_config_panel.py
```

Results:

- all listed targeted unittest commands passed
- all listed `py_compile` commands passed

## Notes

- Work stopped intentionally after Task 4.
- Tasks 5 through 7 remain untouched in this checkpoint.
- A broader `tests.test_config_panel` run still has an unrelated baseline failure around `Config.autorole_view` in this branch, so verification stayed focused on the Tasks 1-4 slice.
