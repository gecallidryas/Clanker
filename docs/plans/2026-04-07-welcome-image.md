# Welcome Image Controls Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Add configurable welcome-image controls to `/welcome manage`, support both `pettinghand` and `catmunch` templates, and route the selected image to the welcome channel, a specific channel, or DMs.

**Architecture:** Extend `guild_config` with a compact welcome-image config block and expose it through `get_welcome_config()`. Keep panel state in `discord_bot/cogs/config.py`, move rendering into utilities, and make `discord_bot/cogs/social.py` resolve one destination per join event and send the rendered attachment without changing the existing text welcome flow.

**Tech Stack:** Python 3, discord.py, Pillow, sqlite-backed guild config helpers, unittest/pytest-style test modules in `discord_bot/tests` and `tests`

---

### Task 1: Lock In Config Defaults

**Files:**
- Modify: `discord_bot/utils/db_handler.py`
- Test: `tests/test_social_welcome_dm.py`

**Step 1: Write the failing test**

Add a test that reads `get_welcome_config()` for a guild with no explicit welcome-image values and asserts:

```python
{
    "welcome_image_enabled": False,
    "welcome_image_template": "pettinghand",
    "welcome_image_destination": "welcome_channel",
    "welcome_image_channel_id": None,
}
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/test_social_welcome_dm.py -k welcome_image_defaults -v`

Expected: FAIL because `get_welcome_config()` does not return the new keys yet.

**Step 3: Write minimal implementation**

Update the guild-config schema/default hydration in `discord_bot/utils/db_handler.py` so the four welcome-image fields exist and `get_welcome_config()` returns them with the documented defaults.

**Step 4: Run test to verify it passes**

Run: `pytest tests/test_social_welcome_dm.py -k welcome_image_defaults -v`

Expected: PASS.

**Step 5: Commit**

```bash
git add discord_bot/utils/db_handler.py tests/test_social_welcome_dm.py
git commit -m "feat: add welcome image config defaults"
```

### Task 2: Expand The Welcome Manage Panel

**Files:**
- Modify: `discord_bot/cogs/config.py`
- Test: `discord_bot/tests/test_admin_surface_consolidation.py`

**Step 1: Write the failing test**

Extend the action snapshot test for `_send_welcome_panel` so it expects the new action values for image toggle, template selection, destination selection, image channel selection, and image test send.

**Step 2: Run test to verify it fails**

Run: `python -m pytest discord_bot/tests/test_admin_surface_consolidation.py -k welcome_manage_panel -v`

Expected: FAIL because the panel action list still only contains text-welcome actions.

**Step 3: Write minimal implementation**

In `discord_bot/cogs/config.py`:

- add the welcome-image summary fields to the panel embed
- add the new `ActionOption` entries
- handle the new actions with the existing panel patterns
- add small helpers to persist template, destination, and destination channel updates

Reuse existing picker/modal/view patterns instead of creating a second admin surface.

**Step 4: Run test to verify it passes**

Run: `python -m pytest discord_bot/tests/test_admin_surface_consolidation.py -k welcome_manage_panel -v`

Expected: PASS.

**Step 5: Commit**

```bash
git add discord_bot/cogs/config.py discord_bot/tests/test_admin_surface_consolidation.py
git commit -m "feat: add welcome image controls to manage panel"
```

### Task 3: Add The Catmunch Renderer

**Files:**
- Create: `discord_bot/utils/welcome_images.py`
- Test: `tests/test_social_welcome_dm.py`

**Step 1: Write the failing test**

Add a utility-level test that:

- builds a sample avatar byte payload
- renders the `catmunch` template
- asserts the output is non-empty PNG data

Use explicit text inputs for member name and ordinal join string.

**Step 2: Run test to verify it fails**

Run: `pytest tests/test_social_welcome_dm.py -k catmunch -v`

Expected: FAIL because no catmunch renderer exists.

**Step 3: Write minimal implementation**

Create `discord_bot/utils/welcome_images.py` with:

