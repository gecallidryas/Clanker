# Summary

This document proposes a memory-system redesign for FemboiBot that separates durable server memory, durable personal memory, ephemeral short-term summary memory, and document/RAG memory into explicit layers with explicit privacy and deletion semantics.

The recommended design keeps the current storage model intact where it already fits:

- Per-guild SQLite remains the primary store for bot state and non-document memory.
- Optional Postgres plus pgvector remains the document/RAG store.
- Migration is additive and compatibility-first rather than a full database replacement.

The core design goal is to remove the current semantic overload where multiple different concepts are stored and consumed as generic "facts" while preserving existing guild data and user facts during rollout.

This plan is based on the current sanitized repo contents. The originally requested input file `docs/FEATURES.md` was not present in this copy of the repository, so the audit is grounded in the code paths that currently implement memory behavior.

# Current state audit

## High-level state

FemboiBot currently has partial memory separation in code, but not in architecture. The system distinguishes some memory types through flags and helper functions, yet the storage, permissions, deletion flows, and prompt assembly logic still treat several different concepts as variations of the same underlying data model.

The result is a memory system with ambiguous ownership, inconsistent privacy enforcement, and weak boundaries between:

- long-lived personal facts
- long-lived server facts
- temporary channel-scoped memory
- persona teaching/configuration
- document retrieval memory

## Current storage model

### SQLite

Per-guild SQLite is the main persistent store.

The current `user_facts` table acts as the main memory table and contains:

- `guild_id`
- `user_id`
- `fact`
- `source`
- `learned_from_user_id`
- `memory_type`
- `created_at`

`memory_type` is currently used to distinguish:

- `personal`
- `long_term`
- `short_term`
- `server`

This is the main semantic overload in the current system.

Server memory is implemented as:

- `memory_type = 'server'`
- `user_id = 0`

Short-term memory is implemented as:

- `memory_type = 'short_term'`
- channel scope encoded into the `source` string using a `short_term:channel:<id>` tag

This means channel scoping is not a first-class part of the schema.

### Persona teaching

Persona teaching is already stored separately in:

- `persona_attributes`
- `sample_dialogues`

This is structurally correct, but prompt assembly currently consumes these alongside memory layers without a strong conceptual distinction between "persona configuration" and "memory."

### Pending facts

There is an existing `pending_facts` table with expiry support. This is a useful foundation for future consent or confirmation-based personal memory workflows, but it is not currently integrated as a general privacy boundary for all user memory writes.

### Postgres / pgvector

Optional Postgres is used for document RAG only.

Current tables:

- `documents`
- `document_chunks`

Current document storage includes:

- guild scope
- title
- source
- content hash
- uploader id
- metadata
- chunk text
- vector embedding

This is already a separate memory subsystem in practice, but it lacks richer lifecycle metadata and does not currently share unified deletion/export semantics with the rest of the memory model.

## Current command and permission model

### Personal and server memory

Current user-facing commands include:

- `!remember`
- `/remember personal`
- `/remember server`
- `!forget`
- `/forget`
- `!myinfo`
- `/myinfo`
- `!aboutuser`
- `/aboutuser`

Current permission behavior:

- personal memory can be written by normal users
- server memory requires `Manage Server`
- document upload/delete requires `Manage Server`

### Privacy

There is a per-user guild-scoped `personal_memory_opt_out` flag stored in `user_profiles`.

Current behavior is incomplete:

- it blocks self-teaching tool writes for `personal`, `short_term`, and `long_term`
- it does not clearly block manual personal-memory writes through the user commands
- it does not clearly block prompt retrieval of already-stored personal memory
- it does not clearly block mention-based lookup of another user's personal facts

This is the largest privacy gap in the current design.

### Admin capabilities

Admins currently have broad access through profile view and reset commands. They can:

- view full user profiles
- view facts
- reset facts
- reset aliases
- reset affection

This is broader than the desired future boundary. The user has now explicitly chosen:

- admins should have count/ID-only plus delete powers for personal memory
- admins should not have raw full-content read access to other users' personal memory by default

## Current prompt assembly behavior

