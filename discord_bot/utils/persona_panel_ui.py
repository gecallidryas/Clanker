from __future__ import annotations

import json
import sqlite3
from dataclasses import dataclass
from pathlib import Path
from typing import Optional, Sequence

import discord

from modes import get_all_modes, get_mode_profile, resolve_mode_key
from utils.admin_panel_logic import action_requires_auth
from utils.admin_views import AdminPanelView, AuthPromptView
from utils.affection_traits import extract_persona_traits
from utils.db_handler import (
    add_guild_config_audit,
    build_custom_mode_key,
    create_custom_persona,
    delete_custom_persona,
    delete_persona_traits,
    get_custom_persona_by_mode_key,
    get_custom_persona_by_name,
    get_evil_mode,
    guild_db,
    get_guild_custom_personas,
    get_server_mode,
    sanitize_persona_name,
    set_evil_mode,
    set_guild_avatar_path,
    set_server_mode,
    update_custom_persona,
    upsert_persona_traits,
)


MANAGE_GUIDANCE = "Primary admin surface: `/persona manage`."
_STRUCTURED_BASE_TEMPLATES = {
    "blank",
    "mode_default",
    "mode_femboy",
    "mode_tsundere",
    "mode_oneesan",
}


@dataclass(frozen=True)
class PersonaEntry:
    mode_key: str
    display_name: str
    group_label: str
    description: str
    is_custom: bool
    bio: Optional[str] = None
    aliases: tuple[str, ...] = ()
    normal_prompt: Optional[str] = None
    evil_prompt: Optional[str] = None
    avatar_path: Optional[str] = None
    banner_path: Optional[str] = None


@dataclass(frozen=True)
class PersonaPanelState:
    guild_id: int
    active_mode: str
    evil_mode_enabled: bool
    entries: tuple[PersonaEntry, ...]


@dataclass(frozen=True)
class PersonaActivationResult:
    mode_key: str
    display_name: str
    is_custom: bool


@dataclass(frozen=True)
class PersonaEvilModeResult:
    enabled: bool
    mode_key: str


def _parse_aliases(raw: str) -> list[str]:
    tokens = [part.strip().lower() for part in (raw or "").replace("\n", ",").split(",")]
    cleaned: list[str] = []
    for token in tokens:
        if token and token not in cleaned:
            cleaned.append(token)
    return cleaned


def _aliases_text(aliases: Sequence[str]) -> str:
    return ", ".join(alias for alias in aliases if alias).strip()


def _normalize_base_template(value: Optional[str]) -> str:
    raw = (value or "").strip().lower()
    if not raw:
        return "blank"
    if raw in _STRUCTURED_BASE_TEMPLATES:
        return raw
    if raw.startswith("mode_") and raw not in _STRUCTURED_BASE_TEMPLATES:
        return "blank"
    resolved = resolve_mode_key(raw)
    if resolved in _STRUCTURED_BASE_TEMPLATES:
        return resolved
    return "blank"


def _normalize_examples(examples: Sequence[str] | None) -> list[str]:
    if not examples:
        return []
    normalized: list[str] = []
    for example in examples:
        text = str(example or "").strip()
        if text and text not in normalized:
            normalized.append(text)
    return normalized


async def apply_structured_persona_fields(
    *,
    guild_id: int,
    mode_key: str,
    base_template: Optional[str] = None,
    voice_tone: Optional[str] = None,
    worldview: Optional[str] = None,
    scene_normal: Optional[str] = None,
    scene_evil: Optional[str] = None,
    examples_normal: Sequence[str] | None = None,
    examples_evil: Sequence[str] | None = None,
) -> None:
    normalized_base_template = _normalize_base_template(base_template)

    voice_tone_text = (voice_tone or "").strip()
    worldview_text = (worldview or "").strip()
    scene_normal_text = (scene_normal or "").strip()
    scene_evil_text = (scene_evil or "").strip()
    examples_normal_list = _normalize_examples(examples_normal)
    examples_evil_list = _normalize_examples(examples_evil)

    voice_json = json.dumps({"tone": voice_tone_text}, ensure_ascii=True) if voice_tone_text else None
    worldview_json = (
        json.dumps({"description": worldview_text}, ensure_ascii=True) if worldview_text else None
    )
    scene_normal_json = (
        json.dumps({"normal": scene_normal_text}, ensure_ascii=True) if scene_normal_text else None
    )
    scene_evil_json = (
        json.dumps({"evil": scene_evil_text}, ensure_ascii=True) if scene_evil_text else None
    )

    examples_payload: dict[str, list[str]] = {}
    if examples_normal_list:
        examples_payload["normal"] = examples_normal_list
    if examples_evil_list:
        examples_payload["evil"] = examples_evil_list
    examples_json = json.dumps(examples_payload, ensure_ascii=True) if examples_payload else None

    async with guild_db(guild_id) as db:
        await db.execute(
            """
            UPDATE custom_personas
            SET schema_version = ?,
                base_template = ?,
                voice_json = ?,
                worldview_json = ?,
                scene_normal_json = ?,
                scene_evil_json = ?,
                examples_json = ?
            WHERE guild_id = ? AND mode_key = ?
            """,
            (
                1,
                normalized_base_template,
                voice_json,
                worldview_json,
                scene_normal_json,
                scene_evil_json,
                examples_json,
                guild_id,
                mode_key,
            ),
        )
        await db.commit()


