# Improvement 7: Mode-Based Personalization, Help Output, Hug/Pat Rules, and Server Avatars

## Overview
This improvement covers four major features:
1. Bot activity status change
2. Help output personalization by mode with a full command list
3. Hug/Pat rate limits with mode-specific responses and affection rules
4. Server-specific bot avatars (replacing webhooks)

---

## Part 1: Bot Activity Status

### [MODIFY] main.py

In `on_ready()`, change the activity from "Watching: over you~" to "Playing: Clanking with humans":

```python
async def on_ready(self):
    # ... existing logging code ...

    # Set bot activity
    activity = discord.Game(name="Clanking with humans")
    await self.change_presence(activity=activity)
```

---

## Part 2: Help Output Personalization (Full Command List + Mode Tone Rules)

### Goal
- The help command must show a complete command list (prefix and slash).
- The greeting and tone must be based on mode.
- Default mode (Clanker) must be plain and neutral.
- Femboy uses "Nii-chan", Oneesan uses "my dear", Tsundere uses "baka".

### [MODIFY] utilities.py

#### A) Centralize command inventory
Add a single source of truth so the command list is not missing items.

Example structure:
```python
HELP_COMMANDS = {
    "ai": {
        "prefix": ["!describe", "!tldr"],
        "slash": ["/describe", "/tldr"],
    },
    "memory": {
        "prefix": ["!remember", "!forget", "!myinfo", "!set_timezone", "!birthday", "!aboutuser", "!aka", "!aliases", "!whois"],
        "slash": ["/remember", "/forget", "/myinfo", "/timezone", "/birthday", "/aboutuser", "/aka", "/aliases", "/whois", "/analyze"],
    },
    "affection": {
        "prefix": ["!affection", "!mood", "!headpat", "!hug"],
        "slash": ["/affection", "/mood", "/headpat", "/hug"],
    },
    "personality": {
        "prefix": ["!mode", "!modes", "!currentmode"],
        "slash": ["/mode", "/modes", "/currentmode", "/evil"],
    },
    "utility": {
        "prefix": ["!help", "!ping", "!stats", "!about", "!translate", "!remind", "!reminders"],
        "slash": ["/help", "/ping", "/stats", "/about", "/translate", "/tldr", "/generate_embed"],
    },
    "moderation": {
        "prefix": ["!setbump", "!clearbump", "!sync"],
        "slash": ["/bumpchannel", "/bumpstart", "/bumpstop", "/automod add", "/automod remove", "/automod list", "/automod spam", "/starboard setup", "/starboard toggle", "/starboard ignore", "/starboard unignore", "/starboard ignored"],
    },
    "config": {
        "prefix": ["!admin", "!reload"],
        "slash": ["/config auth", "/config password", "/config keys", "/config model", "/config env", "/config staff", "/config modlog", "/config autorole", "/config welcome", "/admin reset", "/admin view"],
    },
}
```

#### B) Generate the help output from the inventory
Add a function that builds the output from `HELP_COMMANDS` so it cannot go out of date:

```python
def build_help_lines() -> list[str]:
    lines = []
    for section, cmds in HELP_COMMANDS.items():
        title = section.replace("_", " ").title()
        prefix_cmds = " ".join(cmds.get("prefix", []))
        slash_cmds = " ".join(cmds.get("slash", []))
        if prefix_cmds:
            lines.append(f"{title} (Prefix): {prefix_cmds}")
        if slash_cmds:
            lines.append(f"{title} (Slash): {slash_cmds}")
    return lines
```

#### C) Enforce mode-based greeting rules
Add intros and make sure the tone applies to the whole output.

```python
HELP_INTROS = {
    "mode_default": "Here are my available commands:",
    "mode_femboy": "Here is everything I can do for you, Nii-chan~",
    "mode_tsundere": "Fine, here is what I can do, baka.",
    "mode_oneesan": "Let me show you what I can help you with, my dear.",
}
```

When assembling the response:
- Use `HELP_INTROS[mode]` as the first line.
- Do NOT add extra cutesy text in `mode_default`.
- Do NOT add Nii-chan/my dear/baka outside their modes.

