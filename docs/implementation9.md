# Implementation 9: Custom Affection Logic (Traits + Sentiment)

## Overview
Add a structured affection scoring system that:
- Awards one-time trait bonuses when users trigger persona-specific likes/dislikes.
- Uses sentiment (nice vs rude) to decide when to award or remove points.
- Keeps per-user memory so the same trait only awards points once.
- Works for built-in modes and custom personas without dynamic table creation.
- Keeps the main chat reply natural; affection logic is handled separately.

---

## Goals
- Trait triggers come from persona prompts (lines like `+likes ...`) and are matched via keywords.
- One-time trait points per user and persona.
- No per-session conversation judging or quality scoring.
- No dynamic SQL table creation; use shared tables for all personas.
- Compatible with custom personas created via `/persona create`.

Non-goals:
- Full LangChain/LangGraph orchestration.
- Replacing sentiment-based affection adjustments (keep existing sentiment deltas).

---

## Data Model

### [NEW] Tables (db_handler.py)

```sql
CREATE TABLE IF NOT EXISTS persona_traits (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    guild_id INTEGER NOT NULL,
    mode_key TEXT NOT NULL,
    trait_key TEXT NOT NULL,
    trait_text TEXT NOT NULL,
    trigger_terms TEXT,
    points_value INTEGER DEFAULT 0,
    one_time INTEGER DEFAULT 1,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE (guild_id, mode_key, trait_key)
);

CREATE TABLE IF NOT EXISTS user_trait_history (
    guild_id INTEGER NOT NULL,
    user_id INTEGER NOT NULL,
    mode_key TEXT NOT NULL,
    trait_key TEXT NOT NULL,
    first_triggered_at TIMESTAMP,
    last_triggered_at TIMESTAMP,
    times_triggered INTEGER DEFAULT 1,
    PRIMARY KEY (guild_id, user_id, mode_key, trait_key)
);
```

Notes:
- `trait_key` is a normalized slug (similar to `sanitize_persona_name`).
- `trigger_terms` is JSON stored as TEXT (list of keywords or phrases).
- All data lives in the per-guild DB; no global or per-persona DB tables.

---

## Trait Ingestion

### Source format (prompt-based)
Support prompt lines like:
```
+likes getting asked about his day (+10, one_time)
+likes talking about flowers (+10, one_time, keywords: flowers, roses)
+dislikes rude behavior (-5, repeatable, keywords: rude, insult, mean)
```

### Parser rules
- Lines starting with `+likes` or `+dislikes` become traits.
- Extract:
  - `trait_text` (full line without metadata).
  - `points_value` (default: +10 for likes, -5 for dislikes).
  - `one_time` (default: true for likes, false for dislikes unless specified).
  - Optional `keywords:` list -> `trigger_terms`.
- Normalize `trait_key` from `trait_text`.

### Seeding
- On persona create/edit, parse `normal_prompt` (and `evil_prompt` if present).
- Replace existing traits for that persona in `persona_traits`.
- For built-in modes, seed once per guild when first used or on startup.

---

## Trait Matching (Keyword Based)

- Use `trigger_terms` (keywords) from `persona_traits`.
- If no keywords are provided, fall back to `trait_text` substring matching.
- Match is case-insensitive.

---

## Awarding Points

### Trait points
For each `trait_hit`:
- Check `user_trait_history` for `(guild_id, user_id, trait_key)`.
- If `one_time` and already seen, do NOT award points.
- If not seen, add `points_value` to affection and insert into history.
- Always update `last_triggered_at` and `times_triggered`.

### Sentiment gate
- If sentiment is positive/very_positive, allow positive trait points.
- If sentiment is negative/very_negative/hostile, allow negative trait points.
- Neutral sentiment does not award trait points.

### Existing sentiment adjustments
Keep current sentiment-based deltas for bot-directed messages.
Trait scoring is additive and uses the same sentiment result.

---

## Response Memory (One-time traits)

One-time trait bonuses are tracked in `user_trait_history` so repeats do not award points.

---

## Integration Points

### affection.py
- On bot-directed messages, run sentiment analysis.
- Apply sentiment deltas.
- Apply trait bonuses based on keyword hits and sentiment gating.
- Persist `user_trait_history`.

### db_handler.py
Add helper functions:
```
async def upsert_persona_traits(guild_id, mode_key, traits) -> None
async def get_persona_traits(guild_id, mode_key) -> list[dict]
async def record_trait_hit(guild_id, user_id, mode_key, trait_key) -> bool
async def get_user_trait_history(guild_id, user_id, mode_key) -> list[dict]
```

### persona.py
- On create/edit, parse prompts and store traits with `upsert_persona_traits`.

---

## Safety and Cost Controls
- Only evaluate traits when the message targets the bot.
- Clamp points and ignore unknown traits.
- Log failures at debug level; do not break the user response.

---

## Verification Plan

### Automated Tests
- Trait parser extracts keys, points, one_time, keywords correctly.
- DB helpers:
  - upsert traits replaces old rows
  - trait history enforces one-time behavior
- Trait matching uses keywords when provided, otherwise falls back to substring matching.

### Manual Tests
1. Add `+likes talking about flowers (+10, one_time)` to a persona prompt.
2. Talk about flowers:
   - If sentiment is positive, award +10 once.
   - Repeat mentions do not award points again.
3. Mention flowers again:
   - No extra points.