def _require_manage_guild(interaction: discord.Interaction) -> bool:
    permissions = getattr(interaction.user, "guild_permissions", None)
    return bool(permissions and permissions.manage_guild)


async def _has_password(guild_id: int) -> bool:
    from utils.auth import has_password

    return await has_password(guild_id)


async def _is_authenticated(guild_id: int, user_id: int) -> bool:
    from utils.auth import is_authenticated

    return await is_authenticated(guild_id, user_id)


async def _verify_and_create_session(guild_id: int, user_id: int, password: str) -> bool:
    from utils.auth import verify_and_create_session

    return await verify_and_create_session(guild_id, user_id, password)


async def _get_custom_persona_for_mode(guild_id: int, mode_key: str) -> dict | None:
    if not mode_key.startswith("custom_"):
        return None
    return await get_custom_persona_by_mode_key(guild_id, mode_key)


async def _apply_social_profile(bot, guild_id: int, mode_key: str) -> None:
    social = bot.get_cog("Social") if bot else None
    custom_persona = await _get_custom_persona_for_mode(guild_id, mode_key)
    if social and hasattr(social, "_apply_mode_profile_updates"):
        await social._apply_mode_profile_updates(guild_id, mode_key, custom_persona)


async def load_persona_panel_state(guild_id: int) -> PersonaPanelState:
    active_mode = await get_server_mode(guild_id)
    evil_mode_enabled = await get_evil_mode(guild_id)
    entries: list[PersonaEntry] = []

    for profile in get_all_modes():
        entries.append(
            PersonaEntry(
                mode_key=profile.key,
                display_name=profile.display_name,
                group_label="Built-in",
                description=profile.description,
                is_custom=False,
                bio=profile.bio,
            )
        )

    for persona in await get_guild_custom_personas(guild_id):
        aliases = tuple(persona.get("aliases") or [])
        entries.append(
            PersonaEntry(
                mode_key=persona["mode_key"],
                display_name=persona["name"],
                group_label="Custom",
                description=persona.get("bio") or "Custom persona",
                is_custom=True,
                bio=persona.get("bio"),
                aliases=aliases,
                normal_prompt=persona.get("normal_prompt"),
                evil_prompt=persona.get("evil_prompt"),
                avatar_path=persona.get("avatar_path"),
                banner_path=persona.get("banner_path"),
            )
        )

    return PersonaPanelState(
        guild_id=guild_id,
        active_mode=active_mode,
        evil_mode_enabled=evil_mode_enabled,
        entries=tuple(entries),
    )


def build_persona_select_options(
    state: PersonaPanelState,
    *,
    selected_mode_key: Optional[str] = None,
) -> list[discord.SelectOption]:
    options: list[discord.SelectOption] = []
    for entry in state.entries:
        label = f"[{entry.group_label}] {entry.display_name}"[:100]
        description = (entry.description or "No description")[:100]
        options.append(
            discord.SelectOption(
                label=label,
                description=description,
                value=entry.mode_key,
                default=entry.mode_key == (selected_mode_key or state.active_mode),
            )
        )
    return options[:25]


def _get_entry(state: PersonaPanelState, mode_key: str) -> Optional[PersonaEntry]:
    for entry in state.entries:
        if entry.mode_key == mode_key:
            return entry
    return None


def build_persona_preview_embed(entry: PersonaEntry) -> discord.Embed:
    embed = discord.Embed(
        title=entry.display_name,
        description=entry.bio or entry.description or "No bio provided.",
        color=discord.Color.blurple(),
    )
    embed.add_field(name="Group", value=entry.group_label, inline=True)
    embed.add_field(name="Mode Key", value=f"`{entry.mode_key}`", inline=True)
    embed.add_field(name="Evil Prompt", value="Yes" if entry.evil_prompt else "No", inline=True)
    if entry.aliases:
        embed.add_field(name="Aliases", value=_aliases_text(entry.aliases), inline=False)
    return embed


