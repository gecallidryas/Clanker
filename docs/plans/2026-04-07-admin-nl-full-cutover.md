# Full Admin NLP Cutover Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Fully remove legacy admin fallback routing from `discord_bot/cogs/ai_brain.py`, eliminate prompt-driven admin mutation as a second authority for the supported admin surface, and make the typed natural-language admin control plane the only source of truth for supported admin mutations.

**Architecture:** Keep one authoritative mutation pipeline for the supported admin surface: `interpret_admin_request -> resume_admin_request -> execute_admin_intent -> Discord/db side effects`. Port the remaining channel, role, starboard, and typed moderation/channel-delete execution decisions into this pipeline first, then delete the legacy fallback calls and dead parser/executor helpers in `ai_brain.py`. Prompt-emitted `admin_action` and agentic JSON must not execute supported admin mutations by alternate parsing rules; unsupported admin-like text must fail closed with a deterministic rephrase/help response instead of falling through into the general AI mutation path.

**Tech Stack:** Python 3.14, discord.py, pytest, existing Discord bot cogs in `discord_bot/cogs`, typed admin parser in `discord_bot/utils/admin_nl.py`, executor layer in `discord_bot/utils/admin_actions.py`

---

## Non-Negotiable Cutover Invariants

These rules apply to every task below. Do not proceed to the next task if any invariant is violated.

1. **Single router invariant**
   After cutover, `discord_bot/cogs/ai_brain.py` must route admin mutations only through `_maybe_handle_admin_nl_request`.

2. **Single parser invariant**
   Supported admin mutations must be recognized only by `interpret_admin_request` in `discord_bot/utils/admin_nl.py`.

3. **Single executor invariant**
   Supported admin mutations must be executed only by `execute_admin_intent` in `discord_bot/utils/admin_actions.py` or by a helper it calls directly.

4. **No read-only mutation invariant**
   Informational/admin status questions must never create pending mutation state.

5. **No path-dependent wording invariant**
   Equivalent phrasings such as `set modlog`, `set mod log`, `create starboard`, and `send posts to starboard` must enter the same typed intent path.

6. **Follow-up completeness invariant**
   Every intent that can be underspecified must have an intent-specific `resume_admin_request` branch or a shared helper that actually fills the missing slot.

7. **Confirmation invariant**
   Confirmation policy must be determined by typed intent metadata, not by which helper happened to execute the request.

8. **Permission invariant**
   `administrator`, `manage_guild`, and bot-staff permission semantics must remain explicit and test-covered during and after cutover.

9. **Deletion gate invariant**
   Legacy fallback calls in `ai_brain.py` must not be removed until parser parity, resume parity, executor parity, and AI-brain routing tests are all green.

10. **Single authority invariant**
   Supported admin mutations must not be executable through `handle_admin_actions` or any prompt-only JSON path that bypasses `interpret_admin_request`.

11. **Fail-closed invariant**
   Admin-like text that does not parse into a supported typed intent must not fall through into the general AI response path where prompt-driven mutation is still possible.

## Robustness Gates

The cutover is only complete if all of these gates pass:

- **Parser gate:** all supported mutation phrasings map to typed intents.
- **Resume gate:** every pending mutation can be completed by a natural follow-up reply.
- **Executor gate:** every supported intent has deterministic execution coverage.
- **Permission gate:** admin/manage-guild/staff-role behavior is consistent across the unified path.
- **Question gate:** read-only questions do not create pending admin state.
- **Authority gate:** supported admin mutations cannot execute through `handle_admin_actions` or other prompt-only paths.
- **Fail-closed gate:** admin-like parse misses produce a deterministic non-mutating response, not a fallthrough into the model path.
- **Deletion gate:** `ai_brain.py` contains no legacy fallback calls or dead parser helpers.
- **Order-independence gate:** the targeted pytest suite passes even when test module import order changes.

## Risk Register

1. **Parser parity risk**
   Legacy regex behavior may still recognize phrasings the new parser misses.
   Mitigation: add a cutover matrix and keep expanding it before removing legacy routing.

2. **Execution drift risk**
   A typed intent may parse correctly but execute differently than the old path.
   Mitigation: write intent-level executor tests before deleting legacy code.

3. **Question/mutation confusion risk**
   Read-only admin questions can accidentally start mutation workflows.
   Mitigation: require action verbs in every mutation parser unless the intent is a pure toggle command with explicit imperative wording.

