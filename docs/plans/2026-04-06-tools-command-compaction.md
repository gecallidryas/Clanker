# Tools Command Compaction Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Reorganize the `/tools` command tree so `/tools manage` remains the tool-flag panel, while read-only and operational commands move into compact subgroups.

**Architecture:** Update `discord_bot/cogs/tools_admin.py` so root `/tools` only exposes the high-level grouped surfaces and `/tools manage`, with `status` and `inspect` moved under `/tools info` and context-reset actions moved under `/tools context`. Then sync the help inventory and slash-command docs so the public command map matches the new tree.

**Tech Stack:** Python 3.12, discord.py app commands, unittest, markdown docs

---

### Task 1: Lock the compact `/tools` tree with tests

**Files:**
- Create: `discord_bot/tests/test_tools_admin_surface_consolidation.py`

**Step 1: Write the failing test**

Add assertions that:

- root `/tools` exposes `manage`, `info`, `context`, `policy`, `debug`, `quarantine`, and `mcp`
- root `/tools` no longer exposes `status`, `inspect`, `refresh`, or `clear-guild-recency`
- `/tools info` exposes `status` and `inspect`
- `/tools context` exposes `refresh` and `clear-guild-recency`

**Step 2: Run test to verify it fails**

Run: `python3 -m unittest tests.test_tools_admin_surface_consolidation`
Expected: FAIL because the current tree still keeps those commands flat.

### Task 2: Refactor `/tools` command registration

**Files:**
- Modify: `discord_bot/cogs/tools_admin.py`

**Step 1: Add subgroups**

Add:

- `info_group`
- `context_group`

as children of `tools_group`.

**Step 2: Move flat handlers into subgroups**

Rehome:

- `tools_status(...)` -> `/tools info status`
- `tools_inspect(...)` -> `/tools info inspect`
- `tools_refresh(...)` -> `/tools context refresh`
- `tools_clear_guild_recency(...)` -> `/tools context clear-guild-recency`

Keep `/tools manage` direct.

**Step 3: Run focused test**

Run: `python3 -m unittest tests.test_tools_admin_surface_consolidation`
Expected: PASS.

### Task 3: Update help inventory and command docs

**Files:**
- Modify: `discord_bot/cogs/utilities.py`
- Modify: `discord_bot/docs/slash-commands.md`

**Step 1: Update help inventory**

Make the help list show:

- `/tools manage`
- `/tools info status`
- `/tools info inspect`
- `/tools context refresh`
- `/tools context clear-guild-recency`

and keep the existing grouped sections for policy/debug/quarantine/mcp.

**Step 2: Update slash-command docs**

Replace the flat entries with the regrouped tree and keep descriptions aligned with the actual handlers.

### Task 4: Full verification

**Files:**
- Modify: none

**Step 1: Run tests**

Run:

- `python3 -m unittest tests.test_tools_admin_surface_consolidation`
- `python3 -m unittest tests.test_admin_surface_consolidation`
- `python3 -m unittest tests.test_interaction_status`
- `python3 -m unittest tests.test_persona_manage_create`

Expected: PASS.

**Step 2: Run syntax verification**

Run:

- `python3 -m py_compile discord_bot/cogs/tools_admin.py discord_bot/cogs/utilities.py`

Expected: no syntax errors.

**Step 3: Run docs sanity checks**

Run:

- `rg -n "/tools status|/tools inspect|/tools refresh|/tools clear-guild-recency" discord_bot/docs discord_bot/cogs/utilities.py`

Expected: only the regrouped `/tools info ...` and `/tools context ...` references remain in live docs/help.