async def activate_persona_mode(
    *,
    bot,
    guild_id: int,
    user_id: int,
    mode_key: str,
) -> PersonaActivationResult:
    old_mode = await get_server_mode(guild_id)
    custom_persona = await _get_custom_persona_for_mode(guild_id, mode_key)

    if old_mode.startswith("custom_") and not mode_key.startswith("custom_"):
        await set_guild_avatar_path(guild_id, None)

    await set_server_mode(guild_id, mode_key)
    if mode_key == "mode_default":
        await set_evil_mode(guild_id, False)

    await _apply_social_profile(bot, guild_id, mode_key)

    display_name = custom_persona["name"] if custom_persona else get_mode_profile(mode_key).display_name
    await add_guild_config_audit(
        guild_id,
        user_id,
        "persona_activate",
        field="persona_mode",
        old_value=old_mode,
        new_value=mode_key,
        category="persona_presentation",
        target_type="persona",
        target_id=mode_key,
        summary=f"Activated persona: {display_name}",
        detail={"old_mode": old_mode, "new_mode": mode_key, "display_name": display_name},
    )
    return PersonaActivationResult(
        mode_key=mode_key,
        display_name=display_name,
        is_custom=custom_persona is not None,
    )


async def set_persona_evil_mode(
    *,
    bot,
    guild_id: int,
    user_id: int,
    enabled: bool,
) -> PersonaEvilModeResult:
    mode_key = await get_server_mode(guild_id)
    old_enabled = await get_evil_mode(guild_id)
    await set_evil_mode(guild_id, enabled)
    await _apply_social_profile(bot, guild_id, mode_key)
    new_enabled = await get_evil_mode(guild_id)
    await add_guild_config_audit(
        guild_id,
        user_id,
        "persona_toggle_evil",
        field="evil_mode",
        old_value=str(old_enabled).lower(),
        new_value=str(new_enabled).lower(),
        category="persona_presentation",
        target_type="persona",
        target_id=mode_key,
        summary=f"Evil mode {'enabled' if new_enabled else 'disabled'} for {mode_key}",
        detail={"mode_key": mode_key, "enabled": new_enabled},
    )
    return PersonaEvilModeResult(enabled=new_enabled, mode_key=mode_key)


async def create_persona_from_inputs(
    *,
    guild_id: int,
    user_id: int,
    name: str,
    bio: Optional[str],
    aliases: Sequence[str],
    normal_prompt: str,
    evil_prompt: Optional[str],
    base_template: Optional[str] = None,
    voice_tone: Optional[str] = None,
    worldview: Optional[str] = None,
    scene_normal: Optional[str] = None,
    scene_evil: Optional[str] = None,
    examples_normal: Sequence[str] | None = None,
    examples_evil: Sequence[str] | None = None,
    action: str = "persona_create",
) -> str:
    clean_name = (name or "").strip()
    if not clean_name:
        raise ValueError("Persona name is required.")
    if not sanitize_persona_name(clean_name):
        raise ValueError("Persona name must contain letters or numbers.")
    if await get_custom_persona_by_name(guild_id, clean_name):
        raise ValueError("A custom persona with that name already exists.")
    if not (normal_prompt or "").strip():
        raise ValueError("Normal prompt is required.")

    mode_key = build_custom_mode_key(guild_id, clean_name)
    try:
        await create_custom_persona(
            guild_id=guild_id,
            name=clean_name,
            mode_key=mode_key,
            bio=(bio or "").strip() or None,
            avatar_path=None,
            banner_path=None,
            aliases=list(aliases),
            normal_prompt=normal_prompt.strip(),
            evil_prompt=(evil_prompt or "").strip() or None,
            created_by=user_id,
        )
    except sqlite3.IntegrityError as exc:
        raise ValueError("A custom persona with that name already exists.") from exc

    traits = extract_persona_traits(normal_prompt, (evil_prompt or "").strip() or None)
    if traits:
        await upsert_persona_traits(guild_id, mode_key, traits)
    await apply_structured_persona_fields(
        guild_id=guild_id,
        mode_key=mode_key,
        base_template=base_template,
        voice_tone=voice_tone,
        worldview=worldview,
        scene_normal=scene_normal,
        scene_evil=scene_evil,
        examples_normal=examples_normal,
        examples_evil=examples_evil,
    )

    await add_guild_config_audit(
        guild_id,
        user_id,
        action,
        category="persona_crud",
        target_type="persona",
        target_id=mode_key,
        summary=f"Saved custom persona: {clean_name}",
        detail={"mode_key": mode_key, "name": clean_name},
    )
    return mode_key


