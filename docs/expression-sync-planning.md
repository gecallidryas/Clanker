# Expression Sync / Caching Plan

## Summary

FemboiBot's current emoji and sticker flow is split across multiple unrelated caches, has no event-driven invalidation, and rebuilds expression context repeatedly in the AI path. The result is avoidable rescanning, stale asset risk after startup, and inconsistent behavior between prompt injection, tool-based selection, and final output normalization.

The recommended design is a hybrid expression system with:

- SQLite persistence as the durable catalog for guild expressions and application emojis
- in-memory snapshots as the hot read path
- event-driven sync for guild emoji/sticker changes
- fixed-interval background refresh for application emojis, with on-access fallback
- tool-first sticker selection with narrow, selective prompt exposure
- soft-delete plus prune lifecycle handling for removed guild expressions

This keeps the hot path cheap, survives restarts, and gives the AI a bounded, more reliable expression view without over-engineering v1 metadata.

## Current state audit

### Files reviewed

- `E:\femboibot\femboibot-sanitized-with-holy-water\discord_bot\utils\app_emojis.py`
- `E:\femboibot\femboibot-sanitized-with-holy-water\discord_bot\utils\emoji_manager.py`
- `E:\femboibot\femboibot-sanitized-with-holy-water\discord_bot\utils\expression_picker.py`
- `E:\femboibot\femboibot-sanitized-with-holy-water\discord_bot\utils\expression_tools.py`
- `E:\femboibot\femboibot-sanitized-with-holy-water\discord_bot\cogs\ai_brain.py`
- `E:\femboibot\femboibot-sanitized-with-holy-water\discord_bot\utils\db_handler.py`
- `E:\femboibot\tomoribot\docs\ai\expression-handling.md`

### Requested but missing

- `E:\femboibot\femboibot-sanitized-with-holy-water\docs\FEATURES.md` was not present, so the audit is code-driven rather than doc-driven.

### Current flow

#### Application emoji flow

- `get_application_emojis()` caches application emojis on `bot._app_emojis_cache`.
- The cache has no TTL, no invalidation, and no persistence.
- `EmojiManager.validate_emojis()` depends on this source to validate configured app emojis at startup.

#### Guild emoji flow

- `get_guild_emojis()` caches guild emojis on `bot._guild_emojis_cache[guild.id]`.
- This cache also has no TTL, no invalidation, and no persistence.
- `ai_brain._get_app_emojis()` merges guild emojis with application emojis at prompt-build time.

#### Sticker flow

- `expression_picker.py` keeps a separate module-level 5-minute cache of `guild.emojis` and `guild.stickers`.
- Sticker selection is name/random based.
- Stickers are not persisted in SQLite.
- Sticker prompt knowledge is rebuilt from `guild.stickers` during every prompt build.

#### AI prompt flow

- `ai_brain.build_prompt()` currently injects:
  - a raw server emoji list from `_get_app_emojis()`
  - a configured custom emoji section from `EmojiManager.build_prompt_section()`
  - a raw sticker section from `_build_sticker_knowledge()`
- This means prompt expression context is assembled on every AI turn instead of coming from a shared snapshot.

#### Final response flow

- After model generation, `ai_brain`:
  - cleans output
  - may append trigger emojis from `EmojiManager`
  - re-fetches guild/app emojis
  - runs `replace_custom_emojis()`
  - runs shortcode repair again
  - runs a final emoji repair pass
- This gives good safety coverage, but it is not backed by one authoritative expression snapshot.

#### Tool flow

- `select_sticker_for_response` and `react_with_emoji` use `expression_picker`.
- These tools do not share state with `EmojiManager` or the prompt builder beyond indirectly reading Discord guild caches.

### What is currently cached vs recomputed

#### Currently cached

- Application emojis in memory only, indefinitely
- Guild emojis in memory only, indefinitely
- Guild emojis + stickers in a separate 5-minute picker cache
- Configured app emoji validation results in `EmojiManager`

#### Currently recomputed

- Guild/app merged emoji knowledge for the prompt
- Sticker knowledge for the prompt
- Final response normalization against current guild/app emoji state
- Prompt exposure decisions for emoji/sticker availability

### Main problems in the current design

- There is no single expression source of truth.
- Guild emojis, stickers, and app emojis do not share one cache strategy.
- Sticker and emoji prompt exposure can grow larger than necessary.
- There is no event-driven sync for post-startup asset changes.
- There is no persistence layer for expression state in SQLite.
- Deleted assets can leave stale runtime state until a cache is naturally rebuilt.