4. **Pending-state dead-end risk**
   New intents can enter pending state but never resume correctly.
   Mitigation: no new underspecified intent without a paired `resume_admin_request` branch and test.

5. **Permission regression risk**
   `manage_guild` users can be admitted by the top-level gate but blocked lower down.
   Mitigation: write explicit permission tests before removing legacy routing.

6. **Test pollution risk**
   Stubs in one test module can break unrelated DB-backed tests.
   Mitigation: clear temporary stub modules in teardown/import cleanup and keep the broad targeted suite in the final gate.

7. **Prompt authority drift risk**
   The model can still emit `admin_action` JSON for supported actions even after the typed parser is authoritative.
   Mitigation: make `handle_admin_actions` reject supported-surface admin actions at runtime and shrink prompt instructions so they are explicitly non-authoritative for the supported surface.

8. **Admin-like text leakage risk**
   A parse miss can still reach the normal AI response path and mutate through prompt-side JSON handling.
   Mitigation: make the admin router fail closed for admin-like parse misses with a deterministic rephrase/help reply and test that the general AI path is not reached.

## Rollback Criteria

Stop the cutover and do not delete legacy fallback calls if any of the following is true:

- Any supported admin mutation still relies on `_maybe_handle_channel_request`, `_maybe_handle_role_request`, or `_maybe_handle_starboard_setup_request` to work.
- Any informational admin question still creates pending mutation state.
- Any typed intent still has a generic `Please provide ...` resume path where a concrete slot extractor is possible.
- Any permission-path test for `manage_guild`, administrator, or bot staff fails.
- Any supported admin mutation can still execute through `handle_admin_actions` or prompt-only `admin_action` JSON.
- Any admin-like parse miss still falls through into the normal AI response path.
- The broad targeted suite passes only in one import order.

If rollback is needed, revert only the in-progress cutover task and keep the previous task’s green state as the baseline.

### Task 1: Lock The Supported Intent Matrix

**Files:**
- Modify: `E:\femboibot\docs\plans\2026-04-07-natural-language-admin-control-design.md`
- Modify: `E:\femboibot\docs\plans\2026-04-07-natural-language-admin-control.md`
- Create: `E:\femboibot\tests\test_admin_nl_cutover_matrix.py`

**Step 1: Write the failing test**

Add a matrix-style parser smoke test that proves the cutover surface is explicit.

```python
import pytest

from utils.admin_nl import AdminNLContext, interpret_admin_request


@pytest.mark.parametrize(
    ("text", "intent"),
    [
        ("create channel announcements", "channel.create_text"),
        ("create category events", "channel.create_category"),
        ("create role VIP", "role.create"),
        ("give @Members to @Raider", "role.assign"),
        ("remove @Members from @Raider", "role.remove"),
        ("delete role Temp", "role.delete"),
        ("create starboard in #logs", "starboard.configure"),
        ("timeout @Raider for 10 minutes", "moderation.timeout"),
        ("kick @Raider", "moderation.kick"),
        ("unban <@666>", "moderation.unban"),
    ],
)
def test_cutover_matrix_intents(text, intent):
    context = AdminNLContext(
        current_channel_id=111,
        channel_mentions={"logs": 333},
        role_mentions={"members": 444},
        member_mentions={"raider": 666},
    )
    result = interpret_admin_request(text, context)
    assert result is not None
    assert result.intent == intent
```

Add a second matrix for phrasings that must **not** parse as mutations:

```python
@pytest.mark.parametrize(
    "text",
    [
        "what is the welcome message in #logs?",
        "show me the modlog channel",
        "what is the url safety action?",
    ],
)
def test_cutover_matrix_read_only_questions_do_not_parse(text):
    context = AdminNLContext(current_channel_id=111, channel_mentions={"logs": 333})
    assert interpret_admin_request(text, context) is None
```

**Step 2: Run test to verify it fails**

Run: `python -m pytest tests\test_admin_nl_cutover_matrix.py -q`

Expected: FAIL because remaining legacy-only actions do not have typed intents yet.

**Step 3: Document the cutover surface**

Update the design docs with the authoritative supported intent list:
- channel create/delete variants
- role create/delete/assign/remove
- starboard setup/toggle/ignore/unignore
- welcome public/DM/toggle/clear
- automod keyword/spam
- URL safety action/allowlist/blocklist
- modlog
- autorole
- staff
- moderation `ban`, `unban`, `kick`, `timeout`

