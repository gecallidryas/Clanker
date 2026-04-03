# Persona Manage Edit Assets Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Make `/persona manage` reuse the legacy custom-persona edit wizard so avatar and banner links can be updated from the manage panel.

**Architecture:** Keep one source of truth for custom-persona asset editing by routing the manage-panel `Edit Details` action into the existing `PersonaEditModal` flow in `cogs/persona.py`. Add a focused regression test around the manage-panel callback so future refactors do not silently strip avatar/banner editing again.

**Tech Stack:** Python 3.12, discord.py UI modals/views, unittest

---

### Task 1: Lock the delegation behavior with a regression test

**Files:**
- Modify: `tests/test_persona_manage_create.py`

**Step 1: Write the failing test**

Add a test asserting `PersonaManageView.edit_details(...)` calls the legacy Persona cog edit-modal helper instead of handling the edit entirely inside `utils/persona_panel_ui.py`.

**Step 2: Run test to verify it fails**

Run: `python -m unittest tests.test_persona_manage_create`
Expected: FAIL because the manage-panel still opens `PersonaDetailsModal`.

### Task 2: Reuse the legacy edit wizard

**Files:**
- Modify: `cogs/persona.py`
- Modify: `utils/persona_panel_ui.py`

**Step 1: Add a reusable helper on the Persona cog**

Extract the existing modal-open logic into a helper that can open `PersonaEditModal` from either the slash command path or the manage panel.

**Step 2: Update the manage-panel edit callback**

Have `PersonaManageView.edit_details(...)` call the Persona cog helper when available, falling back to the panel-local modal only if the cog helper cannot be resolved.

**Step 3: Keep slash-command behavior on the same helper**

Point `/persona edit` at the helper so both entry points stay in sync.

### Task 3: Verify and reload

**Files:**
- Modify: none

**Step 1: Run focused verification**

Run:
- `python -m unittest tests.test_persona_manage_create`
- `python -m py_compile cogs/persona.py utils/persona_panel_ui.py`

Expected: all green, no syntax errors.

**Step 2: Restart bot**

Restart the sanitized bot process and confirm fresh startup lines in `logs/femmy.log`.
