# Femmy Discord Bot - Phase 6 Implementation Plan

## 🎯 New Features Overview

| # | Feature | Priority | New Files | DB Changes |
|---|---------|----------|-----------|------------|
| 1 | Error Logging | 🔴 High | `utils/logger.py` | No |
| 2 | Rate Limiting | 🔴 High | `utils/rate_limiter.py` | No |
| 3 | Help Command | 🔴 High | Update `utilities.py` | No |
| 4 | !reload Command | 🟡 Medium | Update `utilities.py` | No |
| 5 | !stats Command | 🟡 Medium | Update `utilities.py` | Yes |
| 6 | Affection System | 🟢 Fun | `cogs/affection.py` | Yes |
| 7 | Mood System | 🟢 Fun | Update `affection.py` | Yes |
| 8 | Birthday Tracking | 🟢 Fun | Update `memories.py` | Yes |
| 9 | Reminders | 🟡 Medium | `cogs/reminders.py` | Yes |
| 10 | Translation | 🟢 Fun | Update `utilities.py` | No |

---

## 📊 Database Schema Changes

```sql
-- Add birthday to users table
ALTER TABLE users ADD COLUMN birthday TEXT;  -- Format: MM-DD

-- Affection tracking
CREATE TABLE IF NOT EXISTS user_affection (
    user_id INTEGER PRIMARY KEY,
    affection_points INTEGER DEFAULT 0,
    total_interactions INTEGER DEFAULT 0,
    last_interaction TIMESTAMP,
    affection_level TEXT DEFAULT 'stranger'
);

-- Bot mood per server
CREATE TABLE IF NOT EXISTS bot_mood (
    guild_id INTEGER PRIMARY KEY,
    mood TEXT DEFAULT 'neutral',
    mood_value INTEGER DEFAULT 50,  -- 0-100 scale
    last_updated TIMESTAMP
);

-- Reminders
CREATE TABLE IF NOT EXISTS reminders (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    guild_id INTEGER,
    channel_id INTEGER NOT NULL,
    message TEXT NOT NULL,
    remind_at TIMESTAMP NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    completed BOOLEAN DEFAULT FALSE
);

-- Bot stats
CREATE TABLE IF NOT EXISTS bot_stats (
    id INTEGER PRIMARY KEY CHECK (id = 1),
    messages_processed INTEGER DEFAULT 0,
    commands_executed INTEGER DEFAULT 0,
    images_analyzed INTEGER DEFAULT 0,
    start_time TIMESTAMP
);
```

---

## 🔴 1. Error Logging

### [NEW] `utils/logger.py`

Centralized logging with file rotation and Discord notification.

```python
# Features:
- File-based logging to logs/femmy.log
- Log rotation (10MB max, 5 backups)
- Console + file output
- Error notification to bot owner (optional)

# Log Levels:
- DEBUG: Detailed trace info
- INFO: General operational events  
- WARNING: Recoverable issues
- ERROR: Serious problems
- CRITICAL: Bot-breaking errors
```

### Usage
```python
from utils.logger import get_logger
logger = get_logger(__name__)
logger.info("Bot started")
logger.error("API failed", exc_info=True)
```

---

## 🔴 2. Rate Limiting (10/min)

### [NEW] `utils/rate_limiter.py`

Token bucket rate limiter per-user for AI commands.

```python
class RateLimiter:
    def __init__(self, rate: int = 10, per: int = 60):
        """10 requests per 60 seconds default"""
    
    async def acquire(self, user_id: int) -> bool:
        """Returns True if allowed, False if rate limited"""
    
    def get_retry_after(self, user_id: int) -> float:
        """Seconds until next allowed request"""
```

### Integration Points
- `ai_brain.py` → `on_message` listener
- `vision.py` → Image analysis
- `utilities.py` → `!tldr` command

### Personality-Aware Responses
```python
RATE_LIMIT_MESSAGES = {
    "mode_femboy": "S-sorry, I need a little break~ Try again in {seconds}s! ♡",
    "mode_tsundere": "Hmph! You're too demanding! Wait {seconds}s, baka!",
    "mode_oneesan": "Ara ara~ Slow down, dear. Take a breath for {seconds}s~"
}
```

---

## 🔴 3. Help Command

### [MODIFY] `cogs/utilities.py`

Custom `!help` that replaces default with personality-aware descriptions.

```python
@commands.command(name="help")
async def custom_help(self, ctx, command_name: str = None):
    """Show all commands with personality-flavored descriptions"""
```

### Features
- Grouped by category (AI, Memory, Social, Utility, Admin)
- Shows command aliases
- Persona-aware intro text
- Embed with color matching current mode

### Categories
| Category | Commands |
|----------|----------|
| 🧠 AI | (mention for chat), !describe |
| 💭 Memory | !remember, !forget, !myinfo, !set_timezone, !birthday |
| 🎭 Social | !mode, !modes, !currentmode |
| 🛠️ Utility | !help, !ping, !stats, !tldr, !portfolio, !translate, !remind |
| 🔧 Admin | !reload, !setbump, !clearbump |

---

## 🟡 4. !reload Command

### [MODIFY] `cogs/utilities.py`

Hot-reload cogs without restarting the bot.

```python
@commands.command(name="reload")
@commands.is_owner()
async def reload_cog(self, ctx, cog_name: str = None):
    """Reload a specific cog or all cogs"""
    # !reload ai_brain → Reload cogs.ai_brain
    # !reload all → Reload all cogs
    # !reload → Show available cogs
```

### Security
- `@commands.is_owner()` decorator
- Only bot owner can use

---

## 🟡 5. !stats Command