async def update_persona_details(
    *,
    guild_id: int,
    user_id: int,
    mode_key: str,
    name: str,
    bio: Optional[str],
    aliases: Sequence[str],
) -> None:
    persona = await get_custom_persona_by_mode_key(guild_id, mode_key)
    if not persona:
        raise ValueError("Custom persona not found.")

    clean_name = (name or "").strip()
    if not clean_name:
        raise ValueError("Persona name is required.")

    existing = await get_custom_persona_by_name(guild_id, clean_name)
    if existing and existing.get("mode_key") != mode_key:
        raise ValueError("A custom persona with that name already exists.")

    await update_custom_persona(
        guild_id,
        mode_key,
        name=clean_name,
        bio=(bio or "").strip() or None,
        aliases=list(aliases),
    )
    await add_guild_config_audit(
        guild_id,
        user_id,
        "persona_edit",
        category="persona_crud",
        target_type="persona",
        target_id=mode_key,
        summary=f"Updated persona details: {clean_name}",
        detail={"mode_key": mode_key, "name": clean_name},
    )


async def update_persona_prompts(
    *,
    guild_id: int,
    user_id: int,
    mode_key: str,
    normal_prompt: str,
    evil_prompt: Optional[str],
) -> None:
    if not (normal_prompt or "").strip():
        raise ValueError("Normal prompt is required.")
    persona = await get_custom_persona_by_mode_key(guild_id, mode_key)
    if not persona:
        raise ValueError("Custom persona not found.")

    normalized_evil = (evil_prompt or "").strip() or None
    await update_custom_persona(
        guild_id,
        mode_key,
        normal_prompt=normal_prompt.strip(),
        evil_prompt=normalized_evil,
    )
    traits = extract_persona_traits(normal_prompt.strip(), normalized_evil)
    await upsert_persona_traits(guild_id, mode_key, traits)
    await add_guild_config_audit(
        guild_id,
        user_id,
        "persona_edit",
        category="persona_crud",
        target_type="persona",
        target_id=mode_key,
        summary=f"Updated persona prompts: {persona.get('name', mode_key)}",
        detail={"mode_key": mode_key},
    )


async def duplicate_custom_persona(
    *,
    guild_id: int,
    user_id: int,
    source_mode_key: str,
    new_name: str,
) -> str:
    persona = await get_custom_persona_by_mode_key(guild_id, source_mode_key)
    if not persona:
        raise ValueError("Only custom personas can be duplicated.")
    return await create_persona_from_inputs(
        guild_id=guild_id,
        user_id=user_id,
        name=new_name,
        bio=persona.get("bio"),
        aliases=persona.get("aliases") or [],
        normal_prompt=persona.get("normal_prompt") or "",
        evil_prompt=persona.get("evil_prompt"),
        action="persona_duplicate",
    )


async def delete_persona_with_fallback(
    *,
    bot,
    guild_id: int,
    user_id: int,
    mode_key: str,
) -> bool:
    persona = await get_custom_persona_by_mode_key(guild_id, mode_key)
    if not persona:
        return False

    current_mode = await get_server_mode(guild_id)
    if current_mode == mode_key:
        await set_server_mode(guild_id, "mode_default")
        await set_evil_mode(guild_id, False)
        await set_guild_avatar_path(guild_id, None)
        await _apply_social_profile(bot, guild_id, "mode_default")
        await add_guild_config_audit(
            guild_id,
            user_id,
            "persona_activate",
            field="persona_mode",
            old_value=mode_key,
            new_value="mode_default",
            category="persona_presentation",
            target_type="persona",
            target_id="mode_default",
            summary=f"Deleted active persona; fell back to default from {persona.get('name', mode_key)}",
            detail={"old_mode": mode_key, "new_mode": "mode_default", "reason": "deleted_active_custom_persona"},
        )

    deleted = await delete_custom_persona(guild_id, mode_key)
    if not deleted:
        return False

    await delete_persona_traits(guild_id, mode_key)
    for asset_path in (persona.get("avatar_path"), persona.get("banner_path")):
        if asset_path:
            try:
                Path(asset_path).unlink(missing_ok=True)
            except OSError:
                pass

    await add_guild_config_audit(
        guild_id,
        user_id,
        "persona_delete",
        category="persona_crud",
        target_type="persona",
        target_id=mode_key,
        summary=f"Deleted custom persona: {persona.get('name', mode_key)}",
        detail={"mode_key": mode_key, "name": persona.get("name")},
    )
    return True


