# Welcome Manage Consolidation Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Make `/welcome manage` the only slash-command entrypoint for welcome configuration while preserving and expanding all current welcome features inside the panel UX.

**Architecture:** Keep the existing `Config` cog as the single command-registration source, but upgrade the welcome panel to expose the full legacy command surface through panel actions and modals. Use static tests around command registration, help inventory, and panel action definitions so future refactors cannot silently reintroduce standalone welcome commands.

**Tech Stack:** Python, discord.py app commands, unittest, AST-based source inspection tests

---

### Task 1: Lock in the new command surface with tests

**Files:**
- Modify: `discord_bot/tests/test_admin_surface_consolidation.py`
- Test: `discord_bot/tests/test_admin_surface_consolidation.py`

**Step 1: Write the failing test**

Add assertions that:
- `Config.welcome_group.commands` is exactly `["manage"]`
- `HELP_COMMANDS["welcome"]["slash"]` is exactly `["/welcome manage"]`
- `_send_welcome_panel` defines the integrated welcome action values needed to replace the removed commands

**Step 2: Run test to verify it fails**

Run: `python -m unittest discord_bot.tests.test_admin_surface_consolidation -v`
Expected: FAIL because the legacy `/welcome` commands and help entries still exist.

**Step 3: Write minimal implementation**

Remove the standalone command registrations and wire the expected actions into the welcome manage panel.

**Step 4: Run test to verify it passes**

Run: `python -m unittest discord_bot.tests.test_admin_surface_consolidation -v`
Expected: PASS

### Task 2: Expand `/welcome manage` to replace the removed commands

**Files:**
- Modify: `discord_bot/cogs/config.py`
- Test: `discord_bot/tests/test_admin_surface_consolidation.py`

**Step 1: Write the failing test**

Use the Task 1 panel-action assertion as the failing spec for the expanded action set.

**Step 2: Run test to verify it fails**

Run: `python -m unittest discord_bot.tests.test_admin_surface_consolidation -v`
Expected: FAIL because the current panel does not expose the full integrated action set.

**Step 3: Write minimal implementation**

Update the welcome panel to support:
- channel selection
- welcome enable/disable controls
- welcome template edit and clear
- DM welcome message edit and clear
- DM welcome toggle
- welcome test send

Preserve auth requirements for state-changing actions and improve the embed summary so admins can see current state from the panel.

**Step 4: Run test to verify it passes**

Run: `python -m unittest discord_bot.tests.test_admin_surface_consolidation -v`
Expected: PASS

### Task 3: Remove legacy inventory references

**Files:**
- Modify: `discord_bot/cogs/utilities.py`
- Modify: `discord_bot/docs/slash-commands.md`
- Test: `discord_bot/tests/test_admin_surface_consolidation.py`

**Step 1: Write the failing test**

Use the Task 1 help-inventory assertion as the failing spec for user-visible command docs and help.

**Step 2: Run test to verify it fails**

Run: `python -m unittest discord_bot.tests.test_admin_surface_consolidation -v`
Expected: FAIL because the help inventory still lists removed welcome commands.

**Step 3: Write minimal implementation**

Reduce the help inventory and slash-command docs to the single `/welcome manage` entry.

**Step 4: Run test to verify it passes**

Run: `python -m unittest discord_bot.tests.test_admin_surface_consolidation -v`
Expected: PASS

### Task 4: Verify the consolidated admin surface

**Files:**
- Modify: `discord_bot/cogs/config.py`
- Modify: `discord_bot/cogs/utilities.py`
- Modify: `discord_bot/docs/slash-commands.md`
- Modify: `discord_bot/tests/test_admin_surface_consolidation.py`

**Step 1: Run focused verification**

Run: `python -m unittest discord_bot.tests.test_admin_surface_consolidation discord_bot.tests.test_tools_admin_surface_consolidation -v`
Expected: PASS

**Step 2: Run a syntax safety check**

Run: `python -m compileall discord_bot/cogs/config.py discord_bot/cogs/utilities.py`
Expected: PASS

**Step 3: Summarize residual risk**

Note that interactive Discord UI behavior is covered by static surface tests here, not end-to-end Discord interaction tests.
