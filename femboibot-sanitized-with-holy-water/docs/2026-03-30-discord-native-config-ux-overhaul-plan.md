# Discord-Native Config UX Overhaul Plan

## Summary

This plan redesigns server configuration, tool management, and persona/presentation management around Discord-native interactive flows instead of many narrow slash subcommands. The v1 target is a panel-first UX built on current `discord.py` primitives that are already available in this repo: ephemeral embeds, buttons, string selects, channel/role/user selects, and focused modals for free-text input.

The new primary admin surfaces should be:

- `/config panel`
- `/tools manage`
- `/persona manage`

Config-adjacent top-level groups that currently live outside `/config` (`/staff`, `/modlog`, `/autorole`, `/welcome`) should route into the same panel architecture rather than remain permanent parallel entrypoints. `/tools refresh` should stay separate because it is an operational action, not persisted configuration.

These should replace the current command sprawl as soon as they are stable enough to land together. Since this project is not yet production, deprecation can be immediate. Old granular slash commands may exist briefly as migration shims during implementation, but they should not remain a long-term supported UX.

The design is guided by these product decisions:

- Config password auth is risk-based, not required for every mutation.
- Auth is required for secrets, destructive changes, and high-impact security/admin changes.
- Staff-role edits and modlog edits are high-risk.
- The design must work with current `discord.ui` primitives in v1.
- The architecture should remain ready for future `discord.py` upgrades or lower-level raw component work.
- Persona management includes active mode selection and evil-mode switching, not just CRUD for custom personas.
- Built-in and custom personas should appear in one combined admin surface, clearly grouped into sections.
- Active mode changes should log to the main audit trail.
- Audit categories should be normalized to a small fixed enum-like set, with flexible detail stored separately.

## Current UX audit

### Config UX

The current `/config` surface in `discord_bot/cogs/config.py` is too fragmented. It combines many unrelated concerns:

- password auth
- API keys
- model settings
- env upload
- feature toggles
- AI reply settings
- URL safety
- custom endpoint config
- staff roles
- modlog
- autorole
- welcome settings
- structure management

This creates several problems:

- Too many tiny subcommands for routine admin work.
- Related settings are edited through separate commands instead of one coherent surface.
- Bulk edits are awkward or impossible.
- Some flows are conceptually duplicated across `/config` and `/tools`.
- Several config-adjacent guild settings live outside `/config` entirely (`/staff`, `/modlog`, `/autorole`, `/welcome`), so admins must know command taxonomy rather than task intent.

The current `/config ui` panel is not a true bulk UX. It only allows switching one flag per interaction, so it reduces typing but does not actually solve configuration sprawl.

### AI settings UX

AI reply settings are currently split between:

- scalar values such as cooldown, threshold, self-reply limit, and streaming budgets
- channel whitelist add/remove/clear
- auto-channel add/remove
- thought/debug logging channel + level + modlog fallback

This is a bad fit for channel-heavy servers because admins must repeatedly invoke commands to reach a final desired state. It also splits one mental model ("how and where the bot auto-replies") across multiple unrelated commands. The storage model already supports bulk editing, but the UX does not.

### Tool management UX

`/tools status` exposes effective tool availability, but it is read-only. The underlying state actually comes from guild config feature flags. That means:

- admins think of tools and config as separate surfaces
- the implementation thinks of tools as feature-flagged config
- the UX does not provide a proper tool toggle panel

This split should be removed in favor of one capability-management model.

`/tools refresh` is useful, but it is not a configuration flow. It should remain a separate operational action command instead of being folded into the toggle panel.

### Persona UX

Custom persona creation and editing in `discord_bot/cogs/persona.py` already uses modals and views, but the flow is still admin-heavy:

- creation is multi-step and linear
- edit and delete are name-driven
- admins must know which persona they want before they can manage it
- active mode selection and persona presentation are not managed together

The current UX treats persona CRUD and live server presentation as separate concerns even though admins will think of them as one thing: "which persona is active, how does the bot present itself, and what persona definitions exist in this server?"

The current custom-persona limit is low enough (`MAX_PERSONAS_PER_GUILD = 5`) that a single combined built-in/custom selector is realistic for v1 if it is grouped clearly.

