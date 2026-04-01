# Memory-System Redesign Review Report

Date: 2026-04-01

Repo reviewed: `E:\femboibot\femboibot-sanitized-with-holy-water`

Primary spec: [docs/memory-architecture-plan.md](E:/femboibot/femboibot-sanitized-with-holy-water/docs/memory-architecture-plan.md)

## Overall Verdict

The implementation is not fully compliant with the memory redesign plan.

The core architectural direction is mostly correct:

- it follows the recommended split-store design rather than the rejected full-replacement alternatives
- SQLite remains the main store for non-document memory
- Postgres/pgvector remains optional and limited to document/RAG memory
- persona teaching remains stored separately from memory
- migration is additive and preserves legacy guild data

However, there are two blocking privacy failures:

1. admins can still write personal memory for opted-out users
2. ordinary users can write durable personal memory about other users without confirmation or a staff-only override path

Those behaviors weaken the plan's privacy model and should be treated as release-blocking defects.

## Findings

### P0: Admin personal-memory writes bypass opt-out

Files:

- [discord_bot/cogs/admin.py#L251](E:/femboibot/femboibot-sanitized-with-holy-water/discord_bot/cogs/admin.py#L251)
- [discord_bot/cogs/admin.py#L533](E:/femboibot/femboibot-sanitized-with-holy-water/discord_bot/cogs/admin.py#L533)
- [discord_bot/utils/db_handler.py#L2779](E:/femboibot/femboibot-sanitized-with-holy-water/discord_bot/utils/db_handler.py#L2779)

Details:

- `!admin setfact` and `/admin setfact` call `add_personal_memory(..., bypass_privacy=True)`.
- `add_personal_memory()` enforces opt-out only when `bypass_privacy` is false.
- The plan explicitly says that if a user opts out of personal memory in a guild, no new personal memories may be written for them.

Impact:

- A user who opted out can still have new durable personal memory stored by admins.
- This is a direct violation of the required privacy semantics, not an acceptable moderation metadata exception.

### P0: Any member can write durable personal memory about another member

Files:

- [discord_bot/cogs/memories.py#L186](E:/femboibot/femboibot-sanitized-with-holy-water/discord_bot/cogs/memories.py#L186)
- [discord_bot/cogs/memories.py#L670](E:/femboibot/femboibot-sanitized-with-holy-water/discord_bot/cogs/memories.py#L670)

Details:

- The text and slash personal-memory commands accept an optional target member.
- If the target has not opted out, the command writes durable personal memory for that target immediately.
- There is no confirmation flow, no `pending` status, and no restriction to moderation/admin override.

Impact:

- Personal memory is not effectively user-owned.
- This violates the plan requirement that third-party durable writes should require confirmation or a moderation/admin override.

### P1: Dual-read fallback is weaker than the migration plan

Files:

- [discord_bot/utils/db_handler.py#L2829](E:/femboibot/femboibot-sanitized-with-holy-water/discord_bot/utils/db_handler.py#L2829)
- [discord_bot/utils/db_handler.py#L2982](E:/femboibot/femboibot-sanitized-with-holy-water/discord_bot/utils/db_handler.py#L2982)
- [discord_bot/utils/db_handler.py#L3146](E:/femboibot/femboibot-sanitized-with-holy-water/discord_bot/utils/db_handler.py#L3146)

Details:

- New-table reads return legacy `user_facts` rows only when the new-table query returns zero rows.
- That means fallback is table-empty fallback, not row-missing fallback.
- In a partially migrated state, if some rows have migrated and some have not, the existence of any migrated row suppresses fallback for remaining legacy rows.

Impact:

- Legacy guild data can be silently hidden during a partial migration or partial rollback window.
- This does not match the plan's stated compatibility requirement: prefer new tables, but fall back when migrated rows are missing.

### P2: Context assembly only partially matches the spec

Files:

- [discord_bot/utils/context_builder.py#L36](E:/femboibot/femboibot-sanitized-with-holy-water/discord_bot/utils/context_builder.py#L36)
- [discord_bot/cogs/ai_brain.py#L3050](E:/femboibot/femboibot-sanitized-with-holy-water/discord_bot/cogs/ai_brain.py#L3050)
- [discord_bot/cogs/ai_brain.py#L3345](E:/femboibot/femboibot-sanitized-with-holy-water/discord_bot/cogs/ai_brain.py#L3345)
- [discord_bot/cogs/ai_brain.py#L3357](E:/femboibot/femboibot-sanitized-with-holy-water/discord_bot/cogs/ai_brain.py#L3357)

Details:

- The memory-layer order in `build_memory_context_sections()` matches the planned memory-layer order.
- `ai_brain` also keeps RAG separate from fact memory during assembly.
- But selection is still simple list slicing such as `[:5]`, `[:3]`, and `[:1]`, not policy-aware relevance selection as called for in the plan.
- `sample_dialogues` are appended after the memory sections and conversation timeline instead of remaining in the persona/configuration layer.

Impact:

- The design direction is correct, but prompt assembly does not fully implement the spec's selection and ordering discipline.

### P2: Command and policy cleanup is incomplete

Files:

- [discord_bot/cogs/memories.py#L57](E:/femboibot/femboibot-sanitized-with-holy-water/discord_bot/cogs/memories.py#L57)
- [discord_bot/cogs/memories.py#L805](E:/femboibot/femboibot-sanitized-with-holy-water/discord_bot/cogs/memories.py#L805)
- [discord_bot/utils/db_handler.py#L3248](E:/femboibot/femboibot-sanitized-with-holy-water/discord_bot/utils/db_handler.py#L3248)

Details:

- Export functionality is still listed as TODO in the memory cog.
- Slash `/forget` still exposes legacy `long_term` scope terminology, even though the redesign is supposed to collapse durable user facts into the personal-memory model with explicit policy.
- The repository supports deletion of guild-wide short-term recency summaries, but I found no admin command surface dedicated to clearing guild-level recency summaries.

Impact:

- The underlying data model moved forward, but the user/admin surface has not been fully cleaned up to final-plan semantics.

### P3: Postgres remains correctly optional and RAG-only, but lifecycle metadata is incomplete

Files:

- [discord_bot/utils/pg_client.py#L66](E:/femboibot/femboibot-sanitized-with-holy-water/discord_bot/utils/pg_client.py#L66)
- [discord_bot/utils/pg_client.py#L80](E:/femboibot/femboibot-sanitized-with-holy-water/discord_bot/utils/pg_client.py#L80)

Details:

- The current Postgres schema is still limited to document/RAG storage, which matches the plan.
- It remains optional and does not replace SQLite for non-document memory.
- The recommended additional metadata is not present: `updated_at`, stored source text, embedding model/family, and a uniqueness constraint around guild/title.

Impact:

- This is not a privacy blocker, but it means the document subsystem does not yet implement the full lifecycle improvements proposed by the plan.

## Pass/Fail Summary By Spec Section

### Schema/storage changes

Status: Partial pass

What passes:

- Recommended split-store architecture is implemented with:
  - `server_memories`
  - `personal_memories`
  - `short_term_memory`
- SQLite remains the primary store for non-document memory.
- `user_profiles` was extended with guild-scoped privacy fields.
- Persona teaching remains separate in:
  - `persona_attributes`
  - `sample_dialogues`
- Postgres remains optional and document-only.

What fails or is incomplete:

- Postgres document metadata changes from the plan are only partially implemented.

### Repository/service layer

Status: Partial fail

What passes:

- New repository helpers exist for the new tables.
- Personal memory remains strictly guild-scoped at the schema and lookup level.
- Mention-based lookup is disabled by default and gated by `allow_mention_fact_lookup`.
- Admin index view for personal memory is metadata/count/ID-oriented and excludes raw content by default.

What fails:

- Privacy can still be bypassed for admin writes.
- Legacy `long_term` semantics still leak into behavior.
- Dual-read fallback logic is not strong enough for partial-migration safety.

### Migration/backfill

Status: Pass

What passes:

- Migration is additive rather than a forced full DB replacement.
- Existing guild data is preserved.
- Legacy mappings match the plan:
  - `server` -> `server_memories`
  - `personal` -> `personal_memories(status='confirmed')`
  - `long_term` -> `personal_memories(status='confirmed')`
  - `short_term` -> `short_term_memory`
- Provenance and legacy traceability are preserved with:
  - `legacy_fact_id`
  - original `source`
  - original timestamps

### Dual-read/dual-write compatibility

Status: Fail

What passes:

- New writes go to the new tables.
- Legacy mirroring still exists for rollback compatibility.

What fails:

- Read fallback is not row-missing-aware.
- Partial migration states can hide unmigrated legacy data.

### Prompt/context assembly

Status: Partial fail

What passes:

- Context assembly clearly separates:
  - server memory
  - current-user personal memory
  - mentioned-user personal memory
  - channel short-term summary
  - guild-wide short-term recency summary
  - document RAG context
- RAG remains separate from fact memory.
- Personal-memory mention lookup is privacy-gated.
- Channel-level recency summary and small guild-wide recency summary are both supported.

What fails:

- Selection is still raw slicing instead of relevance/policy-aware retrieval.
- Persona sample dialogues are not kept strictly in the persona/config layer ordering implied by the plan.

### Command/admin/privacy/export behavior

Status: Fail

What passes:

- Admin personal-memory viewing is metadata/count/ID-oriented rather than raw-content browsing by default.
- Delete-by-ID behavior exists for admin personal-memory deletion.
- User opt-out blocks normal personal-memory reads and writes.
- Mention-based lookup is disabled by default and blocked by opt-out.

What fails:

- Admin writes can bypass opt-out.
- Ordinary users can write durable personal memory for other users without confirmation.
- Export behavior called for in the plan is not implemented.

### Cache invalidation

Status: Partial fail

What passes:

- Short-term channel-bound memory can be cleared, including via the AI brain refresh boundary path.
- DB-backed short-term memory supports expiry/pruning.
- Guild-wide recency summaries can be stored and read separately.

What fails or is incomplete:

- The in-memory short-term cache exists but is not the main redesign path and is only tested in isolation.
- I found no admin-facing command specifically for clearing guild-wide recency summary state.

### Tests

Status: Partial pass

What passes:

- Focused tests exist for migration, opt-out, mention privacy, admin metadata/delete-by-ID, channel summary, guild-wide summary, context-layer ordering, and RAG separation.

What fails or is missing:

- No test covers the command-level privacy failures:
  - admin write bypass against opted-out users
  - third-party durable write via user-facing remember commands
- No test covers partial-migration fallback behavior.
- No test covers export semantics.

## Exact Test Results

Command run:

```powershell
python -m pytest tests/test_memory_redesign.py tests/test_context_builder_memory_layers.py tests/test_short_term_channel_memory.py tests/test_short_term_memory_cache.py tests/test_rag_store.py -q
```

Exact result:

```text
..............                                                           [100%]
============================== warnings summary ===============================
C:\Users\Hp\AppData\Roaming\Python\Python314\site-packages\google\genai\types.py:43
  C:\Users\Hp\AppData\Roaming\Python\Python314\site-packages\google\genai\types.py:43: DeprecationWarning: '_UnionGenericAlias' is deprecated and slated for removal in Python 3.17
    VersionedUnionType = Union[builtin_types.UnionType, _UnionGenericAlias]

tests/test_memory_redesign.py::MemoryRedesignTests::test_admin_personal_memory_view_is_metadata_only_and_delete_by_id_works
tests/test_memory_redesign.py::MemoryRedesignTests::test_channel_and_guild_recency_summaries_are_stored_separately
tests/test_memory_redesign.py::MemoryRedesignTests::test_document_rag_stays_separate_from_fact_memory
tests/test_memory_redesign.py::MemoryRedesignTests::test_mention_lookup_requires_explicit_allowance_and_respects_opt_out
tests/test_memory_redesign.py::MemoryRedesignTests::test_migrates_legacy_fact_tables_into_new_memory_tables
tests/test_memory_redesign.py::MemoryRedesignTests::test_personal_memory_opt_out_blocks_writes_and_reads
tests/test_short_term_channel_memory.py::ShortTermChannelMemoryTests::test_channel_scoped_short_term_add_get_delete
  C:\Users\Hp\AppData\Roaming\Python\Python314\site-packages\aiosqlite\core.py:63: DeprecationWarning: The default datetime adapter is deprecated as of Python 3.12; see the sqlite3 documentation for suggested replacement recipes
    result = function()

tests/test_memory_redesign.py::MemoryRedesignTests::test_channel_and_guild_recency_summaries_are_stored_separately
  E:\femboibot\femboibot-sanitized-with-holy-water\tests\test_memory_redesign.py:204: DeprecationWarning: datetime.datetime.utcnow() is deprecated and scheduled for removal in a future version. Use timezone-aware objects to represent datetimes in UTC: datetime.datetime.now(datetime.UTC).
    expires_at=datetime.utcnow() + timedelta(hours=6),

tests/test_memory_redesign.py::MemoryRedesignTests::test_channel_and_guild_recency_summaries_are_stored_separately
  E:\femboibot\femboibot-sanitized-with-holy-water\tests\test_memory_redesign.py:211: DeprecationWarning: datetime.datetime.utcnow() is deprecated and scheduled for removal in a future version. Use timezone-aware objects to represent datetimes in UTC: datetime.datetime.now(datetime.UTC).
    expires_at=datetime.utcnow() + timedelta(hours=2),

-- Docs: https://docs.pytest.org/en/stable/how-to/capture-warnings.html
14 passed, 10 warnings in 10.35s
```

Coverage explicitly confirmed by those tests:

- migration of legacy `personal` / `server` / `long_term` / `short_term` memory
- personal-memory opt-out on writes and reads
- mention-based lookup privacy
- admin metadata-only visibility and delete-by-ID behavior
- channel short-term memory
- guild-wide recency summary
- context assembly ordering at the memory-layer level
- RAG separation from fact memory

## Missing Verification

The following areas remain unverified or insufficiently verified:

- command-level enforcement that admin writes cannot bypass personal-memory opt-out
- command-level enforcement that non-admin users cannot write durable personal memory about other users without confirmation
- partial-migration compatibility where some rows are migrated and others are still only in `user_facts`
- export behavior for:
  - user personal-memory export
  - admin metadata export
  - document export policy
- admin-facing behavior for clearing guild-wide recency summaries
- full prompt-assembly verification at the `ai_brain` integration level rather than only the context-builder helper

## Recommended Next Actions

1. Remove or tightly constrain `bypass_privacy=True` for personal-memory writes.
2. Change cross-user durable personal-memory writes to a pending/confirmation flow, or restrict them to an audited moderation override path.
3. Strengthen dual-read logic so reads can merge or fall back per missing row rather than only when the new table is empty.
4. Finish the command-policy cleanup:
   - remove legacy `long_term` user-facing semantics
   - add export surfaces
   - add admin control for guild-wide recency summary clearing
5. Add tests for the missing privacy and migration edge cases listed above.
