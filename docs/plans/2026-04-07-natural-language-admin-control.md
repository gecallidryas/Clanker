# Natural-Language Admin Control Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Build one robust natural-language admin control plane that unifies existing conversational admin/config behavior and expands it across adjacent existing server settings such as starboard, welcome, automod, spam thresholds, URL safety, modlog, autorole, staff-role management, and current moderation/server-structure actions.

**Architecture:** Introduce a typed admin-intent layer with deterministic parsing, follow-up state, confirmation policy, and executor dispatch. Keep `AIBrain` responsible for trigger routing only, while the typed admin control plane becomes the sole authority for supported conversational admin mutations. Prompt-generated `admin_action` is explicitly non-authoritative for the supported surface.

**Tech Stack:** Python 3.12, discord.py, unittest/pytest, SQLite-backed guild config helpers

---

### Task 1: Lock the unified admin control behavior with failing tests

**Files:**
- Create: `tests/test_admin_nl_intents.py`
- Create: `tests/test_admin_nl_flow.py`

**Step 1: Write the failing tests**

Add tests that assert the new control plane can:

- detect and parse starboard, welcome, automod, spam, URL safety, modlog, autorole, and staff-role requests
- require follow-up questions when mandatory slots are missing
- require confirmation for channel/category deletion
- avoid confirmation for bans and other non-delete moderation actions
- route follow-up messages to pending admin requests

**Step 2: Run tests to verify they fail**

Run: `python -m pytest tests/test_admin_nl_intents.py tests/test_admin_nl_flow.py -q`
Expected: FAIL because the unified intent/control-plane layer does not exist yet.

### Task 2: Add typed admin intent models and parsing helpers

**Files:**
- Create: `discord_bot/utils/admin_nl.py`
- Modify: `discord_bot/cogs/ai_brain.py`
- Test: `tests/test_admin_nl_intents.py`

**Step 1: Write the minimal parser surface**

Add intent definitions, slot schemas, and parsing helpers for:

- starboard configure/toggle/ignore
- welcome public/DM configuration
- automod keyword add/remove
- spam config
- URL safety config
- modlog set/clear
- autorole set/clear
- staff add/remove/clear
- existing moderation and structure actions

**Step 2: Run focused tests**

Run: `python -m pytest tests/test_admin_nl_intents.py -q`
Expected: FAIL until parsing behavior matches the test cases.

**Step 3: Implement the minimal parser**

Write deterministic parsing helpers that normalize:

- channels and mentions
- role mentions and quoted names
- booleans
- thresholds and duration phrases
- "this channel"/"here"
- delete/clear/remove/disable semantics

**Step 4: Re-run focused tests**

Run: `python -m pytest tests/test_admin_nl_intents.py -q`
Expected: PASS or narrower failures for unsupported patterns that must still be implemented.

### Task 3: Expand the admin executor layer to cover adjacent settings

**Files:**
- Modify: `discord_bot/utils/admin_actions.py`
- Test: `tests/test_admin_nl_intents.py`

**Step 1: Write failing executor tests**

Add assertions that intent execution supports:

- starboard ignore/unignore/toggle
- welcome toggle and DM toggle
- spam config updates
- URL safety updates
- modlog set/clear
- autorole set/clear
- staff add/remove/clear

**Step 2: Run focused tests**

Run: `python -m pytest tests/test_admin_nl_intents.py -q`
Expected: FAIL because these executor actions are not all available through one admin-action layer.

**Step 3: Implement minimal executor support**

Extend the executor layer so each parsed intent dispatches to one normalized function that:

- validates permissions
- resolves guild objects
- writes via `db_handler`
- returns a consistent result payload

**Step 4: Re-run focused tests**

Run: `python -m pytest tests/test_admin_nl_intents.py -q`
Expected: PASS for the new executor coverage.

### Task 4: Replace fragmented `AIBrain` admin fast paths with one unified flow

**Files:**
- Modify: `discord_bot/cogs/ai_brain.py`
- Test: `tests/test_admin_nl_flow.py`

**Step 1: Write the failing flow tests**

Add tests that verify `AIBrain`:

- detects qualifying admin requests through the shared control plane
- stores pending follow-up state when required slots are missing
- asks short follow-up questions
- executes ready intents immediately
- asks for confirmation only for channel/category deletion

**Step 2: Run focused tests**

Run: `python -m pytest tests/test_admin_nl_flow.py -q`
Expected: FAIL because `AIBrain` still uses fragmented `_maybe_handle_*` logic and separate pending handling.

**Step 3: Implement the unified flow**

Replace the starboard-only admin setup fast path and fold current role/channel special cases into a shared admin request handler. Keep prompt-generated `admin_action` support, but map it through the same intent/executor path.

**Step 4: Re-run focused tests**

Run: `python -m pytest tests/test_admin_nl_flow.py -q`
Expected: PASS.

### Task 5: Refresh capability/help guidance so the model keeps using the unified path

**Files:**
- Modify: `discord_bot/cogs/ai_brain.py`
- Modify: `discord_bot/utils/review_capabilities.py`
- Modify: `discord_bot/docs/guide/settings-reference.md`

**Step 1: Write the failing documentation/help assertions**

Add or extend tests so admin capability/help output explicitly reflects the supported conversational admin settings.

**Step 2: Run relevant tests**

Run: `python -m pytest tests/test_ai_brain_admin_intent_bypass.py tests/test_ai_config_surface.py -q`
Expected: FAIL or miss the expanded admin-control descriptions.

**Step 3: Implement the minimal help updates**

Update admin instructions and capability reporting so the bot can consistently describe what can be managed through natural language without relying on scattered prompt hints.

**Step 4: Re-run relevant tests**

Run: `python -m pytest tests/test_ai_brain_admin_intent_bypass.py tests/test_ai_config_surface.py -q`
Expected: PASS.

### Task 6: Full verification

**Files:**
- Modify: none

**Step 1: Run the targeted test suite**

Run: `python -m pytest tests/test_admin_nl_intents.py tests/test_admin_nl_flow.py tests/test_ai_brain_admin_intent_bypass.py tests/test_starboard_settings_parsing.py tests/test_social_welcome_dm.py tests/test_guild_config_audit.py -q`
Expected: PASS.

**Step 2: Run syntax verification**

Run: `python -m py_compile discord_bot/cogs/ai_brain.py discord_bot/utils/admin_actions.py discord_bot/utils/admin_nl.py`
Expected: PASS.

**Step 3: Summarize residual risk**

Note that the natural-language control plane will still rely on deterministic phrasing support for the covered settings. Further expansion into unrelated admin domains should add tests first and extend the same typed-intent layer rather than reintroducing one-off fast paths.

## Supported Intent Surface

The supported admin mutation surface is the typed pipeline only:

- `interpret_admin_request`
- `resume_admin_request`
- `execute_admin_intent`

Supported mutation intents:

- `channel.create_text`
- `channel.create_voice`
- `channel.create_category`
- `channel.delete`
- `role.create`
- `role.delete`
- `role.assign`
- `role.remove`
- `starboard.configure`
- `starboard.toggle`
- `starboard.ignore_channel`
- `starboard.unignore_channel`
- `welcome.configure`
- `welcome.toggle`
- `welcome.message.clear`
- `welcome.dm.configure`
- `welcome.dm.toggle`
- `welcome.dm.message.clear`
- `automod.keyword.add`
- `automod.keyword.remove`
- `automod.spam.configure`
- `url_safety.configure`
- `modlog.set`
- `modlog.clear`
- `autorole.set`
- `autorole.clear`
- `staff.add`
- `staff.remove`
- `staff.clear`
- `moderation.ban`
- `moderation.unban`
- `moderation.kick`
- `moderation.timeout`

Equivalent phrasings such as `set modlog`, `set mod log`, `create starboard`, and `send posts to starboard` must enter the same typed intent path.

Read-only/admin status questions such as `what is the welcome message in #logs?`, `show me the modlog channel`, and `what is the url safety action?` are not supported mutations and must not create pending mutation state.

Admin-like text that does not parse into one of the supported typed intents must fail closed with a deterministic non-mutating help or rephrase response. It must not continue into the general AI mutation path, and prompt-driven `admin_action` is non-authoritative for this supported surface.