Keep the list DRY and consistent with the test matrix.

Add a “not supported as mutation” list for read-only/admin status questions so engineers do not accidentally reintroduce question-to-mutation drift.

Add an “admin-like but fail closed” list for phrases that are clearly admin/config requests but are unsupported or underspecified beyond safe recovery. These must produce deterministic rephrase/help behavior instead of reaching the general AI path.

**Step 4: Run test to confirm the matrix still fails only on unported behavior**

Run: `python -m pytest tests\test_admin_nl_cutover_matrix.py -q`

Expected: FAIL, but only on currently unported legacy behavior.

**Step 5: Commit**

```bash
git add docs/plans/2026-04-07-natural-language-admin-control-design.md docs/plans/2026-04-07-natural-language-admin-control.md tests/test_admin_nl_cutover_matrix.py
git commit -m "test: define admin nlp cutover intent matrix"
```


### Task 2: Port Remaining Legacy Channel And Role Parsing Into Typed Intents

**Files:**
- Modify: `E:\femboibot\discord_bot\utils\admin_nl.py`
- Modify: `E:\femboibot\tests\test_admin_nl_intents.py`
- Modify: `E:\femboibot\tests\test_admin_nl_flow.py`
- Modify: `E:\femboibot\tests\test_admin_nl_cutover_matrix.py`

**Step 1: Write the failing tests**

Add intent and follow-up coverage for:
- `create channel announcements`
- `create voice channel music`
- `create category events`
- `delete channel announcements`
- `create role VIP`
- `delete role Temp`
- `give @Members to @Raider`
- `remove @Members from @Raider`
- missing-slot follow-ups such as `create channel` then `announcements`
- read-only near-miss phrasings such as `what channels can starboard use?` stay unparsed

Use concrete assertions:

```python
def test_parse_create_text_channel_request():
    result = interpret_admin_request("create channel announcements", _context())
    assert result is not None
    assert result.intent == "channel.create_text"
    assert result.params["channel_name"] == "announcements"


def test_parse_assign_role_request():
    result = interpret_admin_request("give @Members to @Raider", _context())
    assert result is not None
    assert result.intent == "role.assign"
    assert result.params["role_id"] == 444
    assert result.params["target_id"] == 666
```

**Step 2: Run tests to verify they fail**

Run: `python -m pytest tests\test_admin_nl_intents.py tests\test_admin_nl_flow.py tests\test_admin_nl_cutover_matrix.py -q`

Expected: FAIL because the parser does not yet emit these channel/role intents.

**Step 3: Implement the minimal parser changes**

In `discord_bot/utils/admin_nl.py`:
- Add typed channel parsers for create/delete category/text/voice operations.
- Add typed role parsers for create/delete/assign/remove.
- Reuse existing normalization helpers instead of new ad hoc regex if possible.
- Add intent-specific `resume_admin_request` branches for all new underspecified intents.
- Keep read-only questions out of the mutation path with explicit action-verb guards.
- Prefer shared extractors over duplicated regex branches:
  - channel target extraction
  - role/member extraction
  - imperative verb detection
  - reply-target moderation extraction

Before moving on, verify that every new parser branch either:
- returns a fully populated intent, or
- returns a pending intent whose missing fields can actually be resumed later.

Do not add new routing logic in `ai_brain.py` here.

**Step 4: Run tests to verify they pass**

Run: `python -m pytest tests\test_admin_nl_intents.py tests\test_admin_nl_flow.py tests\test_admin_nl_cutover_matrix.py -q`

Expected: PASS for the newly ported channel/role parser cases.

**Step 5: Commit**

```bash
git add discord_bot/utils/admin_nl.py tests/test_admin_nl_intents.py tests/test_admin_nl_flow.py tests/test_admin_nl_cutover_matrix.py
git commit -m "feat: port channel and role admin parsing to typed intents"
```


### Task 3: Port Remaining Legacy Execution Into `execute_admin_intent`

**Files:**
- Modify: `E:\femboibot\discord_bot\utils\admin_actions.py`
- Modify: `E:\femboibot\tests\test_admin_actions_intents.py`

**Step 1: Write the failing tests**

Add executor coverage for the new typed intents:
- `channel.create_text`
- `channel.create_voice`
- `channel.create_category`
- `channel.delete`
- `role.create`
- `role.delete`
- `role.assign`
- `role.remove`
- failures for missing target/member/role/channel produce stable error strings
- destructive actions respect confirmation metadata owned by the router, not hidden executor behavior

