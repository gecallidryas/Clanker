# Welcome Image Repair Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Repair legacy guild schemas so the welcome image toggle persists correctly, and simplify welcome images to always send in the main welcome channel.

**Architecture:** Add an idempotent guild-config schema repair helper in the DB layer, then collapse welcome-image routing in the config and social cogs onto `welcome_channel_id`. Keep the old schema fields for compatibility, but stop relying on separate image destination/channel behavior during normal sends and previews.

**Tech Stack:** Python, aiosqlite, unittest, Discord.py

---

### Task 1: Add legacy-schema regression coverage

**Files:**
- Modify: `tests/test_social_welcome_dm.py`
- Modify: `tests/test_welcome_image_config.py`
- Create or Modify: `tests/test_db_handler.py` if needed

**Step 1: Write the failing tests**

- Add a test that creates a temporary guild DB with `guild_config` missing the welcome-image columns, runs the schema init/repair path, and asserts the missing columns are added.
- Add a test that shows welcome image preview uses the main welcome channel.
- Add a test that shows `Set Image Channel` no longer controls runtime routing.

**Step 2: Run tests to verify they fail**

Run:
```bash
python3 -m unittest tests.test_social_welcome_dm tests.test_welcome_image_config
```

Expected:
- The new legacy-schema or routing assertions fail before implementation.

**Step 3: Write minimal implementation**

- Only implement the schema repair and routing simplification needed to satisfy the new tests.

**Step 4: Run tests to verify they pass**

Run:
```bash
python3 -m unittest tests.test_social_welcome_dm tests.test_welcome_image_config
```

Expected:
- All tests in those modules pass.

### Task 2: Repair legacy guild schemas

**Files:**
- Modify: `discord_bot/utils/db_handler.py`
- Test: `tests/test_db_handler.py` or existing DB-related test module

**Step 1: Write the failing test**

- Create a targeted test for a guild DB whose `guild_config` table predates the welcome-image columns.

**Step 2: Run test to verify it fails**

Run:
```bash
python3 -m unittest <targeted-db-handler-test>
```

Expected:
- Failure because the missing columns remain missing.

**Step 3: Write minimal implementation**

- Extract or tighten the migration logic so the welcome-image columns are always backfilled for existing guild DBs.
- Avoid broad exception swallowing around the per-column repair loop.

**Step 4: Run test to verify it passes**

Run:
```bash
python3 -m unittest <targeted-db-handler-test>
```

Expected:
- The repaired schema contains the welcome-image columns.

### Task 3: Simplify welcome image routing

**Files:**
- Modify: `discord_bot/cogs/social.py`
- Modify: `discord_bot/cogs/config.py`
- Test: `tests/test_social_welcome_dm.py`
- Test: `tests/test_welcome_image_config.py`

**Step 1: Write the failing tests**

- Add or update tests so preview sends and join-event sends route images to `welcome_channel_id`.
- Add or update tests so enabling welcome images requires a configured welcome channel.

**Step 2: Run tests to verify they fail**

Run:
```bash
python3 -m unittest tests.test_social_welcome_dm tests.test_welcome_image_config
```

Expected:
- Failures in routing or enablement behavior.

**Step 3: Write minimal implementation**

- Resolve welcome image targets exclusively from the main welcome channel for guild sends.
- Make the toggle guard against enabling when no main welcome channel exists.
- Keep old config fields readable, but stop using them for normal server routing.

**Step 4: Run tests to verify they pass**

Run:
```bash
python3 -m unittest tests.test_social_welcome_dm tests.test_welcome_image_config
```

Expected:
- All welcome-image tests pass.

### Task 4: Final verification

**Files:**
- Modify: `discord_bot/utils/db_handler.py`
- Modify: `discord_bot/cogs/social.py`
- Modify: `discord_bot/cogs/config.py`
- Modify: `tests/test_social_welcome_dm.py`
- Modify: `tests/test_welcome_image_config.py`

**Step 1: Run full verification**

Run:
```bash
python3 -m unittest tests.test_social_welcome_dm tests.test_welcome_image_config
```

Expected:
- Full module suites pass.

**Step 2: Spot-check legacy DBs**

Run:
```bash
python3 - <<'PY'
import sqlite3
from pathlib import Path
for path in sorted(Path('discord_bot/data').glob('guild_*.db')):
    con = sqlite3.connect(path)
    cols = [row[1] for row in con.execute("PRAGMA table_info(guild_config)")]
    print(path.name, all(name in cols for name in [
        "welcome_image_enabled",
        "welcome_image_template",
        "welcome_image_destination",
        "welcome_image_channel_id",
    ]))
    con.close()
PY
```

Expected:
- Every active guild DB reports `True` after repair has run.
