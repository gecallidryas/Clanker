# Command Surface Consolidation Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Remove redundant mode, stats, and legacy persona commands; merge stats into `about`; and make slash-command thinking placeholders show the active bot mode.

**Architecture:** Add one reusable interaction-status helper for mode-aware placeholder replies, then centralize `about`/stats embed construction inside `cogs/utilities.py`. Remove redundant command registrations from `cogs/social.py` and `cogs/persona.py`, keeping `/persona manage` as the primary admin entrypoint and updating help/docs to match the new surface.

**Tech Stack:** Python 3.12, discord.py, unittest, markdown docs

---

### Task 1: Lock mode-name and about behavior with tests

**Files:**
- Create: `discord_bot/tests/test_interaction_status.py`
- Modify: `discord_bot/tests/test_persona_manage_create.py`

**Step 1: Write the failing tests**

Add tests that:

- verify built-in and custom mode keys resolve to `Clanker`, `Femmy`, `Yumi`, or the custom persona name
- verify the shared about embed includes runtime stats fields that used to live under `stats`

**Step 2: Run tests to verify they fail**

Run:

- `python -m unittest discord_bot.tests.test_interaction_status`
- `python -m unittest discord_bot.tests.test_persona_manage_create`

Expected: FAIL because the helper and shared about/stats builder do not exist yet.

### Task 2: Add reusable mode-aware interaction placeholder support

**Files:**
- Create: `discord_bot/utils/interaction_status.py`
- Modify: `discord_bot/cogs/utilities.py`
- Modify: `discord_bot/cogs/memories.py`
- Modify: `discord_bot/cogs/teach.py`
- Modify: `discord_bot/cogs/imagegen.py`

**Step 1: Write minimal helper implementation**

Add a helper that:

- resolves the current guild mode display name
- sends `"X is thinking..."` as the initial slash response
- preserves `ephemeral=True` when needed

**Step 2: Update slash commands that currently defer with thinking**

Replace `interaction.response.defer(thinking=True...)` in the affected slash commands with the new helper, then edit the original response instead of relying on a deferred followup path.

**Step 3: Run focused tests**

Run:

- `python -m unittest discord_bot.tests.test_interaction_status`

Expected: PASS.

### Task 3: Merge stats into about

**Files:**
- Modify: `discord_bot/cogs/utilities.py`

**Step 1: Write a failing test for about stats coverage**

If needed, expand the about-embed test to assert uptime, server, user, message, image, memory, and current-mode fields are present.

**Step 2: Implement one shared embed builder**

Create a helper used by both `!about` and `/about` that combines the old about and stats content into a single embed.

**Step 3: Remove redundant stats commands**

Delete `!stats` and `/stats`, and remove them from help inventory output.

**Step 4: Run focused tests**

Run:

- `python -m unittest discord_bot.tests.test_interaction_status`

Expected: PASS.

### Task 4: Remove redundant mode and legacy persona entrypoints

**Files:**
- Modify: `discord_bot/cogs/social.py`
- Modify: `discord_bot/cogs/persona.py`
- Modify: `discord_bot/cogs/utilities.py`
- Modify: `discord_bot/docs/slash-commands.md`

**Step 1: Remove redundant mode commands**

Delete:

- `!mode`
- `/mode`
- `!modes`
- `/modes`
- `!currentmode`
- `/currentmode`

Also remove duplicate `/mode` slash registration that currently exists in `cogs/social.py`.

**Step 2: Remove legacy persona slash subcommands**

Delete:

- `/persona create`
- `/persona list`
- `/persona preview`

Keep the reusable modal helpers that the manage panel still needs.

**Step 3: Update stale guidance**

Replace references that point users to removed commands with `/persona manage` or `about`, as appropriate.

**Step 4: Run focused tests**

Run:

- `python -m unittest discord_bot.tests.test_persona_manage_create`

Expected: PASS.

### Task 5: Verify syntax and documentation consistency

**Files:**
- Modify: none

**Step 1: Run verification**

Run:

- `python -m unittest discord_bot.tests.test_interaction_status`
- `python -m unittest discord_bot.tests.test_persona_manage_create`
- `python -m py_compile discord_bot/cogs/utilities.py discord_bot/cogs/social.py discord_bot/cogs/persona.py discord_bot/cogs/memories.py discord_bot/cogs/teach.py discord_bot/cogs/imagegen.py discord_bot/utils/interaction_status.py`

Expected: all green, no syntax errors.

**Step 2: Sanity-check command docs**

Run:

- `rg -n "/stats|/currentmode|/mode\\b|/modes\\b|/persona create|/persona list|/persona preview" discord_bot/docs/slash-commands.md discord_bot/cogs`

Expected: no remaining live command references outside intentional historical or prompt text.
