# Implementation 8: Custom Persona Creation Feature

## Overview
Allow server admins to create custom bot personas (modes) with their own:
- Name
- Avatar image (URL)
- Banner image (URL, optional)
- Bio/description
- Normal system prompt
- Evil system prompt (optional)

Notes:
- Built-in modes (femboy, tsundere, oneesan) will ship with repo avatars for normal and evil variants.
- Default mode uses the application avatar and is unchanged.
- Custom persona avatars are used for both normal and evil responses until a future update adds separate evil avatars.

---

## Command Flow

### `/create persona` (alias: `/persona create`) - Multi-step modal workflow

Slash modals are limited to 5 inputs, so this must be multi-step.
Do NOT open a modal directly from another modal submit.
Use an ephemeral message with a button to open the next modal.

Step 1: Basic Info + Image URLs (modal)
```
Name: [text input, max 32 chars, required]
Bio: [paragraph input, max 500 chars, optional]
Avatar Image URL: [text input, required]
Banner Image URL: [text input, optional]
```

Step 2: Prompts (modal)
```
Normal System Prompt: [paragraph input, max 2000 chars, required]
Evil System Prompt: [paragraph input, max 2000 chars, optional]
```

Flow:
1. User runs `/create persona` (or `/persona create`).
2. Step 1 modal submits:
   - Validate name (non-empty, unique per guild).
   - Validate URL format (http/https only) but do not download yet.
   - Store pending data in a short-lived cache (keyed by guild_id + user_id; TTL ~5 minutes).
   - Respond with an ephemeral message containing a "Continue" button.
3. User clicks "Continue": open Step 2 modal.
4. Step 2 modal submits:
   - Re-load pending data from cache; if missing, ask the user to restart.
   - Download and validate images, save to disk.
   - Create the persona row in the database.
   - Reply with success and usage hint.

---

## Database Schema

### [MODIFY] db_handler.py

Add a table for custom personas:

```sql
CREATE TABLE IF NOT EXISTS custom_personas (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    guild_id INTEGER NOT NULL,
    name TEXT NOT NULL,
    mode_key TEXT NOT NULL,
    bio TEXT,
    avatar_path TEXT,
    banner_path TEXT,
    normal_prompt TEXT NOT NULL,
    evil_prompt TEXT,
    created_by INTEGER NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    is_active BOOLEAN DEFAULT 1,
    UNIQUE (mode_key),
    UNIQUE (guild_id, name)
)
```

Helper functions (names must match usage):
```python
async def create_custom_persona(
    guild_id: int,
    name: str,
    mode_key: str,
    bio: str | None,
    avatar_path: str | None,
    banner_path: str | None,
    normal_prompt: str,
    evil_prompt: str | None,
    created_by: int,
) -> int

async def get_custom_persona_by_mode_key(guild_id: int, mode_key: str) -> dict | None

async def get_custom_persona_by_name(guild_id: int, name: str) -> dict | None

async def get_guild_custom_personas(guild_id: int) -> list[dict]

async def update_custom_persona(guild_id: int, mode_key: str, **updates) -> bool

async def delete_custom_persona(guild_id: int, mode_key: str) -> bool
```

Name helpers (single source of truth):
```python
def sanitize_persona_name(name: str) -> str  # lowercase, alnum + underscores, collapse spaces

def build_custom_mode_key(guild_id: int, name: str) -> str  # f"custom_{guild_id}_{slug}"
```

---

## Image Validation and Download

### [NEW] utils/image_downloader.py

Align avatar size checks with the server avatar limit (500 KB max).
All images are converted to WebP to save space.

```python
import aiohttp
from pathlib import Path
from typing import Optional, Tuple
from urllib.parse import urlparse
from PIL import Image
from io import BytesIO

MAX_AVATAR_BYTES = 500 * 1024
MAX_BANNER_BYTES = 500 * 1024
ALLOWED_MIME_TYPES = {"image/png", "image/jpeg", "image/gif", "image/webp"}
ALLOWED_SCHEMES = {"http", "https"}

async def download_and_validate_image(
    url: str,
    save_path: Path,
    max_size: int,
) -> Tuple[bool, str]:
    """
    Download image from URL, validate it is an actual image, then save.
    - Enforce scheme (http/https only)
    - Enforce size limit
    - Check Content-Type when available
    - Validate image bytes by opening with PIL
    """
    parsed = urlparse(url)
    if parsed.scheme not in ALLOWED_SCHEMES:
        return False, "Invalid URL scheme"

    try:
        async with aiohttp.ClientSession() as session:
            # HEAD request (best-effort)
            try:
                async with session.head(url, allow_redirects=True, timeout=10) as resp:
                    if resp.status >= 400:
                        return False, f"URL returned status {resp.status}"
                    content_type = (resp.headers.get("Content-Type") or "").split(";")[0].strip()
                    if content_type and content_type not in ALLOWED_MIME_TYPES:
                        return False, f"Invalid content type: {content_type}"
                    content_length = resp.headers.get("Content-Length")
                    if content_length and int(content_length) > max_size:
                        return False, "Image too large"
            except Exception:
                # Some hosts block HEAD; continue to GET
                pass

            async with session.get(url, timeout=30) as resp:
                if resp.status >= 400:
                    return False, f"Download failed: status {resp.status}"

                data = bytearray()
                async for chunk in resp.content.iter_chunked(8192):
                    data.extend(chunk)
                    if len(data) > max_size:
                        return False, "Image exceeds size limit"

        try:
            image = Image.open(BytesIO(data))
            image.load()
        except Exception:
            return False, "File is not a valid image"

        if image.mode not in ("RGB", "RGBA"):
            image = image.convert("RGBA")

        output = BytesIO()
        image.save(output, format="WEBP", quality=80, method=6)
        converted = output.getvalue()
        if len(converted) > max_size:
            return False, "Image too large after conversion"

        save_path.parent.mkdir(parents=True, exist_ok=True)
        save_path.write_bytes(converted)
        return True, "ok"

    except aiohttp.ClientError as exc:
        return False, f"Network error: {exc}"
    except Exception as exc:
        return False, f"Error: {exc}"
```

