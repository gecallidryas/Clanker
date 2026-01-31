# Implementation Plan: Per-Mode Affection Tracking

Track affection earned for each personality mode separately rather than a single combined total.

---

## Current State

| Component | Current Behavior |
|-----------|-----------------|
| **Database** | `user_affection_v2` stores one `affection_points` value per guild+user |
| **Modes** | `mode_femboy`, `mode_tsundere`, `mode_oneesan`, `mode_default` |
| **Command** | `/affection` shows one combined affection level |

---

## Proposed Changes

**Note:** `mode_default` exists but will be excluded from affection tracking and display.

### 1. Database Schema Update

**File:** `discord_bot/utils/db_handler.py`

Create a new table to track affection per mode (**excluding** `mode_default`):

```sql
CREATE TABLE IF NOT EXISTS user_affection_by_mode (
    guild_id INTEGER NOT NULL,
    user_id INTEGER NOT NULL,
    mode TEXT NOT NULL,  -- 'mode_femboy', 'mode_tsundere', 'mode_oneesan' (exclude 'mode_default')
    affection_points INTEGER DEFAULT 0,
    total_interactions INTEGER DEFAULT 0,
    last_interaction TIMESTAMP,
    affection_level TEXT DEFAULT 'stranger',
    PRIMARY KEY (guild_id, user_id, mode)
);
```

---

### 2. Database Functions

**File:** `discord_bot/utils/db_handler.py`

#### A. Get Affection by Mode

```python
async def get_affection_by_mode(guild_id: int, user_id: int, mode: str) -> Dict[str, Any]:
    """Get user's affection data for a specific mode."""
    async with guild_db(guild_id) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            "SELECT * FROM user_affection_by_mode WHERE guild_id = ? AND user_id = ? AND mode = ?",
            (guild_id, user_id, mode)
        ) as cursor:
            row = await cursor.fetchone()
            if row:
                return dict(row)
            return {
                "guild_id": guild_id,
                "user_id": user_id,
                "mode": mode,
                "affection_points": 0,
                "total_interactions": 0,
                "affection_level": "stranger"
            }
```

#### B. Get All Mode Affection

```python
async def get_all_mode_affection(guild_id: int, user_id: int) -> Dict[str, Dict[str, Any]]:
    """Get user's affection data for all modes."""
    modes = ["mode_femboy", "mode_tsundere", "mode_oneesan"]  # exclude mode_default
    result = {}
    
    async with guild_db(guild_id) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            "SELECT * FROM user_affection_by_mode WHERE guild_id = ? AND user_id = ?",
            (guild_id, user_id)
        ) as cursor:
            rows = await cursor.fetchall()
            for row in rows:
                result[row["mode"]] = dict(row)
    
    # Fill in missing modes with defaults
    for mode in modes:
        if mode not in result:
            result[mode] = {
                "guild_id": guild_id,
                "user_id": user_id,
                "mode": mode,
                "affection_points": 0,
                "total_interactions": 0,
                "affection_level": "stranger"
            }
    
    return result
```

#### C. Add Affection (Updated)

```python
async def add_affection_to_mode(guild_id: int, user_id: int, mode: str, points: int = 1) -> Dict[str, Any]:
    """Add affection points for a specific mode."""
    async with guild_db(guild_id) as db:
        async with db.execute(
            "SELECT affection_points, total_interactions FROM user_affection_by_mode WHERE guild_id = ? AND user_id = ? AND mode = ?",
            (guild_id, user_id, mode)
        ) as cursor:
            row = await cursor.fetchone()
        
        if row:
            new_points = row[0] + points
            new_interactions = row[1] + 1
        else:
            new_points = points
            new_interactions = 1
        
        new_level = _calculate_level(new_points)
        
        await db.execute("""
            INSERT INTO user_affection_by_mode (guild_id, user_id, mode, affection_points, total_interactions, last_interaction, affection_level)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(guild_id, user_id, mode) DO UPDATE SET
                affection_points = ?,
                total_interactions = ?,
                last_interaction = ?,
                affection_level = ?
        """, (guild_id, user_id, mode, new_points, new_interactions, datetime.now(), new_level,
              new_points, new_interactions, datetime.now(), new_level))
        await db.commit()
        
        return {
            "guild_id": guild_id,
            "user_id": user_id,
            "mode": mode,
            "affection_points": new_points,
            "total_interactions": new_interactions,
            "affection_level": new_level
        }
```

