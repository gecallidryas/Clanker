---
description: How to implement the Persona System using webhooks for dynamic bot identity
---

# 🎭 The Persona System (Webhook Implementation)

## 1. The Architecture

Instead of the bot sending messages directly (which locks it to one avatar), the bot acts as a **Puppeteer**.

1. **The Brain:** Decides what to say and which "Mode" is active.
2. **The Manager:** Looks up the name and avatar for that mode.
3. **The Proxy:** A generic Webhook in the channel that puts on the "mask" (Name + Avatar) and sends the message.

---

## 2. Phase 1: The Asset Database

Create a JSON file to store the identity of every mode. This allows you to add "Mode #31" without restarting the bot.

**File:** `data/personas.json`

```json
{
  "default": {
    "name": "Yumi",
    "avatar_url": "https://cdn.discordapp.com/attachments/123.../yumi_default.png"
  },
  "mode_femboy": {
    "name": "Femmy",
    "avatar_url": "https://cdn.discordapp.com/attachments/123.../femmy_pink.png"
  },
  "mode_tsundere": {
    "name": "Yumi-chan 💢",
    "avatar_url": "https://cdn.discordapp.com/attachments/123.../yumi_angry.png"
  },
  "mode_oneesan": {
    "name": "Ara Ara Yumi",
    "avatar_url": "https://cdn.discordapp.com/attachments/123.../yumi_mature.png"
  }
}
```

* **Tip:** Host these images in a private Discord channel and copy the `.png` links as discussed.

---

## 3. Phase 2: The Logic (Python)