### [MODIFY] `cogs/utilities.py`

Bot statistics and uptime display.

```python
@commands.command(name="stats", aliases=["status", "info"])
async def bot_stats(self, ctx):
    """Display bot statistics"""
```

### Displayed Stats
- ⏱️ Uptime
- 🏠 Server count
- 👥 Total users
- 💬 Messages processed
- 🖼️ Images analyzed
- 🎭 Current mode
- 📊 Memory usage

---

## 🟢 6. Affection System

### [NEW] `cogs/affection.py`

Track user interactions and unlock special responses.

### Affection Levels
| Level | Points | Title | Unlocks |
|-------|--------|-------|---------|
| 0 | 0-49 | Stranger | Basic responses |
| 1 | 50-199 | Acquaintance | Occasional nicknames |
| 2 | 200-499 | Friend | More affectionate responses |
| 3 | 500-999 | Close Friend | Special emojis, pet names |
| 4 | 1000+ | Beloved | Unique responses, priority |

### Point Earning
| Action | Points |
|--------|--------|
| Message with bot | +1 |
| Use !remember | +3 |
| Daily first interaction | +5 |
| Help command | +1 |
| Image analysis | +2 |

### Commands
```python
!affection       # View your affection level
!affection @user # View another user's level (if public)
```

### Response Modifiers
Higher affection = more personalized, caring responses injected into AI context.

---

## 🟢 7. Mood System

### [MODIFY] `cogs/affection.py`

Bot mood affects response tone per server.

### Mood States
| Mood | Value Range | Effect |
|------|-------------|--------|
| 😊 Happy | 70-100 | Extra enthusiastic, more emojis |
| 😐 Neutral | 40-69 | Standard responses |
| 😔 Sad | 20-39 | Slightly subdued, needs cheering up |
| 😢 Neglected | 0-19 | Lonely responses, fishing for attention |

### Mood Influences
| Event | Mood Change |
|-------|-------------|
| User interaction | +2 |
| Headpat/affection | +5 |
| Being ignored (1hr no activity) | -3 |
| Server activity (any message) | +1 |
| Insult detection | -10 |

### Commands
```python
!mood           # Check bot's current mood
!headpat        # Give Femmy headpats (+5 mood, +3 affection)
!hug            # Give Femmy a hug (+5 mood, +3 affection)
```

---

## 🟢 8. Birthday Tracking

### [MODIFY] `cogs/memories.py`

Store and celebrate user birthdays.

### Commands
```python
!birthday set MM-DD    # Set your birthday (e.g., !birthday set 03-15)
!birthday              # View your birthday
!birthday @user        # View someone's birthday
!birthday upcoming     # List upcoming birthdays (next 30 days)
```

### Scheduler Addition
- Check daily at midnight (user's timezone)
- Send birthday wish in persona style
- Special birthday responses for 24 hours

### Birthday Messages
```python
BIRTHDAY_MESSAGES = {
    "mode_femboy": "🎂 Happy Birthday, Nii-chan/Onee-chan! I hope your day is super special~ ♡",
    "mode_tsundere": "🎂 I-it's not like I remembered your birthday or anything, baka! ...Happy Birthday.",
    "mode_oneesan": "🎂 Ara ara~ Happy Birthday, my dear! May this year bring you joy and growth~ 💕"
}
```

---

## 🟡 9. Reminders

### [NEW] `cogs/reminders.py`

User reminders with natural language parsing.

### Command
```python
!remind <time> <message>
# Examples:
!remind 2h drink water
!remind 30m check oven
!remind 1d submit assignment
!remind tomorrow at 9am meeting
```

### Time Parsing
| Format | Example |
|--------|---------|
| `Xm` | 30m → 30 minutes |
| `Xh` | 2h → 2 hours |
| `Xd` | 1d → 1 day |
| `Xw` | 1w → 1 week |
| Natural | "tomorrow at 9am" |

### Features
- Per-user reminder list: `!reminders`
- Cancel reminder: `!remind cancel <id>`
- Clear all: `!remind clear`
- Max 25 active reminders per user

### Delivery
- Mention user in original channel
- DM if channel unavailable
- Persona-styled reminder message

---

## 🟢 10. Translation

### [MODIFY] `cogs/utilities.py`

Translate text using Gemini.

### Command
```python
!translate <text> to <language>
# Examples:
!translate Hello world to japanese
!translate こんにちは to english
!translate Bonjour to spanish
```

### Features
- Auto-detect source language
- Support major languages
- Preserve formatting
- Persona-styled response wrapper

---

## 📁 New File Structure

```
discord_bot/
├── logs/                    # [NEW] Log files directory
│   └── femmy.log
├── utils/
│   ├── logger.py            # [NEW] Logging utility
│   ├── rate_limiter.py      # [NEW] Rate limiting
│   └── db_handler.py        # [MODIFY] New tables
├── cogs/
│   ├── affection.py         # [NEW] Affection + Mood
│   ├── reminders.py         # [NEW] Reminders
│   ├── memories.py          # [MODIFY] Add birthday
│   └── utilities.py         # [MODIFY] Help, stats, reload, translate
```

---

## ✅ Verification Plan

### Automated
```bash
python -m py_compile utils/logger.py
python -m py_compile utils/rate_limiter.py
python -m py_compile cogs/affection.py
python -m py_compile cogs/reminders.py
```

### Manual Testing
1. Rate limiting: Send 11 messages quickly
2. Reminders: Set reminder for 1 minute
3. Birthday: Set today's date, verify wish
4. Affection: Interact 50+ times, check level up
5. Mood: Leave server idle, check mood decay
