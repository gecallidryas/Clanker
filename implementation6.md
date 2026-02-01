# Implementation Plan: Natural Language Admin Interface

Enable admins to configure the bot using conversational commands instead of slash commands.

---

## Example Interactions

```
User: "Yumi, set starboard channel in #starboard and set any emoji as the trigger emojis, send messages to starboard after it gets more than 4 reacts per message"
Bot:  "I can do that. Please confirm the trigger emojis (any emoji, or a specific list) and threshold. Current parse: channel #starboard, threshold 5, emoji mode any. Reply 'confirm' or provide corrections."

User: "Femmy, set starboard channel in #starboard and set trigger emojis 💀🤣😂⭐🌟. Send to starboard after more than 4 reacts."
Bot:  "Done! Starboard configured: #starboard, triggers: 💀 🤣 😂 ⭐ 🌟, threshold: 5 reactions."

User: "Yumi, set starboard to #starboard with <:partyblob:123456789012345678> and :tada:"
Bot:  "Done! Starboard configured: #starboard, triggers: <:partyblob:123456789012345678> 🎉, threshold: 3 reactions."

User: "Yumi, ban @spammer for raiding"
Bot:  "Banned @spammer. Reason: raiding"

User: "Clanker, set welcome channel to #welcome and send 'Welcome {member}!' to new users"
Bot:  "Welcome system configured for #welcome with your custom message."
```

---

## Architecture

```
+-------------------------------------------------------------+
|                    AI Brain (ai_brain.py)                   |
|-------------------------------------------------------------|
|  1. Detect admin intent in message                          |
|  2. Extract parameters (channel, user, value, etc.)         |
|  3. Check permissions                                       |
|  4. Call action executor                                    |
|  5. Generate confirmation response                          |
+-------------------------------------------------------------+
```

---

## Supported Actions (Phase 1)

| Category | Action | Example Phrase |
|----------|--------|----------------|
| **Starboard** | Setup channel | "set starboard to #channel" |
| | Set threshold | "starboard needs at least 5 reacts" |
| | Set emoji list | "use 💀 🤣 😂 ⭐ 🌟 for starboard" |
| | Set any emoji | "starboard triggers on any emoji" |
| | Toggle | "disable/enable starboard" |
| **Welcome** | Set channel | "welcome new users in #welcome" |
| | Set message | "welcome message: Hello {member}!" |
| | Set DM | "DM new users: Check the rules" |
| **Automod** | Add rule | "delete messages with 'spam'" |
| | Timeout rule | "timeout users who say 'badword'" |
| | Remove rule | "remove automod rule 'spam'" |
| **Moderation** | Ban | "ban @user for reason" |
| | Kick | "kick @user" |
| | Timeout | "mute @user for 10 minutes" |
| **Config** | Set mode | "switch to tsundere mode" |
| | Set log channel | "log mod actions in #mod-log" |

---

## Implementation

### 1. Intent Detection Prompt

Add to AI system prompt when user has admin permissions:

```
# Admin Commands
You can execute admin commands when asked. Detect these intents:

STARBOARD_SETUP: channel, emoji_triggers, emoji_mode, threshold
WELCOME_SETUP: channel, message, dm_message
AUTOMOD_ADD: keyword, action (delete/timeout/ban), duration
MOD_BAN: user, reason
MOD_KICK: user, reason
MOD_TIMEOUT: user, duration, reason
CONFIG_MODE: mode_name
CONFIG_LOG: channel

When you detect an admin command, respond with a special JSON block:
\`\`\`admin_action
{"action": "STARBOARD_SETUP", "params": {"channel_id": 123, "emoji_triggers": ["💀", "🤣", "😂", "⭐", "🌟"], "threshold": 5}}
\`\`\`
Then provide a natural confirmation message.

Parsing rules:
- If the user says "more than X", set `threshold = X + 1`.
- If the user says "at least X" or "X or more", set `threshold = X`.
- If the user says "any emoji", set `emoji_mode = "any"` and leave `emoji_triggers` empty.
- If the user lists multiple emojis, set `emoji_triggers` to the list in order of appearance.
- If any of channel, emojis (list or any), or threshold are missing, ask a follow-up confirmation question and do NOT emit an `admin_action` block.
```

### 2. Action Executor

**File:** `discord_bot/utils/admin_actions.py`

```python
from typing import Dict, Any, Optional
from utils.db_handler import (
    set_starboard_settings,
    set_welcome_channel,
    set_automod_rule,
    # ... other imports
)

ACTIONS = {
    "STARBOARD_SETUP": execute_starboard_setup,
    "WELCOME_SETUP": execute_welcome_setup,
    "AUTOMOD_ADD": execute_automod_add,
    "MOD_BAN": execute_mod_ban,
    "MOD_KICK": execute_mod_kick,
    "MOD_TIMEOUT": execute_mod_timeout,
    "CONFIG_MODE": execute_config_mode,
    "CONFIG_LOG": execute_config_log,
}

async def execute_admin_action(
    action: str,
    params: Dict[str, Any],
    guild: discord.Guild,
    executor: discord.Member
) -> Dict[str, Any]:
    """Execute an admin action and return result."""
    if action not in ACTIONS:
        return {"success": False, "error": "Unknown action"}

    # Permission check
    if not executor.guild_permissions.administrator:
        return {"success": False, "error": "Insufficient permissions"}

    return await ACTIONS[action](params, guild, executor)


async def execute_starboard_setup(params, guild, executor):
    channel_id = params.get("channel_id")
    emoji_triggers = params.get("emoji_triggers", [])
    emoji_mode = params.get("emoji_mode", "list")
    threshold = params.get("threshold", 3)

    await set_starboard_settings(
        guild.id,
        channel_id=channel_id,
        emoji_triggers=emoji_triggers,
        emoji_mode=emoji_mode,
        threshold=threshold,
        enabled=True
    )

    display_emojis = "any emoji" if emoji_mode == "any" else " ".join(emoji_triggers)

    return {
        "success": True,
        "message": f"Starboard configured: <#{channel_id}>, triggers: {display_emojis}, threshold: {threshold} reactions"
    }
```

