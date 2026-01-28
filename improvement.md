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

**Goal:** Allow admins to say *"Yumi, give @User the 'Cool' role"* or *"Yumi, ban @Troll"* instead of using commands.

### Strategy: Hidden JSON Protocol

The AI outputs a hidden JSON block when an action is requested. Python intercepts and executes the Discord command.

### Database Schema

```sql
CREATE TABLE staff_roles (
    guild_id INTEGER,
    role_id INTEGER,
    permission_level INTEGER, -- 1=Mod (Kick/Mute), 2=Admin (Ban/Roles)
    PRIMARY KEY (guild_id, role_id)
);
```

### System Prompt Addition

```text
[TOOL USE INSTRUCTIONS]
You have the power to manage roles and moderate users.
If an Admin/Staff asks you to create a role, assign a role, or ban/kick a user, output your response in this JSON format inside a code block:

```json
{
  "action": "manage_role" | "moderate_user",
  "sub_action": "create" | "give" | "ban" | "kick",
  "target_name": "Role Name (if needed)",
  "target_id": "USER_ID_NUMERIC",
  "reason": "Reason for action",
  "reply": "Your conversational response here"
}
```

**Constraint:** Check the user's permissions context. If they lack permission, refuse politely without using JSON.
```

### Implementation: `cogs/ai_brain.py`

```python
import json
import re

async def handle_agentic_actions(message, ai_response_text):
    match = re.search(r"```json\s*(\{.*?\})\s*```", ai_response_text, re.DOTALL)
    if not match:
        return False

    data = json.loads(match.group(1))
    guild = message.guild
    
    is_admin = message.author.guild_permissions.administrator
    if not is_admin:
        await message.channel.send("❌ Nice try! You don't have permission.")
        return True

    try:
        if data['action'] == 'manage_role':
            target_id = int(data.get('target_id'))
            member = guild.get_member(target_id)
            
            if data['sub_action'] == 'create':
                role_name = data.get('target_name')
                role = discord.utils.get(guild.roles, name=role_name)
                if not role:
                    role = await guild.create_role(name=role_name, reason=f"Requested by {message.author}")
                await member.add_roles(role)
                
            elif data['sub_action'] == 'give':
                role_name = data.get('target_name')
                role = discord.utils.get(guild.roles, name=role_name)
                if role:
                    await member.add_roles(role)
                else:
                    await message.channel.send(f"❓ I couldn't find the role '{role_name}'.")
                    return True

        elif data['action'] == 'moderate_user':
            target_id = int(data.get('target_id'))
            member = guild.get_member(target_id)
            reason = data.get('reason', 'No reason provided')

            if data['sub_action'] == 'ban':
                await guild.ban(discord.Object(id=target_id), reason=reason)
            elif data['sub_action'] == 'kick':
                await member.kick(reason=reason)

        await message.channel.send(data.get('reply'))
        return True

    except discord.Forbidden:
        await message.channel.send("💢 I don't have permission! Move my role higher!")
    except Exception as e:
        await message.channel.send(f"⚠️ Action failed: {e}")
    
    return True
```

### Deliverables
- [ ] Add `staff_roles` table to `db_handler.py`
- [ ] Update system prompt with tool instructions
- [ ] Add `handle_agentic_actions()` to `ai_brain.py`
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

## Feature: Automation (Auto-Role)

**Goal:** Automatically assign roles on join. Welcome messages already exist.

### Database Schema

```sql
-- Add to guild_settings or guild_config
ALTER TABLE guild_config ADD COLUMN autorole_id INTEGER;
```

### Event Listener: `cogs/scheduler.py` or `cogs/automation.py`

```python
@commands.Cog.listener()
async def on_member_join(self, member):
    settings = await get_guild_config(member.guild.id)
    if not settings:
        return

    # Auto Role
    autorole_id = settings.get('autorole_id')
    if autorole_id:
        role = member.guild.get_role(autorole_id)
        if role:
            try:
                await member.add_roles(role)
            except discord.Forbidden:
                logger.warning(f"Failed to give autorole in {member.guild.name}")
```

### Commands

| Command | Description |
|---------|-------------|
| `/autorole set <role>` | Set the auto-assign role |
| `/autorole clear` | Disable auto-role |
| `/autorole view` | Show current autorole |

### Deliverables
- [ ] Add `autorole_id` column to `guild_config`
- [ ] Add `on_member_join` listener for auto-role
- [ ] Add `/autorole` commands
