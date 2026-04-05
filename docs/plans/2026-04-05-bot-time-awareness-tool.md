# Bot Time Awareness Tool Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Add a built-in `get_current_time` tool that returns authoritative bot-local time in `America/Denver`, and update prompt guidance so the model uses that tool whenever a reply depends on the current date or time.

**Architecture:** Implement a small read-only time tool module under `discord_bot/utils/`, register it through the existing built-in tool registry bridge, and classify it in the unified descriptor layer as a utility tool. Then update `discord_bot/cogs/ai_brain.py` so time-sensitive conversational turns explicitly instruct the model to call `get_current_time` rather than guessing the current date or time from model priors.

**Tech Stack:** Python, discord.py, pytz, pytest, unittest

---

## Context The Implementer Needs

- Built-in legacy tools are defined as `ToolDefinition` objects and registered in `E:\femboibot\discord_bot\utils\tool_registry.py`.
- Legacy built-in tools are mirrored into the unified descriptor registry through `legacy_tool_to_descriptor()` in `E:\femboibot\discord_bot\tools\compat.py`.
- Category and source metadata for legacy tools come from `E:\femboibot\discord_bot\tools\descriptors.py`. If a new tool is not added there, it will fall back to `uncategorized`.
- Prompt assembly happens in `E:\femboibot\discord_bot\cogs\ai_brain.py`, especially the section ordering around `AVAILABLE TOOLS`, `TOOL INSTRUCTIONS`, and the final `build_structured_prompt()` call.
- Existing user timezone and reminder behavior already exists and is out of scope:
  - `E:\femboibot\discord_bot\cogs\reminders.py`
  - `E:\femboibot\discord_bot\utils\db_handler.py`
- The bot's canonical timezone for this feature is fixed to `America/Denver`, including normal daylight-saving transitions.
- Prefer `pytz` here because the repo already uses it in `ai_brain.py`, and it is safer than introducing a new timezone stack just for this feature.

## Definition Of Done

- `get_current_time` exists as a built-in tool and returns a stable payload for `America/Denver`.
- The tool is registered and exposed with `builtin:get_current_time` metadata and `utility` category.
- The model prompt explicitly instructs time-sensitive turns to call `get_current_time`.
- Focused tests cover helper formatting, tool registration/metadata, tool execution, and prompt guidance.
- No reminder, scheduler, or DB schema behavior changes are introduced.

### Task 1: Add The Bot Time Helper And Tool Module

**Files:**
- Create: `E:\femboibot\discord_bot\utils\time_tools.py`
- Create: `E:\femboibot\tests\test_time_tools.py`

**Step 1: Write the failing tests**

Add focused tests for the helper and handler:

```python
from datetime import datetime

import pytz

from utils import time_tools


def test_build_bot_time_snapshot_formats_denver_timestamp():
    tz = pytz.timezone("America/Denver")
    fixed = tz.localize(datetime(2026, 1, 15, 8, 30, 45))

    snapshot = time_tools.build_bot_time_snapshot(fixed)

    assert snapshot["timezone"] == "America/Denver"
    assert snapshot["local_date"] == "2026-01-15"
    assert snapshot["local_time"] == "08:30:45"
    assert snapshot["weekday"] == "Thursday"
    assert snapshot["timezone_abbrev"] == "MST"
```

```python
async def test_get_current_time_tool_returns_read_only_payload():
    result = await time_tools._handle_get_current_time(_FakeContext(), {})
    assert result.ok is True
    assert result.data["timezone"] == "America/Denver"
    assert "local_date" in result.data
    assert "local_time" in result.data
```

**Step 2: Run the tests to verify they fail**

Run:

```powershell
python -m pytest E:\femboibot\tests\test_time_tools.py -q
```

Expected:
- FAIL because `utils.time_tools` does not exist yet

**Step 3: Write the minimal implementation**

Create `E:\femboibot\discord_bot\utils\time_tools.py` with one helper path and one tool definition:

```python
from __future__ import annotations

from datetime import datetime
from typing import Any

import pytz

from utils.tool_context import ToolContext
from utils.tool_registry import ToolDefinition, ToolResult

BOT_TIMEZONE_NAME = "America/Denver"


def _format_utc_offset(dt: datetime) -> str:
    raw = dt.strftime("%z")
    return f"{raw[:3]}:{raw[3:]}" if raw else ""


def build_bot_time_snapshot(now: datetime | None = None) -> dict[str, str]:
    tz = pytz.timezone(BOT_TIMEZONE_NAME)
    current = now.astimezone(tz) if now is not None else datetime.now(tz)
    return {
        "timezone": BOT_TIMEZONE_NAME,
        "iso_datetime": current.isoformat(),
        "local_date": current.strftime("%Y-%m-%d"),
        "local_time": current.strftime("%H:%M:%S"),
        "weekday": current.strftime("%A"),
        "timezone_abbrev": current.tzname() or BOT_TIMEZONE_NAME,
        "utc_offset": _format_utc_offset(current),
    }


async def _handle_get_current_time(context: ToolContext, args: dict[str, Any]) -> ToolResult:
    snapshot = build_bot_time_snapshot()
    return ToolResult(
        ok=True,
        summary=(
            f"Current bot local time in {snapshot['timezone']}: "
            f"{snapshot['local_date']} {snapshot['local_time']} "
            f"{snapshot['timezone_abbrev']} ({snapshot['weekday']})"
        ),
        data=snapshot,
    )


tool_get_current_time = ToolDefinition(
    name="get_current_time",
    description="Get the bot's authoritative current local date and time in America/Denver.",
    args_schema={},
    handler=_handle_get_current_time,
)
```

