# Bot Time Awareness And Timestamp Serialization

**Date:** 2026-04-06

## Summary

This implementation added a built-in bot clock tool so the AI can resolve the current time in a fixed canonical timezone instead of guessing. It also cleaned up the SQLite timestamp write path in the DB layer so Python `datetime` objects are no longer passed directly into SQLite parameter bindings.

The fixed bot-local timezone for this work is:

- `America/Denver`

## What Changed

### 1. Added built-in `get_current_time`

A new read-only built-in tool now exposes the bot's authoritative local time snapshot, including:

- timezone name
- ISO datetime
- local date
- local time
- weekday
- timezone abbreviation
- UTC offset

This logic lives in:

- `discord_bot/utils/time_tools.py`

### 2. Registered the tool in the existing tool stack

The new time tool was wired into the existing built-in tool registration path so it is available through the normal prompt-emulated tool flow. It was also classified as a read-only `utility` tool in the unified descriptor metadata.

This work touched:

- `discord_bot/utils/tool_registry.py`
- `discord_bot/tools/descriptors.py`

### 3. Added prompt guidance so the model uses the tool

Prompt assembly in the AI runtime now includes a `TIME AWARENESS` section that tells the model to call `get_current_time` for questions involving:

- now
- today
- tomorrow
- yesterday
- tonight
- later
- current time

This keeps the model from relying on stale model priors for relative-date questions.

This work touched:

- `discord_bot/cogs/ai_brain.py`

### 4. Removed deprecated SQLite datetime adapter usage

The DB layer had several writes and comparisons that passed raw Python `datetime` objects into SQLite. On Python 3.12+ this triggers the deprecated default sqlite datetime adapter path.

That write path was replaced with explicit ISO string serialization for:

- global bot stats `start_time`
- reminders `remind_at`
- starboard `deleted_at`
- pending fact `expires_at`
- the matching reminder and pending-fact cleanup comparisons

This cleanup lives in:

- `discord_bot/utils/db_handler.py`

## Files Updated

Primary implementation and regression coverage touched during this work:

- `discord_bot/utils/time_tools.py`
- `discord_bot/utils/tool_registry.py`
- `discord_bot/tools/descriptors.py`
- `discord_bot/cogs/ai_brain.py`
- `discord_bot/utils/db_handler.py`
- `tests/test_time_tools.py`
- `tests/test_tool_registry.py`
- `tests/test_tool_executor.py`
- `tests/test_ai_brain_multi_response.py`
- `tests/test_db_handler_timestamp_serialization.py`

## Verification

The following command was run after the implementation and timestamp cleanup:

```bash
python -m pytest E:\femboibot\tests\test_db_handler_timestamp_serialization.py E:\femboibot\tests\test_time_tools.py E:\femboibot\tests\test_tool_registry.py E:\femboibot\tests\test_tool_executor.py E:\femboibot\tests\test_tool_imports.py E:\femboibot\tests\test_tool_availability.py E:\femboibot\tests\test_tool_parser.py E:\femboibot\tests\test_tool_transports.py E:\femboibot\tests\test_ai_brain_multi_response.py E:\femboibot\tests\test_context_builder.py -q
```

Observed result:

- `31 passed, 1 warning in 22.72s`

## Remaining Warning

The remaining warning is not from this implementation. It comes from the installed third-party package:

- `google.genai.types`

Specifically, it warns about `_UnionGenericAlias` deprecation under Python 3.14. The earlier `aiosqlite` datetime adapter warning is no longer present after the DB timestamp serialization cleanup.

## Notes

- This implementation is intentionally tool-driven rather than ambient prompt injection.
- The bot only knows the current time when it calls `get_current_time`.
- Detailed design and task breakdown remain in:
  - `docs/plans/2026-04-05-bot-time-awareness-tool-design.md`
  - `docs/plans/2026-04-05-bot-time-awareness-tool.md`
