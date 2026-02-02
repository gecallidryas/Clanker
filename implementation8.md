# Implementation 8: Custom Persona Creation Feature

## Overview
Allow server admins to create custom bot personas (modes) with their own:
- Name
- Avatar image
- Banner image  
- Bio/description
- Normal system prompt
- Evil system prompt

---

## Command Flow

### `/persona create` - Multi-step modal workflow

Since slash commands cannot accept image uploads directly, use **URL inputs** for images.

**Step 1: Basic Info Modal**
```
Name: [text input, max 32 chars]
Bio: [paragraph input, max 500 chars]
```

**Step 2: Images Modal** 
```
Avatar Image URL: [text input, must be valid image URL]
Banner Image URL: [text input, optional, must be valid image URL]
```

**Step 3: Prompts Modal**
```
Normal System Prompt: [paragraph input, max 2000 chars]
Evil System Prompt: [paragraph input, max 2000 chars, optional]
```

---

## Database Schema

### [MODIFY] db_handler.py

Add new table for custom personas:

```sql
CREATE TABLE IF NOT EXISTS custom_personas (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    guild_id INTEGER NOT NULL,
    name TEXT NOT NULL,
    mode_key TEXT NOT NULL UNIQUE,  -- "custom_<guild_id>_<sanitized_name>"
    bio TEXT,
    avatar_path TEXT,
    banner_path TEXT,
    normal_prompt TEXT NOT NULL,
    evil_prompt TEXT,
    created_by INTEGER NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    is_active BOOLEAN DEFAULT 1
)
```

Add helper functions:
```python
async def create_custom_persona(guild_id, name, bio, avatar_path, banner_path, 
                                 normal_prompt, evil_prompt, created_by) -> int

async def get_custom_persona(guild_id, mode_key) -> Optional[dict]

async def get_guild_custom_personas(guild_id) -> list[dict]

async def update_custom_persona(mode_key, **updates) -> bool

async def delete_custom_persona(mode_key) -> bool

async def get_persona_prompt(guild_id, mode_key, evil_mode=False) -> Optional[str]
```

---

## Image Validation & Download

### [NEW] utils/image_downloader.py

```python
"""Safe image download and validation for custom personas."""

import aiohttp
import imghdr
from pathlib import Path
from typing import Optional, Tuple

MAX_IMAGE_BYTES = 2 * 1024 * 1024  # 2 MB
ALLOWED_EXTENSIONS = {".png", ".jpg", ".jpeg", ".gif", ".webp"}
ALLOWED_MIME_TYPES = {"image/png", "image/jpeg", "image/gif", "image/webp"}

async def download_and_validate_image(
    url: str,
    save_path: Path,
    max_size: int = MAX_IMAGE_BYTES
) -> Tuple[bool, str]:
    """
    Download image from URL, validate it's a real image, and save.
    
    Validation steps:
    1. Check URL format
    2. HEAD request to check Content-Type and Content-Length
    3. Download with size limit
    4. Validate file magic bytes (imghdr)
    5. Save to disk
    
    Returns:
        (success: bool, message: str)
    """
    try:
        async with aiohttp.ClientSession() as session:
            # HEAD request first
            async with session.head(url, allow_redirects=True, timeout=10) as resp:
                if resp.status != 200:
                    return False, f"URL returned status {resp.status}"
                
                content_type = resp.headers.get("Content-Type", "")
                if not any(mime in content_type for mime in ALLOWED_MIME_TYPES):
                    return False, f"Invalid content type: {content_type}"
                
                content_length = resp.headers.get("Content-Length")
                if content_length and int(content_length) > max_size:
                    return False, f"Image too large: {int(content_length)} bytes"
            
            # Download with streaming
            async with session.get(url, timeout=30) as resp:
                if resp.status != 200:
                    return False, f"Download failed: status {resp.status}"
                
                data = b""
                async for chunk in resp.content.iter_chunked(8192):
                    data += chunk
                    if len(data) > max_size:
                        return False, "Image exceeds size limit"
                
                # Validate magic bytes
                image_type = imghdr.what(None, h=data)
                if not image_type:
                    return False, "File is not a valid image"
                
                if image_type not in {"png", "jpeg", "gif", "webp"}:
                    return False, f"Unsupported image type: {image_type}"
                
                # Save
                save_path.parent.mkdir(parents=True, exist_ok=True)
                save_path.write_bytes(data)
                
                return True, "ok"
                
    except aiohttp.ClientError as e:
        return False, f"Network error: {e}"
    except Exception as e:
        return False, f"Error: {e}"
```