class PersonaCreateModal(discord.ui.Modal):
    def __init__(self, view: "PersonaManageView") -> None:
        super().__init__(title="Create Persona")
        self.view = view
        self.name_input = discord.ui.TextInput(label="Name", max_length=32, required=True)
        self.bio_input = discord.ui.TextInput(
            label="Bio",
            style=discord.TextStyle.paragraph,
            max_length=500,
            required=False,
        )
        self.aliases_input = discord.ui.TextInput(
            label="Aliases",
            placeholder="comma, separated, aliases",
            required=False,
        )
        self.normal_prompt_input = discord.ui.TextInput(
            label="Normal prompt",
            style=discord.TextStyle.paragraph,
            max_length=4000,
            required=True,
        )
        self.evil_prompt_input = discord.ui.TextInput(
            label="Evil prompt",
            style=discord.TextStyle.paragraph,
            max_length=4000,
            required=False,
        )
        for item in (
            self.name_input,
            self.bio_input,
            self.aliases_input,
            self.normal_prompt_input,
            self.evil_prompt_input,
        ):
            self.add_item(item)

    async def on_submit(self, interaction: discord.Interaction) -> None:
        if not _require_manage_guild(interaction):
            await interaction.response.send_message("You need Manage Server for this action.", ephemeral=True)
            return
        try:
            mode_key = await create_persona_from_inputs(
                guild_id=self.view.guild_id,
                user_id=interaction.user.id,
                name=str(self.name_input.value or ""),
                bio=str(self.bio_input.value or ""),
                aliases=_parse_aliases(str(self.aliases_input.value or "")),
                normal_prompt=str(self.normal_prompt_input.value or ""),
                evil_prompt=str(self.evil_prompt_input.value or ""),
            )
        except ValueError as exc:
            await interaction.response.send_message(str(exc), ephemeral=True)
            return

        self.view.selected_mode_key = mode_key
        await self.view.refresh_message()
        await interaction.response.send_message(
            f"Custom persona created. {MANAGE_GUIDANCE}",
            ephemeral=True,
        )


class PersonaDetailsModal(discord.ui.Modal):
    def __init__(self, view: "PersonaManageView", entry: PersonaEntry) -> None:
        super().__init__(title=f"Edit Details: {entry.display_name}"[:45])
        self.view = view
        self.entry = entry
        self.name_input = discord.ui.TextInput(label="Name", default=entry.display_name, max_length=32, required=True)
        self.bio_input = discord.ui.TextInput(
            label="Bio",
            style=discord.TextStyle.paragraph,
            default=entry.bio or "",
            max_length=500,
            required=False,
        )
        self.aliases_input = discord.ui.TextInput(
            label="Aliases",
            default=_aliases_text(entry.aliases),
            required=False,
        )
        for item in (self.name_input, self.bio_input, self.aliases_input):
            self.add_item(item)

    async def on_submit(self, interaction: discord.Interaction) -> None:
        if not _require_manage_guild(interaction):
            await interaction.response.send_message("You need Manage Server for this action.", ephemeral=True)
            return
        try:
            await update_persona_details(
                guild_id=self.view.guild_id,
                user_id=interaction.user.id,
                mode_key=self.entry.mode_key,
                name=str(self.name_input.value or ""),
                bio=str(self.bio_input.value or ""),
                aliases=_parse_aliases(str(self.aliases_input.value or "")),
            )
        except ValueError as exc:
            await interaction.response.send_message(str(exc), ephemeral=True)
            return

        await self.view.refresh_message()
        await interaction.response.send_message(
            f"Persona details updated. {MANAGE_GUIDANCE}",
            ephemeral=True,
        )


