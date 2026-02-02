# Improvement 7: Mode-Based Personalization & Server Avatars

## Overview
This improvement covers four major features:
1. Bot activity status change
2. Help command personalization by mode
3. Hug/Pat rate limits with mode-specific responses/affection
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

## Part 2: Help Command Personalization

### [MODIFY] utilities.py

**Update HELP_INTROS to include mode_default (Clanker mode):**

```python
HELP_INTROS = {
    "mode_default": "Here are my available commands:",
    "mode_femboy": "Here's everything I can do for you, Nii-chan~ ♡",
    "mode_tsundere": "Fine, here's what I can do, baka! Don't expect me to help you though!",
    "mode_oneesan": "Ara ara~ Let me show you what I can help you with, my dear~"
}
```

---

## Part 3: Hug/Pat Mode-Specific Responses & Rate Limits

### Database Schema

#### [MODIFY] db_handler.py

Add table for tracking hug/pat cooldowns:

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
    """Returns (can_interact, reason_if_blocked)"""
    # Check hourly limit (1 per hour)
    # Check daily limit (3 per day)
    # Returns ("ok", None), ("hourly", "right now"), or ("daily", "today")

async def record_interaction(guild_id, user_id, interaction_type) -> None:
    """Records interaction timestamp and increments daily count"""
```

---

### Response Dictionaries

#### [MODIFY] affection.py

**Add mode_default responses and rate limit messages:**

```python
# Clanker mode (mode_default) responses
HEADPAT_RESPONSES = {
    "mode_default": ["Human, such actions are meaningless!"],
    "mode_femboy": [
        "*leans into your hand* Mmm~ Nii-chan's pats are the best~ ♡",
        "*purrs softly* M-more please... I love this so much~ ✨",
        "*tail wags excitedly* Ehehe~ You're spoiling me~ >w<"
    ],
    "mode_tsundere": [
        "*blushes furiously* W-what are you doing, baka?! ...d-don't stop.",
        "Hmph! It's not like I like this or anything! *secretly enjoys it*",
        "*crosses arms but doesn't move away* F-fine, just this once!"
    ],
    "mode_oneesan": [
        "*looks coldly* ...What are you doing?",
        "Ara... I'm not a child to be patted. *pulls away*",
        "*sighs* You're quite bold, aren't you? But I don't need that."
    ]
}

HUG_RESPONSES = {
    "mode_default": ["Human, such actions are meaningless!"],
    "mode_femboy": [
        "*melts into your arms* Nii-chan~ I feel so safe with you~ ♡",
        "*hugs back tightly* Never let go, okay? ✨",
        "*nuzzles against you* Your hugs are the best thing ever~"
    ],
    "mode_tsundere": [
        "*stiffens* B-baka! What do you think you're- ...fine. *hugs back*",
        "I-it's not like I wanted a hug! *squeezes you anyway*",
        "Hmph! You're lucky I'm allowing this! *secretly smiling*"
    ],
    "mode_oneesan": [
        "*wraps arms around you gently* There there, my dear~ ♡",
        "Ara ara~ Come here, let me hold you properly~",
        "*gentle embrace* You give the sweetest hugs, little one~"
    ]
}

# Rate limit messages by mode
RATE_LIMIT_MESSAGES = {
    "mode_femboy": {
        "pat_hourly": "Femmy had all the pats right now! Come back later~ ♡",
        "pat_daily": "Femmy had all the pats today! See you tomorrow~ ✨",
        "hug_hourly": "Femmy had all the hugs right now! Come back later~ ♡",
        "hug_daily": "Femmy had all the hugs today! See you tomorrow~ ✨"
    },
    "mode_tsundere": {
        "pat_hourly": "S-stop it! I've had enough pats for now, baka!",
        "pat_daily": "No more pats today! Come back tomorrow, baka!",
        "hug_hourly": "I-I've had enough hugs for now! Go away!",
        "hug_daily": "No more hugs today! ...come back tomorrow."
    },
    "mode_oneesan": {
        "pat_hourly": "That's quite enough for now, dear~",
        "pat_daily": "We've had our moments today. Perhaps tomorrow~",
        "hug_hourly": "One hug is enough for now, little one~",
        "hug_daily": "You've had your fill of hugs today, my dear~"
    }
}
```

---

### Affection Point Rules by Mode

| Mode | Headpat | Hug | Limits |
|------|---------|-----|--------|
| mode_default | 0 (no effect) | 0 (no effect) | None |
| mode_femboy | +1 | +1 | 3/day, 1/hour |
| mode_tsundere | +1 | +1 | 3/day, 1/hour |
| mode_oneesan | **-1** | +1 | 3/day, 1/hour |

---

### Updated Command Logic

```python
@commands.command(name="headpat", aliases=["pat", "pets"])
async def headpat(self, ctx: commands.Context):
    if not ctx.guild:
        return
    
    mode = await get_server_mode(ctx.guild.id)
    
    # mode_default: no affection, no limits
    if mode == "mode_default":
        await ctx.send("Human, such actions are meaningless!")
        return
    
    # Check rate limits
    can_interact, reason = await check_interaction_limit(
        ctx.guild.id, ctx.author.id, "pat"
    )
    
    if not can_interact:
        msg_key = f"pat_{reason}"
        message = RATE_LIMIT_MESSAGES.get(mode, {}).get(msg_key, "Too many pats!")
        await ctx.send(message)
        return
    
    # Record interaction
    await record_interaction(ctx.guild.id, ctx.author.id, "pat")
    
    # Update mood
    await update_mood(ctx.guild.id, 5)
    
    # Apply affection based on mode
    if mode == "mode_oneesan":
        await add_affection_to_mode(ctx.guild.id, ctx.author.id, mode, -1)
    else:
        await add_affection_to_mode(ctx.guild.id, ctx.author.id, mode, 1)
    
    # Send response
    responses = HEADPAT_RESPONSES.get(mode, HEADPAT_RESPONSES["mode_femboy"])
    await ctx.send(random.choice(responses))