Use `AsyncMock` around existing low-level helpers or Discord object methods. Example:

```python
async def test_execute_admin_intent_can_assign_role():
    guild = _guild_with_role_and_member()
    result = await admin_actions.execute_admin_intent(
        "role.assign",
        {"role_id": 444, "target_id": 666},
        guild,
        _executor(),
    )
    assert result["success"] is True
```

**Step 2: Run tests to verify they fail**

Run: `python -m pytest tests\test_admin_actions_intents.py -q`

Expected: FAIL because `execute_admin_intent` does not yet own these operations.

**Step 3: Implement the minimal execution changes**

In `discord_bot/utils/admin_actions.py`:
- Add explicit handlers for each new typed intent.
- If useful, extract tiny helpers like `_resolve_guild_member`, `_resolve_guild_role`, `_resolve_channel_create_target`.
- Keep the return shape consistent: `{"success": bool, "message": ...}` or `{"success": False, "error": ...}`.
- Make destructive operations preserve existing confirmation policy from the parser/router, not from executor-specific branching.
- Normalize low-level Discord lookup failures into deterministic user-facing errors.
- Avoid silent success for no-op deletes/removes unless that matches current bot behavior and is test-covered.

If old logic from `ai_brain.py` is still needed, move it here or factor it into shared helpers called from here only.

**Step 4: Run tests to verify they pass**

Run: `python -m pytest tests\test_admin_actions_intents.py -q`

Expected: PASS.

**Step 5: Commit**

```bash
git add discord_bot/utils/admin_actions.py tests/test_admin_actions_intents.py
git commit -m "feat: move channel and role execution into admin intent executor"
```


### Task 4: Move Intent-Specific Execution Decisions Out Of `ai_brain.py`

**Files:**
- Modify: `E:\femboibot\discord_bot\cogs\ai_brain.py`
- Modify: `E:\femboibot\tests\test_ai_brain_admin_nl_flow.py`

**Step 1: Write the failing tests**

Add AI-brain flow tests that assert `_maybe_handle_admin_nl_request` executes new typed intents without calling legacy handlers and without intent-specific branching inside `ai_brain.py`:
- `create channel announcements`
- `create role VIP`
- `timeout <@666> for 10 minutes`
- `ban <@666>` and `delete channel announcements` no longer depend on `_execute_admin_nl_intent` special cases
- `create starboard in #logs` stores missing follow-up instead of returning `False`
- `manage_guild` users can complete all supported unified intents without touching legacy fallback methods
- informational admin questions do not create pending state in AI-brain flow tests

Use `AsyncMock` around `execute_admin_intent` and assert:

```python
execute_mock.assert_awaited_once()
assert execute_mock.await_args.args[0] == "channel.create_text"
```

**Step 2: Run tests to verify they fail**

Run: `python -m pytest tests\test_ai_brain_admin_nl_flow.py -q`

Expected: FAIL because `ai_brain.py` still relies on special-case routing and legacy delegation.

**Step 3: Implement the minimal routing cleanup**

In `discord_bot/utils/admin_actions.py` and `discord_bot/cogs/ai_brain.py`:
- Keep `_maybe_handle_admin_nl_request` as the single router.
- Move typed moderation and `channel.delete` execution decisions out of `_execute_admin_nl_intent`.
- If an intent still needs agentic transport, make `execute_admin_intent` return deterministic execution metadata such as a transport kind plus payload, and keep `_execute_admin_nl_intent` transport-only.
- Do not leave per-intent branching in `ai_brain.py` for supported admin mutations.
- Ensure no supported intent requires a later on-message fallback or a prompt-generated parser to work.

Do not delete legacy helpers yet in this task; only stop relying on them for any supported typed intent.

**Step 4: Run tests to verify they pass**

Run: `python -m pytest tests\test_ai_brain_admin_nl_flow.py -q`

Expected: PASS.

**Step 5: Commit**

```bash
git add discord_bot/cogs/ai_brain.py tests/test_ai_brain_admin_nl_flow.py
git commit -m "refactor: route all supported admin nlp intents through unified executor"
```


### Task 5: De-Authorize Prompt-Driven Admin Mutation For The Supported Surface

