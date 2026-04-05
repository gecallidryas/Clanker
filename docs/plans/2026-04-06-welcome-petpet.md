# Welcome Petpet Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Add `@user` mention support in welcome templates, attach a generated petpet GIF to public welcomes, and make DM petpet attachments optional per guild.

**Architecture:** Keep guild join orchestration in `discord_bot/cogs/social.py`, move GIF generation into a dedicated `discord_bot/utils/petpet.py` utility, and extend the existing welcome config helpers and panel with one new boolean flag for DM petpet attachments. Public welcome sends should always try to attach the generated GIF; DM sends should reuse the same renderer only when the DM petpet toggle is enabled.

**Tech Stack:** Python 3.12, discord.py, Pillow, unittest, markdown docs

---

### Task 1: Lock template rendering semantics with tests

**Files:**
- Modify: `tests/test_social_welcome_dm.py`

**Step 1: Write the failing tests**

Add focused tests for `Social._apply_welcome_template(...)` that assert:

- `@user welcome to the batcave!` renders with `member.mention`
- existing placeholders such as `{member}`, `{member_name}`, `{member_count}`, `{member_ordinal}`, and `{guild}` still render correctly

**Step 2: Run test to verify it fails**

Run: `python -m unittest tests.test_social_welcome_dm -v`
Expected: FAIL because `@user` is currently left as plain text.

**Step 3: Write minimal implementation**

Modify `discord_bot/cogs/social.py` so `_apply_welcome_template(...)` replaces `@user` with `member.mention` alongside the existing placeholder replacements.

**Step 4: Run test to verify it passes**

Run: `python -m unittest tests.test_social_welcome_dm -v`
Expected: the new template-rendering assertions PASS.

### Task 2: Add the petpet renderer behind isolated tests

**Files:**
- Create: `discord_bot/utils/petpet.py`
- Create: `discord_bot/assets/petpet/hand_0.png`
- Create: `discord_bot/assets/petpet/hand_1.png`
- Create: `discord_bot/assets/petpet/hand_2.png`
- Create: `discord_bot/assets/petpet/hand_3.png`
- Create: `discord_bot/assets/petpet/hand_4.png`
- Create: `tests/test_petpet.py`

**Step 1: Write the failing tests**

Add tests that:

- pass arbitrary image bytes into `make_petpet(...)`
- assert the result is non-empty bytes
- assert the output opens as a GIF with multiple frames

Keep fixtures in-memory with Pillow-generated images instead of relying on checked-in avatar files.

**Step 2: Run test to verify it fails**

Run: `python -m unittest tests.test_petpet -v`
Expected: FAIL because the module and renderer do not exist yet.

**Step 3: Write minimal implementation**

Implement:

- `prepare_image(source)` to open bytes, convert to RGBA, center-crop to square, and resize to a fixed working size
- `load_hand_frames()` to load bundled transparent hand overlays from disk
- `render_petpet_frames(base_image, hand_frames)` with a hardcoded 5-frame table
- `save_gif(frames)` to export an animated GIF with short frame durations
- `make_petpet(source)` to orchestrate the full pipeline

Use a fixed canvas size and a simple squish/recover frame sequence.

**Step 4: Run test to verify it passes**

Run: `python -m unittest tests.test_petpet -v`
Expected: PASS.

### Task 3: Extend guild config for optional DM petpet attachments

**Files:**
- Modify: `discord_bot/utils/db_handler.py`
- Modify: `tests/test_config_panel.py`
- Modify: `tests/test_social_welcome_dm.py`

**Step 1: Write the failing tests**

Add tests that assert:

- `get_welcome_config(...)` includes a `dm_welcome_petpet_enabled` key defaulting to `False`
- the welcome panel reflects the new toggle state
- DM welcome logic only attempts petpet attachment when the toggle is enabled

**Step 2: Run test to verify it fails**

Run: `python -m unittest tests.test_config_panel tests.test_social_welcome_dm -v`
Expected: FAIL because the new config key and behavior do not exist.

**Step 3: Write minimal implementation**

In `discord_bot/utils/db_handler.py`:

- include `dm_welcome_enabled` and `dm_welcome_petpet_enabled` in `get_welcome_config(...)`
- add `get_dm_welcome_petpet_enabled(...)`
- add `set_dm_welcome_petpet_enabled(...)`

Keep missing values backward-compatible by defaulting to `False`.

**Step 4: Run test to verify it passes**