`build_prompt()` currently assembles the model context by pulling from multiple layers in one flat pass:

- persona prompt and mode
- affection state
- server memory
- persona attributes
- RAG chunks
- mentioned-user facts
- short-term memory
- personal memory
- sample dialogues
- conversation history

Problems in the current assembly:

- server memory and long-term server knowledge are mixed under a generic section
- personal and long-term memory are merged into one "LONG-TERM/PERSONAL MEMORY" section
- short-term memory is retrieved separately, but still from the generic facts system
- mention lookups do not have a clear privacy contract
- retrieval is based on list slicing rather than relevance or policy-aware selection

## Current short-term memory behavior

Short-term memory exists in two overlapping forms:

1. persistent DB-backed short-term entries in `user_facts`
2. a separate in-memory cache module for short-term summaries and snippets

The in-memory cache module is not currently the primary prompt source. The active prompt path reads:

- channel conversation context from in-memory conversation buffers
- short-term facts from SQLite

This creates architectural ambiguity about what "short-term memory" actually means.

## Current document/RAG behavior

The document pipeline is already clearly separate at runtime:

- upload through `/teach document`
- parse and chunk text
- embed chunks
- store metadata in `documents`
- store vectors in `document_chunks`
- retrieve top-k chunks during prompt assembly

This is good separation, but the policy boundary is incomplete:

- deletion is document-id based
- there is no broader export policy
- there is no unified metadata for retention, revision, or ownership lifecycle

## Current ambiguities and overloads

The main ambiguities to fix are:

1. `user_facts` currently means four different things.
2. `source` is overloaded to carry provenance and channel scope.
3. personal-memory opt-out is not a complete retrieval/write policy.
4. admin powers are broader than the desired privacy boundary.
5. persona teaching is separate in storage but not clearly separate in policy.
6. short-term memory exists in both DB and in-memory forms without one canonical role.
7. document memory is separate in storage but not in user-visible data-governance semantics.

# Design options

## Option 1: Keep a single memory table and formalize it

### Description

Retain a unified SQLite memory table and evolve it into a richer registry with first-class columns for:

- scope
- owner type
- subject user
- channel scope
- visibility
- expiry
- status
- deletion policy

### Pros

- Lowest schema disruption
- Simplest migration from current `user_facts`
- Minimal code churn in the short term

### Cons

- Preserves conceptual overload in the main storage model
- Makes privacy, deletion, and export logic harder to reason about
- Encourages future policy leakage between memory classes
- Keeps document memory conceptually disconnected anyway

### Assessment

This is workable but not ideal. It solves schema cleanliness better than the current state, but it does not create strong enough conceptual boundaries.

## Option 2: Split-store architecture by memory class

### Description

Create explicit stores for each non-document memory class in SQLite:

- `server_memories`
- `personal_memories`
- `short_term_memory`

Keep persona teaching separate:

- `persona_attributes`
- `sample_dialogues`

Keep document memory separate in Postgres:

- `documents`
- `document_chunks`

### Pros

- Clearest semantics
- Strongest fit for privacy and deletion rules
- Best match for the chosen guild-scoped personal memory policy
- Easiest to reason about in prompt assembly
- Compatible with current SQLite plus optional Postgres architecture

### Cons

- Requires more migration work than Option 1
- Requires a compatibility layer during rollout
- Introduces more repository/service functions

### Assessment

This is the best fit for the current repo and constraints. It creates clear boundaries without requiring a full storage replacement.

## Option 3: Event-log memory architecture with derived views

### Description

Store all memory writes as immutable events and derive current memory state into materialized or computed views for:

- server memory
- personal memory
- short-term summaries
- documents

### Pros

- Best auditability
- Best compliance story
- Easy to track provenance and state transitions

### Cons

- Largest implementation cost
- Too complex for current repo maturity
- Not justified by current feature set
- Would likely require broader persistence and caching redesign

### Assessment

This is not recommended now. It is overbuilt relative to the current system and conflicts with the goal of avoiding an immediate full DB replacement.

# Recommended memory architecture

## Recommendation

Adopt Option 2: a split-store architecture with explicit memory classes.