class PersonaPromptsModal(discord.ui.Modal):
    def __init__(self, view: "PersonaManageView", entry: PersonaEntry) -> None:
        super().__init__(title=f"Edit Prompts: {entry.display_name}"[:45])
        self.view = view
        self.entry = entry
        self.normal_prompt_input = discord.ui.TextInput(
            label="Normal prompt",
            style=discord.TextStyle.paragraph,
            default=entry.normal_prompt or "",
            max_length=4000,
            required=True,
        )
        self.evil_prompt_input = discord.ui.TextInput(
            label="Evil prompt",
            style=discord.TextStyle.paragraph,
            default=entry.evil_prompt or "",
            max_length=4000,
            required=False,
        )
        self.add_item(self.normal_prompt_input)
        self.add_item(self.evil_prompt_input)

    async def on_submit(self, interaction: discord.Interaction) -> None:
        if not _require_manage_guild(interaction):
            await interaction.response.send_message("You need Manage Server for this action.", ephemeral=True)
            return
        try:
            await update_persona_prompts(
                guild_id=self.view.guild_id,
                user_id=interaction.user.id,
                mode_key=self.entry.mode_key,
                normal_prompt=str(self.normal_prompt_input.value or ""),
                evil_prompt=str(self.evil_prompt_input.value or ""),
            )
        except ValueError as exc:
            await interaction.response.send_message(str(exc), ephemeral=True)
            return

        await self.view.refresh_message()
        await interaction.response.send_message(
            f"Persona prompts updated. {MANAGE_GUIDANCE}",
            ephemeral=True,
        )


class PersonaDuplicateModal(discord.ui.Modal):
    def __init__(self, view: "PersonaManageView", entry: PersonaEntry) -> None:
        super().__init__(title=f"Duplicate: {entry.display_name}"[:45])
        self.view = view
        self.entry = entry
        self.name_input = discord.ui.TextInput(
            label="New persona name",
            default=f"{entry.display_name} Copy"[:32],
            max_length=32,
            required=True,
        )
        self.add_item(self.name_input)

    async def on_submit(self, interaction: discord.Interaction) -> None:
        if not _require_manage_guild(interaction):
            await interaction.response.send_message("You need Manage Server for this action.", ephemeral=True)
            return
        try:
            mode_key = await duplicate_custom_persona(
                guild_id=self.view.guild_id,
                user_id=interaction.user.id,
                source_mode_key=self.entry.mode_key,
                new_name=str(self.name_input.value or ""),
            )
        except ValueError as exc:
            await interaction.response.send_message(str(exc), ephemeral=True)
            return

        self.view.selected_mode_key = mode_key
        await self.view.refresh_message()
        await interaction.response.send_message(
            f"Persona duplicated. {MANAGE_GUIDANCE}",
            ephemeral=True,
        )


class PersonaSelect(discord.ui.Select):
    def __init__(self, view: "PersonaManageView") -> None:
        self.manage_view = view
        super().__init__(placeholder="Select persona or presentation mode", min_values=1, max_values=1)

    async def callback(self, interaction: discord.Interaction) -> None:
        self.manage_view.selected_mode_key = self.values[0]
        await self.manage_view.refresh_for_interaction(interaction)