We need a robust manager that handles caching (so we don't spam the API looking for webhooks) and sending.

**File:** `utils/persona_manager.py`

```python
import discord
import json
import aiohttp

class PersonaManager:
    def __init__(self, bot):
        self.bot = bot
        self.personas = self.load_personas()
        # Cache webhooks in memory to speed up responses
        # Format: {channel_id: webhook_object}
        self.webhook_cache = {} 

    def load_personas(self):
        try:
            with open("data/personas.json", "r") as f:
                return json.load(f)
        except FileNotFoundError:
            print("⚠️ personas.json not found! Using default fallback.")
            return {}

    async def get_webhook(self, channel):
        """
        Finds an existing webhook owned by the bot, or creates a new one.
        Uses caching to avoid API rate limits.
        """
        # 1. Check Cache
        if channel.id in self.webhook_cache:
            return self.webhook_cache[channel.id]

        # 2. Check Discord API (If not in cache)
        webhooks = await channel.webhooks()
        
        # Look for a webhook created by THIS bot
        webhook = discord.utils.get(webhooks, user=self.bot.user)

        if webhook is None:
            # 3. Create New Webhook if none exists
            try:
                webhook = await channel.create_webhook(name="Yumi-Proxy")
            except discord.Forbidden:
                # Fallback: If bot lacks 'Manage Webhooks' permission, return None
                print(f"❌ Missing permissions to create webhook in {channel.name}")
                return None
            except discord.HTTPException:
                # If channel has max webhooks (10), try to reuse *any* token-based webhook
                # (This is a rare edge case, usually we just fail gracefully)
                return None

        # 4. Save to Cache
        self.webhook_cache[channel.id] = webhook
        return webhook

    async def send_as_mode(self, channel, content, mode_id, **kwargs):
        """
        Sends a message masquerading as the specific mode.
        """
        # Load Persona Data (Fallback to 'default' if mode not found)
        persona = self.personas.get(mode_id, self.personas.get("default"))
        
        webhook = await self.get_webhook(channel)

        if webhook:
            # SEND VIA WEBHOOK (The "Masquerade")
            await webhook.send(
                content=content,
                username=persona['name'],
                avatar_url=persona['avatar_url'],
                wait=False, # Set True if you need the message object back
                **kwargs # Pass other args like embeds or files
            )
        else:
            # FALLBACK: If webhooks fail (no perms), send as standard bot
            await channel.send(
                f"**[{persona['name']}]**: {content}", 
                **kwargs
            )
```

---

## 4. Phase 3: Integration

Now we hook this into your main AI Brain so that every time the bot replies, it uses the system.

**File:** `cogs/ai_brain.py`

```python
from discord.ext import commands
from utils.persona_manager import PersonaManager

class AIBrain(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        # Initialize the Manager
        self.persona_manager = PersonaManager(bot)

    async def process_chat(self, message):
        # ... [Your existing logic to get AI response] ...
        ai_response = "B-baka! It's not like I like you or anything!" 
        
        # 1. Determine Current Mode
        # (You likely fetch this from your database based on the server settings)
        current_mode = db.get_guild_mode(message.guild.id) # e.g., "mode_tsundere"

        # 2. Send using Persona System
        await self.persona_manager.send_as_mode(
            channel=message.channel,
            content=ai_response,
            mode_id=current_mode
        )
```

---

## 5. Critical Edge Cases (The "Gotchas")

### A. The "Reply" Problem

Webhooks cannot technically "Reply" to a message (the detailed feature where it highlights the user's message).

* **Workaround:** You cannot get the reply highlight. You can mention the user manually in the string: `f"{message.author.mention} {ai_response}"`.

### B. Threads

Webhooks work differently in Threads. If you are in a Thread, you must pass the `thread` object to the webhook.

* **Update `get_webhook` logic:** If `channel` is a Thread, you actually need the webhook of the *parent channel*, and then send with `thread=channel`.

```python
# In send_as_mode:
if isinstance(channel, discord.Thread):
    parent_webhook = await self.get_webhook(channel.parent)
    await parent_webhook.send(..., thread=channel)
```

### C. Permissions

The bot **MUST** have the `Manage Webhooks` permission in the server.

* If it doesn't, the code above falls back to `channel.send`, which will just look like the normal bot (breaking the immersion).

---

## 6. Summary Checklist

1. [ ] Create `data/personas.json` and fill it with links.
2. [ ] Copy the `PersonaManager` class into your utils.
3. [ ] Ensure the bot has `Manage Webhooks` permission.
4. [ ] Update your AI response code to call `send_as_mode` instead of `ctx.send`.

---

# 🛡️ Admin Control Features

This section covers giving Admins total control over the "Bouncer," the "Welcome DM," and the "Audit Logs."

---

## 7. Feature 1: The "Customizable Bouncer" (Automod)

A flexible database design so that **Keyword A** can trigger a 5-minute timeout, while **Keyword B** triggers an instant Kick.

### A. Database Schema Update

Update the `automod_rules` table to store specific punishments per word.

```sql
CREATE TABLE automod_rules (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    guild_id INTEGER NOT NULL,
    keyword TEXT NOT NULL,
    punishment_type TEXT NOT NULL, -- 'timeout', 'kick', 'ban', 'delete_only'
    duration_minutes INTEGER DEFAULT 0, -- Only used for timeouts
    UNIQUE(guild_id, keyword)
);
```

### B. The Slash Commands (Admin Control)

Admins will use these commands to manage the list without touching code.

* **Add Rule:** `/automod add <keyword> <action> <duration>`
  * *Example 1:* `/automod add word:steam-gift action:timeout duration:10080` (1 week mute)
  * *Example 2:* `/automod add word:slur_word action:kick`
* **Remove Rule:** `/automod remove <keyword>`
* **List Rules:** `/automod list`

### C. The Logic (Code Snippet)

Add this to `cogs/automod.py`. It calculates the punishment dynamically.

```python
from datetime import timedelta

async def process_automod(message):
    # 1. Fetch rules for this server
    rules = db.get_all_automod_rules(message.guild.id) 
    
    content = message.content.lower()
    
    for rule in rules:
        keyword = rule['keyword']
        action = rule['punishment_type']
        duration = rule['duration_minutes']

        if keyword in content:
            # 2. Delete immediately
            try:
                await message.delete()
            except:
                pass # Message might already be gone

            # 3. Apply Punishment
            try:
                if action == 'timeout':
                    # Native Discord Timeout
                    until = discord.utils.utcnow() + timedelta(minutes=duration)
                    await message.author.timeout(until, reason=f"Automod: Used forbidden word '{keyword}'")
                    response = f"🚫 **{message.author.mention}** has been timed out for {duration} mins."

                elif action == 'kick':
                    await message.author.kick(reason=f"Automod: Used forbidden word '{keyword}'")
                    response = f"🥾 **{message.author.mention}** has been kicked."

                elif action == 'ban':
                    await message.author.ban(reason=f"Automod: Used forbidden word '{keyword}'")
                    response = f"🔨 **{message.author.mention}** has been banned."

                else: # delete_only
                    response = f"⚠️ **{message.author.mention}**, that word is not allowed here."

                # 4. Notify Channel
                await message.channel.send(response, delete_after=10)
                
                # 5. Log it (See Feature 3)
                await self.log_incident(message.guild, message.author, action, keyword)
                
                return True # Stop processing other rules
                
            except discord.Forbidden:
                print(f"Failed to punish user in {message.guild.name} - Missing Permissions")
```

---

## 8. Feature 2: The "Owner's DM" (Preset Welcome)

This separates the "Public AI Greeting" from the "Private Official Information."

### A. The Slash Command

* **Command:** `/welcome set_dm_message`
* **Input:** A modal or long string where the owner pastes their Rules, Links, etc.
* **Storage:** Saves to `guild_settings` table in column `dm_welcome_message`.

### B. The Event Listener

Add this to `cogs/automation.py`. It handles the "Closed DMs" error gracefully.

```python
@commands.Cog.listener()
async def on_member_join(self, member):
    # 1. Retrieve the preset message
    settings = db.get_guild_settings(member.guild.id)
    dm_text = settings.get('dm_welcome_message')

    if dm_text:
        try:
            # 2. Send the DM
            embed = discord.Embed(
                title=f"Welcome to {member.guild.name}!",
                description=dm_text,
                color=discord.Color.blue()
            )
            embed.set_footer(text="This is an automated message from the server staff.")
            
            await member.send(embed=embed)
            
        except discord.Forbidden:
            # 3. Fallback if DMs are closed
            # Optional: Ping them in the public welcome channel telling them to check DMs
            print(f"Could not DM {member.name} (DMs closed)")
```

---

## 9. Feature 3: Enhanced Logging (Mutes & Timeouts)

Discord does not have a simple `on_timeout` event. You must compare the user's state "before" and "after" an update to detect it.

### A. The Logic (Detecting Mutes)

Add this listener to `cogs/logger.py`.

```python
@commands.Cog.listener()
async def on_member_update(self, before, after):
    # 1. Detect Timeout (Communication Disabled)
    # Check if the 'communication_disabled_until' attribute has changed
    if before.timed_out_until != after.timed_out_until:
        
        # Case A: Timeout Added
        if after.timed_out_until is not None:
            # Calculate duration
            diff = after.timed_out_until - discord.utils.utcnow()
            minutes = round(diff.total_seconds() / 60)
            
            # Create Log Embed
            embed = discord.Embed(
                title="🚫 Member Timed Out",
                description=f"**User:** {after.mention} (`{after.id}`)\n**Duration:** ~{minutes} minutes\n**Expires:** {discord.utils.format_dt(after.timed_out_until, 'R')}",
                color=discord.Color.orange()
            )
            # Try to fetch *who* did it via Audit Logs
            async for entry in after.guild.audit_logs(limit=1, action=discord.AuditLogAction.member_update):
                if entry.target.id == after.id:
                    embed.add_field(name="Moderator", value=entry.user.mention)
                    if entry.reason:
                        embed.add_field(name="Reason", value=entry.reason)
                    break
            
            await self.send_log(after.guild, embed)

        # Case B: Timeout Removed (Unmuted)
        elif after.timed_out_until is None:
            embed = discord.Embed(
                title="🔊 Member Timeout Removed",
                description=f"**User:** {after.mention} is free to speak again.",
                color=discord.Color.green()
            )
            await self.send_log(after.guild, embed)
```

### B. Summary of Logging Triggers

With this code, your `#mod-logs` channel will now capture:

1. **Timeouts:** Uses `on_member_update` (code above).
2. **Kicks/Bans:** Uses `on_member_ban` and `on_member_remove`.
3. **Automod:** Uses the explicit call from Feature 1.
4. **Deleted Messages:** Uses `on_message_delete`.

---

## 10. Admin Features Checklist

1. [ ] Create `automod_rules` table in database.
2. [ ] Add `dm_welcome_message` column to `guild_settings` table.
3. [ ] Implement `/automod add`, `/automod remove`, `/automod list` commands.
4. [ ] Implement `/welcome set_dm_message` command.
5. [ ] Add timeout detection listener to `cogs/logger.py`.
6. [ ] Ensure bot has `Moderate Members`, `Kick Members`, `Ban Members` permissions.