### Admin friction and slash-command sprawl

The current design still carries too much command-surface weight:

- many boolean toggles live as separate commands
- list management is mostly add/remove one item at a time
- some commands exist mainly to compensate for lack of a panel
- some legacy or parallel surfaces remain alongside newer app commands

This increases admin friction and makes documentation noisier than necessary.

### Permission model inconsistency

The current surface mixes `administrator` and `manage_guild` requirements by history rather than clear risk level. Most `/config` mutations require administrator, persona CRUD uses Manage Guild, and `/tools refresh` uses Manage Guild even though it lives under `/tools`. The overhaul should normalize permission expectations by task risk and command intent, not by which cog currently owns the command.

### Localization

Localization support exists in `discord_bot/utils/i18n.py`, but most config/persona/admin interaction text is hardcoded. Locale coverage is currently too thin for a richer interaction surface. A panel-based UX will require systematic localization of:

- section titles
- button labels
- placeholders
- validation messages
- auth prompts
- confirmation text
- deprecation guidance

### Documentation gap

The originally requested `docs/FEATURES.md` file was not present at the inspected path. That is a process issue as well as a UX issue: the command/config surface is evolving without one reliable high-level reference.

## Design options

### Option 1: Panel-first message UX

Use ephemeral message-based panels as the primary control surface.

Pattern:

- slash command opens a section overview
- buttons switch between config domains
- string selects and entity selects handle choices
- focused modals capture long text or structured text input
- save/cancel/confirm buttons finalize changes

Pros:

- Works cleanly with current `discord.py`
- Best fit for bulk editing with today's primitives
- Reduces slash-command sprawl immediately
- Easy to phase in by section

Cons:

- Some checkbox/radio-style interactions must be approximated with selects and buttons
- Complex multi-page state handling requires careful view management

### Option 2: Wizard-first guided flows

Replace command families with guided step-by-step setup wizards, such as:

- AI setup wizard
- welcome setup wizard
- persona setup wizard

Pros:

- Good for first-time admins
- Easy to teach and document as a linear path

Cons:

- Weak for routine edits
- Weak for bulk removal and large existing sets
- Slower for experienced admins

### Option 3: Future-oriented modal-heavy UX

Design toward true checkbox/radio modal inputs inspired by the Tomori docs, but keep a compatibility layer for current `discord.py`.

Pros:

- Could become the cleanest long-term UX
- Good match for bulk choose/confirm flows if library support improves

Cons:

- Not the safest v1 path
- Current runtime should not assume native checkbox/radio modal items are usable here
- Higher implementation complexity for little short-term gain

### Recommendation

Choose Option 1, implemented in a way that keeps Option 3 open later.

That means the v1 UX should be message-first and panel-first, but all state loading, rendering, and apply logic should be separated well enough that richer modal controls can replace some message interactions in the future without a system redesign.

## Recommended interaction patterns

### Toggle many boolean flags

Use a "Capabilities" panel as the default bulk toggle surface.

Pattern:

- one panel
- grouped multi-selects or grouped page views
- current state shown in the embed
- `Save`, `Reset defaults`, `Cancel`

Suggested groups:

- AI tools
- expression and media
- memory and learning
- safety and moderation

Rules:

- low-risk toggles should not require auth
- high-risk capability changes should prompt auth before save
- changes should be diffed and logged once per save action, not once per clicked control unless immediate-apply UX is explicitly chosen

### Pick one mode from many

Use a single-select persona/mode selector inside `/persona manage`.

The surface should show:

- current active mode
- whether evil mode is enabled
- whether the selected persona is built-in or custom
- presentation status such as avatar/banner if relevant

This is a routine presentation control and should normally not require auth unless paired with a high-risk change.

### Bulk remove entries

Use a paginated list of current entries with page-scoped multi-select removal.

Pattern:

- show up to one page of entries
- allow multi-select on current page
- `Remove selected`
- `Next`
- `Previous`
- separate `Clear all` danger action

Rules:

- standard removal can be one confirm step
- destructive "clear all" requires auth and explicit confirmation

### Manage whitelists/blacklists

Use separate `Add` and `Remove` flows within the same panel.

Add flow:

- channel/role/user select components where applicable
- allow multi-select when the component supports it

