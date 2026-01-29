# Improvements

## Overview
This file tracks upcoming improvements and refactors for the project.

## Planned work
- Refactor AI brain into mode modules (see implementation plan below).
- Keep emoji usage limited to application emojis configured in discord.dev.
- Continue cleaning up legacy global config paths.

## AI brain module refactor (high level)
1. Define a ModeProfile interface and registry.
2. Move mode-specific data into mode modules.
3. Update AIBrain to query the registry for prompts/behavior.
4. Update Social to use registry for mode display and emojis.
5. Validate behavior via a quick runtime check and small unit test.

## Notes
- Emoji images are stored in `femmyemojis/` and `yumiemojis/` with cleaned names.
- No slash commands are required for listing emojis.

---

## Feature: Agentic Tools (Natural Language Admin)

**Goal:** Allow admins/staff to say *"Yumi, give @User the 'Cool' role"* or *"Yumi, ban @Troll"* instead of using commands.

### Strategy: Hidden JSON Protocol

The AI outputs a hidden JSON block when an action is requested. Python intercepts and executes the Discord command.

### Database Schema

```sql
CREATE TABLE staff_roles (
    guild_id INTEGER,
    role_id INTEGER,
    permission_level INTEGER, -- 1=Mod (Kick/Mute/Timeout), 2=Admin (Ban/Roles)
    PRIMARY KEY (guild_id, role_id)
);

-- Add to guild_config
ALTER TABLE guild_config ADD COLUMN mod_log_channel_id INTEGER;
```

### System Prompt Addition

```text
[TOOL USE INSTRUCTIONS]
You have the power to manage roles and moderate users.
If an Admin/Staff asks you to create a role, assign a role, or ban/kick/timeout a user, output your response in this JSON format inside a code block:

```json
{
  "action": "manage_role" | "moderate_user",
  "sub_action": "create" | "give" | "remove" | "ban" | "kick" | "timeout",
  "target_name": "Role Name (if applicable)",
  "target_id": "USER_ID_NUMERIC",
  "duration": "timeout duration in minutes (if timeout)",
  "reason": "Reason for action",
  "reply": "Your conversational response here"
}
```

**Constraint:** Check the user's permissions context. If they lack permission, refuse politely without using JSON.
```

### Permission Check Logic

```python
async def has_agentic_permission(member: discord.Member, action: str) -> bool:
    """Check if user can perform agentic action."""
    # Always allow server admins
    if member.guild_permissions.administrator:
        return True
    
    # Check staff_roles table
    staff_roles = await get_staff_roles(member.guild.id)
    user_role_ids = {r.id for r in member.roles}
    
    for role_id, permission_level in staff_roles:
        if role_id in user_role_ids:
            # Level 1 = Mod (kick/mute/timeout), Level 2 = Admin (ban/roles)
            if action in ('kick', 'timeout', 'mute') and permission_level >= 1:
                return True
            if action in ('ban', 'create', 'give', 'remove') and permission_level >= 2:
                return True
    return False
```

### Implementation: `cogs/ai_brain.py`

```python
import json
import re

# Default permissions for newly created roles
DEFAULT_ROLE_PERMISSIONS = discord.Permissions(
    send_messages=True,
    read_messages=True,
    read_message_history=True,
    add_reactions=True,
    use_external_emojis=True,
)

async def handle_agentic_actions(message, ai_response_text):
    match = re.search(r"```json\s*(\{.*?\})\s*```", ai_response_text, re.DOTALL)
    if not match:
        return False

    data = json.loads(match.group(1))
    guild = message.guild
    action = data.get('sub_action', '')
    
    # Permission check (admin OR staff role)
    if not await has_agentic_permission(message.author, action):
        await message.channel.send("❌ Nice try! You don't have permission.")
        return True

    try:
        if data['action'] == 'manage_role':
            target_id = int(data.get('target_id'))
            member = guild.get_member(target_id)
            role_name = data.get('target_name')
            
            if data['sub_action'] in ('create', 'give'):
                # Auto-create role if it doesn't exist
                role = discord.utils.get(guild.roles, name=role_name)
                if not role:
                    role = await guild.create_role(
                        name=role_name,
                        permissions=DEFAULT_ROLE_PERMISSIONS,
                        reason=f"Requested by {message.author}"
                    )
                await member.add_roles(role)
                
            elif data['sub_action'] == 'remove':
                role = discord.utils.get(guild.roles, name=role_name)
                if role:
                    await member.remove_roles(role)

        elif data['action'] == 'moderate_user':
            target_id = int(data.get('target_id'))
            member = guild.get_member(target_id)
            reason = data.get('reason', 'No reason provided')

            if data['sub_action'] == 'ban':
                await guild.ban(discord.Object(id=target_id), reason=reason)
            elif data['sub_action'] == 'kick':
                await member.kick(reason=reason)
            elif data['sub_action'] == 'timeout':
                duration = int(data.get('duration', 10))
                await member.timeout(
                    discord.utils.utcnow() + timedelta(minutes=duration),
                    reason=reason
                )
            
            # Post to mod log channel
            await post_mod_log(guild, message.author, data['sub_action'], member, reason)

        await message.channel.send(data.get('reply'))
        return True

    except discord.Forbidden:
        await message.channel.send("💢 I don't have permission! Move my role higher!")
    except Exception as e:
        await message.channel.send(f"⚠️ Action failed: {e}")
    
    return True


async def post_mod_log(guild, moderator, action, target, reason):
    """Post action receipt to mod log channel."""
    config = await get_guild_config(guild.id)
    channel_id = config.get('mod_log_channel_id')
    if not channel_id:
        return
    
    channel = guild.get_channel(channel_id)
    if not channel:
        return
    
    embed = discord.Embed(
        title=f"🔨 {action.upper()}",
        color=discord.Color.red(),
        timestamp=discord.utils.utcnow()
    )
    embed.add_field(name="Target", value=str(target), inline=True)
    embed.add_field(name="Moderator", value=str(moderator), inline=True)
    embed.add_field(name="Reason", value=reason, inline=False)
    await channel.send(embed=embed)
```

