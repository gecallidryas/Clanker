# Femmy/Yumi Bot - Complete Implementation Plan v2

## 🎯 Overview
Major enhancement covering slash commands, server isolation, multi-model support, and identity fixes.

---

## Phase 1: Slash Commands Migration

### Core Commands → Slash
| Prefix | Slash | Description |
|--------|-------|-------------|
| `!mode` | `/mode` | Switch personality |
| `!modes` | `/modes` | List personalities |
| `!currentmode` | `/currentmode` | Show current mode |
| `!affection` | `/affection` | View affection |
| `!mood` | `/mood` | Check bot mood |
| `!headpat` | `/headpat` | Give affection |
| `!hug` | `/hug` | Give affection |

### Memory Commands → Slash
| Prefix | Slash | Description |
|--------|-------|-------------|
| `!remember` | `/remember` | Save fact |
| `!forget` | `/forget` | Clear your facts |
| `!myinfo` | `/myinfo` | View your info |
| `!aboutuser` | `/aboutuser` | View user facts |
| `!aka` | `/aka` | Add alias |
| `!aliases` | `/aliases` | List aliases |
| `!whois` | `/whois` | Find by alias |
| `!set_timezone` | `/timezone` | Set timezone |
| `!birthday` | `/birthday` | Set birthday |

### Utility Commands → Slash
| Prefix | Slash | Description |
|--------|-------|-------------|
| `!help` | `/help` | Show help |
| `!ping` | `/ping` | Latency check |
| `!stats` | `/stats` | Bot stats |
| `!about` | `/about` | Bot info |
| `!translate` | `/translate` | Translate text |
| `!remind` | `/remind` | Set reminder |
| `!reminders` | `/reminders` | List reminders |
| `!describe` | `/describe` | Describe image |
| `!tldr` | `/tldr` | Summarize messages |
| `!portfolio` | `/portfolio` | Check website |

### Admin Commands → Slash
| Prefix | Slash | Permissions |
|--------|-------|-------------|
| `!admin reset` | `/admin reset` | Admin |
| `!admin view` | `/admin view` | Admin |
| `!admin setfact` | `/admin setfact` | Admin |
| `!admin delfact` | `/admin delfact` | Admin |
| `!setbump` | `/bumpchannel` | Manage Guild |
| `!clearbump` | `/bumpstop` | Manage Guild |
| `!setaffection` | `/admin affection` | Admin |
| `!reload` | `/reload` | Owner |
| `!evil` | `/evil` | Manage Guild |

### New Admin Commands
| Command | Description |
|---------|-------------|
| `/admin model <name> <password>` | Change AI model (password: gayboi123) |
| `/setgenderrole <@role> <gender>` | Configure gender roles |

---

## Phase 2: Server Isolation

### Database Schema Changes
```sql
-- Add guild_id to user_facts
ALTER TABLE user_facts ADD COLUMN guild_id INTEGER;

-- New affection table with composite key
CREATE TABLE user_affection_v2 (
    guild_id INTEGER NOT NULL,
    user_id INTEGER NOT NULL,
    affection_points INTEGER DEFAULT 0,
    affection_level TEXT DEFAULT 'stranger',
    PRIMARY KEY (guild_id, user_id)
);

-- Add guild_id to aliases
ALTER TABLE user_aliases ADD COLUMN guild_id INTEGER;

-- Gender roles per server
CREATE TABLE gender_roles (
    guild_id INTEGER NOT NULL,
    role_id INTEGER NOT NULL,
    gender TEXT NOT NULL,
    PRIMARY KEY (guild_id, role_id)
);
```

### Migration Strategy
1. Wipe database (user confirmed fresh start OK)
2. Create new tables with guild_id
3. Update all DB functions to require guild_id

---

## Phase 3: Multi-Model Support

### OpenRouter Models
| Key | Model ID | Type |
|-----|----------|------|
| `venice` | `cognitivecomputations/dolphin-mistral-24b-venice-edition:free` | Free |
| `hermes` | `nousresearch/hermes-3-llama-3.1-405b:free` | Free |
| `deephermes` | `nousresearch/deephermes-3-mistral-24b-preview` | Paid |
| `mistral` | `mistralai/mistral-small-3.1-24b-instruct:free` | Free |

### Gemini Models
| Key | Model ID |
|-----|----------|
| `flash` | `google/gemini-2.5-flash` |
| `flash-lite` | `google/gemini-2.5-flash-lite` |

---

## Phase 4: Multi-API Architecture

### Separate API Keys
```env
OPENROUTER_API_KEY=...      # Evil mode chat
GEMINI_API_KEY=...          # Main chat
GEMINI_TRANSLATE_KEY=...    # Translation only
GEMINI_SUMMARIZE_KEY=...    # Fact deduplication
ADMIN_PASSWORD=gayboi123    # Model change password
```

### API Routing
| Task | API |
|------|-----|
| Evil Mode | OpenRouter |
| Normal Chat | Gemini |
| Translation | Gemini (translate key) |
| Fact Summary | Gemini (summarize key) |

---

## Phase 5: Name-Based Triggers

### Trigger Words Per Mode
```python
MODE_TRIGGERS = {
    "mode_femboy": ["femmy", "femboy"],
    "mode_oneesan": ["yumi", "yumi chan", "yumi-chan", "oneesan", "onesan"],
    "mode_tsundere": ["tsun", "tsundere"]
}
```

Bot responds when message contains trigger word (case-insensitive).

---

## Phase 6: Identity Isolation (Yumi vs Femmy)

### Problem
Yumi (oneesan mode) sometimes calls itself "Femmy" in help text.

### Fix
1. Make bot name configurable via `BOT_NAME` env var
2. Update help embeds to use `self.bot.user.name`
3. Update personas to reference `{bot_name}` dynamically

---

## Phase 7: Fact Deduplication

When `!remember @user <fact>`:
1. Fetch existing facts for user
2. Send to Gemini: "Summarize, remove contradictions"
3. Replace old facts with summary + new fact

---

## 📁 Files to Modify

| File | Changes |
|------|---------|
| `main.py` | Add CommandTree, sync slash commands |
| `utils/api_manager.py` | Multi-model, multi-API clients |
| `utils/db_handler.py` | guild_id everywhere, gender_roles table |
| `cogs/ai_brain.py` | Name triggers, gender in prompt |
| `cogs/social.py` | Slash: /mode, /evil |
| `cogs/affection.py` | Slash: /affection, /headpat, /hug |
| `cogs/memories.py` | Slash: /remember, fact dedup |
| `cogs/utilities.py` | Slash: /help, use bot.user.name |
| `cogs/admin.py` | Slash: /admin group, /setgenderrole |
| `.env.example` | New API keys |

---

## ✅ Verification Checklist
- [ ] All slash commands registered
- [ ] Server A data isolated from Server B
- [ ] "Femmy" help text shows "Yumi" in oneesan mode
- [ ] Name triggers work without @mention
- [ ] Admin password protects model change
- [ ] Gender roles detected correctly
