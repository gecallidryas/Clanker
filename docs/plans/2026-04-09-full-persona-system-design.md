# Full Persona System Design

**Problem**

The current persona system is a mix of thin flat prompt files, built-in mode metadata, guild-scoped custom prompt blobs, affection overlays, and ad hoc runtime instructions in `discord_bot/cogs/ai_brain.py`. That makes roleplay quality fragile, utility behavior uneven, and custom personas structurally weaker than built-in modes. It also makes it hard to evolve persona behavior without editing large raw prompts that can accidentally break tool use, admin handling, or reply quality.

**Approved Direction**

Build a unified full persona system where built-in and guild custom personas compile through the same structured runtime contract before prompt assembly. The system should preserve practical utility while making roleplay stronger, more continuous, and more explicit about the distinction between normal-mode intimacy and `evil mode` escalation.

**Scope**

- Introduce a structured persona definition and compiler path shared by built-in and custom personas.
- Replace prompt-file-only built-in behavior with structured persona contracts plus authored fragments and dialogue examples.
- Add a schema-backed model for guild custom personas with inheritance from built-in personas.
- Keep a temporary compatibility path for existing custom personas that only have `normal_prompt` / `evil_prompt`.
- Add prompt-construction tests and behavioral regression fixtures that protect roleplay quality, utility, tool use, and evil-mode boundaries.

**Out of Scope**

- Reworking affection scoring thresholds or the current memory database model.
- Replacing the entire `/persona manage` surface in one pass.
- Multi-persona simultaneous speaking or persona-to-persona dialogue.
- Model-provider-specific prompt transport rewrites unrelated to persona compilation.

**Approach Options**

1. Rewrite prompt files only.
Rejected because it keeps the same brittle architecture and leaves guild personas as raw prompt blobs.

2. Add a shared roleplay contract plus stronger prompt files.
Good medium-term improvement, but still leaves custom personas structurally underpowered and keeps prompt logic too prose-heavy.

3. Build a full structured persona system with compiler, inheritance, and guild-schema support.
Approved because it is the most robust long-term path and gives built-in and custom personas one authoritative runtime model.

**Target Architecture**

- `discord_bot/personas/definition.py`
  - canonical dataclasses / typed dictionaries for persona identity, voice, worldview, relationship rules, normal-mode scene rules, evil-mode scene rules, utility rules, examples, and hard constraints
- `discord_bot/personas/builtin/`
  - built-in persona definitions for `mode_default`, `mode_femboy`, `mode_tsundere`, and `mode_oneesan`
- `discord_bot/personas/compiler.py`
  - compiles one persona plus overlays into ordered prompt sections
- `discord_bot/personas/custom.py`
  - loads guild custom personas from DB, resolves inheritance, and adapts legacy prompt-only personas
- `discord_bot/cogs/ai_brain.py`
  - stops loading a single prompt blob as the main persona source and instead asks the compiler for ordered persona sections
- `discord_bot/cogs/persona.py`
  - evolves toward structured authoring for custom personas while preserving legacy editing during migration
- `discord_bot/utils/db_handler.py`
  - adds schema support for structured persona storage and schema versioning

**Canonical Persona Definition**

Every persona should compile from the same shape:

- `identity`
  - `key`, `display_name`, `aliases`, `triggers`, `bio`, `avatar`, `banner`
- `voice`
  - `tone`, `cadence`, `verbosity_bias`, `signature_phrases`, `forbidden_phrases`, `punctuation_style`, `formality`
- `worldview`
  - how the persona frames humans, affection, authority, shame, praise, teasing, dependency, jealousy, or emotional distance
- `relationship_model`
  - tier-specific warmth, boundaries, compliance posture, and escalation behavior
- `interaction_style`
  - how the persona answers questions, gives advice, refuses, asks clarifiers, comforts, jokes, and flirts
- `scene_style_normal`
  - allowed amount of action beats, body language, sensory detail, suggestiveness, and narrative prose in normal mode
- `scene_style_evil`
  - explicit escalation contract when `evil mode` is enabled and the user steers into erotic or highly intimate roleplay
- `utility_rules`
  - how the persona stays useful, concise when needed, tool-competent, and compliant with admin / permission gates
- `examples`
  - curated sample replies for utility, teasing, comfort, flirtation, refusal, and evil-mode escalation
- `constraints`
  - hard rules and invariants

**Prompt Compiler**

The compiler should emit explicit ordered sections instead of relying on one large raw persona text:

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

Then `discord_bot/cogs/ai_brain.py` should append existing dynamic runtime sections such as affection state, user gender/addressing notes, wellbeing notes, memories, tools, admin permissions, and conversation context.

The key rule is that shared runtime behavior must be structural and high priority. Persona text should flavor the output, not replace tool/admin/memory contracts.

**Built-In Personas**

Built-in modes remain defined in `discord_bot/modes/*.py` for identity, aliases, switching, banners, and activity metadata, but the actual persona brain should move into structured definitions under `discord_bot/personas/builtin/`.

Each built-in persona should gain:

- explicit worldview and emotional logic instead of adjective-only prompt prose
- separate normal-mode and evil-mode scene rules
- dialogue examples that demonstrate utility and roleplay together
- constraints that stop drift

`Clanker` specifically should be modeled as:

- precise, cold, highly observant, quietly disdainful
- privately convinced humans are noisy, inefficient, emotional, and often stupid
- outwardly controlled and never openly confesses that contempt unless a sharper conflict path explicitly allows it
- useful first, but with subtext that feels more alive and less generic

**Guild Custom Personas**

Guild custom personas should become first-class personas under the same compiler instead of raw prompt exceptions.

Guilds should be able to configure:

- identity
- voice
- worldview
- relationship style
- normal-mode scene style
- evil-mode scene style
- examples
- constraints
- inheritance base

Guilds should not directly replace:

- tool-call rules
- admin-action rules
- memory/addressing scaffolding
- permission and safety gates
- top-level prompt assembly order

The authoring model should default to structured fields plus dialogue examples. Raw full-prompt override can exist as an expert compatibility escape hatch, but not as the default authoring surface.

**Inheritance Model For Custom Personas**

Custom personas should be able to inherit from:

- `blank`
- `mode_default`
- `mode_femboy`
- `mode_tsundere`
- `mode_oneesan`
- another future custom persona only if that is later proven necessary

Inheritance should merge:

- defaults from the base persona
- guild-authored overrides
- runtime overlays such as affection state and evil-mode state

Inheritance is important because most guild personas are variants of an archetype, not entirely new universes.

**Database Model**

Current custom personas in `discord_bot/utils/db_handler.py` store `normal_prompt`, `evil_prompt`, aliases, bio, and persona traits. The new schema should add versioned structured columns, preferably JSON text fields for incremental rollout:

- `schema_version`
- `base_template`
- `identity_json`
- `voice_json`
- `worldview_json`
- `relationship_json`
- `scene_normal_json`
- `scene_evil_json`
- `utility_json`
- `examples_json`
- `constraints_json`
- `author_notes_text`
- `legacy_normal_prompt`
- `legacy_evil_prompt`

Legacy prompt fields should remain during migration, but no new custom persona should rely on them as the primary source of truth.

**Legacy Compatibility**

Existing custom personas should continue working through a legacy adapter:

- load the current DB record
- wrap `normal_prompt` / `evil_prompt` into a low-priority authored text block
- preserve aliases, bio, and current mode key behavior
- mark the persona as legacy-backed until an admin upgrades it in `/persona manage`

This avoids breaking existing guilds while still shifting the system toward the structured compiler.

**Authoring UX**

The existing persona creation flow in `discord_bot/cogs/persona.py` should evolve rather than be replaced immediately.

Recommended custom persona workflow:

1. Choose a base persona or `blank`
2. Set identity and aliases
3. Fill structured voice / worldview / relationship / scene-style fields
4. Add 5-12 sample dialogues
5. Preview the compiled persona contract
6. Test against canned scenarios
7. Save and optionally activate

This keeps persona creation understandable for admins while making outputs more robust.

**Testing Strategy**

Prompt construction and behavior both need protection.

Prompt tests should verify:

- compiler output section order
- evil-mode sections only appear when enabled
- built-in and custom personas produce the same structural sections
- inheritance merges correctly
- legacy custom persona adaptation preserves authored content

Behavioral fixture tests should cover:

- practical help prompts
- affectionate but non-explicit prompts
- normal-mode roleplay prompts with light action beats
- evil-mode erotic escalation prompts
- tool-use requests
- admin-mutation requests
- refusal and boundary cases

Success means:

- all modes sound distinct
- all modes remain useful on practical tasks
- normal mode supports immersive action beats without routinely becoming graphic
- evil mode escalates clearly when user steering is explicit
- custom personas inherit shared utility/tool/admin rules automatically

**Rollout Plan**

- Phase 1: add the compiler and runtime model behind a feature flag or internal toggle
- Phase 2: port one built-in persona end to end, verify prompt and behavior tests
- Phase 3: port the remaining built-ins
- Phase 4: add structured DB support and custom persona inheritance
- Phase 5: migrate `/persona manage` to structured authoring
- Phase 6: retire legacy prompt-only custom persona creation, keeping read compatibility for one release window

**Failure Modes**

- persona flattening, where every mode sounds the same
- utility collapse, where stronger roleplay weakens practical help
- explicitness leak, where normal mode becomes too graphic
- custom override corruption, where guild prompts suppress tool/admin contracts
- migration loss, where existing custom personas lose tone or aliases

**Mitigations**

- keep shared utility/tool rules in dedicated high-priority compiler sections
- separate normal-mode and evil-mode scene rules structurally
- use scenario-based regression tests across all personas
- keep legacy adapter support during migration
- preview compiled prompt sections before activation for custom personas

**Decision**

Build the full structured persona system and treat guild custom personas as first-class compiled personas with inheritance, schema versioning, and a legacy adapter path. This is the strongest path for maximizing roleplay quality without sacrificing competence, maintainability, or customizability.