Remove flow:

- paginated string select over currently configured entries

Rules:

- security-sensitive allowlist/blocklist edits are high-risk
- show entity mention plus stable fallback ID
- deleted or inaccessible entities must still be manageable by ID representation

### Edit persona settings

Use `/persona manage` as the unified persona and presentation surface.

The combined selector should be grouped into:

- Currently active
- Built-in personas
- Custom personas

Actions for the selected persona:

- `Activate`
- `Toggle Evil Mode`
- `Preview`
- `Edit Details`
- `Edit Prompts`
- `Duplicate`
- `Delete` for custom personas only
- `Create New`

Rules:

- active mode switch logs under `persona_presentation`
- evil-mode switch lives in the same surface
- custom persona deletion is destructive and requires auth
- prompt edits may remain modal-based
- long free-text fields should continue to use focused modals

## Command families to target first

### 1. Config feature flags and tool toggles

Why first:

- highest slash-command sprawl reduction
- largest immediate UX win
- can share one capability editor between `/config panel` and `/tools manage`

Target outcomes:

- `/tools status` becomes a companion view, not the primary management path
- `/config toggle ...` commands become unnecessary
- `/tools refresh` stays separate as an operational action command

### 2. AI reply settings

Why second:

- strongest clear case for bulk editing
- mixes scalar values and list management
- already backed by a simple config row and serialized ID lists

Target outcomes:

- one AI settings panel
- bulk channel whitelist editor
- bulk auto-channel editor
- streaming and thought-log controls live in the same AI section instead of separate command leaves

### 3. Secrets, models, and custom endpoint routing

Why third:

- `/config keys`, `/config model`, `/config env`, and `/config custom_endpoint` are all part of one provider-management mental model
- these flows are high-risk enough to exercise the auth model, but still benefit from a unified overview
- they are a cleaner fit for section panels plus targeted modals than for dozens of separate slash leaves

Target outcomes:

- one authenticated "Providers and models" section inside `/config panel`
- masked read-only overview of configured keys, providers, and model choices
- modal-driven edits for secrets and custom endpoint values

### 4. Persona and presentation management

Why fourth:

- this is the most important qualitative UX improvement
- it benefits from shared panel primitives created in steps 1 to 3
- it should unify active mode selection, evil mode, and custom persona CRUD

### 5. Welcome, autorole, modlog, and staff roles

Why fifth:

- they fit naturally into section-based configuration
- they involve more auth/risk logic
- staff and modlog now need high-risk gating
- they are currently split across standalone top-level groups, so consolidation is part of the UX win

### 6. Remaining high-risk admin and structure-management flows

Why later:

- more destructive
- weaker bulk-edit value
- should follow once the interaction framework is stable

## Technical architecture

### Primary entrypoints

The new primary app-command surface should be:

- `/config panel`
- `/tools manage`
- `/persona manage`

`/tools manage` may internally route to the same capability editor as `/config panel`, but it should still exist as a clear top-level entrypoint for admins thinking in terms of tools rather than raw config.

Config-adjacent top-level groups such as `/staff`, `/modlog`, `/autorole`, and `/welcome` should become temporary shortcuts into `/config panel` rather than permanent separate management surfaces. `/tools refresh` should remain its own action command because it does not mutate persisted guild configuration.

### Transitional command behavior

Because immediate deprecation is acceptable, old granular commands should not be treated as a permanent supported surface. If they remain temporarily during development, they should:

- still perform the action
- call the same backend helpers as the new panels where possible
- return short success-plus-guidance messaging pointing to the new panel UX

Example guidance style:

- "Updated. This setting now lives in `/config panel`."
- "Done. Use `/persona manage` for the new bulk persona UX."

### Risk-based auth model

Auth is not required for every mutation.

Require auth for:

- secrets
- destructive changes
- high-impact security/admin changes

High-risk examples:

- API keys
- env upload
- custom endpoint credentials
- security-sensitive allowlist/blocklist changes
- staff-role edits
- modlog edits
- destructive clears
- custom persona deletion

Low-risk or routine examples:

- most standard feature toggles
- non-destructive scalar config edits
- active mode changes
- evil-mode switching
- ordinary welcome text edits

Specific decision:

- evil-mode switching stays low-risk in v1 while it only changes presentation mode/state
- if a future evil-mode flow also mutates protected assets or credentials, gate that asset-mutation step instead of turning every mode switch into a password-auth event

Implementation rules:

- validate permissions before opening the panel when possible
- validate risk and auth again on submit
- when auth is missing for a gated action, offer an ephemeral auth step instead of forcing the user to start over

### Audit trail model

Use the same main audit trail as the existing config changes.

The current `guild_config_audit` table only stores `action`, `field`, `old_value`, and `new_value`. Supporting normalized categories plus flexible details is not just a helper change; it likely requires either a schema extension or a compatibility wrapper that writes richer structured detail alongside the current columns.

Do not use free-form categories. Use a controlled enum-like set such as:

- `config_general`
- `config_security`
- `config_routing`
- `config_destructive`
- `persona_presentation`
- `persona_crud`
- `tools_config`

Store flexible meaning in detail fields, not the category. Suggested fields:

- `action`
- `target_type`
- `target_id`
- `old_value`
- `new_value`
- `summary`

This keeps queries stable while preserving human-readable context.

Recommendation:

- add an explicit `category` field and structured detail storage such as `detail_json`, or an equivalent normalized column set
- enforce allowed categories both in Python constants and at the database helper boundary
- keep a backward-compatible read path or migration for existing audit rows

### Panel and state architecture

Split the interaction system into three layers:

- state loading
- view rendering
- mutation application

Do not bury business logic directly inside button/select callbacks more than necessary.

Why:

- easier testing
- easier auth/risk enforcement
- easier future migration to richer modal components
- easier reuse across config, tools, and persona panels

### Pagination behavior

Use pagination for any list that can exceed comfortable single-message limits.

Recommended rules:

- use pages sized for readability, not just Discord max limits
- keep page controls consistent across panels
- preserve selection context only within the current page unless a draft-state model is intentionally added
- show current page and total pages in the embed footer

### Timeout behavior

Recommended defaults:

- 5-minute idle timeout for routine config panels
- 10-minute timeout for persona create/edit flows
- shorter timeout for destructive confirmation views

On timeout:

- disable components
- show clear expiration text
- instruct the user to reopen the panel rather than guessing state continuity

### Permission behavior

Rules:

- all mutating interactions must recheck guild permissions
- all mutating interactions must recheck invoker binding
- all high-risk interactions must recheck auth status at submit time
- only the original invoker should be able to use the ephemeral panel
- non-invokers should receive a short ephemeral refusal telling them to open their own panel

### Localization and i18n implications

The new UX requires significantly expanded localization coverage.

The following need translation keys:

- section titles
- descriptions
- button labels
- select placeholders
- empty states
- validation errors
- auth-required prompts
- confirmation text
- timeout text
- deprecation guidance
- audit summaries shown to users

The current `t()` helper is sufficient for v1, but the locale files (`discord_bot/locales/en.json` and `discord_bot/locales/ja.json`) must be expanded substantially. English should be the source of truth, with Japanese kept in sync as far as practical.

### File-by-file impact plan

#### `discord_bot/cogs/config.py`

Primary impact area.

Changes:

- add `/config panel`
- add shared config section routing
- migrate toggles into bulk capability panels
- migrate AI settings into a unified panel
- add a provider/models section that covers keys, model routing, env upload guidance, and custom endpoint config
- migrate URL safety into one editor surface
- migrate welcome, autorole, staff, and modlog into section panels
- keep current auth entrypoints only until the panel can launch the same risk-based auth step inline
- keep temporary shim commands only as needed during implementation

#### `discord_bot/cogs/tools_admin.py`

Changes:

- add `/tools manage`
- connect tool management to the same capability editor logic
- keep `/tools status` as a view/reporting surface
- keep `/tools refresh` as a separate operational command, not a config editor

#### `discord_bot/cogs/persona.py`

Primary impact area.

Changes:

- add `/persona manage`
- build one grouped combined selector for built-in and custom personas
- include active mode selection in the same surface
- include evil-mode switching in the same surface
- keep text-heavy creation/edit flows modal-based where appropriate
- reduce or remove reliance on name-driven management commands
- add persona presentation audit writes through the shared config audit path