```

---

## Part 4: Server-Specific Bot Avatars

### Overview
Replace webhook-based persona system with Discord's native Server Profiles API.

### New Utility File

#### [NEW] server_avatar.py

```python
"""Server-specific avatar management using Discord's raw API."""

import discord
import base64
from pathlib import Path
from utils.logger import get_logger

logger = get_logger(__name__)

# Default avatar paths per mode
MODE_AVATARS = {
    "mode_default": "data/avatars/clanker.png",
    "mode_femboy": "data/avatars/femmy.png",
    "mode_tsundere": "data/avatars/tsun.png",
    "mode_oneesan": "data/avatars/yumi.png",
}


async def set_server_avatar(bot: discord.Client, guild_id: int, image_path: str | None) -> tuple[bool, str]:
    """
    Set the bot's avatar for a specific server.
    
    Args:
        bot: The discord bot instance
        guild_id: The guild to update avatar for
        image_path: Path to image file, or None to reset to global default
    
    Returns:
        (success: bool, message: str)
    """
    try:
        if image_path is None:
            payload = {"avatar": None}
        else:
            path = Path(image_path)
            if not path.exists():
                return False, f"Image not found: {image_path}"
            
            image_bytes = path.read_bytes()
            b64_data = base64.b64encode(image_bytes).decode('utf-8')
            
            # Detect mime type
            suffix = path.suffix.lower()
            mime_map = {".png": "image/png", ".jpg": "image/jpeg", ".jpeg": "image/jpeg", ".gif": "image/gif"}
            mime_type = mime_map.get(suffix, "image/png")
            
            data_uri = f"data:{mime_type};base64,{b64_data}"
            payload = {"avatar": data_uri}
        
        url = f"/guilds/{guild_id}/members/@me"
        await bot.http.request(
            discord.http.Route("PATCH", url),
            json=payload
        )
        
        return True, "Avatar updated successfully"
        
    except discord.HTTPException as e:
        if e.status == 429:
            return False, "Rate limited - changing avatars too fast"
        elif e.status == 403:
            return False, "Missing permissions to change avatar"
        else:
            return False, f"API Error: {e.status}"


async def set_mode_avatar(bot: discord.Client, guild_id: int, mode: str) -> tuple[bool, str]:
    """Set the bot's avatar based on personality mode."""
    avatar_path = MODE_AVATARS.get(mode)
    if avatar_path:
        return await set_server_avatar(bot, guild_id, avatar_path)
    return False, f"No avatar defined for mode: {mode}"
```

---

### Avatar Storage Structure

```
discord_bot/
├── data/
│   └── avatars/
│       ├── clanker.png    # Default Clanker mode
│       ├── femmy.png      # Femboy mode
│       ├── tsun.png       # Tsundere mode
│       └── yumi.png       # Oneesan mode
```

---

### Admin Commands for Server Avatars

#### [MODIFY] admin.py

Add new slash command group:

```python
avatar_group = app_commands.Group(name="avatar", description="Manage bot server avatar")

@avatar_group.command(name="set", description="Upload a custom server avatar")
@app_commands.checks.has_permissions(administrator=True)
async def avatar_set(self, interaction: discord.Interaction, image: discord.Attachment):
    """Upload a custom avatar for this server."""
    # Validate file type
    # Save to server-specific path
    # Call set_server_avatar()

@avatar_group.command(name="mode", description="Set avatar to match personality mode")
@app_commands.checks.has_permissions(administrator=True)
async def avatar_mode(self, interaction: discord.Interaction):
    """Set avatar to match current personality mode."""
    mode = await get_server_mode(interaction.guild.id)
    success, msg = await set_mode_avatar(self.bot, interaction.guild.id, mode)
    await interaction.response.send_message(msg, ephemeral=True)

@avatar_group.command(name="reset", description="Reset to global default avatar")
@app_commands.checks.has_permissions(administrator=True)
async def avatar_reset(self, interaction: discord.Interaction):
    """Reset server avatar to global default."""
    success, msg = await set_server_avatar(self.bot, interaction.guild.id, None)
    await interaction.response.send_message(msg, ephemeral=True)
```

---

### Auto-Update Avatar on Mode Change

#### [MODIFY] social.py

In the `!mode` command, after changing mode:

```python
# After mode change succeeds
from utils.server_avatar import set_mode_avatar

# Attempt to update avatar (non-blocking, log errors)
try:
    success, msg = await set_mode_avatar(self.bot, ctx.guild.id, new_mode)
    if not success:
        logger.warning("Avatar update failed: %s", msg)
except Exception as e:
    logger.error("Avatar update error: %s", e)
```

---

### Remove Webhook System

#### [DELETE] Webhook-related code from persona_manager.py

Remove `get_webhook()` and `send_as_mode()` methods that create/use webhooks.

---

## Verification Plan

### Automated Tests
1. Test activity shows "Playing: Clanking with humans"
2. Test help command shows mode-appropriate greeting
3. Test hug/pat rate limits (1/hour, 3/day)
4. Test mode-specific affection changes

### Manual Verification
1. Run `!mode femboy` and verify avatar changes
2. Test `!pat` in each mode and verify correct response
3. Spam `!hug` to verify rate limiting works
4. Check `/avatar set` with custom image
