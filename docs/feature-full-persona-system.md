# Full Persona System Reference

## Purpose

This document describes the completed full persona-system work that was implemented in the dedicated `full-persona-system` workstream.

Important scope note:

- Some older detached checkouts may still predate the runtime files described here.
- This reference documents the implemented feature set and intended steady-state architecture, not just the older prompt-blob baseline.

## What Changed

The old persona stack treated built-in modes and guild custom personas differently:

- built-in modes mostly depended on prompt files plus mode metadata
- custom personas were largely raw `normal_prompt` / `evil_prompt` blobs
- prompt assembly in `ai_brain.py` had to mix persona text, utility rules, admin rules, memories, and affection overlays in one place

The full persona system replaces that with one structured persona contract shared by:

- built-in personas
- structured custom personas
- legacy custom personas through an adapter layer

## Operator View

For admins and day-to-day bot usage, the practical changes are:

- `/persona manage` remains the main admin entrypoint
- built-in personas keep their existing names, aliases, and switching semantics
- custom personas can be authored as structured variants of a base persona instead of requiring one giant raw prompt
- old custom personas still continue to work
- evil mode remains a runtime overlay, not a separate persona identity
- multi-persona behavior stays queue-based, with one speaking persona per reply

## Runtime Architecture

The implemented design introduces a dedicated persona runtime layer:

- `discord_bot/personas/definition.py`
  - canonical typed persona structures
- `discord_bot/personas/compiler.py`
  - ordered prompt-section compiler
- `discord_bot/personas/builtin/`
  - structured built-in persona definitions
- `discord_bot/personas/custom.py`
  - custom-persona loader, inheritance resolver, and legacy adapter

`discord_bot/cogs/ai_brain.py` no longer has to treat built-ins as a special flat-prompt path. It asks the compiler for persona sections, then appends the existing runtime overlays such as:

- affection state
- user addressing and gender notes
- wellbeing prompts
- memories and recency summaries
- tool instructions
- admin permission notes
- conversation context

The key architectural rule is that tool, admin, memory, and permission behavior stay in high-priority runtime sections. Persona flavor should influence style and subtext, not override core competence or guardrails.

## Structured Persona Contract

Built-in and structured custom personas compile from the same conceptual shape:

- identity
- voice and cadence
- worldview and subtext
- relationship rules
- normal-mode scene rules
- evil-mode scene rules
- utility and competence rules
- hard constraints
- example replies

The compiler emits explicit ordered sections instead of relying on one large persona blob. The target sections are:

- `ROLEPLAY CONTRACT`
- `ACTIVE PERSONA IDENTITY`
- `VOICE AND CADENCE`
- `WORLDVIEW AND SUBTEXT`
- `RELATIONSHIP RULES`
- `NORMAL MODE SCENE RULES`
- `EVIL MODE SCENE RULES`
- `TASK AND TOOL COMPETENCE RULES`
- `HARD CONSTRAINTS`
- `EXAMPLE REPLIES`

This makes prompt construction testable and lets built-in and custom personas share the same runtime guarantees.

## Built-In Personas

Built-in persona intelligence moves under `discord_bot/personas/builtin/`, while existing mode metadata in `discord_bot/modes/` still remains authoritative for:

- display names
- aliases
- switching semantics
- presentation metadata

That split is intentional:

- `discord_bot/modes/` continues to answer "what mode is this?"
- `discord_bot/personas/builtin/` answers "how does this persona think and speak?"

The built-ins are modeled with distinct invariants, including:

- `mode_default` / Clanker: quiet contempt and emotional distance without openly confessing it
- `mode_femboy` / Femmy: affectionate and submissive flavor without collapsing utility
- `mode_tsundere`: resistance and defensiveness before warmth
- `mode_oneesan`: warm older-sister energy with brevity controls

## Custom Personas

Structured custom personas become first-class personas rather than prompt exceptions.

The database model gains structured schema support while keeping legacy fields:

- schema versioning
- base template selection
- structured JSON-backed sections
- legacy prompt preservation

Custom personas can inherit from a built-in base such as:

- `blank`
- `mode_default`
- `mode_femboy`
- `mode_tsundere`
- `mode_oneesan`

Inheritance is used for:

- shared defaults
- shared utility behavior
- stable persona scaffolding

Guild-authored overrides then layer on top of that base.

## Legacy Compatibility

Older custom personas that only have `normal_prompt` and `evil_prompt` are not discarded.

Instead, the runtime adapts them by:

- preserving the current mode key and aliases
- preserving bio and authored prompt tone
- wrapping old prompt text into a lower-priority compatibility layer
- letting them continue to compile through the same prompt-construction path

That means the migration path is additive rather than destructive.

## `/persona manage` Authoring Flow

The admin surface evolves without requiring a brand-new command family.

In the structured rollout, `/persona manage` remains responsible for:

- selecting active personas
- toggling evil mode
- creating custom personas
- editing details
- editing prompts and structured persona data
- duplicating personas
- deleting personas safely

The important design change is that custom persona authoring is no longer conceptually "write two giant prompts and hope for the best". The intended flow becomes:

1. choose a base persona or blank template
2. define identity and aliases
3. define voice, worldview, relationship, and scene-style traits
4. add or refine prompts and examples
5. preview the compiled persona contract
6. save and optionally activate

## Runtime Behavior

The persona-system rollout intentionally preserves a few important behaviors:

- one active speaking persona per reply
- queued follow-up personas instead of simultaneous multi-speaker output
- built-in alias and mode-switch semantics
- evil-mode scene-rule switching
- tool/admin rules staying outside guild-authored prompt control

This keeps persona quality stronger without weakening operational behavior.

## Testing And Verification

The implementation was protected with task-by-task regression coverage:

- compiler structure tests
- built-in persona definition tests
- `ai_brain` prompt-construction regression tests
- structured custom-persona schema tests
- legacy custom-persona adapter tests
- custom-persona inheritance tests
- `/persona manage` structured authoring tests
- scenario-style behavior contract tests

The point of this test strategy was not just "does it load" but:

- do personas stay distinct
- does evil-mode switching remain explicit
- do custom personas inherit correctly
- do legacy personas keep working
- do tool/admin/runtime sections survive the new compiler path

## Why This Matters

This feature is more than a prompt refactor.

It gives the bot:

- one authoritative persona runtime model
- better long-term maintainability
- stronger behavioral consistency
- safer custom-persona extensibility
- better testing around roleplay quality and competence

In practice, it reduces the risk that persona edits accidentally break utility, admin behavior, or prompt ordering while making custom personas much more robust than raw prompt blobs.
