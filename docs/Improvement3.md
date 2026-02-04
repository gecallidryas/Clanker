# The Persona System & Admin Controls (Revised)

A practical, project-aligned guide for persona webhooks, automod, DM welcome, logging, and starboard.
This version matches the current code layout and the per-guild database design.

---

## Part 1: Persona System (Webhook Implementation)

### 1.1 Architecture

Use webhooks for all chatbot replies to allow per-mode names and avatars, while keeping moderation and admin output on the default bot avatar.

1. **Brain**: generates the response and selects the current mode.
2. **Manager**: maps mode -> display name + avatar URL (from JSON).
3. **Proxy**: a webhook per channel sends the message with the persona mask.

**Rule of thumb**
- Chat content (AI replies, welcome chatter, mention reactions): webhook persona.
- Moderation/admin content (automod notices, logs, starboard, commands): default bot avatar.

---

### 1.2 Persona Asset File (JSON)

Store persona identities in a JSON file, reloaded automatically when it changes.

**File:** `discord_bot/data/personas.json`

```json
{
  "default": {
    "name": "Femmy",
    "avatar_url": "https://cdn.discordapp.com/attachments/123.../femmy_default.png"
  },
  "mode_femboy": {
    "name": "Femmy",
    "avatar_url": "https://cdn.discordapp.com/attachments/123.../femmy_pink.png"
  },
  "mode_tsundere": {
    "name": "Yumi-chan",
    "avatar_url": "https://cdn.discordapp.com/attachments/123.../yumi_angry.png"
  },
  "mode_oneesan": {
    "name": "Ara Ara Yumi",
    "avatar_url": "https://cdn.discordapp.com/attachments/123.../yumi_mature.png"
  }
}
```

---

### 1.3 PersonaManager (Implemented)

**File:** `discord_bot/utils/persona_manager.py`

Key behaviors:
- Caches webhooks per channel.
- Reloads `personas.json` when the file changes.
- Uses `wait=True` so callers can receive a `discord.Message` back.
- Falls back to normal `channel.send` if webhooks are unavailable.
- DM channels always use normal send (webhooks do not apply).

---

### 1.4 AI Brain Integration (Implemented)

**File:** `discord_bot/cogs/ai_brain.py`

The AI response now goes through `bot.persona_manager.send_as_mode(...)` so replies are sent via webhook persona.

**Important**: Webhooks do not create Discord "replies" (highlighted reply UI). If you want reply behavior, mention the user in content.

---

### 1.5 Edge Cases

**A. Reply UI**
- Webhooks do not support the rich reply UI. Use a manual mention if needed.

**B. Threads**
- For thread messages, the manager sends via the parent channel webhook with `thread=channel`.

**C. Permissions**
- Bot needs **Manage Webhooks** to create webhooks. Without it, it falls back to normal sends (no persona mask).

**D. Allowed Mentions**
- Default is no pings for webhook messages to avoid accidental @everyone.
- Welcome messages are allowed to mention the new member.

---

## Part 2: Admin Control Features (Per-Guild DB)

All admin data is stored in the per-guild SQLite DB created by `discord_bot/utils/db_handler.py`.

### 2.1 Automod Rules

**Schema (per-guild DB):**

```sql
CREATE TABLE automod_rules (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  guild_id INTEGER NOT NULL,
  keyword TEXT NOT NULL,
  punishment_type TEXT NOT NULL,
  duration_minutes INTEGER DEFAULT 0,
  UNIQUE(guild_id, keyword)
);
```

**Accessors (implemented in db_handler):**
- `add_automod_rule(...)`
- `remove_automod_rule(...)`
- `get_automod_rules(...)`

**Behavior notes:**
- Automod output uses the default bot avatar (not webhook).
- Recommended: exclude staff/admin/bots and use safer keyword matching.

**Spam Timeout (Auto-timeout on message floods):**
- Command: `/automod spam`
- Example: `/automod spam max_messages:12 window_seconds:10 timeout_minutes:5`
- Disable: `/automod spam state:off`

---

### 2.2 Owner DM Welcome (Preset Message)

**Storage (per-guild DB):** `guild_config.dm_welcome_message`

**Accessors (implemented in db_handler):**
- `get_dm_welcome_message(guild_id)`
- `set_dm_welcome_message(guild_id, message)`