## Design options

### Option 1: Unified in-memory cache only

Create one shared runtime `ExpressionService` that owns:

- per-guild emoji/sticker snapshots
- a global app emoji snapshot
- lookup maps for prompt building, tool selection, and final normalization

Pros:

- Lowest implementation cost
- Eliminates duplicated caches quickly
- Very fast on the hot path

Cons:

- No persistence across restarts
- Weaker recovery if events are missed
- Less useful for background refresh bookkeeping and lifecycle tracking

### Option 2: SQLite-first catalog

Persist all expressions and read SQLite as the normal source for prompt/tool/runtime decisions.

Pros:

- Durable and inspectable
- Easy to reason about state history
- Good for future admin-authored metadata

Cons:

- Adds DB reads to the hot path unless layered with memory anyway
- More expensive than needed for per-message access
- Still needs an in-memory layer to avoid repeated DB work

### Option 3: Hybrid persisted catalog plus hot snapshots

Use SQLite as the durable catalog and in-memory snapshots as the fast read path.

Pros:

- Best fit for FemboiBot's current architecture
- Survives restarts
- Supports event-driven invalidation
- Keeps hot-path reads cheap
- Gives a clean place for future manual metadata

Cons:

- Slightly more moving parts than memory-only
- Needs clear ownership so old caches can be retired cleanly

### Recommendation

Choose Option 3.

It is the best balance between reliability, low-overhead reads, restart recovery, and future extensibility. It also maps cleanly onto the existing SQLite-based configuration model in `db_handler.py`.

## Recommended architecture

### Core idea

Add a new `ExpressionService` that owns all expression reading, sync, ranking, and invalidation behavior.

This service should unify:

- guild emojis
- guild stickers
- application emojis

under one runtime API, while still respecting different sync strategies for guild assets versus app emojis.

### Runtime layers

#### 1. Durable catalog in SQLite

Persist expressions as first-class records:

- guild emojis
- guild stickers
- application emojis

This becomes the durable source of truth that survives restarts and supports lifecycle state.

#### 2. Hot in-memory snapshots

Load compact snapshots into memory for:

- per-guild expressions
- global app emojis

These snapshots are what prompt building, tools, and normalization should read on the hot path.

#### 3. Sync / reconciliation layer

One sync layer should handle:

- guild emoji/sticker event-driven refresh
- startup/reconnect reconciliation
- fixed-interval app emoji background refresh
- on-access fallback refresh when needed

### Data model

#### `expressions`

Unified persisted catalog table.

Suggested fields:

- `id` INTEGER PRIMARY KEY
- `scope_type` TEXT NOT NULL
- `scope_id` INTEGER NOT NULL
- `kind` TEXT NOT NULL
- `source` TEXT NOT NULL
- `discord_expression_id` TEXT NOT NULL
- `name` TEXT NOT NULL
- `normalized_name` TEXT NOT NULL
- `animated` INTEGER
- `format_type` INTEGER
- `discord_description` TEXT
- `available` INTEGER NOT NULL DEFAULT 1
- `snapshot_version` INTEGER NOT NULL DEFAULT 0
- `first_seen_at` TIMESTAMP NOT NULL
- `last_seen_at` TIMESTAMP NOT NULL
- `deleted_at` TIMESTAMP

Recommended uniqueness:

- unique on `(scope_type, scope_id, kind, discord_expression_id)`

Recommended values:

- `scope_type`: `guild`, `application`
- `kind`: `emoji`, `sticker`
- `source`: `guild_emoji`, `guild_sticker`, `app_emoji`

#### `expression_metadata_overrides`

Planned extension point for future manual metadata.

Suggested fields:

- `expression_id` INTEGER PRIMARY KEY
- `admin_description` TEXT
- `admin_tags_json` TEXT
- `updated_by` INTEGER
- `updated_at` TIMESTAMP

v1 does not need to populate this table, but the design should reserve it from day one so richer manual metadata can be added later without reshaping the core catalog.

#### `expression_sync_state`

Track sync bookkeeping per scope.

Suggested fields:

- `scope_type` TEXT NOT NULL
- `scope_id` INTEGER NOT NULL
- `last_sync_at` TIMESTAMP
- `last_background_refresh_at` TIMESTAMP
- `item_count` INTEGER NOT NULL DEFAULT 0
- `snapshot_version` INTEGER NOT NULL DEFAULT 0