Run: `python -m unittest tests.test_config_panel tests.test_social_welcome_dm -v`
Expected: config-related assertions PASS, with social tests still failing on public attachment behavior until later tasks.

### Task 4: Wire the new toggle into the welcome admin surface

**Files:**
- Modify: `discord_bot/cogs/config.py`
- Modify: `tests/test_config_panel.py`

**Step 1: Write the failing tests**

Add tests that assert:

- the welcome panel shows a DM petpet status field
- a new panel action or toggle path updates `dm_welcome_petpet_enabled`
- slash or panel responses confirm the toggle change

Prefer reusing the existing modal/toggle pattern rather than inventing a new admin surface.

**Step 2: Run test to verify it fails**

Run: `python -m unittest tests.test_config_panel -v`
Expected: FAIL because the panel does not expose the DM petpet flag yet.

**Step 3: Write minimal implementation**

Modify `discord_bot/cogs/config.py` to:

- display the DM petpet state in `_send_welcome_panel(...)`
- add one welcome action for toggling DM petpet
- persist changes through the new DB helper
- audit the config update like the other welcome settings

**Step 4: Run test to verify it passes**

Run: `python -m unittest tests.test_config_panel -v`
Expected: PASS.

### Task 5: Add public welcome petpet attachment behavior

**Files:**
- Modify: `discord_bot/cogs/social.py`
- Modify: `tests/test_social_welcome_dm.py`

**Step 1: Write the failing tests**

Add tests that assert:

- public welcome channel sends include both rendered text and a file attachment
- the attachment path is skipped gracefully when petpet generation fails
- `allowed_mentions` still only permits user mentions

Use a fake channel object with `send = AsyncMock()` and patch the petpet/avatar helpers.

**Step 2: Run test to verify it fails**

Run: `python -m unittest tests.test_social_welcome_dm -v`
Expected: FAIL because public welcome sends currently pass only content.

**Step 3: Write minimal implementation**

In `discord_bot/cogs/social.py`:

- fetch the joining member avatar bytes once
- call `make_petpet(...)`
- wrap GIF bytes in `discord.File`
- include the file in the public `channel.send(...)`
- fall back to text-only send if avatar download or GIF generation fails

Keep existing AI/template welcome text behavior intact.

**Step 4: Run test to verify it passes**

Run: `python -m unittest tests.test_social_welcome_dm -v`
Expected: PASS.

### Task 6: Add optional DM petpet attachment behavior

**Files:**
- Modify: `discord_bot/cogs/social.py`
- Modify: `tests/test_social_welcome_dm.py`

**Step 1: Write the failing tests**

Add tests that assert:

- DM welcome sends text only by default
- when `dm_welcome_petpet_enabled` is true, the DM send includes the generated petpet file
- if petpet generation fails, DM welcome still sends the text message

**Step 2: Run test to verify it fails**

Run: `python -m unittest tests.test_social_welcome_dm -v`
Expected: FAIL because DMs do not yet consider the petpet toggle.

**Step 3: Write minimal implementation**

Extend the DM branch in `discord_bot/cogs/social.py` to:

- check `get_dm_welcome_petpet_enabled(...)`
- reuse the same avatar bytes / GIF bytes when already available, or lazily generate if needed
- call `member.send(dm_text, file=discord.File(...))` only when the toggle is enabled

**Step 4: Run test to verify it passes**

Run: `python -m unittest tests.test_social_welcome_dm -v`
Expected: PASS.

### Task 7: Verify the end-to-end surface and docs

**Files:**
- Modify: `discord_bot/docs/slash-commands.md`
- Modify: `docs/FEATURES.md`

**Step 1: Update docs**

Document:

- `@user` mention support in welcome templates
- public welcome petpet attachments
- optional DM petpet attachments in the welcome config surface

Only update live feature docs that describe current welcome behavior.

**Step 2: Run targeted verification**

Run:

- `python -m unittest tests.test_petpet tests.test_social_welcome_dm tests.test_config_panel -v`
- `python -m py_compile discord_bot/cogs/social.py discord_bot/cogs/config.py discord_bot/utils/db_handler.py discord_bot/utils/petpet.py`

Expected: PASS and no syntax errors.

**Step 3: Sanity-check references**

Run:

- `Select-String -Path discord_bot\\cogs\\config.py,discord_bot\\cogs\\social.py,discord_bot\\docs\\slash-commands.md,docs\\FEATURES.md -Pattern '@user|petpet'`

Expected: user-facing references appear in the intended config/help locations only.