### 3. AI Brain Integration

**File:** `discord_bot/cogs/ai_brain.py`

```python
import re
import json
from utils.admin_actions import execute_admin_action

async def process_response(self, message, response_text):
    # Check for admin action block
    action_match = re.search(r'```admin_action\n(.+?)\n```', response_text, re.DOTALL)

    if action_match:
        try:
            action_data = json.loads(action_match.group(1))
            result = await execute_admin_action(
                action=action_data["action"],
                params=action_data["params"],
                guild=message.guild,
                executor=message.author
            )

            if not result["success"]:
                # Replace action block with error
                response_text = response_text.replace(
                    action_match.group(0),
                    f"⚠️ {result['error']}"
                )
        except Exception as e:
            logger.error(f"Admin action failed: {e}")

        # Remove the JSON block from visible response
        response_text = re.sub(r'```admin_action\n.+?\n```\s*', '', response_text, flags=re.DOTALL)

    return response_text
```

### 4. Permission-Aware Prompting

Only inject admin capabilities into prompt when user has permissions:

```python
def build_admin_prompt(member: discord.Member) -> str:
    if not member.guild_permissions.administrator:
        return ""

    return """
# Admin Commands
You can execute configuration commands. When the user asks to configure something, output:
```admin_action
{"action": "ACTION_NAME", "params": {...}}
```

Available actions:
- STARBOARD_SETUP: channel_id, emoji_triggers, emoji_mode, threshold
- WELCOME_SETUP: channel_id, message, dm_message  
- MOD_BAN: user_id, reason
- MOD_TIMEOUT: user_id, duration_minutes, reason
- CONFIG_MODE: mode (femboy/tsundere/oneesan)
"""
```

---

## Channel/User/Emoji Resolution

The AI must resolve mentions/names to IDs and validate emojis:

```python
def resolve_channel(guild, text):
    # Try mention format: <#123456>
    match = re.match(r'<#(\d+)>', text)
    if match:
        return int(match.group(1))

    # Try channel name
    for channel in guild.text_channels:
        if channel.name.lower() == text.lower().strip('#'):
            return channel.id

    return None


def resolve_emoji_list(guild, tokens):
    """Return a list of normalized emoji strings (unicode or custom emoji mention)."""
    resolved = []
    for token in tokens:
        token = token.strip()

        # Custom emoji mention: <:name:id> or <a:name:id>
        match = re.match(r'<a?:\w+:(\d+)>', token)
        if match:
            emoji_id = int(match.group(1))
            emoji_obj = discord.utils.get(guild.emojis, id=emoji_id)
            if emoji_obj:
                resolved.append(str(emoji_obj))
            continue

        # Name-based custom emoji, like :partyblob:
        if token.startswith(':') and token.endswith(':'):
            name = token.strip(':')
            emoji_obj = discord.utils.get(guild.emojis, name=name)
            if emoji_obj:
                resolved.append(str(emoji_obj))
                continue

        # Fallback: assume unicode emoji
        if token:
            resolved.append(token)

    return resolved


def normalize_threshold(phrase: str, number: int) -> int:
    phrase = phrase.lower()
    if "more than" in phrase:
        return number + 1
    return number
```

---

## Security Considerations

| Risk | Mitigation |
|------|------------|
| Non-admin tries admin command | Permission check before execution |
| AI hallucinates action | Validate action exists in ACTIONS dict |
| Invalid parameters | Parameter validation in each executor |
| Destructive actions (ban/kick) | Require explicit confirmation for moderation |
| Emoji list includes invalid custom emoji | Resolve against `guild.emojis`, reject unknown entries |

---

## Confirmation for Destructive Actions

For bans/kicks, require confirmation:

```
User: "Ban @baduser for spam"
Bot:  "⚠️ Confirm ban @baduser for 'spam'? Reply 'yes' to confirm."
User: "yes"
Bot:  "✅ Banned @baduser. Reason: spam"
```

---

## Implementation Checklist

- [ ] Create `utils/admin_actions.py` with action executors
- [ ] Add channel/user resolution helpers
- [ ] Add emoji list resolution and validation (unicode + custom)
- [ ] Normalize threshold language (more than / at least / or more)
- [ ] Add missing-parameter confirmation flow (no action block until confirmed)
- [ ] Update AI prompt to include admin capabilities (permission-gated)
- [ ] Add action block parsing in `ai_brain.py`
- [ ] Implement confirmation flow for destructive actions
- [ ] Add audit logging for NLU admin commands
- [ ] Update starboard settings storage to allow multiple emoji triggers
- [ ] Update starboard reaction counting to match any configured trigger emoji
- [ ] Test with various natural language phrasings