- a small template-dispatch function
- a wrapper around the existing `make_petpet(...)`
- a new `render_catmunch(...)` function that:
  - loads `E:/femboibot/catmunch/cattomunch (2).png`
  - loads `E:/femboibot/catmunch/ArtistsAlleyBB.otf`
  - crops/scales the avatar into the center circle
  - draws the required top and bottom text
  - returns PNG bytes plus filename/content type metadata

Keep all asset paths centralized in the module.

**Step 4: Run test to verify it passes**

Run: `pytest tests/test_social_welcome_dm.py -k catmunch -v`

Expected: PASS.

**Step 5: Commit**

```bash
git add discord_bot/utils/welcome_images.py tests/test_social_welcome_dm.py
git commit -m "feat: add catmunch welcome image renderer"
```

### Task 4: Route Welcome Images During Member Join

**Files:**
- Modify: `discord_bot/cogs/social.py`
- Test: `tests/test_social_welcome_dm.py`

**Step 1: Write the failing test**

Add focused tests for join handling that cover:

- `welcome_channel` destination sends the image to the welcome channel
- `specific_channel` destination sends the image to the configured override channel
- `dm` destination DMs the image even when DM welcome text is disabled

Keep renderer calls stubbed at the seam so the tests validate routing logic, not image bytes.

**Step 2: Run test to verify it fails**

Run: `pytest tests/test_social_welcome_dm.py -k welcome_image_routing -v`

Expected: FAIL because `on_member_join` only sends pettinghand to the welcome channel today.

**Step 3: Write minimal implementation**

In `discord_bot/cogs/social.py`:

- replace the hardcoded pettinghand send path with a welcome-image send helper
- resolve the image destination from the new config fields
- render the selected template once
- send the resulting `discord.File` to the resolved destination
- preserve the existing text welcome and DM text welcome behavior
- log and continue on image-send failures

**Step 4: Run test to verify it passes**

Run: `pytest tests/test_social_welcome_dm.py -k welcome_image_routing -v`

Expected: PASS.

**Step 5: Commit**

```bash
git add discord_bot/cogs/social.py tests/test_social_welcome_dm.py
git commit -m "feat: route welcome images by destination"
```

### Task 5: Run The Focused Verification Set

**Files:**
- Verify only

**Step 1: Run the welcome-focused tests**

Run: `pytest discord_bot/tests/test_admin_surface_consolidation.py tests/test_social_welcome_dm.py -v`

Expected: PASS with the new welcome-image coverage and no regressions in welcome panel behavior.

**Step 2: Run a targeted syntax check if needed**

Run: `python -m py_compile discord_bot/cogs/config.py discord_bot/cogs/social.py discord_bot/utils/db_handler.py discord_bot/utils/welcome_images.py`

Expected: no output.

**Step 3: Commit**

```bash
git add discord_bot/cogs/config.py discord_bot/cogs/social.py discord_bot/utils/db_handler.py discord_bot/utils/welcome_images.py discord_bot/tests/test_admin_surface_consolidation.py tests/test_social_welcome_dm.py
git commit -m "feat: add configurable welcome image templates"
```

### Task 6: Update Operator-Facing Docs

**Files:**
- Modify: `discord_bot/docs/guide/settings-reference.md`
- Modify: `discord_bot/docs/slash-commands.md`

**Step 1: Write the failing expectation**

Document the new welcome-image settings and `/welcome manage` behavior in the operator docs.

**Step 2: Make the minimal doc update**

Add concise documentation for:

- welcome image toggle
- template selector
- image destination behavior
- DM independence from the DM text welcome toggle

**Step 3: Verify**

Run: `git diff -- discord_bot/docs/guide/settings-reference.md discord_bot/docs/slash-commands.md`

Expected: only the intended welcome-image documentation changes.

**Step 4: Commit**

```bash
git add discord_bot/docs/guide/settings-reference.md discord_bot/docs/slash-commands.md
git commit -m "docs: describe welcome image controls"
```