---

## Part 3: Hug/Pat Mode-Specific Responses and Rate Limits

### Requirements Summary
- Only `/hug` and `/headpat` (and aliases) use this logic.
- Rate limits apply only to non-default modes: 1 per hour and 3 per day.
- `mode_default` (Clanker):
  - Response: "Human, such actions are meaningless!" for both hug and pat.
  - Affection system disabled. Do not add or remove affection points.
  - Evil mode disabled (hard block) while in default mode.
- `mode_femboy`:
  - Hug: +1 affection
  - Pat: +1 affection
  - Response must be submissive and affectionate (generate message)
- `mode_tsundere`:
  - Hug: +1 affection
  - Pat: +1 affection
  - Response must be angry and include "baka"
- `mode_oneesan`:
  - Hug: +1 affection
  - Pat: -1 affection
  - Pat response must be cold/angry

### Database Schema

#### [MODIFY] db_handler.py

Add a table for hug/pat cooldowns:

```sql
CREATE TABLE IF NOT EXISTS interaction_cooldowns (
    guild_id INTEGER,
    user_id INTEGER,
    interaction_type TEXT,  -- 'hug' or 'pat'
    last_used TIMESTAMP,
    daily_count INTEGER DEFAULT 0,
    daily_reset DATE,
    PRIMARY KEY (guild_id, user_id, interaction_type)
)
```

Add helper functions:
```python
async def check_interaction_limit(guild_id, user_id, interaction_type) -> tuple[bool, str]:
    """Returns (can_interact, reason_if_blocked)
    reason_if_blocked is "hourly" or "daily".
    """
    # if daily_reset != today: reset daily_count to 0
    # if last_used within 1 hour: return (False, "hourly")
    # if daily_count >= 3: return (False, "daily")
    # otherwise return (True, "ok")

async def record_interaction(guild_id, user_id, interaction_type) -> None:
    """Update last_used, daily_count, daily_reset."""
```

### Response Dictionaries (ASCII only)

#### [MODIFY] affection.py

```python
HEADPAT_RESPONSES = {
    "mode_default": ["Human, such actions are meaningless!"],
    "mode_femboy": [
        "Mmm... your pats feel so nice, Nii-chan.",
        "Please keep going... I love your pats.",
        "E-eh... that feels really good... thank you."
    ],
    "mode_tsundere": [
        "W-what are you doing, baka?!",
        "Hmph. I do not need your pats, baka.",
        "D-don't get the wrong idea, baka."
    ],
    "mode_oneesan": [
        "Stop that. I am not a child.",
        "Do not pat me. That is rude.",
        "Enough. I will not tolerate that."
    ]
}

HUG_RESPONSES = {
    "mode_default": ["Human, such actions are meaningless!"],
    "mode_femboy": [
        "I feel safe in your arms, Nii-chan...",
        "Your hugs make me melt...",
        "I-I'm happy when you hold me..."
    ],
    "mode_tsundere": [
        "B-baka! What do you think you're doing?!",
        "Hmph. I am only allowing this, baka.",
        "D-don't get used to it, baka."
    ],
    "mode_oneesan": [
        "There, there... calm down, my dear.",
        "Come here. I will hold you properly.",
        "You are safe. I have you."
    ]
}

RATE_LIMIT_MESSAGES = {
    "mode_femboy": {
        "pat_hourly": "Femmy had all the pats right now!",
        "pat_daily": "Femmy had all the pats today!",
        "hug_hourly": "Femmy had all the hugs right now!",
        "hug_daily": "Femmy had all the hugs today!"
    },
    "mode_tsundere": {
        "pat_hourly": "Stop it. No more pats right now, baka.",
        "pat_daily": "No more pats today, baka.",
        "hug_hourly": "I have had enough hugs right now, baka.",
        "hug_daily": "No more hugs today."
    },
    "mode_oneesan": {
        "pat_hourly": "That is enough for now.",
        "pat_daily": "No more pats today.",
        "hug_hourly": "One hug is enough for now.",
        "hug_daily": "No more hugs today, my dear."
    }
}
```