Recommended uniqueness:

- unique on `(scope_type, scope_id)`

### Effective metadata rules in v1

The AI-facing effective metadata should be derived as:

- effective name: expression name
- effective description:
  - admin override description if present in the future
  - else Discord sticker description for stickers
  - else name-derived fallback
- effective tags:
  - empty in v1 unless future manual metadata exists

This keeps v1 simple while leaving a direct extension path.

### Snapshot shape

Each runtime snapshot should include:

- `snapshot_version`
- `refreshed_at`
- `stale` flag
- expressions by id
- expressions by normalized name
- prompt-safe shortlist material
- counts by kind/source

This allows one shared read path for:

- prompt building
- tool lookup
- normalization / repair

## Cache/invalidation rules

### In-memory TTLs

#### Guild snapshots

- 5-minute TTL
- refreshed or invalidated earlier when events arrive

#### Application emoji snapshot

- 10-15 minute TTL
- refreshed on a fixed interval globally
- on-access fallback if background refresh has not updated it in time

### Fixed-interval background refresh

Application emoji refresh should run on a fixed interval globally rather than jittered or purely demand-driven.

Recommended behavior:

- refresh the app emoji snapshot on a fixed schedule
- persist new state when changed
- update the hot app snapshot
- record refresh metadata in `expression_sync_state`

If the fixed refresh fails:

- keep serving the last hot snapshot if present
- keep the persisted app catalog intact
- allow the next on-access request to attempt a fallback refresh when stale

### Guild event-driven invalidation

Use Discord event handlers for:

- `on_guild_emojis_update`
- `on_guild_stickers_update`

Behavior:

- invalidate the affected guild slice immediately
- rebuild the relevant expressions from Discord state
- persist the refreshed catalog rows
- bump `snapshot_version`
- replace the in-memory snapshot

### Startup and reconnect behavior

On startup:

- do not eagerly deep-scan every guild unless needed
- initialize the service and persisted schema
- allow first access to hydrate from SQLite if available

On reconnect/resume:

- mark guild snapshots as suspect
- reconcile on next access or next relevant event

### Refresh source preference

When rebuilding a guild snapshot:

- prefer current Discord guild state (`guild.emojis`, `guild.stickers`) if populated
- fetch explicitly only when:
  - current cache is empty but persisted state exists
  - runtime send/react failure suggests stale data
  - a reconciliation check shows mismatch or suspect state

### Soft delete and prune rules

When a guild expression disappears from Discord:

- mark `available = 0`
- set `deleted_at = now`
- keep the row during a retention window

Retention decision:

- prune soft-deleted guild expressions after 7 days

Benefits:

- safer recovery from transient inconsistencies
- preserves short-term history for stale-id recovery
- avoids immediate churn from hard delete

Application emojis should follow the same persisted lifecycle pattern once they disappear from the authoritative refresh source.

### Runtime stale-asset recovery

If an emoji or sticker fails at send/react time:

- invalidate the relevant snapshot
- refresh once
- retry once
- if it still fails, degrade gracefully without crashing

This is especially important for:

- `react_with_emoji`
- `select_sticker_for_response` send path
- final shortcode normalization when a once-valid asset is gone

## AI context integration

### Goals

The AI should get enough expression information to make good choices without repeatedly injecting full raw inventories into the prompt.

### Default prompt policy

Always include:

- the existing curated emoji usage rules from `emoji_config.json`
- a compact summary of available expressions
- a small ranked emoji shortlist when relevant

Do not broadly enumerate stickers by default.

### Sticker policy

Stickers should remain tool-first by default.

Prompt exposure should be selective and narrow. Broader sticker metadata should only appear when the turn explicitly signals expressive behavior.

### What counts as explicit emote behavior

This should include:

- literal requests for a sticker
- literal requests for an emoji
- requests for an emote
- requests like "reply with a cute sticker"
- requests like "send a funny emote"
- requests for a more expressive or reaction-like response

This should not mean every casual emotional turn gets sticker inventory injected.

### Ranked prompt shortlist

For prompt-time expression exposure, rank against:

- user message lexical cues
- current mode
- affection state
- recent expression reuse penalty
- sticker name and Discord sticker description

Recommended default limits:

- guild emoji shortlist: small, such as 5-8 items
- sticker shortlist: none by default, or 1-3 items only on explicit emote turns

### Tool guidance

The prompt should explicitly preserve the model's ability to use:

- `select_sticker_for_response`
- `react_with_emoji`

