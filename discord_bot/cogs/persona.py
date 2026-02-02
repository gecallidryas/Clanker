"""
Custom persona management.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path
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
    get_custom_persona_by_name,
    get_guild_custom_personas,
    sanitize_persona_name,
    update_custom_persona,
    get_server_mode,
    set_server_mode,
    set_evil_mode,
    set_guild_avatar_path,
)
from utils.image_downloader import (
    MAX_AVATAR_BYTES,
    MAX_BANNER_BYTES,
    download_and_validate_image,
)
from utils.server_avatar import set_custom_avatar, set_mode_avatar
from utils.logger import get_logger

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
    created_at: datetime


class ContinueToPromptsView(discord.ui.View):
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
                "This creation session expired. Please run /create persona again.",
                ephemeral=True,
            )
            return

        modal = PersonaPromptsModal(self.cog, self.guild_id, self.user_id)
        await interaction.response.send_modal(modal)


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

        self.add_item(self.name_input)
        self.add_item(self.bio_input)
        self.add_item(self.avatar_url_input)
        self.add_item(self.banner_url_input)

    async def on_submit(self, interaction: discord.Interaction) -> None:
        name = (self.name_input.value or "").strip()
        bio = (self.bio_input.value or "").strip() or None
        avatar_url = (self.avatar_url_input.value or "").strip()
        banner_url = (self.banner_url_input.value or "").strip() or None

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
            created_at=datetime.utcnow(),
        )
        self.cog.store_pending(self.guild_id, self.user_id, pending)

        view = ContinueToPromptsView(self.cog, self.guild_id, self.user_id)
        await interaction.response.send_message(
            "Step 1 saved. Click Continue to add prompts.",
            view=view,
            ephemeral=True,
        )


class PersonaPromptsModal(discord.ui.Modal):
    def __init__(self, cog: "Persona", guild_id: int, user_id: int):
        super().__init__(title="Create Persona (Step 2)")
        self.cog = cog
        self.guild_id = guild_id
        self.user_id = user_id

        self.normal_prompt = discord.ui.TextInput(
            label="Normal System Prompt",
            style=discord.TextStyle.paragraph,
            max_length=2000,
            required=True,
        )
        self.evil_prompt = discord.ui.TextInput(
            label="Evil System Prompt (optional)",
            style=discord.TextStyle.paragraph,
            max_length=2000,
            required=False,
        )

        self.add_item(self.normal_prompt)
        self.add_item(self.evil_prompt)

    async def on_submit(self, interaction: discord.Interaction) -> None:
        pending = self.cog.pop_pending(self.guild_id, self.user_id)
        if not pending:
            await interaction.response.send_message(
                "This creation session expired. Please run /create persona again.",
                ephemeral=True,
            )
            return

        if self.cog.is_rate_limited(self.guild_id, self.user_id):
            await interaction.response.send_message(
                "Persona creation is limited to 3 per hour per user.",
                ephemeral=True,
            )
            return

        mode_key = build_custom_mode_key(self.guild_id, pending.name)
        if not mode_key:
            await interaction.response.send_message(
                "Failed to build a mode key for that name.",
                ephemeral=True,
            )
            return

        slug = sanitize_persona_name(pending.name)
        base_dir = DATA_DIR / "avatars" / "custom"
        avatar_path = base_dir / f"guild_{self.guild_id}_{slug}_avatar.webp"
        banner_path = (
            base_dir / f"guild_{self.guild_id}_{slug}_banner.webp"
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
                guild_id=self.guild_id,
                name=pending.name,
                mode_key=mode_key,
                bio=pending.bio,
                avatar_path=str(avatar_path),
                banner_path=str(banner_path) if banner_path else None,
                normal_prompt=self.normal_prompt.value,
                evil_prompt=self.evil_prompt.value or None,
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

        self.cog.record_creation(self.guild_id, self.user_id)

        await interaction.followup.send(
            f"Custom persona **{pending.name}** created! Use `!mode {pending.name}` or `/mode {pending.name}`.",
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

        self.normal_prompt = discord.ui.TextInput(
            label="Normal Prompt (optional)",
            style=discord.TextStyle.paragraph,
            max_length=2000,
            required=False,
            placeholder="Leave blank to keep current",
        )
        self.evil_prompt = discord.ui.TextInput(
            label="Evil Prompt (optional)",
            style=discord.TextStyle.paragraph,
            max_length=2000,
            required=False,
            placeholder="Leave blank to keep, or type 'clear' to remove",
        )

        self.add_item(self.normal_prompt)
        self.add_item(self.evil_prompt)

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

        normal_prompt = (self.normal_prompt.value or "").strip()
        if normal_prompt:
            updates["normal_prompt"] = normal_prompt

        evil_prompt = (self.evil_prompt.value or "").strip()
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

    create_group = app_commands.Group(name="create", description="Create resources")
    persona_group = app_commands.Group(name="persona", description="Manage custom personas")

    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self._pending: dict[tuple[int, int], PendingPersona] = {}
        self._pending_edits: dict[tuple[int, int], PendingPersonaEdit] = {}
        self._creation_log: dict[tuple[int, int], list[datetime]] = {}

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

    @create_group.command(name="persona", description="Create a custom persona.")
    @app_commands.checks.has_permissions(manage_guild=True)
    async def create_persona(self, interaction: discord.Interaction):
        await self._open_basic_modal(interaction)

    @persona_group.command(name="create", description="Create a custom persona.")
    @app_commands.checks.has_permissions(manage_guild=True)
    async def create_persona_alias(self, interaction: discord.Interaction):
        await self._open_basic_modal(interaction)

    @persona_group.command(name="list", description="List custom personas.")
    async def list_personas(self, interaction: discord.Interaction):
        if not interaction.guild:
            await interaction.response.send_message("Use this command in a server.", ephemeral=True)
            return

        personas = await get_guild_custom_personas(interaction.guild.id)
        if not personas:
            await interaction.response.send_message("No custom personas found.", ephemeral=True)
            return

        embed = discord.Embed(
            title="Custom Personas",
            color=discord.Color.blue(),
        )

        for persona in personas[:10]:
            name = persona.get("name", "Unnamed")
            mode_key = persona.get("mode_key", "")
            bio = persona.get("bio") or "No bio provided."
            embed.add_field(
                name=name,
                value=f"Mode: `{mode_key}`\n{bio[:200]}",
                inline=False,
            )

        if len(personas) > 10:
            embed.set_footer(text=f"And {len(personas) - 10} more...")

        await interaction.response.send_message(embed=embed, ephemeral=True)

    @persona_group.command(name="preview", description="Preview a custom persona.")
    async def preview_persona(self, interaction: discord.Interaction, name: str):
        if not interaction.guild:
            await interaction.response.send_message("Use this command in a server.", ephemeral=True)
            return

        persona = await get_custom_persona_by_name(interaction.guild.id, name)
        if not persona:
            await interaction.response.send_message("Persona not found.", ephemeral=True)
            return

        embed = discord.Embed(
            title=persona.get("name", "Custom Persona"),
            description=persona.get("bio") or "No bio provided.",
            color=discord.Color.purple(),
        )
        embed.add_field(name="Mode Key", value=f"`{persona.get('mode_key', '')}`", inline=False)
        embed.add_field(
            name="Avatar",
            value="Set" if persona.get("avatar_path") else "Not set",
            inline=True,
        )
        embed.add_field(
            name="Banner",
            value="Set" if persona.get("banner_path") else "Not set",
            inline=True,
        )
        embed.add_field(
            name="Evil Prompt",
            value="Yes" if persona.get("evil_prompt") else "No",
            inline=True,
        )

        await interaction.response.send_message(embed=embed, ephemeral=True)

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

        modal = PersonaEditModal(self, interaction.guild.id, interaction.user.id, persona)
        await interaction.response.send_modal(modal)

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

        current_mode = await get_server_mode(interaction.guild.id)
        if current_mode == mode_key:
            await set_server_mode(interaction.guild.id, "mode_default")
            await set_evil_mode(interaction.guild.id, False)
            await set_guild_avatar_path(interaction.guild.id, None)
            try:
                await set_mode_avatar(
                    self.bot,
                    interaction.guild.id,
                    "mode_default",
                    evil_mode=False,
                    force=True,
                )
            except Exception as exc:
                logger.warning("Failed to reset avatar on persona delete: %s", exc)

        deleted = await delete_custom_persona(interaction.guild.id, mode_key)
        if not deleted:
            await interaction.response.send_message("Failed to delete persona.", ephemeral=True)
            return

        for path_value in (persona.get("avatar_path"), persona.get("banner_path")):
            if not path_value:
                continue
            try:
                Path(path_value).unlink(missing_ok=True)
            except OSError:
                logger.warning("Failed to remove persona asset: %s", path_value)

        await interaction.response.send_message(
            f"Persona **{persona.get('name', name)}** deleted.",
            ephemeral=True,
        )


def _is_valid_url(value: str) -> bool:
    parsed = urlparse(value or "")
    return parsed.scheme in {"http", "https"}


async def setup(bot: commands.Bot):
    await bot.add_cog(Persona(bot))
