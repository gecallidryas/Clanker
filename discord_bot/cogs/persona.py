"""
Custom persona management.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path
import re
from typing import Optional
from urllib.parse import urlparse
import sqlite3

import discord
from discord import app_commands
from discord.ext import commands

from utils.db_handler import (
    DATA_DIR,
    build_custom_mode_key,
    create_custom_persona,
    delete_custom_persona,
    delete_persona_traits,
    get_active_persona_modes,
    get_custom_persona_by_name,
    get_guild_custom_personas,
    sanitize_persona_name,
    set_active_persona_modes,
    update_custom_persona,
    get_server_mode,
    set_server_mode,
    set_evil_mode,
    set_guild_avatar_path,
    upsert_persona_traits,
)
from utils.affection_traits import extract_persona_traits
from utils.image_downloader import (
    MAX_AVATAR_BYTES,
    MAX_BANNER_BYTES,
    download_and_validate_image,
)
from utils.server_avatar import set_custom_avatar, set_mode_avatar
from utils.logger import get_logger
from utils.persona_panel_ui import (
    MANAGE_GUIDANCE,
    delete_persona_with_fallback,
    open_persona_manage_panel,
)
from modes import resolve_mode_key

logger = get_logger(__name__)

MAX_PERSONAS_PER_GUILD = 5
MAX_CREATIONS_PER_HOUR = 3
PENDING_TTL_SECONDS = 300


@dataclass
class PendingPersona:
    name: str
    bio: Optional[str]
    avatar_url: str
    banner_url: Optional[str]
    aliases: list[str]
    normal_prompt: Optional[str]
    evil_prompt: Optional[str]
    created_at: datetime


@dataclass
class PendingPersonaEdit:
    mode_key: str
    name: str
    bio: Optional[str]
    avatar_url: Optional[str]
    banner_url: Optional[str]
    current_avatar_path: Optional[str]
    current_banner_path: Optional[str]
    current_normal_prompt: Optional[str]
    current_evil_prompt: Optional[str]
    created_at: datetime


def _combine_prompt_parts(part1: Optional[str], part2: Optional[str]) -> str:
    chunks = []
    for part in (part1, part2):
        text = (part or "").strip()
        if text:
            chunks.append(text)
    return "\n".join(chunks).strip()


def _parse_aliases_input(raw: str, persona_name: str) -> list[str]:
    if not raw:
        return []
    tokens = re.split(r"[,\\n]+", raw)
    cleaned: list[str] = []
    name_lower = (persona_name or "").strip().lower()
    for token in tokens:
        value = token.strip().lower()
        if not value:
            continue
        value = re.sub(r"\s+", " ", value)
        if name_lower and value == name_lower:
            continue
        if value not in cleaned:
            cleaned.append(value)
    return cleaned


class ContinueToNormalPromptsView(discord.ui.View):
    def __init__(self, cog: "Persona", guild_id: int, user_id: int):
        super().__init__(timeout=PENDING_TTL_SECONDS)
        self.cog = cog
        self.guild_id = guild_id
        self.user_id = user_id

    @discord.ui.button(label="Continue", style=discord.ButtonStyle.primary)
    async def continue_button(
        self,
        interaction: discord.Interaction,
        button: discord.ui.Button,
    ) -> None:
        if interaction.user.id != self.user_id:
            await interaction.response.send_message(
                "This prompt is not for you.",
                ephemeral=True,
            )
            return

        if not self.cog.has_pending(self.guild_id, self.user_id):
            await interaction.response.send_message(
                "This creation session expired. Reopen `/persona manage` and start Create Persona again.",
                ephemeral=True,
            )
            return

        modal = PersonaNormalPromptModal(self.cog, self.guild_id, self.user_id)
        await interaction.response.send_modal(modal)


class ContinueToEvilPromptsView(discord.ui.View):
    def __init__(self, cog: "Persona", guild_id: int, user_id: int):
        super().__init__(timeout=PENDING_TTL_SECONDS)
        self.cog = cog
        self.guild_id = guild_id
        self.user_id = user_id

    @discord.ui.button(label="Continue", style=discord.ButtonStyle.primary)
    async def continue_button(
        self,
        interaction: discord.Interaction,
        button: discord.ui.Button,
    ) -> None:
        if interaction.user.id != self.user_id:
            await interaction.response.send_message(
                "This prompt is not for you.",
                ephemeral=True,
            )
            return

        if not self.cog.has_pending(self.guild_id, self.user_id):
            await interaction.response.send_message(
                "This creation session expired. Reopen `/persona manage` and start Create Persona again.",
                ephemeral=True,
            )
            return

        modal = PersonaEvilPromptModal(self.cog, self.guild_id, self.user_id)
        await interaction.response.send_modal(modal)


class ContinueToConfirmView(discord.ui.View):
    def __init__(self, cog: "Persona", guild_id: int, user_id: int):
        super().__init__(timeout=PENDING_TTL_SECONDS)
        self.cog = cog
        self.guild_id = guild_id
        self.user_id = user_id

    @discord.ui.button(label="Create Persona", style=discord.ButtonStyle.success)
    async def confirm_button(
        self,
        interaction: discord.Interaction,
        button: discord.ui.Button,
    ) -> None:
        if interaction.user.id != self.user_id:
            await interaction.response.send_message(
                "This prompt is not for you.",
                ephemeral=True,
            )
            return

        await self.cog.finalize_pending_persona(interaction, self.guild_id, self.user_id)


class PersonaBasicModal(discord.ui.Modal):
    def __init__(self, cog: "Persona", guild_id: int, user_id: int):
        super().__init__(title="Create Persona (Step 1)")
        self.cog = cog
        self.guild_id = guild_id
        self.user_id = user_id

        self.name_input = discord.ui.TextInput(
            label="Persona Name",
            placeholder="Unique name (max 32 chars)",
            max_length=32,
            required=True,
        )
        self.bio_input = discord.ui.TextInput(
            label="Bio (optional)",
            style=discord.TextStyle.paragraph,
            max_length=500,
            required=False,
        )
        self.avatar_url_input = discord.ui.TextInput(
            label="Avatar Image URL",
            placeholder="https://example.com/avatar.png",
            required=True,
        )
        self.banner_url_input = discord.ui.TextInput(
            label="Banner Image URL (optional)",
            placeholder="https://example.com/banner.png",
            required=False,
        )
        self.aliases_input = discord.ui.TextInput(
            label="Bot Aliases (optional)",
            placeholder="Names it responds to (comma or newline separated)",
            max_length=500,
            required=False,
        )

        self.add_item(self.name_input)
        self.add_item(self.bio_input)
        self.add_item(self.avatar_url_input)
        self.add_item(self.banner_url_input)
        self.add_item(self.aliases_input)

    async def on_submit(self, interaction: discord.Interaction) -> None:
        name = (self.name_input.value or "").strip()
        bio = (self.bio_input.value or "").strip() or None
        avatar_url = (self.avatar_url_input.value or "").strip()
        banner_url = (self.banner_url_input.value or "").strip() or None
        aliases = _parse_aliases_input(self.aliases_input.value or "", name)

        if not name:
            await interaction.response.send_message("Name is required.", ephemeral=True)
            return

        slug = sanitize_persona_name(name)
        if not slug:
            await interaction.response.send_message(
                "Name must contain letters or numbers.",
                ephemeral=True,
            )
            return

        if self.cog.is_rate_limited(self.guild_id, self.user_id):
            await interaction.response.send_message(
                "Persona creation is limited to 3 per hour per user.",
                ephemeral=True,
            )
            return

        existing = await get_custom_persona_by_name(self.guild_id, name)
        if existing:
            await interaction.response.send_message(
                "A custom persona with that name already exists.",
                ephemeral=True,
            )
            return

        personas = await get_guild_custom_personas(self.guild_id)
        if len(personas) >= MAX_PERSONAS_PER_GUILD:
            await interaction.response.send_message(
                "This server already has the maximum number of custom personas.",
                ephemeral=True,
            )
            return

        if not _is_valid_url(avatar_url):
            await interaction.response.send_message(
                "Avatar URL must be http or https.",
                ephemeral=True,
            )
            return

        if banner_url and not _is_valid_url(banner_url):
            await interaction.response.send_message(
                "Banner URL must be http or https.",
                ephemeral=True,
            )
            return

        pending = PendingPersona(
            name=name,
            bio=bio,
            avatar_url=avatar_url,
            banner_url=banner_url,
            aliases=aliases,
            normal_prompt=None,
            evil_prompt=None,
            created_at=datetime.utcnow(),
        )
        self.cog.store_pending(self.guild_id, self.user_id, pending)

        view = ContinueToNormalPromptsView(self.cog, self.guild_id, self.user_id)
        await interaction.response.send_message(
            "Step 1 saved. Click Continue to add the normal prompt.",
            view=view,
            ephemeral=True,
        )


class PersonaNormalPromptModal(discord.ui.Modal):
    def __init__(self, cog: "Persona", guild_id: int, user_id: int):
        super().__init__(title="Create Persona (Step 2)")
        self.cog = cog
        self.guild_id = guild_id
        self.user_id = user_id

        self.part1 = discord.ui.TextInput(
            label="Normal Prompt (Part 1)",
            style=discord.TextStyle.paragraph,
            max_length=2000,
            required=True,
        )
        self.part2 = discord.ui.TextInput(
            label="Normal Prompt (Part 2, optional)",
            style=discord.TextStyle.paragraph,
            max_length=2000,
            required=False,
        )
        self.part3 = discord.ui.TextInput(
            label="Normal Prompt (Part 3, optional)",
            style=discord.TextStyle.paragraph,
            max_length=2000,
            required=False,
        )
        self.part4 = discord.ui.TextInput(
            label="Normal Prompt (Part 4, optional)",
            style=discord.TextStyle.paragraph,
            max_length=2000,
            required=False,
        )
        self.part5 = discord.ui.TextInput(
            label="Normal Prompt (Part 5, optional)",
            style=discord.TextStyle.paragraph,
            max_length=2000,
            required=False,
        )

        self.add_item(self.part1)
        self.add_item(self.part2)
        self.add_item(self.part3)
        self.add_item(self.part4)
        self.add_item(self.part5)

    async def on_submit(self, interaction: discord.Interaction) -> None:
        pending = self.cog.get_pending(self.guild_id, self.user_id)
        if not pending:
            await interaction.response.send_message(
                "This creation session expired. Reopen `/persona manage` and start Create Persona again.",
                ephemeral=True,
            )
            return

        normal_prompt = "\n".join(
            part.strip()
            for part in [
                self.part1.value,
                self.part2.value,
                self.part3.value,
                self.part4.value,
                self.part5.value,
            ]
            if (part or "").strip()
        ).strip()

        if not normal_prompt:
            await interaction.response.send_message(
                "Normal prompt is required.",
                ephemeral=True,
            )
            return

        pending.normal_prompt = normal_prompt

        view = ContinueToEvilPromptsView(self.cog, self.guild_id, self.user_id)
        await interaction.response.send_message(
            "Step 2 saved. Click Continue to add the evil prompt.",
            view=view,
            ephemeral=True,
        )


class PersonaEvilPromptModal(discord.ui.Modal):
    def __init__(self, cog: "Persona", guild_id: int, user_id: int):
        super().__init__(title="Create Persona (Step 3)")
        self.cog = cog
        self.guild_id = guild_id
        self.user_id = user_id

        self.part1 = discord.ui.TextInput(
            label="Evil Prompt (Part 1, optional)",
            style=discord.TextStyle.paragraph,
            max_length=2000,
            required=False,
        )
        self.part2 = discord.ui.TextInput(
            label="Evil Prompt (Part 2, optional)",
            style=discord.TextStyle.paragraph,
            max_length=2000,
            required=False,
        )
        self.part3 = discord.ui.TextInput(
            label="Evil Prompt (Part 3, optional)",
            style=discord.TextStyle.paragraph,
            max_length=2000,
            required=False,
        )
        self.part4 = discord.ui.TextInput(
            label="Evil Prompt (Part 4, optional)",
            style=discord.TextStyle.paragraph,
            max_length=2000,
            required=False,
        )
        self.part5 = discord.ui.TextInput(
            label="Evil Prompt (Part 5, optional)",
            style=discord.TextStyle.paragraph,
            max_length=2000,
            required=False,
        )

        self.add_item(self.part1)
        self.add_item(self.part2)
        self.add_item(self.part3)
        self.add_item(self.part4)
        self.add_item(self.part5)

    async def on_submit(self, interaction: discord.Interaction) -> None:
        pending = self.cog.get_pending(self.guild_id, self.user_id)
        if not pending:
            await interaction.response.send_message(
                "This creation session expired. Reopen `/persona manage` and start Create Persona again.",
                ephemeral=True,
            )
            return

        evil_prompt = "\n".join(
            part.strip()
            for part in [
                self.part1.value,
                self.part2.value,
                self.part3.value,
                self.part4.value,
                self.part5.value,
            ]
            if (part or "").strip()
        ).strip()

        pending.evil_prompt = evil_prompt or None

        view = ContinueToConfirmView(self.cog, self.guild_id, self.user_id)
        await interaction.response.send_message(
            "Step 3 saved. Click Create Persona to finalize.",
            view=view,
            ephemeral=True,
        )


class PersonaEditModal(discord.ui.Modal):
    def __init__(self, cog: "Persona", guild_id: int, user_id: int, persona: dict):
        title = f"Edit Persona: {persona.get('name', 'custom')}"
        super().__init__(title=title[:45])
        self.cog = cog
        self.guild_id = guild_id
        self.user_id = user_id
        self.persona = persona

        self.bio_input = discord.ui.TextInput(
            label="New Bio (optional)",
            style=discord.TextStyle.paragraph,
            max_length=500,
            required=False,
            placeholder="Leave blank to keep current bio",
        )
        self.avatar_url_input = discord.ui.TextInput(
            label="New Avatar URL (optional)",
            required=False,
            placeholder="Leave blank to keep current avatar",
        )
        self.banner_url_input = discord.ui.TextInput(
            label="New Banner URL (optional)",
            required=False,
            placeholder="Leave blank to keep, or type 'clear' to remove",
        )

        self.add_item(self.bio_input)
        self.add_item(self.avatar_url_input)
        self.add_item(self.banner_url_input)

    async def on_submit(self, interaction: discord.Interaction) -> None:
        bio = (self.bio_input.value or "").strip() or None
        avatar_url = (self.avatar_url_input.value or "").strip() or None
        banner_url = (self.banner_url_input.value or "").strip() or None

        if avatar_url and not _is_valid_url(avatar_url):
            await interaction.response.send_message(
                "Avatar URL must be http or https.",
                ephemeral=True,
            )
            return

        if banner_url and banner_url.lower() != "clear" and not _is_valid_url(banner_url):
            await interaction.response.send_message(
                "Banner URL must be http or https, or type 'clear' to remove.",
                ephemeral=True,
            )
            return

        pending = PendingPersonaEdit(
            mode_key=self.persona.get("mode_key", ""),
            name=self.persona.get("name", "custom"),
            bio=bio,
            avatar_url=avatar_url,
            banner_url=banner_url,
            current_avatar_path=self.persona.get("avatar_path"),
            current_banner_path=self.persona.get("banner_path"),
            current_normal_prompt=self.persona.get("normal_prompt"),
            current_evil_prompt=self.persona.get("evil_prompt"),
            created_at=datetime.utcnow(),
        )
        self.cog.store_edit_pending(self.guild_id, self.user_id, pending)

        view = ContinueEditPromptsView(self.cog, self.guild_id, self.user_id)
        await interaction.response.send_message(
            "Step 1 saved. Click Continue to edit prompts (optional).",
            view=view,
            ephemeral=True,
        )


class PersonaEditPromptsModal(discord.ui.Modal):
    def __init__(self, cog: "Persona", guild_id: int, user_id: int):
        super().__init__(title="Edit Persona Prompts")
        self.cog = cog
        self.guild_id = guild_id
        self.user_id = user_id

        self.normal_prompt_part1 = discord.ui.TextInput(
            label="Normal Prompt (Part 1, optional)",
            style=discord.TextStyle.paragraph,
            max_length=2000,
            required=False,
            placeholder="Leave blank to keep current",
        )
        self.normal_prompt_part2 = discord.ui.TextInput(
            label="Normal Prompt (Part 2, optional)",
            style=discord.TextStyle.paragraph,
            max_length=2000,
            required=False,
            placeholder="Leave blank to keep current",
        )
        self.evil_prompt_part1 = discord.ui.TextInput(
            label="Evil Prompt (Part 1, optional)",
            style=discord.TextStyle.paragraph,
            max_length=2000,
            required=False,
            placeholder="Leave blank to keep, or type 'clear' to remove",
        )
        self.evil_prompt_part2 = discord.ui.TextInput(
            label="Evil Prompt (Part 2, optional)",
            style=discord.TextStyle.paragraph,
            max_length=2000,
            required=False,
            placeholder="Leave blank to keep, or type 'clear' to remove",
        )

        self.add_item(self.normal_prompt_part1)
        self.add_item(self.normal_prompt_part2)
        self.add_item(self.evil_prompt_part1)
        self.add_item(self.evil_prompt_part2)

    async def on_submit(self, interaction: discord.Interaction) -> None:
        pending = self.cog.pop_edit_pending(self.guild_id, self.user_id)
        if not pending:
            await interaction.response.send_message(
                "This edit session expired. Please run /persona edit again.",
                ephemeral=True,
            )
            return

        updates: dict[str, object] = {}
        if pending.bio is not None:
            updates["bio"] = pending.bio

        slug = sanitize_persona_name(pending.name)
        base_dir = DATA_DIR / "avatars" / "custom"
        avatar_path = base_dir / f"guild_{self.guild_id}_{slug}_avatar.webp"
        banner_path = base_dir / f"guild_{self.guild_id}_{slug}_banner.webp"

        await interaction.response.defer(ephemeral=True)

        if pending.avatar_url:
            success, message = await download_and_validate_image(
                pending.avatar_url,
                avatar_path,
                MAX_AVATAR_BYTES,
            )
            if not success:
                await interaction.followup.send(f"Avatar error: {message}", ephemeral=True)
                return
            updates["avatar_path"] = str(avatar_path)

        if pending.banner_url:
            if pending.banner_url.lower() == "clear":
                if pending.current_banner_path:
                    try:
                        Path(pending.current_banner_path).unlink(missing_ok=True)
                    except OSError:
                        pass
                updates["banner_path"] = None
            else:
                success, message = await download_and_validate_image(
                    pending.banner_url,
                    banner_path,
                    MAX_BANNER_BYTES,
                )
                if not success:
                    await interaction.followup.send(f"Banner error: {message}", ephemeral=True)
                    return
                updates["banner_path"] = str(banner_path)

        normal_prompt = _combine_prompt_parts(
            self.normal_prompt_part1.value,
            self.normal_prompt_part2.value,
        )
        if normal_prompt:
            updates["normal_prompt"] = normal_prompt

        evil_prompt = _combine_prompt_parts(
            self.evil_prompt_part1.value,
            self.evil_prompt_part2.value,
        )
        if evil_prompt:
            if evil_prompt.lower() == "clear":
                updates["evil_prompt"] = None
            else:
                updates["evil_prompt"] = evil_prompt

        if not updates:
            await interaction.followup.send("No changes to apply.", ephemeral=True)
            return

        updated = await update_custom_persona(
            self.guild_id,
            pending.mode_key,
            **updates,
        )

        if not updated:
            await interaction.followup.send("Failed to update persona.", ephemeral=True)
            return

        if "normal_prompt" in updates or "evil_prompt" in updates:
            normal_prompt = updates.get("normal_prompt") or pending.current_normal_prompt or ""
            evil_prompt = updates.get("evil_prompt")
            if evil_prompt is None and "evil_prompt" not in updates:
                evil_prompt = pending.current_evil_prompt
            traits = extract_persona_traits(normal_prompt, evil_prompt)
            try:
                await upsert_persona_traits(self.guild_id, pending.mode_key, traits)
            except Exception as exc:
                logger.warning("Failed to update persona traits: %s", exc)

        current_mode = await get_server_mode(self.guild_id)
        if current_mode == pending.mode_key and "avatar_path" in updates:
            try:
                avatar_bytes = avatar_path.read_bytes()
                await set_custom_avatar(self.cog.bot, self.guild_id, avatar_bytes)
            except Exception as exc:
                logger.warning("Failed to update active persona avatar: %s", exc)

        await interaction.followup.send("Persona updated.", ephemeral=True)


class ContinueEditPromptsView(discord.ui.View):
    def __init__(self, cog: "Persona", guild_id: int, user_id: int):
        super().__init__(timeout=PENDING_TTL_SECONDS)
        self.cog = cog
        self.guild_id = guild_id
        self.user_id = user_id

    @discord.ui.button(label="Continue", style=discord.ButtonStyle.primary)
    async def continue_button(
        self,
        interaction: discord.Interaction,
        button: discord.ui.Button,
    ) -> None:
        if interaction.user.id != self.user_id:
            await interaction.response.send_message(
                "This prompt is not for you.",
                ephemeral=True,
            )
            return

        if not self.cog.has_edit_pending(self.guild_id, self.user_id):
            await interaction.response.send_message(
                "This edit session expired. Please run /persona edit again.",
                ephemeral=True,
            )
            return

        modal = PersonaEditPromptsModal(self.cog, self.guild_id, self.user_id)
        await interaction.response.send_modal(modal)


class Persona(commands.Cog):
    """Custom persona management."""

    persona_group = app_commands.Group(name="persona", description="Manage custom personas")

    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self._pending: dict[tuple[int, int], PendingPersona] = {}
        self._pending_edits: dict[tuple[int, int], PendingPersonaEdit] = {}
        self._creation_log: dict[tuple[int, int], list[datetime]] = {}

    async def _resolve_active_persona_mode_keys(
        self,
        guild_id: int,
        values: list[str],
    ) -> list[str]:
        personas = await get_guild_custom_personas(guild_id)
        custom_by_name = {
            str(persona.get("name") or "").strip().lower(): str(persona.get("mode_key") or "")
            for persona in personas
            if persona.get("name") and persona.get("mode_key")
        }
        custom_by_mode_key = {
            str(persona.get("mode_key") or "").strip(): str(persona.get("mode_key") or "").strip()
            for persona in personas
            if persona.get("mode_key")
        }

        resolved: list[str] = []
        for raw_value in values:
            token = str(raw_value or "").strip()
            if not token:
                continue
            lowered = token.lower()
            mode_key = custom_by_mode_key.get(token)
            if not mode_key and lowered.startswith("mode_"):
                mode_key = lowered
            if not mode_key and lowered.startswith("custom_"):
                mode_key = token
            if not mode_key:
                mode_key = resolve_mode_key(lowered)
            if not mode_key:
                mode_key = custom_by_name.get(lowered)
            if not mode_key:
                raise ValueError(f"Unknown persona selection: {token}")
            resolved.append(mode_key)
        return resolved

    async def _set_active_persona_modes_for_guild(
        self,
        guild_id: int,
        values: list[str],
    ) -> list[str]:
        resolved = await self._resolve_active_persona_mode_keys(guild_id, values)
        await set_active_persona_modes(guild_id, resolved)
        return await get_active_persona_modes(guild_id)

    def _prune_pending(self) -> None:
        cutoff = datetime.utcnow() - timedelta(seconds=PENDING_TTL_SECONDS)
        stale_keys = [
            key for key, pending in self._pending.items()
            if pending.created_at < cutoff
        ]
        for key in stale_keys:
            self._pending.pop(key, None)

    def store_pending(self, guild_id: int, user_id: int, pending: PendingPersona) -> None:
        self._prune_pending()
        self._pending[(guild_id, user_id)] = pending

    def get_pending(self, guild_id: int, user_id: int) -> Optional[PendingPersona]:
        self._prune_pending()
        return self._pending.get((guild_id, user_id))

    def pop_pending(self, guild_id: int, user_id: int) -> Optional[PendingPersona]:
        self._prune_pending()
        return self._pending.pop((guild_id, user_id), None)

    def has_pending(self, guild_id: int, user_id: int) -> bool:
        self._prune_pending()
        return (guild_id, user_id) in self._pending

    def _prune_edit_pending(self) -> None:
        cutoff = datetime.utcnow() - timedelta(seconds=PENDING_TTL_SECONDS)
        stale_keys = [
            key for key, pending in self._pending_edits.items()
            if pending.created_at < cutoff
        ]
        for key in stale_keys:
            self._pending_edits.pop(key, None)

    def store_edit_pending(self, guild_id: int, user_id: int, pending: PendingPersonaEdit) -> None:
        self._prune_edit_pending()
        self._pending_edits[(guild_id, user_id)] = pending

    def pop_edit_pending(self, guild_id: int, user_id: int) -> Optional[PendingPersonaEdit]:
        self._prune_edit_pending()
        return self._pending_edits.pop((guild_id, user_id), None)

    def has_edit_pending(self, guild_id: int, user_id: int) -> bool:
        self._prune_edit_pending()
        return (guild_id, user_id) in self._pending_edits

    def _prune_creation_log(self, guild_id: int, user_id: int) -> int:
        key = (guild_id, user_id)
        cutoff = datetime.utcnow() - timedelta(hours=1)
        entries = self._creation_log.get(key, [])
        entries = [stamp for stamp in entries if stamp >= cutoff]
        self._creation_log[key] = entries
        return len(entries)

    def is_rate_limited(self, guild_id: int, user_id: int) -> bool:
        count = self._prune_creation_log(guild_id, user_id)
        return count >= MAX_CREATIONS_PER_HOUR

    def record_creation(self, guild_id: int, user_id: int) -> None:
        key = (guild_id, user_id)
        entries = self._creation_log.get(key, [])
        entries.append(datetime.utcnow())
        self._creation_log[key] = entries

    async def _open_basic_modal(self, interaction: discord.Interaction) -> None:
        if not interaction.guild:
            await interaction.response.send_message("Use this command in a server.", ephemeral=True)
            return

        modal = PersonaBasicModal(self, interaction.guild.id, interaction.user.id)
        await interaction.response.send_modal(modal)

    async def _open_edit_modal_by_mode_key(
        self,
        interaction: discord.Interaction,
        mode_key: str,
    ) -> None:
        if not interaction.guild:
            await interaction.response.send_message("Use this command in a server.", ephemeral=True)
            return

        persona = await get_custom_persona_by_mode_key(interaction.guild.id, mode_key)
        if not persona:
            await interaction.response.send_message("Persona not found.", ephemeral=True)
            return

        modal = PersonaEditModal(self, interaction.guild.id, interaction.user.id, persona)
        await interaction.response.send_modal(modal)

    async def finalize_pending_persona(
        self,
        interaction: discord.Interaction,
        guild_id: int,
        user_id: int,
    ) -> None:
        pending = self.pop_pending(guild_id, user_id)
        if not pending:
            await interaction.response.send_message(
                "This creation session expired. Reopen `/persona manage` and start Create Persona again.",
                ephemeral=True,
            )
            return

        if self.is_rate_limited(guild_id, user_id):
            await interaction.response.send_message(
                "Persona creation is limited to 3 per hour per user.",
                ephemeral=True,
            )
            return

        if not pending.normal_prompt:
            await interaction.response.send_message(
                "Normal prompt is required.",
                ephemeral=True,
            )
            return

        mode_key = build_custom_mode_key(guild_id, pending.name)
        if not mode_key:
            await interaction.response.send_message(
                "Failed to build a mode key for that name.",
                ephemeral=True,
            )
            return

        slug = sanitize_persona_name(pending.name)
        base_dir = DATA_DIR / "avatars" / "custom"
        avatar_path = base_dir / f"guild_{guild_id}_{slug}_avatar.webp"
        banner_path = (
            base_dir / f"guild_{guild_id}_{slug}_banner.webp"
            if pending.banner_url
            else None
        )

        await interaction.response.defer(ephemeral=True)

        success, message = await download_and_validate_image(
            pending.avatar_url,
            avatar_path,
            MAX_AVATAR_BYTES,
        )
        if not success:
            await interaction.followup.send(f"Avatar error: {message}", ephemeral=True)
            return

        if banner_path and pending.banner_url:
            success, message = await download_and_validate_image(
                pending.banner_url,
                banner_path,
                MAX_BANNER_BYTES,
            )
            if not success:
                try:
                    avatar_path.unlink(missing_ok=True)
                except OSError:
                    pass
                await interaction.followup.send(f"Banner error: {message}", ephemeral=True)
                return

        try:
            await create_custom_persona(
                guild_id=guild_id,
                name=pending.name,
                mode_key=mode_key,
                bio=pending.bio,
                avatar_path=str(avatar_path),
                banner_path=str(banner_path) if banner_path else None,
                aliases=pending.aliases,
                normal_prompt=pending.normal_prompt,
                evil_prompt=pending.evil_prompt or None,
                created_by=interaction.user.id,
            )
        except sqlite3.IntegrityError:
            try:
                avatar_path.unlink(missing_ok=True)
            except OSError:
                pass
            if banner_path:
                try:
                    banner_path.unlink(missing_ok=True)
                except OSError:
                    pass
            await interaction.followup.send(
                "A custom persona with that name already exists.",
                ephemeral=True,
            )
            return

        traits = extract_persona_traits(
            pending.normal_prompt,
            pending.evil_prompt or None,
        )
        if traits:
            try:
                await upsert_persona_traits(guild_id, mode_key, traits)
            except Exception as exc:
                logger.warning("Failed to save persona traits: %s", exc)

        self.record_creation(guild_id, user_id)

        await interaction.followup.send(
            f"Custom persona **{pending.name}** created! {MANAGE_GUIDANCE}",
            ephemeral=True,
        )

    @persona_group.command(name="manage", description="Open the persona and presentation admin panel.")
    @app_commands.checks.has_permissions(manage_guild=True)
    async def manage_personas(self, interaction: discord.Interaction):
        await open_persona_manage_panel(interaction, bot=self.bot)

    @persona_group.command(name="edit", description="Edit a custom persona.")
    @app_commands.checks.has_permissions(manage_guild=True)
    async def edit_persona(self, interaction: discord.Interaction, name: str):
        if not interaction.guild:
            await interaction.response.send_message("Use this command in a server.", ephemeral=True)
            return

        persona = await get_custom_persona_by_name(interaction.guild.id, name)
        if not persona:
            await interaction.response.send_message("Persona not found.", ephemeral=True)
            return

        await self._open_edit_modal_by_mode_key(interaction, persona["mode_key"])

    @persona_group.command(name="delete", description="Delete a custom persona.")
    @app_commands.checks.has_permissions(manage_guild=True)
    async def delete_persona(self, interaction: discord.Interaction, name: str):
        if not interaction.guild:
            await interaction.response.send_message("Use this command in a server.", ephemeral=True)
            return

        persona = await get_custom_persona_by_name(interaction.guild.id, name)
        if not persona:
            await interaction.response.send_message("Persona not found.", ephemeral=True)
            return

        mode_key = persona.get("mode_key")
        if not mode_key:
            await interaction.response.send_message("Persona mode key missing.", ephemeral=True)
            return

        deleted = await delete_persona_with_fallback(
            bot=self.bot,
            guild_id=interaction.guild.id,
            user_id=interaction.user.id,
            mode_key=mode_key,
        )
        if not deleted:
            await interaction.response.send_message("Failed to delete persona.", ephemeral=True)
            return

        await interaction.response.send_message(
            f"Persona **{persona.get('name', name)}** deleted. {MANAGE_GUIDANCE}",
            ephemeral=True,
        )


def _is_valid_url(value: str) -> bool:
    parsed = urlparse(value or "")
    return parsed.scheme in {"http", "https"}


async def setup(bot: commands.Bot):
    await bot.add_cog(Persona(bot))