Keep this module read-only. Do not add DB access, user timezone lookups, or reminder integration.

**Step 4: Run the tests to verify they pass**

Run:

```powershell
python -m pytest E:\femboibot\tests\test_time_tools.py -q
```

Expected:
- PASS

**Step 5: Commit**

```powershell
git add E:\femboibot\discord_bot\utils\time_tools.py E:\femboibot\tests\test_time_tools.py
git commit -m "feat: add bot current time tool module"
```

### Task 2: Register The Tool In The Existing Tool Stack

**Files:**
- Modify: `E:\femboibot\discord_bot\utils\tool_registry.py`
- Modify: `E:\femboibot\discord_bot\tools\descriptors.py`
- Modify: `E:\femboibot\tests\test_tool_registry.py`
- Modify: `E:\femboibot\tests\test_tool_executor.py`

**Step 1: Write the failing tests**

Add registry and executor regressions:

```python
def test_get_current_time_registration_uses_builtin_utility_descriptor():
    async def _noop(context, args):
        return None

    tool = ToolDefinition(
        name="get_current_time",
        description="Current bot time",
        args_schema={},
        handler=_noop,
    )

    register_tool(tool)

    descriptor = get_unified_tool_registry().resolve_descriptor("get_current_time")
    assert descriptor is not None
    assert descriptor.tool_id == "builtin:get_current_time"
    assert descriptor.category == "utility"
    assert descriptor.side_effect_level == "read"
```

```python
async def test_executor_runs_get_current_time_tool():
    self.tool_registry.register_builtin_tools()
    await self.db_handler.init_db()

    envelope = ToolCallEnvelope(
        call_id="clock-1",
        tool_name="get_current_time",
        arguments={},
        invocation_mode=ToolInvocationMode.MODEL,
    )
    result = await self.executor.execute_tool_envelope(envelope, _make_context(111))

    assert result.ok is True
    assert result.data["timezone"] == "America/Denver"
```

**Step 2: Run the tests to verify they fail**

Run:

```powershell
python -m pytest E:\femboibot\tests\test_tool_registry.py E:\femboibot\tests\test_tool_executor.py -q
```

Expected:
- FAIL because the new tool is not yet registered or categorized

**Step 3: Write the minimal implementation**

Update `E:\femboibot\discord_bot\utils\tool_registry.py`:

```python
from utils.time_tools import tool_get_current_time

for tool in [
    tool_review_capabilities,
    tool_get_current_time,
    tool_web_search,
    ...
]:
    register_tool(tool)
```

Update `E:\femboibot\discord_bot\tools\descriptors.py`:

```python
LEGACY_TOOL_CATEGORIES = {
    "review_capabilities": "utility",
    "get_current_time": "utility",
    ...
}
```

Do not add a feature-flag entry in `E:\femboibot\discord_bot\utils\feature_flag_mapper.py`. This tool should remain always available.

**Step 4: Run the tests to verify they pass**

Run:

```powershell
python -m pytest E:\femboibot\tests\test_tool_registry.py E:\femboibot\tests\test_tool_executor.py E:\femboibot\tests\test_time_tools.py -q
```

Expected:
- PASS

**Step 5: Commit**

```powershell
git add E:\femboibot\discord_bot\utils\tool_registry.py E:\femboibot\discord_bot\tools\descriptors.py E:\femboibot\tests\test_tool_registry.py E:\femboibot\tests\test_tool_executor.py E:\femboibot\tests\test_time_tools.py
git commit -m "feat: register get current time tool"
```

### Task 3: Add Prompt Guidance So The Model Actually Uses The Tool

**Files:**
- Modify: `E:\femboibot\discord_bot\cogs\ai_brain.py`
- Modify: `E:\femboibot\tests\test_ai_brain_multi_response.py`

**Step 1: Write the failing tests**

Add a prompt-guidance regression that asserts the time-tool instructions exist:

```python
def test_time_awareness_prompt_instructions_reference_get_current_time():
    section = ai_brain_mod.section_from_lines(
        "TIME AWARENESS",
        ai_brain_mod.TIME_AWARENESS_TOOL_LINES,
    )
    assert section is not None
    assert "get_current_time" in section.body
    assert "America/Denver" in section.body
```