The tool path should have access to the full runtime snapshot even when the prompt only sees a shortlist.

### Why this is better than the current flow

This reduces:

- repeated prompt bloat
- inconsistent sticker exposure
- model drift caused by seeing outdated or overly broad expression inventories

It also makes prompt selection and tool selection read from the same authoritative snapshot version.

## Migration phases

### Phase 1: Add the new expression persistence and service layer

Create:

- `E:\femboibot\femboibot-sanitized-with-holy-water\discord_bot\utils\expression_cache.py`
- `E:\femboibot\femboibot-sanitized-with-holy-water\discord_bot\utils\expression_sync.py`

Modify:

- `E:\femboibot\femboibot-sanitized-with-holy-water\discord_bot\utils\db_handler.py`

Responsibilities:

- define the new SQLite tables
- implement snapshot models
- implement hydrate/store helpers
- implement sync bookkeeping

### Phase 2: Move runtime readers onto the shared service

Modify:

- `E:\femboibot\femboibot-sanitized-with-holy-water\discord_bot\utils\expression_picker.py`
- `E:\femboibot\femboibot-sanitized-with-holy-water\discord_bot\utils\expression_tools.py`
- `E:\femboibot\femboibot-sanitized-with-holy-water\discord_bot\utils\app_emojis.py`

Responsibilities:

- retire the module-level picker cache
- stop using forever-memory guild/app caches as the primary state model
- route emoji/sticker selection through the shared runtime snapshot
- keep formatting/repair helpers in `app_emojis.py`, but move cache ownership into the service

### Phase 3: Update prompt injection and configured emoji behavior

Modify:

- `E:\femboibot\femboibot-sanitized-with-holy-water\discord_bot\utils\emoji_manager.py`
- `E:\femboibot\femboibot-sanitized-with-holy-water\discord_bot\cogs\ai_brain.py`

Responsibilities:

- make `EmojiManager` validate configured emojis through the shared app snapshot
- replace raw prompt-time scans with bounded shortlist logic
- make sticker exposure selective and tool-first
- make final response normalization use the shared snapshot version

### Phase 4: Add lifecycle hooks and background refresh

Modify:

- `E:\femboibot\femboibot-sanitized-with-holy-water\discord_bot\main.py`

Responsibilities:

- instantiate the new service
- register guild emoji/sticker update listeners
- start fixed-interval global app emoji refresh
- mark guild snapshots suspect on reconnect/resume

### Phase 5: Remove legacy cache ownership

Once the new service is stable:

- remove or thin the old forever-memory caches in `app_emojis.py`
- remove the standalone `_cache` in `expression_picker.py`
- ensure all expression reads go through the shared service

## Testing plan

### Unit tests

Add or extend tests for:

- snapshot build from persisted rows
- snapshot build from current Discord state
- lookup by id and normalized name
- prompt shortlist ranking
- sticker description matching
- soft-delete marking
- 7-day prune behavior

### Persistence tests

Cover:

- guild emoji persistence
- guild sticker persistence
- application emoji persistence
- sync state bookkeeping
- metadata override extension path presence

### Event-driven sync tests

Cover:

- guild emoji rename
- guild emoji add
- guild emoji delete
- sticker add
- sticker delete
- event-triggered version bumps

### Background refresh tests

Cover:

- fixed-interval global app emoji refresh
- persistence updates on changed app emojis
- hot-snapshot update after refresh
- on-access fallback after background refresh failure

### AI context tests

Cover:

- normal turns do not get broad sticker exposure
- explicit expressive turns do get selective sticker exposure
- default prompt stays bounded in size
- current mode and affection influence shortlist ranking

### Failure handling tests

Cover:

- deleted emoji between selection and reaction
- deleted sticker between selection and send
- stale snapshot invalidation and retry
- fallback to persisted state when live refresh fails

### Regression coverage to preserve

Keep or extend existing coverage around:

- shortcode repair
- malformed custom emoji repair
- trigger emoji selection
- expression tool behavior

## Open questions

- Fixed-interval global app emoji refresh cadence still needs a final numeric value.
- The exact threshold for switching from persisted guild snapshot to forced live reconciliation should be finalized.
- Whether manual metadata editing for future admin-authored descriptions/tags should be guild-admin-only, bot-owner-only for app emojis, or both has been decided conceptually as both, but the eventual permission model still needs operational detail.
- If future manual metadata is added, conflict resolution between global app emoji metadata and guild-local overrides will need a precedence rule.