#### D. Admin Set/Reset by Mode

```python
async def set_affection_value_by_mode(guild_id: int, user_id: int, mode: str, points: int) -> Dict[str, Any]:
    """Set affection for a specific mode (admin use)."""
    new_level = _calculate_level(points)
    async with guild_db(guild_id) as db:
        await db.execute(
            """
            INSERT INTO user_affection_by_mode (guild_id, user_id, mode, affection_points, total_interactions, last_interaction, affection_level)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(guild_id, user_id, mode) DO UPDATE SET
                affection_points = ?,
                affection_level = ?,
                last_interaction = ?
            """,
            (guild_id, user_id, mode, points, 0, datetime.now(), new_level, points, new_level, datetime.now()),
        )
        await db.commit()
    return {
        "guild_id": guild_id,
        "user_id": user_id,
        "mode": mode,
        "affection_points": points,
        "affection_level": new_level
    }

async def reset_affection_by_mode(guild_id: int, user_id: int, mode: str) -> int:
    """Reset affection for a specific mode (admin use)."""
    async with guild_db(guild_id) as db:
        cursor = await db.execute(
            "DELETE FROM user_affection_by_mode WHERE guild_id = ? AND user_id = ? AND mode = ?",
            (guild_id, user_id, mode)
        )
        await db.commit()
        return cursor.rowcount
```

---

### 3. Affection Command Update

**File:** `discord_bot/cogs/affection.py`

Update `/affection` command to display all tracked modes (exclude `mode_default`) in a single embed:

```
┌────────────────────────────────────────┐
│ 💕 Username's Affection                │
├────────────────────────────────────────┤
│ 🎀 Femboy Mode                         │
│ Level: Friend  •  Points: 342          │
│ [████████░░] 68%                        │
├────────────────────────────────────────┤
│ 💢 Tsundere Mode                       │
│ Level: Stranger  •  Points: 12         │
│ [█░░░░░░░░░] 24%                        │
├────────────────────────────────────────┤
│ 💋 Oneesan Mode                        │
│ Level: Acquaintance  •  Points: 87     │
│ [████░░░░░░] 43%                        │
└────────────────────────────────────────┘
```

#### Mode Display Metadata

```python
MODE_AFFECTION_DISPLAY = {
    "mode_femboy": {"emoji": "🎀", "name": "Femboy Mode"},
    "mode_tsundere": {"emoji": "💢", "name": "Tsundere Mode"},
    "mode_oneesan": {"emoji": "💋", "name": "Oneesan Mode"},
}
```

Only tracked modes are shown; `mode_default` is excluded.

---

### 4. Affection Earning Logic

**Files:** `discord_bot/cogs/affection.py`, `discord_bot/cogs/ai_brain.py`

When affection is earned:
1. Get the server's **current active mode** via `get_server_mode(guild_id)`
2. If mode is `mode_default`, **do not** record affection (excluded)
3. Otherwise call `add_affection_to_mode(guild_id, user_id, current_mode, points)`

#### Affected Functions

| Location | Current Call | Updated Call |
|----------|--------------|--------------|
| `affection.py` → `headpat` | `add_affection(guild_id, user_id, 3)` | `add_affection_to_mode(guild_id, user_id, mode, 3)` |
| `affection.py` → `hug` | `add_affection(guild_id, user_id, 3)` | `add_affection_to_mode(guild_id, user_id, mode, 3)` |
| `affection.py` → `on_message` | `add_affection(guild_id, user_id, delta)` | `add_affection_to_mode(guild_id, user_id, mode, delta)` (skip if `mode_default`) |
| `ai_brain.py` → AI interactions | `add_affection(...)` | **No direct `add_affection` here** — only update `get_affection` to `get_affection_by_mode` |

---

### 5. Migration Strategy

#### Option A: Fresh Start (Recommended)
- Keep `user_affection_v2` for backward compatibility
- New interactions populate `user_affection_by_mode`
- Old single-value affection is ignored going forward

#### Option B: Copy to Default Mode
- Copy all existing `user_affection_v2` data into `user_affection_by_mode` with `mode = 'mode_femboy'`
- Requires one-time migration script
- `mode_default` remains excluded