**Files:**
- Modify: `E:\femboibot\discord_bot\cogs\ai_brain.py`
- Modify: `E:\femboibot\tests\test_ai_brain_admin_nl_flow.py`
- Modify: `E:\femboibot\tests\test_ai_brain_admin_intent_bypass.py`
- Modify: `E:\femboibot\docs\plans\2026-04-07-natural-language-admin-control-design.md`
- Modify: `E:\femboibot\docs\plans\2026-04-07-natural-language-admin-control.md`

**Step 1: Write the failing tests**

Add tests that prove prompt-driven admin mutation is not authoritative for supported intents:
- if the model emits `admin_action` JSON for a supported action like starboard setup, channel create, or modlog set, the runtime does not execute it as an alternate authority
- admin-like text that fails `interpret_admin_request` gets a deterministic rephrase/help response and does not continue into the normal AI mutation path
- non-admin conversational text still reaches the normal AI path unchanged

Use explicit assertions around `handle_admin_actions`, `handle_agentic_actions`, and the model path mocks so the test proves supported admin mutations are gated by the typed router only.

**Step 2: Run tests to verify they fail**

Run: `python -m pytest tests\test_ai_brain_admin_nl_flow.py tests\test_ai_brain_admin_intent_bypass.py -q`

Expected: FAIL because supported-surface `admin_action` is still executable and admin-like parse misses still fall through.

**Step 3: Implement the authority cutover**

In `discord_bot/cogs/ai_brain.py`:
- Make `_maybe_handle_admin_nl_request` fail closed for admin-like parse misses with a deterministic, non-mutating reply such as a short rephrase/help prompt.
- Ensure this returns `True` so the message does not continue into the general AI response path.
- Make `handle_admin_actions` reject or ignore supported-surface actions at runtime so prompt drift cannot silently recreate a second mutation authority.
- Keep prompt-driven admin mutation only for intentionally unsupported future/admin-adjacent behavior, if any remains at all.

In the design docs:
- Mark the typed admin NLP path as authoritative for the supported admin surface.
- Mark prompt-driven `admin_action` as non-authoritative and forbidden for supported intents.

**Step 4: Run tests to verify they pass**

Run: `python -m pytest tests\test_ai_brain_admin_nl_flow.py tests\test_ai_brain_admin_intent_bypass.py -q`

Expected: PASS.

**Step 5: Commit**

```bash
git add discord_bot/cogs/ai_brain.py tests/test_ai_brain_admin_nl_flow.py tests/test_ai_brain_admin_intent_bypass.py docs/plans/2026-04-07-natural-language-admin-control-design.md docs/plans/2026-04-07-natural-language-admin-control.md
git commit -m "refactor: make typed admin nlp the sole authority for supported actions"
```


### Task 6: Cut Over Starboard Setup Completely

**Files:**
- Modify: `E:\femboibot\discord_bot\utils\admin_nl.py`
- Modify: `E:\femboibot\discord_bot\utils\admin_actions.py`
- Modify: `E:\femboibot\tests\test_admin_nl_intents.py`
- Modify: `E:\femboibot\tests\test_admin_nl_flow.py`
- Modify: `E:\femboibot\tests\test_admin_actions_intents.py`

**Step 1: Write the failing tests**

Add deterministic coverage for starboard phrases currently dependent on legacy extraction:
- `create starboard in #logs`
- `send posts to starboard in #logs`
- missing emoji/threshold follow-up continuation
- any existing threshold semantics such as `more than 4 reactions`
- reply, mention, and plain-trigger phrasings all behave the same once they reach the admin router
- read-only starboard questions do not start follow-up state

Add executor tests proving `starboard.configure` can succeed with only typed params and never needs the old extractor.

**Step 2: Run tests to verify they fail**

Run: `python -m pytest tests\test_admin_nl_intents.py tests\test_admin_nl_flow.py tests\test_admin_actions_intents.py -q`

Expected: FAIL on the newly added starboard cases.

**Step 3: Implement the minimal parser/executor changes**

In `discord_bot/utils/admin_nl.py`:
- Finalize starboard parser support for `create`/`send` variants.
- Keep follow-ups short and deterministic.

In `discord_bot/utils/admin_actions.py`:
- Ensure `starboard.configure` covers all required behavior without needing `_extract_starboard_request`.
- Keep defaults only where the product explicitly allows them. If details are required by policy, keep them in missing-slot follow-up flow rather than guessing.

**Step 4: Run tests to verify they pass**