If you prefer not to expose the instruction tuple directly, extract a small helper from `ai_brain.py` and test that helper instead.

**Step 2: Run the tests to verify they fail**

Run:

```powershell
python -m pytest E:\femboibot\tests\test_ai_brain_multi_response.py -q
```

Expected:
- FAIL because the time-tool instruction lines do not exist yet

**Step 3: Write the minimal implementation**

Add explicit instruction text in `E:\femboibot\discord_bot\cogs\ai_brain.py`:

```python
TIME_AWARENESS_TOOL_LINES = [
    "Use get_current_time before answering any question that depends on the current date or time.",
    "Call get_current_time for words like now, today, tomorrow, yesterday, tonight, later, this morning, and current time.",
    "Interpret relative dates using the tool output in America/Denver instead of guessing from model knowledge.",
]
```

Then insert the section into prompt assembly before or adjacent to `AVAILABLE TOOLS` and `TOOL INSTRUCTIONS`:

```python
section_time_awareness = section_from_lines("TIME AWARENESS", TIME_AWARENESS_TOOL_LINES)
if section_time_awareness:
    section_order.append(section_time_awareness)
```

Keep this scoped to guidance only. Do not inject a static current timestamp into the prompt in this task.

**Step 4: Run the tests to verify they pass**

Run:

```powershell
python -m pytest E:\femboibot\tests\test_ai_brain_multi_response.py E:\femboibot\tests\test_tool_executor.py -q
```

Expected:
- PASS

**Step 5: Commit**

```powershell
git add E:\femboibot\discord_bot\cogs\ai_brain.py E:\femboibot\tests\test_ai_brain_multi_response.py
git commit -m "feat: add get current time prompt guidance"
```

### Task 4: Final Verification And Cleanup

**Files:**
- Modify only if a focused test reveals small cleanup needs in touched files

**Step 1: Write any missing failing regressions**

Add only narrow regressions if verification reveals a gap, for example:
- summary text missing weekday or timezone abbreviation
- executor path returning malformed offsets
- prompt guidance being placed after response-style text in a way that weakens tool use

Do not expand scope into reminders, DB config, or admin-panel settings.

**Step 2: Run the focused suite to verify failures**

Run:

```powershell
python -m pytest E:\femboibot\tests\test_time_tools.py E:\femboibot\tests\test_tool_registry.py E:\femboibot\tests\test_tool_executor.py E:\femboibot\tests\test_ai_brain_multi_response.py E:\femboibot\tests\test_tool_imports.py -q
```

Expected:
- any final edge-case regressions fail before cleanup

**Step 3: Write minimal fixes**

Patch only the specific failures discovered by the focused suite. Keep the final surface area limited to:
- `time_tools.py`
- `tool_registry.py`
- `descriptors.py`
- `ai_brain.py`
- touched tests

**Step 4: Run the final verification suite**

Run:

```powershell
python -m pytest E:\femboibot\tests\test_time_tools.py E:\femboibot\tests\test_tool_registry.py E:\femboibot\tests\test_tool_executor.py E:\femboibot\tests\test_tool_imports.py E:\femboibot\tests\test_tool_availability.py E:\femboibot\tests\test_tool_parser.py E:\femboibot\tests\test_tool_transports.py E:\femboibot\tests\test_ai_brain_multi_response.py E:\femboibot\tests\test_context_builder.py -q
```

Expected:
- PASS

**Step 5: Commit**

```powershell
git add E:\femboibot\discord_bot\utils\time_tools.py E:\femboibot\discord_bot\utils\tool_registry.py E:\femboibot\discord_bot\tools\descriptors.py E:\femboibot\discord_bot\cogs\ai_brain.py E:\femboibot\tests\test_time_tools.py E:\femboibot\tests\test_tool_registry.py E:\femboibot\tests\test_tool_executor.py E:\femboibot\tests\test_ai_brain_multi_response.py
git commit -m "feat: add bot time awareness tool"
```

## Notes For Execution

- Keep the tool name singular and specific: `get_current_time`. Do not add `get_calendar_context` unless a later requirement actually needs richer schedule state.
- Keep the tool argument schema empty. The timezone is fixed by product decision, so do not let the model choose arbitrary timezones here.
- Keep the tool read-only and deterministic in shape so downstream prompt-emulated tool parsing stays simple.
- If a later feature needs richer calendar context, build that as a second tool on top of the same helper module instead of expanding `get_current_time` into a multi-purpose API.

## Execution Handoff

Plan complete and saved to `docs/plans/2026-04-05-bot-time-awareness-tool.md`. Two execution options:

**1. Subagent-Driven (this session)** - I dispatch fresh subagent per task, review between tasks, fast iteration

**2. Parallel Session (separate)** - Open new session with executing-plans, batch execution with checkpoints

**Which approach?**
