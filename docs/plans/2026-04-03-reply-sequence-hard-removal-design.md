# Reply Sequence Hard Removal Design

**Problem:** The active Discord runtime already uses persona job selection, per-channel persona queueing, and the shared streaming sender stack, but the repository still contains a legacy reply-sequence orchestration model. That leaves dead runtime code, obsolete config/state fields, and preservation tests that imply two competing continuation systems still exist.

**Decision:** Perform a hard removal of the legacy reply-sequence system. Remove its runtime types and helpers from `discord_bot/cogs/ai_brain.py`, remove all `reply_sequence_*` guild-config fields from `discord_bot/utils/db_handler.py`, remove native config-panel affordances from `discord_bot/utils/native_config_panel.py`, and replace preservation tests with removal/regression tests that assert persona-queue orchestration is the only production model.

**Scope:**
- Remove legacy reply-sequence runtime, prompt shaping, parsing, state tracking, and payload helpers.
- Remove legacy reply-sequence config fields and panel controls.
- Remove or rewrite tests that preserve the deleted model.
- Keep the current persona queue runtime, streaming sender stack, webhook identity flow, and non-stream processing-ack recovery path.

**Out of Scope:**
- Rewriting the current persona queue behavior.
- Removing historical planning documents under `docs/`.
- Refactoring unrelated AI runtime behavior.

**Target Architecture:**
- `discord_bot/cogs/ai_brain.py` exposes one orchestration model: trigger resolution, immediate persona execution, queued follow-up personas, and shared send/stream handling.
- `discord_bot/utils/db_handler.py` stores only currently supported AI runtime config.
- `discord_bot/utils/native_config_panel.py` exposes only supported AI runtime settings.
- Tests verify the absence of reply-sequence runtime and protect persona-queue behavior from regression.