This design best matches the current repo because:

- SQLite is already the canonical per-guild state store
- memory is already guild-scoped in practice
- RAG is already separate in Postgres
- the migration can be additive and safe
- privacy semantics become easier to enforce consistently

## Core design principles

1. Personal memory remains strictly guild-scoped.
2. Personal memory is user-owned.
3. Server memory is guild-owned.
4. Short-term memory is ephemeral and never treated as durable fact by default.
5. Document memory is retrieval-only knowledge and never silently promoted into facts.
6. Persona teaching is bot configuration, not memory.
7. Privacy controls apply at both write time and retrieval time.

## Exact boundaries and semantics

### Server memory

Server memory is durable, guild-owned knowledge about the server itself.

It should contain:

- server norms
- community conventions
- recurring channel usage patterns
- stable server facts
- server-specific roleplay or bot-behavior context that belongs to the guild rather than a person

It should not contain:

- personal user preferences
- temporary channel conversation state
- uploaded documents
- persona prompt configuration

Properties:

- scope: guild
- lifetime: durable until deleted
- owner: guild
- write permission: admin or `Manage Server`
- read permission in prompt assembly: allowed for all bot responses in that guild
- deletion: admin-only
- export: guild-admin export only

### Personal memory

Personal memory is durable, guild-scoped, user-owned memory about a specific member in a specific guild.

It should contain:

- stable preferences
- self-declared identity preferences
- long-lived dislikes/likes
- durable facts the user wants the bot to remember in that guild

It should not contain:

- short-lived conversation goals
- inferred temporary moods
- raw transcripts
- server facts
- document excerpts

Properties:

- scope: guild plus user
- lifetime: durable until deleted
- owner: target user
- write permission:
  - direct self-write always allowed unless personal memory is opted out
  - third-party durable write should require confirmation or a moderation/admin override
- read permission in prompt assembly:
  - for the current user, yes if not opted out
  - for mentioned users, only if their privacy setting allows mention-based lookup
- deletion:
  - user can delete own personal memory
  - admin can delete by ID
- export:
  - user can export own personal memory
  - admin gets count/ID metadata only, not raw full export by default

### Short-term summary memory

Short-term summary memory is ephemeral recency memory used to preserve working context that should survive beyond the immediate raw message window without becoming long-term fact.

It should contain:

- active conversation goals
- open loops
- recent temporary preferences
- recent coordination context
- compact summaries of recent channel and guild activity

It should be split into two scopes:

1. channel recency summary
2. small guild-wide recency summary for cross-channel continuity

The user has explicitly chosen to support a small guild-wide recency summary for multi-channel conversations.

Properties:

- scope:
  - channel summary: guild plus channel
  - guild recency summary: guild
- lifetime: TTL-based
- owner: system-managed
- write path:
  - generated from recent interaction context
  - may also accept explicit model tool writes for temporary context
- retrieval:
  - channel summary first
  - guild summary second, with tighter size limits
- deletion:
  - `/tools refresh` clears channel-bound short-term memory and resets context boundary
  - admin can clear guild-wide recency summary
  - expired entries self-prune
- promotion rule:
  - never auto-promote into personal or server memory without explicit user/admin confirmation

### Document / RAG memory

Document memory is server-owned knowledge uploaded as external files and consumed only through retrieval.

It should contain:

- uploaded text
- markdown
- PDF knowledge sources
- chunked embeddings

It should not contain:

- user facts
- temporary chat memory
- persona prompts

Properties:

- scope: guild
- lifetime: durable until deleted
- owner: guild
- write permission: admin or `Manage Server`
- retrieval: top-k chunk injection only
- deletion: admin-only by document id or title
- export: admin-only document metadata plus optionally original text
- promotion rule: document content never becomes server memory or personal memory unless explicitly summarized and saved through a separate workflow

## Persona teaching boundary

Persona teaching remains a separate configuration layer:

- `persona_attributes`
- `sample_dialogues`

These should be treated as bot-behavior configuration, not as memory. They belong in prompt assembly, but outside the memory policy model.

# Data model and privacy rules

