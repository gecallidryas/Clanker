# Admin Surface Consolidation Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Remove direct slash commands for autorole set/clear/view and server-structure create/delete actions, keeping `/autorole manage` as the only autorole slash surface and routing structure changes through the existing normal-chat AI admin-action flow.

**Architecture:** Trim the public slash surface in `cogs/config.py`, `cogs/utilities.py`, and `docs/slash-commands.md`, then verify that `cogs/ai_brain.py` remains the supported path for create/delete role/category/channel requests. Preserve destructive confirmations and permission checks by keeping the current AI pending-action flow rather than introducing a new command entrypoint.

**Tech Stack:** Python 3.12, discord.py app commands, unittest, markdown docs

---

### Task 1: Lock the desired command surface with tests

**Files:**
- Create: `discord_bot/tests/test_admin_surface_consolidation.py`

**Step 1: Write the failing test**

Add tests that assert:

- `/autorole manage` exists
- `/autorole set`, `/autorole clear`, and `/autorole view` do not exist
- `/manage create_category`, `/manage create_text_channel`, `/manage create_voice_channel`, `/manage create_role`, `/manage delete_category`, `/manage delete_channel`, and `/manage delete_role` do not exist

Use the cog command tree metadata or direct command object inspection instead of string-only docs checks.

**Step 2: Run test to verify it fails**

Run: `python3 -m unittest tests.test_admin_surface_consolidation`
Expected: FAIL because the redundant slash commands are still registered.

### Task 2: Remove redundant autorole slash commands

**Files:**
- Modify: `discord_bot/cogs/config.py`
- Modify: `discord_bot/cogs/utilities.py`

**Step 1: Remove direct autorole slash commands**

Delete:

- `autorole_set(...)`
- `autorole_clear(...)`
- `autorole_view(...)`

Keep `autorole_manage(...)` and the underlying panel helpers it uses.

**Step 2: Update help inventory**

Remove `/autorole set`, `/autorole clear`, and `/autorole view` from the utilities help inventory and any related guidance text that still recommends them.

**Step 3: Run focused test**

Run: `python3 -m unittest tests.test_admin_surface_consolidation`
Expected: still FAIL until `/manage ...` commands are removed too, but autorole assertions should now pass.

### Task 3: Remove direct structure-management slash commands

**Files:**
- Modify: `discord_bot/cogs/config.py`

**Step 1: Remove the `/manage` slash handlers**

Delete:

- `manage_create_category(...)`
- `manage_create_text_channel(...)`
- `manage_create_voice_channel(...)`
- `manage_create_role(...)`
- `manage_delete_category(...)`
- `manage_delete_channel(...)`
- `manage_delete_role(...)`

If the `manage_group` object becomes unused afterward, remove it too.

**Step 2: Preserve shared behavior only if still needed**

If any helper is still needed by other code, keep the helper and remove only the public command decorator path.

**Step 3: Run focused test**

Run: `python3 -m unittest tests.test_admin_surface_consolidation`
Expected: PASS.

### Task 4: Update docs and AI guidance

**Files:**
- Modify: `discord_bot/docs/slash-commands.md`
- Modify: `discord_bot/cogs/utilities.py`
- Modify: `discord_bot/cogs/ai_brain.py`

**Step 1: Update slash command docs**

Remove:

- `/autorole set`
- `/autorole clear`
- `/autorole view`
- all `/manage ...` structure commands

Leave `/autorole manage`.

**Step 2: Update help inventory**

Ensure public help output no longer lists the removed commands.

**Step 3: Update AI help text**

Change user-facing help/prompts so they describe normal-chat structure management, for example:

- “Ask me in chat to create or delete roles, channels, and categories.”

Avoid pointing users back to removed slash commands.

**Step 4: Run grep verification**

Run:

- `rg -n "/autorole set|/autorole clear|/autorole view|/manage create_|/manage delete_" discord_bot`

Expected: no remaining live user-facing references outside historical docs or comments that are intentionally retained.

### Task 5: Full verification

**Files:**
- Modify: none

**Step 1: Run tests**

Run:

- `python3 -m unittest tests.test_admin_surface_consolidation`
- `python3 -m unittest tests.test_interaction_status`
- `python3 -m unittest tests.test_persona_manage_create`

Expected: PASS.

**Step 2: Run syntax verification**

Run:

- `python3 -m py_compile discord_bot/cogs/config.py discord_bot/cogs/utilities.py discord_bot/cogs/ai_brain.py`

Expected: no syntax errors.

**Step 3: Run surface sanity check**

Run:

- `rg -n "/autorole manage|/manage " discord_bot/docs/slash-commands.md discord_bot/cogs`

Expected:
- `/autorole manage` still present
- removed `/manage ...` commands absent as user-facing commands