---

## Storage Structure

```
discord_bot/data/personas/
├── guild_<ID>/
│   ├── <persona_name>_avatar.png
│   └── <persona_name>_banner.png
```

---

## Admin Commands

### [NEW] cogs/persona.py

```python
class Persona(commands.Cog):
    """Custom persona management."""
    
    persona_group = app_commands.Group(
        name="persona",
        description="Manage custom bot personas"
    )
    
    @persona_group.command(name="create")
    @app_commands.checks.has_permissions(administrator=True)
    async def create_persona(self, interaction: discord.Interaction):
        """Create a new custom persona with a multi-step modal."""
        # Send first modal for basic info
        modal = PersonaBasicInfoModal(self.bot, interaction.guild.id)
        await interaction.response.send_modal(modal)
    
    @persona_group.command(name="list")
    async def list_personas(self, interaction: discord.Interaction):
        """List all custom personas for this server."""
        personas = await get_guild_custom_personas(interaction.guild.id)
        # Build embed with persona list
    
    @persona_group.command(name="edit")
    @app_commands.checks.has_permissions(administrator=True)
    async def edit_persona(self, interaction: discord.Interaction, name: str):
        """Edit an existing custom persona."""
        # Modal for editing
    
    @persona_group.command(name="delete")
    @app_commands.checks.has_permissions(administrator=True)
    async def delete_persona(self, interaction: discord.Interaction, name: str):
        """Delete a custom persona."""
        # Confirmation and deletion
    
    @persona_group.command(name="preview")
    async def preview_persona(self, interaction: discord.Interaction, name: str):
        """Preview a custom persona's details."""
        # Show embed with avatar, banner, bio, prompts


class PersonaBasicInfoModal(discord.ui.Modal):
    """Step 1: Name and Bio"""
    
    name = discord.ui.TextInput(
        label="Persona Name",
        placeholder="Enter a unique name (max 32 chars)",
        max_length=32,
        required=True
    )
    
    bio = discord.ui.TextInput(
        label="Bio/Description",
        style=discord.TextStyle.paragraph,
        placeholder="Short description of this persona",
        max_length=500,
        required=False
    )
    
    async def on_submit(self, interaction):
        # Validate name is unique
        # Store in temp cache
        # Send next modal for images
        modal = PersonaImagesModal(self.bot, self.guild_id, self.name.value, self.bio.value)
        await interaction.response.send_modal(modal)


class PersonaImagesModal(discord.ui.Modal):
    """Step 2: Avatar and Banner URLs"""
    
    avatar_url = discord.ui.TextInput(
        label="Avatar Image URL",
        placeholder="https://example.com/avatar.png",
        required=True
    )
    
    banner_url = discord.ui.TextInput(
        label="Banner Image URL (optional)",
        placeholder="https://example.com/banner.png",
        required=False
    )
    
    async def on_submit(self, interaction):
        await interaction.response.defer(ephemeral=True)
        
        # Download and validate avatar
        avatar_path = DATA_DIR / "personas" / f"guild_{self.guild_id}" / f"{sanitize(self.name)}_avatar.png"
        success, msg = await download_and_validate_image(self.avatar_url.value, avatar_path)
        if not success:
            await interaction.followup.send(f"Avatar error: {msg}", ephemeral=True)
            return
        
        # Download banner if provided
        banner_path = None
        if self.banner_url.value:
            banner_path = DATA_DIR / "personas" / f"guild_{self.guild_id}" / f"{sanitize(self.name)}_banner.png"
            success, msg = await download_and_validate_image(self.banner_url.value, banner_path)
            if not success:
                await interaction.followup.send(f"Banner error: {msg}", ephemeral=True)
                return
        
        # Send final modal for prompts
        # Note: Cannot chain modals directly, use button interaction
        view = ContinueToPromptsView(...)
        await interaction.followup.send("Images saved! Click to continue:", view=view, ephemeral=True)


class PersonaPromptsModal(discord.ui.Modal):
    """Step 3: System Prompts"""
    
    normal_prompt = discord.ui.TextInput(
        label="Normal System Prompt",
        style=discord.TextStyle.paragraph,
        placeholder="Instructions for normal mode behavior",
        max_length=2000,
        required=True
    )
    
    evil_prompt = discord.ui.TextInput(
        label="Evil System Prompt (optional)",
        style=discord.TextStyle.paragraph,
        placeholder="Instructions for evil mode behavior",
        max_length=2000,
        required=False
    )
    
    async def on_submit(self, interaction):
        # Create persona in database
        mode_key = f"custom_{self.guild_id}_{sanitize(self.name)}"
        await create_custom_persona(
            guild_id=self.guild_id,
            name=self.name,
            mode_key=mode_key,
            bio=self.bio,
            avatar_path=str(self.avatar_path),
            banner_path=str(self.banner_path) if self.banner_path else None,
            normal_prompt=self.normal_prompt.value,
            evil_prompt=self.evil_prompt.value or None,
            created_by=interaction.user.id
        )
        
        await interaction.response.send_message(
            f"Custom persona **{self.name}** created! Use `/mode {self.name}` to activate.",
            ephemeral=True
        )
```