#### `discord_bot/cogs/admin.py`

Lower initial impact.

Changes:

- align any future admin mutations with the same risk/auth conventions
- keep user-data reset/fact/affection commands separate from guild config UX
- optionally add guidance toward new panel surfaces where overlap exists

#### `discord_bot/utils/db_handler.py`

Moderate impact with at least one targeted audit-schema change.

Changes:

- add helpers for bulk list mutation if helpful
- extend or wrap `guild_config_audit` so normalized categories and structured detail fields are actually representable
- validate allowed audit categories at the helper boundary
- add helper methods for persona presentation audit writes if needed

#### `discord_bot/utils/i18n.py` and `discord_bot/locales/en.json` / `discord_bot/locales/ja.json`

Changes:

- no major helper redesign required
- add a large new key set for panel UX

#### `docs`

Changes:

- add this planning document
- restore or replace the missing high-level feature/config reference that was expected at `docs/FEATURES.md`
- later add updated admin/config usage documentation once implementation lands

## Rollout phases

### Phase 1: Shared primitives and overview surfaces

Build:

- reusable panel/view base patterns
- consistent save/cancel/confirm handling
- pagination and timeout conventions
- read-only overview panels
- audit-category scaffolding needed by later interactive saves

### Phase 2: Capabilities and tools management

Ship:

- `/config panel`
- `/tools manage`
- grouped bulk toggle UX

Outcome:

- old toggle commands can be removed or reduced to temporary shims quickly

### Phase 3: AI settings bulk editor

Ship:

- AI scalar settings panel
- bulk whitelist management
- bulk auto-channel management
- streaming and thought-log controls in the same AI section

Outcome:

- removes many awkward per-channel commands

### Phase 4: Providers, models, and custom endpoint section

Ship:

- authenticated provider/model overview inside `/config panel`
- modal-driven key and custom-endpoint edits
- masked state reporting and model routing controls

Outcome:

- high-risk provider configuration becomes one coherent flow instead of several unrelated slash leaves

### Phase 5: Unified persona and presentation management

Ship:

- `/persona manage`
- grouped combined selector
- active mode switch
- evil-mode switch
- custom persona CRUD

Outcome:

- persona and live presentation become one coherent admin UX

### Phase 6: Welcome, autorole, modlog, and staff

Ship:

- section editors for these remaining guild config domains
- risk-based auth enforcement for staff and modlog

### Phase 7: Cleanup

Ship:

- removal of temporary granular command shims
- updated documentation
- remaining polish and consistency fixes

## Testing plan

### Unit tests

Add or update tests for:

- risk classification
- auth-required vs non-auth-required actions
- bulk diff generation for toggles
- list add/remove/clear logic
- pagination boundaries
- audit category normalization
- audit schema compatibility or migration behavior
- persona presentation vs persona CRUD audit routing

### Interaction tests

Test view and callback behavior for:

- save
- cancel
- next/previous page
- remove selected
- clear all
- auth-required flow
- authenticated provider/modal handoff flow
- expired auth flow
- timeout behavior
- invoker-only enforcement

### Persona-specific tests

Test:

- built-in and custom persona grouping
- active mode switching
- evil-mode switching
- persona create/edit/delete flows
- selected active custom persona deletion fallback behavior

### Regression tests

Keep regression coverage around:

- legacy commands that remain temporarily as shims
- existing database behavior
- audit logging shape
- any interaction between persona deletion and active mode reset

### Manual QA

Manual guild QA should cover:

- empty state behavior
- large-server pagination behavior
- deleted role/channel handling
- stale panel behavior
- auth prompts for high-risk actions
- no-auth smooth flow for low-risk routine edits

### Localization checks

Add checks that:

- required English keys exist
- panel text never falls back accidentally because a key was forgotten
- Japanese keys are tracked and surfaced for completion work

## Open questions

No blocking product questions remain. Non-blocking implementation questions:

- Should structure-management create/delete commands stay under `/manage` permanently, or should `/config panel` eventually include a shortcut/read-only summary for them?
- If `discord.py` gains first-class support for richer modal checkbox/radio inputs during implementation, do we adopt them immediately or keep the v1 message-view controls stable until after rollout?
