# Persona Impersonation Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Add `/persona impersonate` so staff can generate an inactive custom persona from a member's recent messages, with generated prompts, persona-specific sample dialogue, and copied avatar assets.

**Architecture:** Extend the existing custom persona system instead of building a separate impersonation mode. Add a focused helper module for collection/filtering/generation, persist persona-specific dialogue on `custom_personas`, and teach the prompt builder to prefer persona-local sample dialogue when an impersonated custom persona is active.

**Tech Stack:** Python 3.12, discord.py app commands, aiosqlite, Gemini profile-text generation, unittest

---

### Task 1: Add storage for persona-specific sample dialogue

**Files:**
- Modify: `discord_bot/utils/db_handler.py`
- Test: `discord_bot/tests/test_persona_impersonation_storage.py`

**Step 1: Write the failing storage test**

Create `discord_bot/tests/test_persona_impersonation_storage.py` with a test that inserts a custom persona carrying persona-specific sample dialogue and then reads it back through `get_custom_persona_by_name(...)`.

```python
import json
import unittest

from utils.db_handler import (
    create_custom_persona,
    get_custom_persona_by_name,
)


class PersonaImpersonationStorageTests(unittest.IsolatedAsyncioTestCase):
    async def test_custom_persona_persists_sample_dialogues_json(self) -> None:
        guild_id = 987654321
        mode_key = "custom_test_impersonation"
        sample_dialogues = [
            "yeah no i get you",
            "LMFAO that is so cursed",
        ]

        await create_custom_persona(
            guild_id=guild_id,
            name="Impersonated User",
            mode_key=mode_key,
            bio="Generated persona",
            avatar_path=None,
            banner_path=None,
            normal_prompt="Normal prompt",
            evil_prompt=None,
            created_by=111,
            aliases=["impersonated"],
            sample_dialogues_json=json.dumps(sample_dialogues),
        )

        persona = await get_custom_persona_by_name(guild_id, "Impersonated User")

        assert persona is not None
        assert json.loads(persona["sample_dialogues_json"]) == sample_dialogues
```

**Step 2: Run test to verify it fails**

Run: `cd /mnt/e/femboibot/discord_bot && python -m unittest tests.test_persona_impersonation_storage -v`

Expected: FAIL because `create_custom_persona(...)` and the schema do not yet support `sample_dialogues_json`.

**Step 3: Add the schema migration**

Update `custom_personas` schema and migrations in `discord_bot/utils/db_handler.py` to add:

```python
sample_dialogues_json TEXT
```

Also add a safe migration:

```python
try:
    await db.execute("ALTER TABLE custom_personas ADD COLUMN sample_dialogues_json TEXT")
except Exception:
    pass
```

**Step 4: Extend the custom persona accessors**

Update `create_custom_persona(...)` and `update_custom_persona(...)` to accept `sample_dialogues_json`.

```python
async def create_custom_persona(
    guild_id: int,
    name: str,
    mode_key: str,
    bio: Optional[str],
    avatar_path: Optional[str],
    banner_path: Optional[str],
    normal_prompt: str,
    evil_prompt: Optional[str],
    created_by: int,
    aliases: Optional[List[str]] = None,
    sample_dialogues_json: Optional[str] = None,
) -> int:
```

**Step 5: Run the storage test again**

Run: `cd /mnt/e/femboibot/discord_bot && python -m unittest tests.test_persona_impersonation_storage -v`

Expected: PASS.

**Step 6: Commit**

```bash
git add discord_bot/utils/db_handler.py discord_bot/tests/test_persona_impersonation_storage.py
git commit -m "feat: add persona-local sample dialogue storage"
```

### Task 2: Build the impersonation helper pipeline

**Files:**
- Create: `discord_bot/utils/persona_impersonation.py`
- Test: `discord_bot/tests/test_persona_impersonation_helpers.py`

**Step 1: Write the failing helper tests**

Create `discord_bot/tests/test_persona_impersonation_helpers.py` with focused tests for filtering, suffix generation, and Gemini payload parsing.

```python
import unittest

from utils.persona_impersonation import (
    choose_unique_persona_name,
    filter_impersonation_messages,
    parse_impersonation_payload,
)


class PersonaImpersonationHelperTests(unittest.TestCase):
    def test_filter_impersonation_messages_removes_low_signal_content(self) -> None:
        raw_messages = [
            "/help",
            "ok",
            "look at this",
            "look at this",
            "LMFAOOO absolutely not",
        ]

        filtered = filter_impersonation_messages(raw_messages)

        assert filtered == ["look at this", "LMFAOOO absolutely not"]

    def test_choose_unique_persona_name_adds_impersonation_suffix(self) -> None:
        existing = {"Tomori", "Tomori (impersonated)"}
        result = choose_unique_persona_name("Tomori", existing)
        assert result == "Tomori (impersonated 2)"

    def test_parse_impersonation_payload_requires_prompt_and_dialogues(self) -> None:
        payload = parse_impersonation_payload(
            '{"bio":"bio","normal_prompt":"prompt","sample_dialogues":["a","b"]}'
        )
        assert payload.normal_prompt == "prompt"
        assert payload.sample_dialogues == ["a", "b"]
```