```python
async def migrate_affection_to_modes(guild_id: int):
    """One-time migration of v2 affection data to per-mode table."""
    async with guild_db(guild_id) as db:
        await db.execute("""
            INSERT OR IGNORE INTO user_affection_by_mode 
                (guild_id, user_id, mode, affection_points, total_interactions, last_interaction, affection_level)
            SELECT guild_id, user_id, 'mode_femboy', affection_points, total_interactions, last_interaction, affection_level
            FROM user_affection_v2
        """)
        await db.commit()
```

---

### 6. AI Brain Integration

**File:** `discord_bot/cogs/ai_brain.py`

Update the AI response generation to:
1. Fetch affection for the **current mode** instead of global affection
2. Pass mode-specific affection to prompt builder
3. If `mode_default`, use a zeroed affection payload (stranger/0) so prompts stay neutral

```python
# Before
affection_data = await get_affection(guild_id, user_id)

# After
current_mode = await get_server_mode(guild_id)
affection_data = await get_affection_by_mode(guild_id, user_id, current_mode)
```

---

### 7. Admin Command Updates (Mode-Specific)

**File:** `discord_bot/cogs/admin.py`

- `!admin setaffection @user <points> <mode>` (require mode; validate against femboy/tsundere/oneesan)
- `/admin affection` add a `mode` choice (femboy/tsundere/oneesan); resolve to mode key and pass through to DB
- `!admin reset @user affection <mode>` and `/admin reset` add an optional `mode` parameter that is **required** when `reset_type=affection`
- If `reset_type` is not `affection`, ignore any `mode` parameter
- `mode_default` is excluded and should be rejected with a clear message
- For slash choices, expose only `femboy`, `tsundere`, `oneesan` and resolve with `resolve_mode_key`
- If `reset_type=affection` and no mode is provided, respond with a validation error (ephemeral for slash)

---

## Implementation Checklist

### Database Layer (`db_handler.py`)
- [ ] Add `user_affection_by_mode` table creation in `_init_guild_schema()`
- [ ] Implement `get_affection_by_mode(guild_id, user_id, mode)`
- [ ] Implement `get_all_mode_affection(guild_id, user_id)`
- [ ] Implement `add_affection_to_mode(guild_id, user_id, mode, points)`
- [ ] (Optional) Add migration function for existing data
- [ ] Add admin helpers for per-mode set/reset (e.g., `set_affection_value_by_mode`, `reset_affection_by_mode`)
- [ ] Update `reset_user_data` to support per-mode resets when `reset_type=affection`

### Affection Cog (`affection.py`)
- [ ] Add `MODE_AFFECTION_DISPLAY` metadata
- [ ] Update `/affection` command to show all tracked modes
- [ ] Update `!affection` command to show all tracked modes
- [ ] Update `headpat` command to use current mode
- [ ] Update `hug` command to use current mode
- [ ] Update `on_message` listener to use current mode
- [ ] Skip affection tracking when `mode_default`

### AI Brain (`ai_brain.py`)
- [ ] Update `get_affection()` calls to `get_affection_by_mode()`
- [ ] Ensure mode is passed to affection functions
- [ ] When `mode_default`, feed neutral affection data (stranger/0) into prompts

### Admin Commands (`admin.py`)
- [ ] Update `!admin setaffection` to require a mode argument (femboy/tsundere/oneesan)
- [ ] Update `/admin affection` slash command to include a `mode` choice and validate input
- [ ] Update `!admin reset` and `/admin reset` to accept a `mode` argument when `reset_type=affection`
- [ ] Update admin profile view to show per-mode affection (exclude `mode_default`)
- [ ] Update admin help text/command descriptions to mention mode requirements

### Imports & Exports
- [ ] Export new functions from `db_handler.py`
- [ ] Update imports in `affection.py`
- [ ] Update imports in `ai_brain.py`
- [ ] Update imports in `admin.py`

---

## Testing Plan

1. **Unit Test**: Verify `add_affection_to_mode()` correctly increments only the specified mode
2. **Integration Test**: Headpat in femboy mode → only femboy affection increases
3. **Display Test**: `/affection` shows all three modes with correct values
4. **Mode Switch Test**: Switch server mode, earn affection, verify correct mode updated
5. **Default Mode Test**: Switch to `mode_default`, earn affection, verify no per-mode changes
6. **Admin Test**: `setaffection` and `reset` affect only the selected mode

---

## Backward Compatibility

- Keep `get_affection()` and `add_affection()` functions (mark as deprecated)
- New code uses `*_by_mode` variants
- Old `user_affection_v2` table remains untouched
- `mode_default` is intentionally excluded from per-mode affection