## SQLite changes

## New tables

### `server_memories`

Columns:

- `id`
- `guild_id`
- `content`
- `category`
- `source`
- `created_by_user_id`
- `created_at`
- `updated_at`
- `is_deleted`
- `deleted_at`
- `deleted_by_user_id`

Notes:

- `category` can begin simple and optional
- soft-delete is useful for audit and rollback during rollout

### `personal_memories`

Columns:

- `id`
- `guild_id`
- `user_id`
- `content`
- `category`
- `source`
- `status`
- `created_by_user_id`
- `confirmed_by_user_id`
- `created_at`
- `updated_at`
- `is_deleted`
- `deleted_at`
- `deleted_by_user_id`
- `legacy_fact_id`

`status` values:

- `confirmed`
- `pending`
- `rejected`
- `admin_override`

Notes:

- `legacy_fact_id` supports migration traceability
- `created_by_user_id` and `confirmed_by_user_id` make consent explicit

### `short_term_memory`

Columns:

- `id`
- `guild_id`
- `channel_id`
- `user_id`
- `scope_kind`
- `memory_kind`
- `content`
- `source_message_id`
- `created_at`
- `updated_at`
- `expires_at`

`scope_kind` values:

- `channel`
- `guild`

`memory_kind` values:

- `summary`
- `observation`
- `open_loop`

Notes:

- `user_id` can be nullable for guild-wide summaries
- this table should be compact and aggressively pruned

## Existing tables to keep

Keep:

- `user_profiles`
- `persona_attributes`
- `sample_dialogues`
- `pending_facts`

Extend `user_profiles` with privacy controls instead of replacing it.

Recommended added fields:

- `allow_mention_fact_lookup INTEGER DEFAULT 0`
- `personal_memory_export_enabled INTEGER DEFAULT 1`
- `privacy_updated_at`

## Postgres changes

Keep `documents` and `document_chunks`, but add stronger lifecycle metadata.

Recommended changes:

- add `updated_at`
- add unique constraint on `(guild_id, title)` or equivalent normalized title
- add `text_content` or stored source text
- add `embedding_model`
- add `embedding_family`
- add `is_deleted` or soft-delete support only if needed operationally

These changes keep Postgres optional and scoped only to document memory.

## Privacy controls

### Personal memory opt-out

If a user opts out of personal memory in a guild:

- no new personal memories may be written for them
- no new short-term user-scoped memory may be written for them
- their personal memory must not be injected into prompts
- mention-based fact lookup about them must be disabled

Existing server memory and document memory remain unaffected.

### Mention-based lookup

Default future policy:

- disabled unless the target user explicitly allows it

This prevents `aboutuser` style visibility from becoming an accidental privacy leak.

### Admin visibility

The chosen admin boundary is:

- admins can see counts and IDs for personal memory
- admins can delete specific personal-memory rows by ID
- admins do not get unrestricted raw content browsing of another user's personal memory by default

Admin-visible metadata should include:

- memory ID
- memory type
- created_at
- source
- status

Admin-hidden by default:

- full memory text

Exception path:

- if a future moderation override is added, it should be explicit, audited, and narrowly scoped

## Export rules

### User export

Users can export their own guild-scoped personal memory in a guild.

Export should include:

- memory IDs
- content
- status
- source
- created_at
- updated_at

Users may also export:

- their own user-scoped short-term memory that has not expired yet

Users should not export:

- server memory unless separately allowed as a guild-admin export
- other users' personal memory
- full RAG corpus unless they are guild admins

### Admin export

Guild admins can export:

- server memory
- document metadata and optionally source documents
- aggregate personal-memory counts and IDs

Guild admins should not receive unrestricted raw export of another user's personal memory by default.

## Delete rules

### User deletion

Users can delete:

- their own personal memory
- their own unexpired user-scoped short-term memory

Users cannot delete:

- server memory
- documents
- another user's personal memory

### Admin deletion

Admins can delete:

- server memory
- document memory
- guild recency summaries
- personal-memory rows by ID

Admins should not bulk-wipe all personal memory content casually. Bulk delete should require explicit confirmation and audit logging.