class PersonaManageView(AdminPanelView):
    def __init__(self, *, bot, guild_id: int, invoker_id: int) -> None:
        super().__init__(invoker_id=invoker_id, timeout_message="This persona panel expired. Reopen `/persona manage` to continue.")
        self.bot = bot
        self.guild_id = guild_id
        self.state: PersonaPanelState | None = None
        self.selected_mode_key: Optional[str] = None
        self._pending_delete_mode_key: Optional[str] = None

        self.selector = PersonaSelect(self)
        self.activate_button = discord.ui.Button(label="Activate", style=discord.ButtonStyle.primary, row=1)
        self.activate_button.callback = self.activate_selected
        self.toggle_evil_button = discord.ui.Button(label="Toggle Evil", style=discord.ButtonStyle.secondary, row=1)
        self.toggle_evil_button.callback = self.toggle_evil
        self.preview_button = discord.ui.Button(label="Preview", style=discord.ButtonStyle.secondary, row=1)
        self.preview_button.callback = self.preview_selected
        self.edit_details_button = discord.ui.Button(label="Edit Details", style=discord.ButtonStyle.secondary, row=2)
        self.edit_details_button.callback = self.edit_details
        self.edit_prompts_button = discord.ui.Button(label="Edit Prompts", style=discord.ButtonStyle.secondary, row=2)
        self.edit_prompts_button.callback = self.edit_prompts
        self.create_button = discord.ui.Button(label="Create", style=discord.ButtonStyle.success, row=3)
        self.create_button.callback = self.create_persona
        self.duplicate_button = discord.ui.Button(label="Duplicate", style=discord.ButtonStyle.secondary, row=3)
        self.duplicate_button.callback = self.duplicate_persona
        self.delete_button = discord.ui.Button(label="Delete", style=discord.ButtonStyle.danger, row=3)
        self.delete_button.callback = self.delete_persona

        for item in (
            self.selector,
            self.activate_button,
            self.toggle_evil_button,
            self.preview_button,
            self.edit_details_button,
            self.edit_prompts_button,
            self.create_button,
            self.duplicate_button,
            self.delete_button,
        ):
            self.add_item(item)

    async def load(self) -> None:
        self.state = await load_persona_panel_state(self.guild_id)
        valid_keys = {entry.mode_key for entry in self.state.entries}
        if self.selected_mode_key not in valid_keys:
            self.selected_mode_key = self.state.active_mode if self.state.active_mode in valid_keys else next(iter(valid_keys), None)
        self.selector.options = build_persona_select_options(self.state, selected_mode_key=self.selected_mode_key)

        selected = self.get_selected_entry()
        can_edit = bool(selected and selected.is_custom)
        self.edit_details_button.disabled = not can_edit
        self.edit_prompts_button.disabled = not can_edit
        self.duplicate_button.disabled = not can_edit
        self.delete_button.disabled = not can_edit
        self.activate_button.disabled = not bool(self.selected_mode_key) or self.selected_mode_key == self.state.active_mode
        self.toggle_evil_button.label = "Disable Evil" if self.state.evil_mode_enabled else "Enable Evil"

    def get_selected_entry(self) -> Optional[PersonaEntry]:
        if not self.state or not self.selected_mode_key:
            return None
        return _get_entry(self.state, self.selected_mode_key)

    def build_embed(self) -> discord.Embed:
        assert self.state is not None
        selected = self.get_selected_entry()
        active = _get_entry(self.state, self.state.active_mode)
        embed = discord.Embed(
            title="Persona Manage",
            description="Manage presentation mode, evil-mode state, and custom personas from one panel.",
            color=discord.Color.blue(),
        )
        embed.add_field(
            name="Active",
            value=active.display_name if active else f"`{self.state.active_mode}`",
            inline=True,
        )
        embed.add_field(
            name="Evil Mode",
            value="Enabled" if self.state.evil_mode_enabled else "Disabled",
            inline=True,
        )
        if selected:
            embed.add_field(
                name="Selected",
                value=f"{selected.display_name} ({selected.group_label})",
                inline=False,
            )
            embed.add_field(
                name="Summary",
                value=(selected.bio or selected.description or "No description.")[:500],
                inline=False,
            )
        embed.set_footer(text=MANAGE_GUIDANCE)
        return embed

    async def refresh_message(self) -> None:
        await self.load()
        if self._bound_message is not None:
            await self._bound_message.edit(embed=self.build_embed(), view=self)

    async def refresh_for_interaction(self, interaction: discord.Interaction) -> None:
        await self.load()
        await interaction.response.edit_message(embed=self.build_embed(), view=self)

    async def activate_selected(self, interaction: discord.Interaction) -> None:
        if not _require_manage_guild(interaction):
            await interaction.response.send_message("You need Manage Server for this action.", ephemeral=True)
            return
        if not self.selected_mode_key:
            await interaction.response.send_message("Select a persona first.", ephemeral=True)
            return
        result = await activate_persona_mode(
            bot=self.bot,
            guild_id=self.guild_id,
            user_id=interaction.user.id,
            mode_key=self.selected_mode_key,
        )
        await self.load()
        await interaction.response.edit_message(embed=self.build_embed(), view=self)
        await interaction.followup.send(
            f"Activated **{result.display_name}**. {MANAGE_GUIDANCE}",
            ephemeral=True,
        )

    async def toggle_evil(self, interaction: discord.Interaction) -> None:
        if not _require_manage_guild(interaction):
            await interaction.response.send_message("You need Manage Server for this action.", ephemeral=True)
            return
        assert self.state is not None
        result = await set_persona_evil_mode(
            bot=self.bot,
            guild_id=self.guild_id,
            user_id=interaction.user.id,
            enabled=not self.state.evil_mode_enabled,
        )
        await self.load()
        await interaction.response.edit_message(embed=self.build_embed(), view=self)
        await interaction.followup.send(
            f"Evil mode {'enabled' if result.enabled else 'disabled'}. {MANAGE_GUIDANCE}",
            ephemeral=True,
        )

    async def preview_selected(self, interaction: discord.Interaction) -> None:
        selected = self.get_selected_entry()
        if not selected:
            await interaction.response.send_message("Select a persona first.", ephemeral=True)
            return
        await interaction.response.send_message(embed=build_persona_preview_embed(selected), ephemeral=True)

    async def create_persona(self, interaction: discord.Interaction) -> None:
        if not _require_manage_guild(interaction):
            await interaction.response.send_message("You need Manage Server for this action.", ephemeral=True)
            return
        persona_cog = self.bot.get_cog("Persona") if self.bot else None
        if persona_cog and hasattr(persona_cog, "_open_basic_modal"):
            await persona_cog._open_basic_modal(interaction)
            return
        await interaction.response.send_modal(PersonaCreateModal(self))

    async def edit_details(self, interaction: discord.Interaction) -> None:
        selected = self.get_selected_entry()
        if not selected or not selected.is_custom:
            await interaction.response.send_message("Select a custom persona to edit.", ephemeral=True)
            return
        persona_cog = self.bot.get_cog("Persona") if self.bot else None
        if persona_cog and hasattr(persona_cog, "_open_edit_modal_by_mode_key"):
            await persona_cog._open_edit_modal_by_mode_key(interaction, selected.mode_key)
            return
        await interaction.response.send_modal(PersonaDetailsModal(self, selected))

    async def edit_prompts(self, interaction: discord.Interaction) -> None:
        selected = self.get_selected_entry()
        if not selected or not selected.is_custom:
            await interaction.response.send_message("Select a custom persona to edit.", ephemeral=True)
            return
        await interaction.response.send_modal(PersonaPromptsModal(self, selected))

    async def duplicate_persona(self, interaction: discord.Interaction) -> None:
        selected = self.get_selected_entry()
        if not selected or not selected.is_custom:
            await interaction.response.send_message("Only custom personas can be duplicated.", ephemeral=True)
            return
        await interaction.response.send_modal(PersonaDuplicateModal(self, selected))

    async def delete_persona(self, interaction: discord.Interaction) -> None:
        selected = self.get_selected_entry()
        if not selected or not selected.is_custom:
            await interaction.response.send_message("Only custom personas can be deleted.", ephemeral=True)
            return
        if not _require_manage_guild(interaction):
            await interaction.response.send_message("You need Manage Server for this action.", ephemeral=True)
            return

        self._pending_delete_mode_key = selected.mode_key
        if action_requires_auth("persona_delete"):
            if not await _has_password(self.guild_id):
                await interaction.response.send_message(
                    "Deleting a custom persona requires a config password. Set one first.",
                    ephemeral=True,
                )
                return
            if not await _is_authenticated(self.guild_id, interaction.user.id):
                prompt = AuthPromptView(
                    invoker_id=interaction.user.id,
                    title="Authenticate to delete persona",
                    on_submit=self._handle_delete_auth_submit,
                )
                await interaction.response.send_message(
                    f"Authenticate to delete **{selected.display_name}**.",
                    view=prompt,
                    ephemeral=True,
                )
                return

        await self._perform_delete(interaction)

    async def _handle_delete_auth_submit(self, interaction: discord.Interaction, password: str) -> None:
        if not _require_manage_guild(interaction):
            await interaction.response.send_message("You need Manage Server for this action.", ephemeral=True)
            return
        ok = await _verify_and_create_session(self.guild_id, interaction.user.id, password)
        if not ok:
            await interaction.response.send_message("Authentication failed.", ephemeral=True)
            return
        await self._perform_delete(interaction)

    async def _perform_delete(self, interaction: discord.Interaction) -> None:
        mode_key = self._pending_delete_mode_key or self.selected_mode_key
        if not mode_key:
            await interaction.response.send_message("Select a custom persona first.", ephemeral=True)
            return
        deleted = await delete_persona_with_fallback(
            bot=self.bot,
            guild_id=self.guild_id,
            user_id=interaction.user.id,
            mode_key=mode_key,
        )
        if not deleted:
            await interaction.response.send_message("Failed to delete persona.", ephemeral=True)
            return
        self._pending_delete_mode_key = None
        if self.selected_mode_key == mode_key:
            self.selected_mode_key = "mode_default"
        await self.refresh_message()
        await interaction.response.send_message(
            f"Persona deleted. {MANAGE_GUIDANCE}",
            ephemeral=True,
        )


async def open_persona_manage_panel(interaction: discord.Interaction, *, bot) -> None:
    if not interaction.guild:
        await interaction.response.send_message("Use this command in a server.", ephemeral=True)
        return
    view = PersonaManageView(bot=bot, guild_id=interaction.guild.id, invoker_id=interaction.user.id)
    await view.load()
    await interaction.response.send_message(embed=view.build_embed(), view=view, ephemeral=True)
    try:
        view.bind_message(await interaction.original_response())
    except Exception:
        pass