### Staff Management Commands

| Command | Description |
|---------|-------------|
| `/staff add <role> <level>` | Add role as staff (level 1=Mod, 2=Admin) |
| `/staff remove <role>` | Remove role from staff |
| `/staff list` | List all staff roles and levels |

### Mod Log Commands

| Command | Description |
|---------|-------------|
| `/modlog set <channel>` | Set the mod action log channel |
| `/modlog clear` | Disable mod logging |

### Deliverables
- [ ] Add `staff_roles` table to `db_handler.py`
- [ ] Add `mod_log_channel_id` to `guild_config`
- [ ] Implement `has_agentic_permission()` with staff_roles lookup
- [ ] Update system prompt with tool instructions (including timeout)
- [ ] Add `handle_agentic_actions()` with timeout + auto-create role
- [ ] Add `post_mod_log()` function
- [ ] Add `/staff add|remove|list` commands
- [ ] Add `/modlog set|clear` commands
- [ ] Integration with on_message handler

---

## Feature: AI Embed Builder

**Goal:** Create Discord embeds by describing them naturally.

### Command
`/generate_embed <prompt>`

**Example:** *"Make a pink embed titled 'Rules'. Field 1: No spam. Footer: Have fun!"*

### Implementation: `cogs/utilities.py`

```python
@app_commands.command(name="generate_embed", description="Describe an embed and I'll build it")
async def generate_embed(self, interaction: discord.Interaction, prompt: str):
    if not interaction.user.guild_permissions.manage_messages:
        await interaction.response.send_message("❌ Missing permissions.", ephemeral=True)
        return

    await interaction.response.defer()

    sys_prompt = """You are a JSON generator for Discord Embeds. 
    Convert the user's description into this exact JSON structure:
    {"title": "...", "description": "...", "color": "hex (e.g. 0xFF00FF)", "fields": [{"name": "...", "value": "..."}], "footer": "..."}
    Do NOT output markdown. Just the raw JSON string."""

    json_response = await self.bot.ai.generate(sys_prompt, prompt)
    
    try:
        data = json.loads(json_response)
        embed = discord.Embed(
            title=data.get('title'),
            description=data.get('description'),
            color=discord.Color(int(str(data.get('color')).replace("#","").replace("0x",""), 16))
        )
        for f in data.get('fields', []):
            embed.add_field(name=f['name'], value=f['value'])
        if data.get('footer'):
            embed.set_footer(text=data['footer'])
            
        await interaction.followup.send(embed=embed)
    except:
        await interaction.followup.send("❌ AI failed to generate valid JSON.")
```

### Deliverables
- [ ] Add `/generate_embed` command to `utilities.py`
- [ ] Create embed-specific AI prompt

---

## Feature: Automation (Auto-Role & AI Welcome)

**Goal:** Automatically assign roles on join AND send unique AI-generated welcome messages.

### Database Schema

```sql
-- Add to guild_config
ALTER TABLE guild_config ADD COLUMN autorole_id INTEGER;
ALTER TABLE guild_config ADD COLUMN welcome_channel_id INTEGER;
ALTER TABLE guild_config ADD COLUMN autorole_enabled INTEGER DEFAULT 1;
ALTER TABLE guild_config ADD COLUMN welcome_enabled INTEGER DEFAULT 1;
```

### Event Listener: `cogs/scheduler.py`

```python
@commands.Cog.listener()
async def on_member_join(self, member):
    config = await get_guild_config(member.guild.id)
    if not config:
        return

    # Auto Role (if enabled)
    if config.get('autorole_enabled') and config.get('autorole_id'):
        role = member.guild.get_role(config['autorole_id'])
        if role:
            try:
                await member.add_roles(role)
            except discord.Forbidden:
                logger.warning(f"Failed to give autorole in {member.guild.name}")

    # AI Welcome Message (if enabled)
    if config.get('welcome_enabled') and config.get('welcome_channel_id'):
        channel = member.guild.get_channel(config['welcome_channel_id'])
        if channel:
            prompt = f"Write a short, cute 1-sentence welcome for a user named {member.display_name} joining the server {member.guild.name}. Be playful and unique!"
            welcome_msg = await self.bot.ai.generate_text(prompt)
            await channel.send(f"{welcome_msg} {member.mention}")
```

### Auto-Role Commands

| Command | Description |
|---------|-------------|
| `/autorole set <role>` | Set the auto-assign role |
| `/autorole clear` | Remove the autorole |
| `/autorole view` | Show current autorole |

### Welcome Commands

| Command | Description |
|---------|-------------|
| `/welcome channel <channel>` | Set the welcome channel |
| `/welcome clear` | Disable welcome messages |
| `/welcome test` | Send a test welcome message |

### Feature Toggle Commands

| Command | Description |
|---------|-------------|
| `/config toggle autorole` | Enable/disable auto-role |
| `/config toggle welcome` | Enable/disable AI welcome messages |

### Deliverables
- [ ] Add `autorole_id`, `welcome_channel_id` to `guild_config`
- [ ] Add `autorole_enabled`, `welcome_enabled` toggle columns
- [ ] Add `on_member_join` listener with auto-role AND AI welcome
- [ ] Add `/autorole` commands
- [ ] Add `/welcome` commands
- [ ] Add `/config toggle autorole|welcome` commands