**Step 2: Run test to verify it fails**

Run: `cd /mnt/e/femboibot/discord_bot && python -m unittest tests.test_persona_impersonation_helpers -v`

Expected: FAIL because the helper module does not exist yet.

**Step 3: Create the helper module**

Implement `discord_bot/utils/persona_impersonation.py` with:

- a dataclass for the parsed generation result
- `filter_impersonation_messages(raw_messages: list[str]) -> list[str]`
- `choose_unique_persona_name(base_name: str, existing_names: set[str]) -> str`
- `build_impersonation_prompt(...) -> str`
- `parse_impersonation_payload(payload_text: str) -> ImpersonationPayload`
- `collect_member_messages(...)`
- `copy_member_avatar(...)`

Key filtering rules:

```python
def filter_impersonation_messages(raw_messages: list[str]) -> list[str]:
    filtered: list[str] = []
    seen_normalized: set[str] = set()
    for message in raw_messages:
        text = " ".join((message or "").split()).strip()
        if not text:
            continue
        if text.startswith("/") or text.startswith("!"):
            continue
        if len(text) < 3:
            continue
        normalized = text.casefold()
        if normalized in {"ok", "k", "lol", "lmao"}:
            continue
        if normalized in seen_normalized:
            continue
        seen_normalized.add(normalized)
        filtered.append(text)
    return filtered
```

**Step 4: Run the helper tests again**

Run: `cd /mnt/e/femboibot/discord_bot && python -m unittest tests.test_persona_impersonation_helpers -v`

Expected: PASS.

**Step 5: Commit**

```bash
git add discord_bot/utils/persona_impersonation.py discord_bot/tests/test_persona_impersonation_helpers.py
git commit -m "feat: add persona impersonation helpers"
```

### Task 3: Add the `/persona impersonate` command

**Files:**
- Modify: `discord_bot/cogs/persona.py`
- Test: `discord_bot/tests/test_persona_impersonate_command.py`

**Step 1: Write the failing command tests**

Create `discord_bot/tests/test_persona_impersonate_command.py` covering:

- permission denial without `manage_guild`
- insufficient usable message count
- successful persona creation via helper stubs

```python
import unittest
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

from cogs.persona import Persona


class PersonaImpersonateCommandTests(unittest.IsolatedAsyncioTestCase):
    async def test_impersonate_requires_manage_guild(self) -> None:
        cog = Persona(bot=SimpleNamespace())
        interaction = SimpleNamespace(
            guild=SimpleNamespace(id=123, text_channels=[]),
            user=SimpleNamespace(id=1, guild_permissions=SimpleNamespace(manage_guild=False)),
            response=SimpleNamespace(send_message=AsyncMock(), defer=AsyncMock()),
            followup=SimpleNamespace(send=AsyncMock()),
        )
        member = SimpleNamespace(id=2, display_name="Target", bot=False)

        await cog.impersonate_persona.callback(cog, interaction, member, None)

        interaction.response.send_message.assert_awaited()
```

**Step 2: Run test to verify it fails**

Run: `cd /mnt/e/femboibot/discord_bot && python -m unittest tests.test_persona_impersonate_command -v`

Expected: FAIL because the command does not exist yet.

**Step 3: Implement the slash command**

Add a new subcommand in `discord_bot/cogs/persona.py`:

```python
@persona_group.command(name="impersonate", description="Generate a custom persona from a member's message history.")
@app_commands.checks.has_permissions(manage_guild=True)
@app_commands.describe(member="User to mirror", name="Optional custom persona name")
async def impersonate_persona(
    self,
    interaction: discord.Interaction,
    member: discord.Member,
    name: Optional[str] = None,
):
```

Flow:

- reject DMs
- defer ephemerally
- collect and filter target messages
- require at least `100` usable messages
- call `generate_guild_gemini_profile_text(...)`
- parse structured output
- choose a unique persona name
- copy avatar
- create the custom persona with `sample_dialogues_json`
- upsert persona traits from the generated prompts
- send ephemeral confirmation

**Step 4: Run the command tests again**

Run: `cd /mnt/e/femboibot/discord_bot && python -m unittest tests.test_persona_impersonate_command -v`

Expected: PASS.

**Step 5: Commit**

```bash
git add discord_bot/cogs/persona.py discord_bot/tests/test_persona_impersonate_command.py
git commit -m "feat: add persona impersonation command"
```