Run: `python -m pytest tests\test_admin_nl_intents.py tests\test_admin_nl_flow.py tests\test_admin_actions_intents.py -q`

Expected: PASS.

**Step 5: Commit**

```bash
git add discord_bot/utils/admin_nl.py discord_bot/utils/admin_actions.py tests/test_admin_nl_intents.py tests/test_admin_nl_flow.py tests/test_admin_actions_intents.py
git commit -m "feat: complete typed starboard setup cutover"
```


### Task 7: Remove Legacy Fallback Calls From `ai_brain.py`

**Files:**
- Modify: `E:\femboibot\discord_bot\cogs\ai_brain.py`
- Modify: `E:\femboibot\tests\test_ai_brain_admin_nl_flow.py`
- Modify: `E:\femboibot\tests\test_ai_brain_admin_intent_bypass.py`

**Step 1: Write the failing tests**

Add assertions that no legacy fallback methods are called from `_maybe_handle_admin_nl_request` and that admin-like parse misses no longer use them as recovery:

```python
async def test_unified_admin_router_does_not_call_legacy_fallbacks():
    brain._maybe_handle_channel_request = AsyncMock(return_value=False)
    brain._maybe_handle_role_request = AsyncMock(return_value=False)
    brain._maybe_handle_starboard_setup_request = AsyncMock(return_value=False)
    await brain._maybe_handle_admin_nl_request(_FakeMessage("create channel announcements"))
    brain._maybe_handle_channel_request.assert_not_awaited()
    brain._maybe_handle_role_request.assert_not_awaited()
    brain._maybe_handle_starboard_setup_request.assert_not_awaited()
```

Add an assertion that `supported` admin phrases still succeed after those fallbacks are disabled:

```python
async def test_supported_admin_intents_still_work_after_fallback_removal():
    handled = await brain._maybe_handle_admin_nl_request(_FakeMessage("create channel announcements"))
    assert handled is True
```

**Step 2: Run tests to verify they fail**

Run: `python -m pytest tests\test_ai_brain_admin_nl_flow.py tests\test_ai_brain_admin_intent_bypass.py -q`

Expected: FAIL because the router still falls back to these methods.

**Step 3: Remove the fallback calls**

In `discord_bot/cogs/ai_brain.py`:
- Delete the fallback block inside `_maybe_handle_admin_nl_request` that calls:
  - `_maybe_handle_channel_request`
  - `_maybe_handle_role_request`
  - `_maybe_handle_starboard_setup_request`
- Preserve the fail-closed behavior for unsupported admin-like parse misses; removing fallback calls must not reopen fallthrough into the general AI path.
- Do not leave commented-out dead code behind.

Do not delete the methods yet; first make the router independent.

**Step 4: Run tests to verify they pass**

Run: `python -m pytest tests\test_ai_brain_admin_nl_flow.py tests\test_ai_brain_admin_intent_bypass.py -q`

Expected: PASS.

**Step 5: Commit**

```bash
git add discord_bot/cogs/ai_brain.py tests/test_ai_brain_admin_nl_flow.py tests/test_ai_brain_admin_intent_bypass.py
git commit -m "refactor: remove legacy admin fallback calls from ai brain"
```


### Task 8: Delete Dead Legacy Helpers And Prompt Drift

**Files:**
- Modify: `E:\femboibot\discord_bot\cogs\ai_brain.py`
- Modify: `E:\femboibot\docs\plans\2026-04-07-natural-language-admin-control-design.md`
- Modify: `E:\femboibot\docs\plans\2026-04-07-natural-language-admin-control.md`

**Step 1: Write the failing check**

Add a simple grep-based assertion step to the plan execution notes:

Run:
```powershell
Select-String -Path discord_bot\cogs\ai_brain.py -Pattern "_maybe_handle_channel_request|_maybe_handle_role_request|_maybe_handle_starboard_setup_request|_extract_channel_request|_extract_role_request|_extract_starboard_request"
```

Expected before deletion: matches still exist.

Add a second grep for legacy extraction helper aliases/wrappers:

Run:
```powershell
Select-String -Path discord_bot\cogs\ai_brain.py -Pattern "_extract_channel_request_v2|_extract_channel_request_v3|_extract_channel_request_resolved|_extract_channel_request_new"
```

Expected before deletion: matches still exist if legacy wrappers remain.

**Step 2: Delete dead code**

