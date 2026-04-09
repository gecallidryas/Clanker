# Full Persona System Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Replace the current prompt-file-first persona stack with a structured persona compiler shared by built-in and guild custom personas, while preserving utility, tool/admin rules, affection overlays, and a compatibility path for legacy custom personas.

**Architecture:** Introduce a canonical persona definition, a compiler that emits ordered prompt sections, and built-in persona definitions under a dedicated `discord_bot/personas/` package. Then evolve custom personas in the DB and `/persona manage` to use the same schema with inheritance and legacy adaptation. Protect the rollout with prompt-structure tests, scenario-based behavior fixtures, and a staged migration path.

**Tech Stack:** Python, dataclasses or typed dicts, aiosqlite, discord.py, unittest, pytest

---

## Context The Implementer Needs

- Persona prompt assembly currently lives in `E:\femboibot\discord_bot\cogs\ai_brain.py`, especially `_load_persona()` and `build_prompt()`.
- Built-in mode metadata lives in:
  - `E:\femboibot\discord_bot\modes\default.py`
  - `E:\femboibot\discord_bot\modes\femboy.py`
  - `E:\femboibot\discord_bot\modes\tsundere.py`
  - `E:\femboibot\discord_bot\modes\oneesan.py`
- Built-in prompt text currently lives in `E:\femboibot\discord_bot\prompts\`.
- Custom personas and traits currently live in `E:\femboibot\discord_bot\utils\db_handler.py` and are edited through `E:\femboibot\discord_bot\cogs\persona.py`.
- Existing custom personas only have `normal_prompt`, `evil_prompt`, aliases, bio, and derived trait rows.
- Tool/admin/runtime rules already exist inside `build_prompt()` and must not be delegated to guild-authored persona text.
- This plan intentionally avoids multi-persona simultaneous speaking. Keep one active speaking persona per reply.

## Definition Of Done

- Built-in personas compile from structured definitions instead of relying on raw prompt blobs as the primary source of truth.
- `build_prompt()` uses a persona compiler that emits stable, testable prompt sections.
- Guild custom personas can inherit from built-in personas and store structured fields.
- Existing guild custom personas continue to work through a legacy adapter.
- Prompt-structure and behavior tests cover normal mode, evil mode, utility behavior, and custom persona inheritance.
- `/persona manage` can create or edit structured custom personas without requiring raw full-prompt authoring for the default path.

### Task 1: Add Persona Runtime Types And Compiler Skeleton

**Files:**
- Create: `E:\femboibot\discord_bot\personas\__init__.py`
- Create: `E:\femboibot\discord_bot\personas\definition.py`
- Create: `E:\femboibot\discord_bot\personas\compiler.py`
- Create: `E:\femboibot\tests\test_persona_compiler.py`

**Step 1: Write the failing tests**

- Add tests that assert a compiler can accept a minimal persona definition and emit ordered sections:
  - `ROLEPLAY CONTRACT`
  - `ACTIVE PERSONA IDENTITY`
  - `VOICE AND CADENCE`
  - `RELATIONSHIP RULES`
  - `TASK AND TOOL COMPETENCE RULES`
- Add a test that asserts evil-mode compilation includes `EVIL MODE SCENE RULES` and non-evil compilation does not.

**Step 2: Run tests to verify they fail**

Run:
```powershell
python -m pytest E:\femboibot\tests\test_persona_compiler.py -q
```

Expected:
- FAIL because the `discord_bot.personas` package and compiler do not exist yet.

**Step 3: Write minimal implementation**

- Create typed runtime structures for:
  - identity
  - voice
  - worldview
  - relationship model
  - scene rules
  - utility rules
  - examples
  - constraints
- Add a compiler that converts one persona definition plus an `evil_mode` flag into a list of prompt sections or a structured prompt block.
- Keep this first version independent of DB loading and `ai_brain.py`.

**Step 4: Run tests to verify they pass**

Run:
```powershell
python -m pytest E:\femboibot\tests\test_persona_compiler.py -q
```

Expected:
- PASS

**Step 5: Commit**

```powershell
git add E:\femboibot\discord_bot\personas\__init__.py E:\femboibot\discord_bot\personas\definition.py E:\femboibot\discord_bot\personas\compiler.py E:\femboibot\tests\test_persona_compiler.py
git commit -m "feat: add persona compiler skeleton"
```

### Task 2: Port Built-In Personas Into Structured Definitions

**Files:**
- Create: `E:\femboibot\discord_bot\personas\builtin\__init__.py`
- Create: `E:\femboibot\discord_bot\personas\builtin\default.py`
- Create: `E:\femboibot\discord_bot\personas\builtin\femboy.py`
- Create: `E:\femboibot\discord_bot\personas\builtin\tsundere.py`
- Create: `E:\femboibot\discord_bot\personas\builtin\oneesan.py`
- Create: `E:\femboibot\tests\test_builtin_personas.py`

**Step 1: Write the failing tests**

- Add tests that verify each built-in persona loads as a structured definition.
- Add targeted assertions for distinctive invariants:
  - `Clanker` has a quiet contempt worldview and a hard constraint against openly stating it
  - `Yumi` never identifies as Femmy
  - `Tsundere` starts resistant before helpfulness
  - `Femmy` preserves affectionate/submissive identity while still supporting utility

**Step 2: Run tests to verify they fail**

Run:
```powershell
python -m pytest E:\femboibot\tests\test_builtin_personas.py -q
```

Expected:
- FAIL because the built-in persona definitions do not exist yet.

**Step 3: Write minimal implementation**

- Move built-in persona intelligence into structured definitions under `discord_bot/personas/builtin/`.
- Reuse mode metadata from `discord_bot/modes/` where it makes sense, but keep prompt-brain details in the new package.
- Preserve current aliases, display names, and switching semantics.

**Step 4: Run tests to verify they pass**

Run:
```powershell
python -m pytest E:\femboibot\tests\test_builtin_personas.py E:\femboibot\tests\test_persona_compiler.py -q
```

Expected:
- PASS

**Step 5: Commit**

```powershell
git add E:\femboibot\discord_bot\personas\builtin E:\femboibot\tests\test_builtin_personas.py
git commit -m "feat: add structured builtin personas"
```

### Task 3: Integrate The Compiler Into `ai_brain` Without Changing Custom Personas Yet

**Files:**
- Modify: `E:\femboibot\discord_bot\cogs\ai_brain.py`
- Modify: `E:\femboibot\tests\test_ai_brain_multi_response.py`
- Modify: `E:\femboibot\tests\test_persona_message_triggering.py` if needed

**Step 1: Write the failing tests**

- Add a prompt-construction test that verifies built-in persona output is assembled through structured sections rather than a single prompt blob.
- Add a regression test that asserts tool/admin sections still appear in the final prompt when the structured persona compiler is used.
- Add a regression test that normal mode includes normal scene rules while evil mode includes evil scene rules for built-in personas.

**Step 2: Run tests to verify they fail**

Run:
```powershell
python -m pytest E:\femboibot\tests\test_ai_brain_multi_response.py -q
```

Expected:
- FAIL because `ai_brain.py` still uses `_load_persona()` as the main built-in prompt path.

**Step 3: Write minimal implementation**

- Teach `build_prompt()` to request a compiled persona section bundle for built-in modes.
- Keep the existing dynamic overlays for affection, memories, tools, admin access, and addressing notes.
- Preserve raw prompt-file fallback only as a backup, not the primary path.

**Step 4: Run tests to verify they pass**

Run:
```powershell
python -m pytest E:\femboibot\tests\test_ai_brain_multi_response.py E:\femboibot\tests\test_builtin_personas.py E:\femboibot\tests\test_persona_compiler.py -q
```

Expected:
- PASS

**Step 5: Commit**

```powershell
git add E:\femboibot\discord_bot\cogs\ai_brain.py E:\femboibot\tests\test_ai_brain_multi_response.py E:\femboibot\tests\test_persona_message_triggering.py
git commit -m "feat: compile builtin personas in ai brain"
```

### Task 4: Add Structured Custom Persona Schema And Loaders

**Files:**
- Modify: `E:\femboibot\discord_bot\utils\db_handler.py`
- Create: `E:\femboibot\discord_bot\personas\custom.py`
- Create: `E:\femboibot\tests\test_custom_persona_schema.py`

**Step 1: Write the failing tests**

- Add a DB migration test that verifies `custom_personas` gains:
  - `schema_version`
  - `base_template`
  - structured JSON columns
  - preserved legacy prompt columns
- Add a loader test that verifies a structured custom persona can be hydrated into the canonical runtime shape.

**Step 2: Run tests to verify they fail**

Run:
```powershell
python -m pytest E:\femboibot\tests\test_custom_persona_schema.py -q
```

Expected:
- FAIL because the schema and loader do not exist yet.

**Step 3: Write minimal implementation**

- Add DB migration logic for the structured columns with safe defaults.
- Add `discord_bot/personas/custom.py` that can:
  - load a custom persona by mode key
  - decode JSON columns
  - resolve `base_template`
  - return a canonical persona definition

**Step 4: Run tests to verify they pass**

Run:
```powershell
python -m pytest E:\femboibot\tests\test_custom_persona_schema.py -q
```

Expected:
- PASS

**Step 5: Commit**

```powershell
git add E:\femboibot\discord_bot\utils\db_handler.py E:\femboibot\discord_bot\personas\custom.py E:\femboibot\tests\test_custom_persona_schema.py
git commit -m "feat: add structured custom persona schema"
```

### Task 5: Add Legacy Custom Persona Adapter

**Files:**
- Modify: `E:\femboibot\discord_bot\personas\custom.py`
- Modify: `E:\femboibot\discord_bot\cogs\ai_brain.py`
- Create: `E:\femboibot\tests\test_legacy_custom_persona_adapter.py`

**Step 1: Write the failing tests**

- Add a test that seeds a legacy custom persona with only `normal_prompt` / `evil_prompt`.
- Assert the adapter returns a compiled persona definition instead of failing.
- Assert aliases, bio, and evil-mode prompt text are preserved in the adapted output.

**Step 2: Run tests to verify they fail**

Run:
```powershell
python -m pytest E:\femboibot\tests\test_legacy_custom_persona_adapter.py -q
```

Expected:
- FAIL because no legacy adapter exists.

**Step 3: Write minimal implementation**

- Build a legacy adapter that wraps raw prompt text as low-priority authored notes within the new compiler path.
- Make `ai_brain.py` use the structured custom persona path for both new-schema and legacy personas.
- Do not remove old custom persona behavior yet.

**Step 4: Run tests to verify they pass**

Run:
```powershell
python -m pytest E:\femboibot\tests\test_legacy_custom_persona_adapter.py E:\femboibot\tests\test_ai_brain_multi_response.py -q
```

Expected:
- PASS

**Step 5: Commit**

```powershell
git add E:\femboibot\discord_bot\personas\custom.py E:\femboibot\discord_bot\cogs\ai_brain.py E:\femboibot\tests\test_legacy_custom_persona_adapter.py
git commit -m "feat: adapt legacy custom personas to compiler"
```

### Task 6: Add Inheritance And Merge Rules For Custom Personas

**Files:**
- Modify: `E:\femboibot\discord_bot\personas\custom.py`
- Modify: `E:\femboibot\discord_bot\personas\compiler.py`
- Create: `E:\femboibot\tests\test_custom_persona_inheritance.py`

**Step 1: Write the failing tests**

- Add a test that a custom persona inheriting from `mode_oneesan` receives default oneesan behavior plus guild overrides.
- Add a test that `blank` inheritance does not accidentally inherit unrelated built-in rules.
- Add a test that override precedence is:
  - base template
  - custom structured fields
  - runtime overlays

**Step 2: Run tests to verify they fail**

Run:
```powershell
python -m pytest E:\femboibot\tests\test_custom_persona_inheritance.py -q
```

Expected:
- FAIL because inheritance resolution does not exist yet.

**Step 3: Write minimal implementation**

- Implement inheritance resolution against built-in structured personas.
- Define deterministic merge rules for lists, strings, examples, and constraints.
- Keep inheritance to built-ins only for this iteration.

**Step 4: Run tests to verify they pass**

Run:
```powershell
python -m pytest E:\femboibot\tests\test_custom_persona_inheritance.py E:\femboibot\tests\test_custom_persona_schema.py -q
```

Expected:
- PASS

**Step 5: Commit**

```powershell
git add E:\femboibot\discord_bot\personas\custom.py E:\femboibot\discord_bot\personas\compiler.py E:\femboibot\tests\test_custom_persona_inheritance.py
git commit -m "feat: add custom persona inheritance"
```

### Task 7: Upgrade `/persona manage` To Structured Authoring

**Files:**
- Modify: `E:\femboibot\discord_bot\cogs\persona.py`
- Modify: `E:\femboibot\discord_bot\utils\persona_panel_ui.py`
- Modify: `E:\femboibot\tests\test_persona_manage.py`
- Modify: `E:\femboibot\tests\test_persona_panel_ui.py` if present

**Step 1: Write the failing tests**

- Add tests that a new custom persona can be created with:
  - base template
  - structured voice/worldview fields
  - normal scene rules
  - evil scene rules
  - examples
- Add tests that legacy prompt-only editing remains readable for existing personas.

**Step 2: Run tests to verify they fail**

Run:
```powershell
python -m pytest E:\femboibot\tests\test_persona_manage.py -q
```

Expected:
- FAIL because the UI still assumes prompt-text-first authoring.

**Step 3: Write minimal implementation**

- Add structured authoring steps to the persona creation flow.
- Support selecting a base template during creation.
- Keep an expert escape hatch for raw prompt notes only if needed.
- Preserve current activation, deletion, alias, and avatar flows.

**Step 4: Run tests to verify they pass**

Run:
```powershell
python -m pytest E:\femboibot\tests\test_persona_manage.py E:\femboibot\tests\test_custom_persona_inheritance.py -q
```

Expected:
- PASS

**Step 5: Commit**

```powershell
git add E:\femboibot\discord_bot\cogs\persona.py E:\femboibot\discord_bot\utils\persona_panel_ui.py E:\femboibot\tests\test_persona_manage.py
git commit -m "feat: add structured custom persona authoring"
```

### Task 8: Add Scenario-Based Behavior Regressions Across All Personas

**Files:**
- Create: `E:\femboibot\tests\test_persona_behavior_contract.py`
- Modify: `E:\femboibot\tests\test_ai_brain_multi_response.py` if helper reuse is needed

**Step 1: Write the failing tests**

- Add behavior fixture tests for:
  - practical help request
  - affectionate non-explicit roleplay
  - normal-mode action-beat roleplay
  - evil-mode explicit roleplay
  - tool-use request
  - admin request
- Use assertions on prompt content and compiler output rather than fragile full-text matching of model prose.

**Step 2: Run tests to verify they fail**

Run:
```powershell
python -m pytest E:\femboibot\tests\test_persona_behavior_contract.py -q
```

Expected:
- FAIL because the new contract coverage does not exist yet.

**Step 3: Write minimal implementation**

- Add reusable fixtures and helpers that compile personas and inspect the presence or absence of critical rules.
- Only patch production code if the tests expose a real gap in section ordering, merge behavior, or evil-mode gating.

**Step 4: Run tests to verify they pass**

Run:
```powershell
python -m pytest E:\femboibot\tests\test_persona_behavior_contract.py E:\femboibot\tests\test_ai_brain_multi_response.py -q
```

Expected:
- PASS

**Step 5: Commit**

```powershell
git add E:\femboibot\tests\test_persona_behavior_contract.py E:\femboibot\tests\test_ai_brain_multi_response.py
git commit -m "test: add persona behavior contract coverage"
```

### Task 9: Final Verification And Cleanup

**Files:**
- Modify only if targeted regressions reveal missing glue in touched persona, DB, or UI files

**Step 1: Run the focused suite**

Run:
```powershell
python -m pytest E:\femboibot\tests\test_persona_compiler.py E:\femboibot\tests\test_builtin_personas.py E:\femboibot\tests\test_custom_persona_schema.py E:\femboibot\tests\test_legacy_custom_persona_adapter.py E:\femboibot\tests\test_custom_persona_inheritance.py E:\femboibot\tests\test_persona_behavior_contract.py E:\femboibot\tests\test_ai_brain_multi_response.py E:\femboibot\tests\test_persona_manage.py -q
```

Expected:
- PASS

**Step 2: Run broader regression coverage**

Run:
```powershell
python -m pytest E:\femboibot\tests\test_tool_executor.py E:\femboibot\tests\test_tool_registry.py E:\femboibot\tests\test_persona_message_triggering.py E:\femboibot\tests\test_context_builder.py -q
```

Expected:
- PASS

**Step 3: Spot-check prompt compilation manually**

Run a small local script or targeted test helper that compiles:
- `mode_default` normal mode
- `mode_default` evil mode
- one inherited custom persona
- one legacy adapted custom persona

Expected:
- each emits ordered sections
- tool/admin/runtime sections remain intact
- evil-mode rules only appear when enabled

**Step 4: Write minimal cleanup if needed**

- Fix only concrete failures found in the focused or broader suites.
- Do not expand into unrelated affection, tooling, or admin refactors.

**Step 5: Commit**

```powershell
git add E:\femboibot\discord_bot\personas E:\femboibot\discord_bot\cogs\ai_brain.py E:\femboibot\discord_bot\cogs\persona.py E:\femboibot\discord_bot\utils\db_handler.py E:\femboibot\discord_bot\utils\persona_panel_ui.py E:\femboibot\tests
git commit -m "feat: implement full persona system"
```

## Notes For Execution

- Keep raw prompt files in `discord_bot/prompts/` as fallback or authored fragments during migration, but do not let them remain the primary behavioral source.
- Treat shared tool/admin/runtime rules as compiler-owned sections with higher authority than guild-authored persona text.
- Keep evil-mode explicitness structurally separate from normal-mode action beats. Do not rely on vague wording to maintain that boundary.
- Prefer inheritance from built-ins for new guild personas. Do not support custom-persona-to-custom-persona inheritance until the built-in inheritance path is stable.
- Do not break existing guild personas during rollout. Legacy compatibility is required until admins can upgrade them through `/persona manage`.

## Execution Handoff

Plan complete and saved to `docs/plans/2026-04-09-full-persona-system.md`. Two execution options:

**1. Subagent-Driven (this session)** - I dispatch fresh subagent per task, review between tasks, fast iteration

**2. Parallel Session (separate)** - Open new session with executing-plans, batch execution with checkpoints

**Which approach?**