### Task 4: Prefer persona-local sample dialogue in prompt building

**Files:**
- Modify: `discord_bot/cogs/ai_brain.py`
- Test: `discord_bot/tests/test_persona_prompt_dialogues.py`

**Step 1: Write the failing prompt-builder test**

Create `discord_bot/tests/test_persona_prompt_dialogues.py` with a test that verifies a custom persona's `sample_dialogues_json` is used instead of guild-global sample dialogues.

```python
import json
import unittest
from unittest.mock import AsyncMock, patch

from cogs.ai_brain import AIBrain


class PersonaPromptDialogueTests(unittest.IsolatedAsyncioTestCase):
    async def test_build_prompt_prefers_custom_persona_dialogues(self) -> None:
        brain = AIBrain(bot=AsyncMock())
        custom_persona = {
            "normal_prompt": "persona prompt",
            "sample_dialogues_json": json.dumps(["first line", "second line"]),
        }

        with patch.object(brain, "_load_persona", AsyncMock(return_value="persona prompt")):
            with patch("cogs.ai_brain.get_custom_persona_by_mode_key", AsyncMock(return_value=custom_persona)):
                parsed = brain._persona_sample_dialogues_from_record(custom_persona)
                assert parsed == ["first line", "second line"]
```

**Step 2: Run test to verify it fails**

Run: `cd /mnt/e/femboibot/discord_bot && python -m unittest tests.test_persona_prompt_dialogues -v`

Expected: FAIL because persona-local sample dialogue parsing does not exist yet.

**Step 3: Update the prompt builder**

In `discord_bot/cogs/ai_brain.py`:

- add a small parser helper for `sample_dialogues_json`
- when the active mode is a custom persona, fetch the persona row
- if persona-local sample dialogue exists, render that into the `SAMPLE DIALOGUES` section
- otherwise retain current `get_sample_dialogues(...)` behavior

Suggested helper:

```python
def _persona_sample_dialogues_from_record(self, persona: Optional[dict]) -> list[str]:
    if not persona or not persona.get("sample_dialogues_json"):
        return []
    try:
        data = json.loads(persona["sample_dialogues_json"])
    except (TypeError, json.JSONDecodeError):
        return []
    return [str(item).strip() for item in data if str(item).strip()]
```

**Step 4: Run the prompt-builder test again**

Run: `cd /mnt/e/femboibot/discord_bot && python -m unittest tests.test_persona_prompt_dialogues -v`

Expected: PASS.

**Step 5: Commit**

```bash
git add discord_bot/cogs/ai_brain.py discord_bot/tests/test_persona_prompt_dialogues.py
git commit -m "feat: use persona-local sample dialogues in prompts"
```

### Task 5: Document the new command and verification path

**Files:**
- Modify: `discord_bot/docs/slash-commands.md`
- Modify: `discord_bot/guild.env.example`

**Step 1: Write the doc changes**

Update `discord_bot/docs/slash-commands.md` in the Social And Persona section with:

```markdown
| `/persona impersonate` | Generate a saved custom persona from a member's recent messages and avatar. | `persona.py` |
```

Clarify in `discord_bot/guild.env.example` that `GEMINI_PROFILE_KEY` is used by profile analysis and persona impersonation generation.

**Step 2: Run a quick doc sanity check**

Run:

- `cd /mnt/e/femboibot/discord_bot && rg -n "/persona impersonate|GEMINI_PROFILE_KEY" docs/slash-commands.md guild.env.example`

Expected: both updated references are present.

**Step 3: Commit**

```bash
git add discord_bot/docs/slash-commands.md discord_bot/guild.env.example
git commit -m "docs: document persona impersonation requirements"
```

### Task 6: Run full verification before shipping

**Files:**
- Modify: none

**Step 1: Run focused tests**

Run:

- `cd /mnt/e/femboibot/discord_bot && python -m unittest tests.test_persona_impersonation_storage -v`
- `cd /mnt/e/femboibot/discord_bot && python -m unittest tests.test_persona_impersonation_helpers -v`
- `cd /mnt/e/femboibot/discord_bot && python -m unittest tests.test_persona_impersonate_command -v`
- `cd /mnt/e/femboibot/discord_bot && python -m unittest tests.test_persona_prompt_dialogues -v`
- `cd /mnt/e/femboibot/discord_bot && python -m unittest tests.test_persona_manage_create -v`

Expected: all PASS.

**Step 2: Run syntax verification**

Run:

- `cd /mnt/e/femboibot/discord_bot && python -m py_compile cogs/persona.py cogs/ai_brain.py utils/persona_impersonation.py utils/db_handler.py`

Expected: no output, exit code `0`.

**Step 3: Commit**

```bash
git add -A
git commit -m "feat: add persona impersonation generation flow"
```