Remove from `discord_bot/cogs/ai_brain.py`:
- unused legacy fallback router methods
- unused legacy extraction helpers only referenced by those methods
- stale comments referring to fast-path admin bypasses
- stale prompt text or inline docs that imply supported admin behavior still depends on fallback routing or prompt-side `admin_action`

Update plan/design docs so they no longer describe the legacy split as active architecture.

**Step 3: Run grep check again**

Run:
```powershell
Select-String -Path discord_bot\cogs\ai_brain.py -Pattern "_maybe_handle_channel_request|_maybe_handle_role_request|_maybe_handle_starboard_setup_request|_extract_channel_request|_extract_role_request|_extract_starboard_request"
```

Expected: no matches.

Run:
```powershell
Select-String -Path discord_bot\cogs\ai_brain.py -Pattern "_extract_channel_request_v2|_extract_channel_request_v3|_extract_channel_request_resolved|_extract_channel_request_new"
```

Expected: no matches.

**Step 4: Commit**

```bash
git add discord_bot/cogs/ai_brain.py docs/plans/2026-04-07-natural-language-admin-control-design.md docs/plans/2026-04-07-natural-language-admin-control.md
git commit -m "refactor: delete legacy admin fallback code"
```


### Task 9: Final Verification And Safety Sweep

**Files:**
- Modify if needed: `E:\femboibot\tests\test_admin_nl_intents.py`
- Modify if needed: `E:\femboibot\tests\test_admin_nl_flow.py`
- Modify if needed: `E:\femboibot\tests\test_admin_actions_intents.py`
- Modify if needed: `E:\femboibot\tests\test_ai_brain_admin_nl_flow.py`
- Modify if needed: `E:\femboibot\tests\test_admin_nl_cutover_matrix.py`

**Step 1: Run the full targeted suite**

Run:

```bash
python -m pytest tests\test_admin_actions_intents.py tests\test_admin_nl_flow.py tests\test_admin_nl_intents.py tests\test_ai_brain_admin_nl_flow.py tests\test_ai_brain_admin_intent_bypass.py tests\test_starboard_settings_parsing.py tests\test_social_welcome_dm.py tests\test_guild_config_audit.py tests\test_admin_nl_cutover_matrix.py -q
```

Expected: all PASS.

**Step 2: Run static syntax verification**

Run:

```bash
python -m py_compile discord_bot\utils\admin_nl.py discord_bot\utils\admin_actions.py discord_bot\cogs\ai_brain.py
```

Expected: success, no syntax errors.

**Step 3: Run dead-code guards**

Run:

```powershell
Select-String -Path discord_bot\cogs\ai_brain.py -Pattern "_maybe_handle_channel_request|_maybe_handle_role_request|_maybe_handle_starboard_setup_request"
```

Expected: no matches.

Run:

```powershell
Select-String -Path discord_bot\cogs\ai_brain.py -Pattern "handle_admin_actions\\(|ADMIN_ACTION_INSTRUCTIONS"
```

Expected: matches may still exist for unsupported/non-authoritative behavior, but no remaining code or prompt text should claim supported admin mutations can execute through prompt-side `admin_action`.

Run:

```powershell
Select-String -Path discord_bot\cogs\ai_brain.py -Pattern "_extract_channel_request|_extract_role_request|_extract_starboard_request"
```

Expected: no matches.

**Step 4: Run a deterministic question-safety subset**

Run:

```bash
python -m pytest tests\test_admin_nl_intents.py -k "read_only or question" -q
```

Expected: PASS. No informational admin question should parse into a mutation.

**Step 5: Commit**

```bash
git add tests/test_admin_actions_intents.py tests/test_admin_nl_flow.py tests/test_admin_nl_intents.py tests/test_ai_brain_admin_nl_flow.py tests/test_ai_brain_admin_intent_bypass.py tests/test_admin_nl_cutover_matrix.py
git commit -m "test: finalize unified admin nlp cutover coverage"
```

**Step 6: Final sanity note**

Record in the final implementation summary:
- legacy fallback calls were removed from `ai_brain.py`
- all supported admin mutations now route through typed parser + executor
- any remaining prompt-driven admin handling is explicitly non-authoritative and cannot execute the supported admin surface
- admin-like parse misses now fail closed with deterministic help instead of reaching the general AI mutation path
- informational admin questions are guaranteed not to create mutation workflows
- test order no longer affects the targeted suite