**Design:**
- Public welcome messages stay in `cogs/social.py`.
- Private rule/links message is DM-only.

**Commands:**
- `/welcome set_dm_message`
- `/welcome clear_dm_message`
- `/welcome toggle_dm` (on/off)

### 2.3 Public Welcome Message Template (Editable)

Store an optional per-guild template for public welcomes.

**Storage (per-guild DB):** `guild_config.welcome_message_template`

**Placeholders:**
- `{member}` -> mention
- `{member_name}` -> display name
- `{member_count}` -> numeric count
- `{member_ordinal}` -> ordinal count (e.g., 67th)
- `{guild}` -> guild name

**Commands:**
- `/welcome set_message`
- `/welcome view_message`
- `/welcome clear_message`

---

### 2.4 Enhanced Logging

**Timeout logging** should use `on_member_update` and audit logs, posted to the mod log channel configured via `guild_config.mod_log_channel_id`.

Moderation logs use the default bot avatar.

---

## Part 3: Advanced Starboard System (Per-Guild DB)

Starboard is a reaction-driven highlight board. It **creates** the starboard post only when the threshold is reached, then **edits the count up or down** as reactions change. If the source message is deleted, the starboard post is **kept** but marked.

### 3.1 Database Schema (Per-Guild DB)

**Table A: `starboard_settings`**

| Column | Type | Description |
|--------|------|-------------|
| guild_id | INTEGER (PK) | Guild ID |
| channel_id | INTEGER | Destination channel |
| emoji_trigger | TEXT | Emoji to track, or `ANY` |
| threshold | INTEGER | Minimum count to post |
| allow_self_star | INTEGER | 0/1 |
| enabled | INTEGER | 0/1 |

**Table B: `starboard_entries`**

| Column | Type | Description |
|--------|------|-------------|
| original_message_id | INTEGER (PK) | Source message ID |
| guild_id | INTEGER | Guild ID |
| starboard_message_id | INTEGER | Posted message ID |
| channel_id | INTEGER | Source channel ID |
| emoji_used | TEXT | Emoji tracked |
| is_deleted | INTEGER | 0/1 |
| deleted_at | TIMESTAMP | When original was deleted |

**Table C: `starboard_ignored_channels`**

| Column | Type | Description |
|--------|------|-------------|
| guild_id | INTEGER | Guild ID |
| channel_id | INTEGER | Ignored channel ID |
| PRIMARY KEY (guild_id, channel_id) |

---

### 3.2 Core Logic & Event Flow

**Listeners:**
- `on_raw_reaction_add`
- `on_raw_reaction_remove`
- `on_raw_message_delete`

**Rules:**
1. Only create starboard posts when `effective_count >= threshold`.
2. When reactions change (add/remove), update the count in the starboard header.
3. If count drops below threshold, keep the starboard post but update the count.
4. If original message is deleted, **do not delete** the starboard post; mark it instead.

---

### 3.3 Presentation

**Header format:**

```
[Emoji] **[Count]** | #channel | @author
```

**Embed:**
- Color: `0xffac33`
- Timestamp: message timestamp
- Author: message author display name + avatar
- Description: message content (truncate to 4096)
- Field: `Source` -> `message.jump_url`
- Media: image attachment in embed; video URL appended to content

---

### 3.4 Admin Commands (Slash)

**File:** `discord_bot/cogs/starboard.py`

- `/starboard setup` (channel, threshold, emoji, allow_self_star)
- `/starboard toggle` (on/off)
- `/starboard ignore` (channel)
- `/starboard unignore` (channel)
- `/starboard ignored` (list)

---

## Implementation Checklist (Aligned to Current Codebase)

### Persona System
- [ ] Create `discord_bot/data/personas.json`
- [ ] Ensure **Manage Webhooks** permission for persona usage
- [ ] Keep moderation/admin output on default bot avatar

### Admin Controls
- [x] Automod commands + logic (`cogs/automod.py`)
- [x] DM welcome command (`/welcome set_dm_message`)
- [x] Timeout logging (`cogs/logger.py`)
- [x] Public welcome template (`/welcome set_message`)

### Starboard
- [x] Starboard commands are loaded via `cogs/starboard.py`
- [x] Reaction add/remove updates count
- [x] Delete marks starboard entry without removing it