## Audit expectations

All delete and export operations should be audited with:

- actor user id
- target user id or guild id
- memory class
- record ids affected
- timestamp
- operation type

# Context assembly strategy

## Goals

Context assembly should:

- use the smallest amount of memory needed
- preserve policy boundaries between layers
- avoid treating temporary recency as durable fact
- avoid treating documents as facts
- make privacy enforcement happen before prompt injection

## Recommended context order

1. persona configuration
2. system rules and guild config
3. server memory
4. current-user personal memory
5. mentioned-user personal memory, if privacy allows
6. short-term channel summary
7. short-term guild-wide recency summary
8. RAG document snippets
9. raw conversation timeline

## Layer-specific consumption rules

### Server memory

Use:

- top relevant stable items
- hard cap of about 3 to 5 entries

Selection priority:

- category match
- explicit recent usage
- recency of update

### Personal memory

Use:

- top relevant items for the current user
- around 3 to 5 entries

Selection priority:

- explicit preference match
- semantic similarity to current request
- recency of confirmation or update

Mentioned users:

- include only if the target user allows mention-based lookup
- include at most 1 to 3 highly relevant items

### Short-term channel summary

Use:

- one compact summary
- optional 1 to 3 open-loop items

This should represent:

- what the current channel conversation is trying to do
- temporary context not worth storing durably

### Short-term guild-wide recency summary

Use:

- one very small summary block
- only when relevant to cross-channel continuity

This should represent:

- recent bot-relevant guild context
- active topics that may matter outside one channel

It should be much smaller and less trusted than channel summary memory.

### Document RAG memory

Use:

- top 3 to 4 chunks
- similarity threshold
- clear source labeling

RAG should remain retrieval-only context and should not be re-expressed internally as "facts."

## Promotion and demotion rules

### Short-term to personal

Allowed only when:

- the user explicitly asks the bot to remember something durable
- or the user confirms a pending suggestion

### Short-term to server

Allowed only when:

- an admin explicitly saves stable guild context

### RAG to server/personal

Never automatic.

Only allowed through an explicit summarization-and-save workflow with normal permissions.

# Migration phases

## Phase 0: Preparation

- add the new tables to SQLite
- add the new metadata columns to Postgres document tables where needed
- introduce repository/service helpers that can read from both legacy and new stores
- add structured audit logging for export/delete actions

No user-visible behavior changes in this phase.

## Phase 1: Backfill and mapping

Backfill current `user_facts` rows into the new schema.

Mapping rules:

- `memory_type = 'server'` and `user_id = 0` -> `server_memories`
- `memory_type = 'personal'` -> `personal_memories(status='confirmed')`
- `memory_type = 'long_term'` -> `personal_memories(status='confirmed')`
- `memory_type = 'short_term'` -> `short_term_memory`

For legacy short-term rows:

- parse channel id from the current `source` tag
- write `scope_kind='channel'`
- use `memory_kind='observation'` by default

Preserve source traceability with:

- `legacy_fact_id`
- original `source`
- original `created_at`

## Phase 2: Dual-read and dual-write

For a temporary migration window:

- new writes go to the new tables
- optionally mirror writes to legacy `user_facts` for rollback safety
- reads prefer new tables
- reads fall back to legacy rows if the migrated row is missing

This phase should include metrics on:

- write counts by memory class
- read fallback rates
- delete-path correctness

## Phase 3: Prompt assembly switch

Switch context assembly to the new memory services:

- server memory from `server_memories`
- personal memory from `personal_memories`
- short-term summaries from `short_term_memory`
- documents from Postgres RAG

At this point:

- privacy filtering should happen before selection
- relevance selection should replace raw "first 10" slicing

## Phase 4: Command and policy cleanup

Update command behavior to align with final semantics:

- `/remember personal` writes durable personal memory
- `/remember server` writes durable server memory
- `/forget` maps cleanly to each memory class
- `/personal privacy` blocks both writes and reads for personal memory
- admin tools shift to count/ID-only plus delete for personal memory
- add explicit export commands

## Phase 5: Legacy retirement