### Affection Rules Table

| Mode | Headpat | Hug | Limits |
|------|---------|-----|--------|
| mode_default | 0 | 0 | None |
| mode_femboy | +1 | +1 | 3/day, 1/hour |
| mode_tsundere | +1 | +1 | 3/day, 1/hour |
| mode_oneesan | -1 | +1 | 3/day, 1/hour |

### Updated Command Logic (summary)
- Default mode: return fixed response, skip affection and limits.
- Other modes: apply rate limits first, then affection changes.

Also hard-block affection system and evil mode while in `mode_default` (Clanker).

---

## Part 4: Server-Specific Bot Avatars (Replace Webhooks)

### Goal
- Remove all webhook-based persona delivery.
- Use Discord server profile avatars instead.
- Mode changes auto-update avatars.
- Admins can upload custom avatars (max 500 KB).

### New Utility File

#### [NEW] server_avatar.py

Same as previous, plus:
- Reject files larger than 500 KB.
- Support per-guild custom avatar override path.

### Avatar Storage and Persistence

#### Storage
```
discord_bot/data/avatars/
  mode_default.png
  mode_femboy.png
  mode_tsundere.png
  mode_oneesan.png

discord_bot/data/avatars/custom/
  guild_<GUILD_ID>.png
```

#### [MODIFY] db_handler.py
Add a table to store per-guild avatar overrides:

```sql
CREATE TABLE IF NOT EXISTS guild_avatar_config (
    guild_id INTEGER PRIMARY KEY,
    custom_avatar_path TEXT,
    updated_at TIMESTAMP
)
```

Add helpers:
```python
async def get_guild_avatar_path(guild_id: int) -> Optional[str]
async def set_guild_avatar_path(guild_id: int, path: Optional[str]) -> None
```

### Admin Commands for Server Avatars

#### [MODIFY] admin.py
Add a new slash command group:

```python
avatar_group = app_commands.Group(name="avatar", description="Manage bot server avatar")

@avatar_group.command(name="set")
async def avatar_set(self, interaction, image: discord.Attachment):
    # Validate file type
    # Validate size <= 500 KB
    # Save to discord_bot/data/avatars/custom/guild_<ID>.png
    # set_guild_avatar_path()
    # Call set_server_avatar()

@avatar_group.command(name="mode")
async def avatar_mode(self, interaction):
    # Set avatar based on current mode and clear custom override

@avatar_group.command(name="reset")
async def avatar_reset(self, interaction):
    # Clear custom override and reset to global default
```

### Auto-Update Avatar on Mode Change

#### [MODIFY] social.py
After mode change succeeds:
```python
from utils.server_avatar import set_mode_avatar
await set_mode_avatar(self.bot, ctx.guild.id, new_mode)
```

If a custom avatar exists for the guild, do NOT override it unless the admin calls `/avatar mode` or `/avatar reset`.

### Remove Webhook System Completely

#### [REMOVE] persona_manager.py
- Delete webhook creation and send_as_mode logic.
- Replace usage in `ai_brain.py` with normal `message.reply()` or channel send.
- Remove webhook config fields if any are stored.

### Migration/cleanup
- Remove any webhook IDs stored in data/config.
- Remove any webhook setup docs from FEATURES and help.

---

## Verification Plan

### Automated Tests
1. Activity shows "Playing: Clanking with humans".
2. Help output uses correct greeting per mode and includes full command list.
3. Hug/pat rate limits: 1/hour and 3/day for non-default modes.
4. Affection changes: default=0, femboy/tsundere=+1, oneesan pat=-1.
5. Gemini key rotation still works with new config.

### Manual Verification
1. Run `!mode femboy` and verify avatar changes.
2. Test `!pat` and `!hug` in each mode and verify response tone.
3. Spam `!hug` to verify rate limits.
4. Use `/avatar set` with < 500 KB image.
5. Verify custom avatar persists and mode change does not override unless forced.