---

## Storage Structure

Use ASCII-only paths and names:
```
discord_bot/data/avatars/custom/
  guild_<ID>_<persona_slug>_avatar.webp
  guild_<ID>_<persona_slug>_banner.webp
```

---

## Admin Commands

### [NEW] cogs/persona.py

Provide `/create persona` as required, and keep `/persona create` as an alias.
Other management commands can live under `/persona`.

```python
class Persona(commands.Cog):
    """Custom persona management."""

    create_group = app_commands.Group(name="create", description="Create resources")
    persona_group = app_commands.Group(name="persona", description="Manage custom personas")

    @create_group.command(name="persona")
    @app_commands.checks.has_permissions(manage_guild=True)
    async def create_persona(self, interaction: discord.Interaction):
        # Show Step 1 modal

    @persona_group.command(name="create")
    @app_commands.checks.has_permissions(manage_guild=True)
    async def create_persona_alias(self, interaction: discord.Interaction):
        # Call same handler as /create persona

    @persona_group.command(name="list")
    async def list_personas(self, interaction: discord.Interaction):
        # List custom personas for this guild

    @persona_group.command(name="delete")
    @app_commands.checks.has_permissions(manage_guild=True)
    async def delete_persona(self, interaction: discord.Interaction, name: str):
        # Delete persona and remove stored files

    @persona_group.command(name="preview")
    async def preview_persona(self, interaction: discord.Interaction, name: str):
        # Show details (name, bio, avatar, banner, prompts truncated)
```

Modal handling (outline):
- `PersonaBasicModal` (Step 1): name, bio, avatar_url, banner_url.
- On submit, validate uniqueness and store pending data in cache.
- Respond with an ephemeral message containing a button to open `PersonaPromptsModal`.
- `PersonaPromptsModal` (Step 2): normal_prompt, evil_prompt.
- On submit, download images, create persona record, then reply with success.

---

## Integration with Mode System

### [MODIFY] db_handler.py
- Allow `mode_default` and custom mode keys in `set_server_mode`:
  - built-ins: mode_default, mode_femboy, mode_tsundere, mode_oneesan
  - custom: any mode key starting with `custom_`

### [MODIFY] social.py
- Prefix `!mode`:
  - Try `resolve_mode_key` for built-ins.
  - If not found, look up custom persona by name using `sanitize_persona_name`.
  - On success: `set_server_mode` to the custom `mode_key`.
  - If persona has `avatar_path`, load bytes and call `set_custom_avatar` (rate-limited).
  - Use custom persona name in the switch message.

- Slash `/mode`:
  - Replace static choices with a free-text `mode: str` plus autocomplete.
  - Autocomplete should return built-ins + custom persona names for that guild.

### [MODIFY] ai_brain.py
- Update `_load_persona`:
  - If `mode` starts with `custom_`, fetch persona by mode_key.
  - If `evil_mode` and `evil_prompt` exists, use it; otherwise use `normal_prompt`.
  - If not custom, fall back to current registry file prompt behavior.

---

## Security Considerations

1. Image Validation
   - Enforce http/https only.
   - Enforce 500 KB max for avatar (server avatar limit).
   - Validate actual image bytes with PIL.
2. Rate Limiting
   - Max 5 custom personas per guild.
   - Max 3 persona creations per hour per user.
3. Input Sanitization
   - Sanitize persona names for filesystem paths and mode_key creation.
   - Enforce prompt length limits.

---

## Verification Plan

### Automated Tests
1. Image download rejects non-image files.
2. Image download respects size limits (500 KB).
3. Persona creation stores correct data and mode_key.
4. Custom mode activates with the correct prompt and avatar.

### Manual Verification
1. Create persona with all fields via `/create persona`.
2. Activate with `!mode <name>` and `/mode <name>`.
3. Verify avatar changes on mode switch (rate limit respected).
4. Test evil mode prompt selection for custom persona.