After one stable release cycle:

- stop writing legacy `user_facts` rows for new memory traffic
- keep a one-time migration check for older guild databases
- eventually remove legacy fallback reads

## Rollback strategy

Rollback should remain possible until legacy reads are removed.

Rollback requirements:

- legacy data remains untouched until final cutover
- migration scripts are idempotent
- dual-read path remains available during rollout

# Testing plan

## Test categories

### Schema and migration tests

Add tests that verify:

- legacy `personal` rows migrate correctly
- legacy `long_term` rows migrate correctly
- legacy `server` rows migrate correctly
- legacy `short_term` rows migrate correctly with channel extraction
- migrated rows preserve timestamps and provenance

### Privacy tests

Add tests that verify:

- opt-out blocks personal-memory writes
- opt-out blocks short-term user-scoped writes
- opt-out blocks retrieval in prompt assembly
- opt-out blocks mention-based lookup
- mention-based lookup only works when the target user allows it

### Permission tests

Add tests that verify:

- admins can manage server memory
- admins can manage documents
- admins can view personal-memory counts and IDs only
- admins can delete personal-memory rows by ID
- admins cannot bulk-read raw personal-memory text by default
- users can export and delete only their own data

### Context assembly tests

Add tests that verify:

- context layer ordering
- caps per layer
- privacy filtering happens before prompt injection
- short-term guild summary is smaller and lower priority than channel summary
- RAG snippets remain separate from fact memory
- short-term memory does not auto-promote to long-term memory

### Short-term lifecycle tests

Add tests that verify:

- channel summary expiry
- guild recency summary expiry
- `/tools refresh` clears channel-level short-term memory
- guild-level recency summaries can be cleared separately

### RAG tests

Add tests that verify:

- document metadata lifecycle
- document deletion semantics
- retrieval threshold behavior
- document export and admin-only access rules

## Existing tests to reuse and extend

The repo already contains useful coverage that should be extended rather than replaced:

- `tests/test_memory_command_migration.py`
- `tests/test_short_term_channel_memory.py`
- `tests/test_short_term_memory_cache.py`
- `tests/test_rag_store.py`
- `tests/test_memories_summary_safety.py`
- `tests/test_teach_summary_safety.py`
- `tests/test_memory_limits.py`

## Rollout plan

### Stage 1: Hidden schema rollout

- deploy schema additions only
- no user-visible changes
- monitor initialization and migration safety

### Stage 2: Internal dual-write rollout

- enable new writes for a small set of guilds
- compare old/new counts
- log policy mismatches

### Stage 3: Prompt read rollout

- switch a small cohort of guilds to new prompt assembly
- observe response quality
- verify privacy filters

### Stage 4: Command policy rollout

- enable final command semantics
- enable export/delete surfaces
- change admin visibility boundary

### Stage 5: Full rollout and legacy deprecation

- expand to all guilds
- remove dual-write
- later remove legacy read fallback

## Success criteria

The rollout is successful when:

- existing personal and server facts remain accessible after migration
- short-term memory is clearly distinct from durable memory
- privacy opt-out is consistently enforced on both writes and reads
- admin boundaries match the chosen count/ID-only plus delete model
- cross-channel recency works through a small guild-wide summary without polluting durable memory
- RAG remains functional without requiring a broader DB replacement

# Open questions

The major policy choices requested in the brief have now been resolved:

- personal memory remains strictly guild-scoped
- admins get count/ID-only plus delete powers for personal memory
- short-term memory supports a small guild-wide recency summary for multi-channel continuity

Open implementation questions still worth resolving before coding:

1. Should third-party personal-memory writes always become `pending` unless made by the target user, or should trusted staff be allowed to write `admin_override` directly?
2. Should user export include expired short-term memories that are still present in storage, or only currently active ones?
3. Should guild-wide recency summaries be regenerated on a timer, on message volume thresholds, or only on demand after conversation boundaries?
4. Should document deletion remain numeric-ID based only, or also support exact-title deletion for admin usability?
5. Should soft-delete be retained long-term for memory tables, or used only during migration and removed later if operationally unnecessary?