---

## Integration with Mode System

### [MODIFY] social.py

Update `!mode` command to support custom personas:

```python
async def mode(self, ctx, mode_name: str):
    # Check built-in modes first
    if mode_name in BUILT_IN_MODES:
        # ... existing logic
    
    # Check custom personas
    custom = await get_custom_persona(ctx.guild.id, f"custom_{ctx.guild.id}_{mode_name}")
    if custom:
        await set_server_mode(ctx.guild.id, custom["mode_key"])
        # Update avatar if persona has one
        if custom["avatar_path"]:
            avatar_bytes = Path(custom["avatar_path"]).read_bytes()
            await set_custom_avatar(self.bot, ctx.guild.id, avatar_bytes)
        await ctx.send(f"Mode changed to **{custom['name']}**!")
        return
    
    await ctx.send(f"Unknown mode: {mode_name}")
```

### [MODIFY] ai_brain.py

Get system prompt from custom persona if active:

```python
async def get_system_prompt(guild_id, mode, evil_mode=False):
    # Check if mode is a custom persona
    if mode.startswith("custom_"):
        persona = await get_custom_persona_by_mode_key(mode)
        if persona:
            if evil_mode and persona["evil_prompt"]:
                return persona["evil_prompt"]
            return persona["normal_prompt"]
    
    # Fall back to built-in prompts
    return BUILT_IN_PROMPTS.get(mode, DEFAULT_PROMPT)
```

---

## Security Considerations

1. **Image Validation**:
   - Check MIME type via HEAD request before download
   - Validate magic bytes after download (imghdr)
   - Enforce strict size limits (2MB max)
   - Only allow known image types (png, jpg, gif, webp)

2. **Rate Limiting**:
   - Max 5 custom personas per guild
   - Max 3 persona creations per hour per user

3. **Input Sanitization**:
   - Sanitize persona names for filesystem paths
   - Limit prompt lengths
   - No executable content in prompts

---

## Verification Plan

### Automated Tests
1. Image download rejects non-image files
2. Image download respects size limits
3. Persona creation stores correct data
4. Custom mode activates with correct prompt

### Manual Verification
1. Create persona with all fields
2. Test `/mode <custom_name>` activates correctly
3. Verify avatar changes on mode switch
4. Test evil mode with custom evil prompt
