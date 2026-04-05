# Config Panel Compaction Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Compact the `/config` command surface so AI, toggle, URL safety, key/model, and custom-endpoint configuration are managed through panel-entry `manage` commands instead of many direct slash mutators.

**Architecture:** Update the command registration in `discord_bot/cogs/config.py` so the targeted `/config` subgroup trees only expose `manage`, then route those entry commands into the panel helpers that already exist for AI, capabilities, URL safety, and providers. Rewrite the public docs so the command inventory, guide material, and feature map all point to the panel-first workflow and reference the actual code files that implement each feature.

**Tech Stack:** Python 3.12, discord.py app commands, unittest, markdown docs

---

### Task 1: Lock the compact command tree with tests

**Files:**
- Modify: `discord_bot/tests/test_admin_surface_consolidation.py`

**Step 1: Write the failing test**

Add assertions that:

- `/config ai` exposes only `manage`
- `/config toggle` exposes only `manage`
- `/config url_safety` exposes only `manage`
- `/config custom_endpoint` exposes only `manage`
- `/config keys` exposes only `manage`
- `/config model` exposes only `manage`
- `/config env` still exposes `example` and `upload`
- `/config password` still exposes `set`, `change`, and `reset`

**Step 2: Run test to verify it fails**

Run: `python3 -m unittest tests.test_admin_surface_consolidation`
Expected: FAIL because the old granular subgroup commands are still registered.

### Task 2: Remove redundant subgroup slash commands and keep only panel entrypoints

**Files:**
- Modify: `discord_bot/cogs/config.py`

**Step 1: Add compact subgroup entry commands**

Ensure these commands exist and route to existing panel helpers:

- `/config ai manage` -> `_send_ai_panel(...)`
- `/config toggle manage` -> `_send_capabilities_panel(...)`
- `/config url_safety manage` -> `_send_url_safety_panel(...)`
- `/config custom_endpoint manage` -> `_send_provider_panel(...)`
- `/config keys manage` -> `_send_provider_panel(...)`
- `/config model manage` -> `_send_provider_panel(...)`

**Step 2: Remove granular subgroup slash handlers**

Delete the direct slash handlers for:

- `/config ai view`
- `/config ai cooldown`
- `/config ai cooldown_type`
- `/config ai self_reply_limit`
- `/config ai auto_threshold`
- `/config ai whitelist_add`
- `/config ai whitelist_remove`
- `/config ai whitelist_clear`
- `/config ai auto_channel_add`
- `/config ai auto_channel_remove`
- `/config ai streaming`
- `/config ai stream_budget`
- `/config ai thought_channel`
- `/config ai thought_level`
- `/config ai thought_modlog`
- `/config toggle evil`
- `/config toggle autorole`
- `/config toggle welcome`
- `/config toggle web_search`
- `/config toggle image_gen`
- `/config toggle stickers`
- `/config toggle emojis`
- `/config toggle pin_message`
- `/config toggle self_teaching`
- `/config toggle youtube`
- `/config toggle profile_peek`
- `/config toggle rag`
- `/config toggle gif_responses`
- `/config toggle url_safety`
- `/config url_safety view`
- `/config url_safety action`
- `/config url_safety allowlist`
- `/config url_safety blocklist`
- `/config url_safety clear`
- `/config custom_endpoint view`
- `/config custom_endpoint set`
- `/config keys view`
- `/config keys clear`
- `/config keys set`
- `/config model view`
- `/config model set`

Keep `/config panel`, `/config auth`, `/config password *`, and `/config env *`.

**Step 3: Run focused test**

Run: `python3 -m unittest tests.test_admin_surface_consolidation`
Expected: PASS.

### Task 3: Update slash command docs to match the real tree

**Files:**
- Modify: `discord_bot/docs/slash-commands.md`

**Step 1: Rewrite the config section**

Remove the granular `/config` commands that no longer exist and replace them with the compact tree:

- `/config ai manage`
- `/config toggle manage`
- `/config url_safety manage`
- `/config custom_endpoint manage`
- `/config keys manage`
- `/config model manage`
- `/config panel`
- `/config auth`
- `/config password set|change|reset`
- `/config env example|upload`

**Step 2: Keep top-level manage groups aligned**

Retain `/autorole manage`, `/welcome manage`, `/staff manage`, and `/modlog manage` in the docs.

**Step 3: Run grep verification**

Run: `rg -n "/config ai |/config toggle |/config url_safety |/config custom_endpoint |/config keys |/config model " discord_bot/docs/slash-commands.md`
Expected: only `manage` entries remain for those groups.

### Task 4: Add guide docs and a code-referenced feature map

**Files:**
- Create: `discord_bot/docs/guide/README.md`
- Create: `discord_bot/docs/guide/config-panel.md`
- Create: `discord_bot/docs/guide/settings-reference.md`
- Create: `discord_bot/docs/features.md`

**Step 1: Write the guide index**

Create a short guide landing page that links the new how-to docs.

**Step 2: Write the config panel guide**

Explain how to:

- authenticate
- upload env files
- open `/config panel`
- use each compact subgroup `manage` entry command
- make high-risk changes safely

**Step 3: Write the settings reference**

Document what each major setting does across:

- capabilities/toggles
- AI behavior
- URL safety
- providers/models/custom endpoint
- welcome/autorole/staff/modlog

Reference the code files that own the behavior.

**Step 4: Write the feature map**

Create `discord_bot/docs/features.md` describing each feature area and linking it to the implementing code in files such as:

- `discord_bot/cogs/config.py`
- `discord_bot/utils/native_config_panel.py`
- `discord_bot/cogs/social.py`
- `discord_bot/cogs/tools_admin.py`
- `discord_bot/utils/tool_registry.py`
- `discord_bot/utils/db_handler.py`

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

- `python3 -m py_compile discord_bot/cogs/config.py`

Expected: no syntax errors.

**Step 3: Run docs sanity checks**

Run:

- `rg -n "/config ai (?!manage)|/config toggle (?!manage)|/config url_safety (?!manage)|/config custom_endpoint (?!manage)|/config keys (?!manage)|/config model (?!manage)" discord_bot/docs`

Expected: no matches in the live docs.
