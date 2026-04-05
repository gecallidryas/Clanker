# Bot Time Awareness Tool Design

**Problem:** The bot can answer conversational questions that depend on current time, but it does not have an authoritative built-in clock for those turns. That makes questions like "what time is it", "is it tomorrow yet", or "later tonight" vulnerable to stale model assumptions instead of runtime-resolved time.

**Decision:** Add a read-only built-in tool named `get_current_time` that returns the bot's canonical local time in `America/Denver`. Update prompt guidance in `discord_bot/cogs/ai_brain.py` so the model is explicitly told to call this tool whenever a reply depends on the current date, time, weekday, or relative time words such as `today`, `tomorrow`, `yesterday`, `tonight`, or `right now`.

**Scope:**
- Add a built-in bot-time tool that resolves the current local time in `America/Denver`.
- Register the tool in the existing legacy-to-unified tool bridge so it appears in normal prompt-emulated tool use.
- Add prompt guidance that makes the model call the tool for time-sensitive questions.
- Add focused tests for helper formatting, registry/descriptors, executor/runtime access, and prompt guidance.

**Out of Scope:**
- User reminder parsing or scheduling changes.
- Per-user timezone behavior.
- Persistent calendar events, recurring schedules, or DB-backed bot calendar state.
- Ambient prompt injection of the current time on every turn.

**Target Architecture:**
- `discord_bot/utils/time_tools.py` owns the canonical timezone constant, the runtime clock helper, the serialized snapshot payload, and the `ToolDefinition` for `get_current_time`.
- `discord_bot/utils/tool_registry.py` imports and registers `tool_get_current_time` alongside the existing built-in tools.
- `discord_bot/tools/descriptors.py` classifies the new tool as a read-only `utility` built-in tool so the unified registry exposes sane metadata.
- `discord_bot/cogs/ai_brain.py` adds explicit time-awareness instructions that tell the model to call `get_current_time` instead of guessing for current-time or relative-date questions.
- No DB schema, reminder code, or feature-flag mapping changes are required; the tool should always be available because it is foundational runtime context, not a user-toggle feature.

**Important Tradeoff:** This design is intentionally tool-driven rather than ambient. The bot will only know the current time when it actually calls `get_current_time`. Reliability therefore depends on strong prompt instructions and regression tests that protect those instructions from being removed or weakened.
