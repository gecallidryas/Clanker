from __future__ import annotations

import json
from collections import OrderedDict
from typing import Any, Callable, Mapping, Optional, Sequence

import discord

from utils.admin_panel_support import (
    AUDIT_CATEGORY_CONFIG_DESTRUCTIVE,
    AUDIT_CATEGORY_CONFIG_GENERAL,
    AUDIT_CATEGORY_CONFIG_ROUTING,
    AUDIT_CATEGORY_CONFIG_SECURITY,
    AUDIT_CATEGORY_TOOLS_CONFIG,
    apply_id_list_changes,
    diff_config_values,
    requires_auth_for_action,
)
from utils.admin_panel_views import AdminPanelView, PagedItemEditorView
from utils.api_manager import OPENROUTER_MODELS, normalize_gemini_model, normalize_openrouter_model
from utils.auth import has_password, is_authenticated, verify_and_create_session
from utils.db_handler import (
    add_guild_config_audit,
    add_staff_role,
    get_autorole_config,
    get_dm_welcome_enabled,
    get_guild_config,
    get_mod_log_channel_id,
    get_staff_roles,
    get_url_safety_config,
    get_welcome_config,
    remove_staff_role,
    set_autorole_enabled,
    set_autorole_id,
    set_dm_welcome_enabled,
    set_dm_welcome_message,
    set_mod_log_channel_id,
    set_url_safety_config,
    set_welcome_channel_id,
    set_welcome_enabled,
    set_welcome_message_template,
    update_guild_config,
)
from utils.encryption import get_encryption
from utils.guild_ai import RECOMMENDED_GEMINI_MODELS, RECOMMENDED_OPENROUTER_MODELS
from utils.i18n import get_locale_from_interaction, t
from utils.tool_flags import DEFAULT_FLAG_VALUES


encryption = get_encryption()

CAPABILITY_GROUPS = OrderedDict(
    [
        (
            "AI tools",
            [
                ("web_search_enabled", "Web search"),
                ("image_gen_enabled", "Image generation"),
                ("rag_enabled", "RAG retrieval"),
                ("profile_peek_enabled", "Profile peek"),
            ],
        ),
        (
            "Expression & media",
            [
                ("sticker_usage_enabled", "Sticker usage"),
                ("emoji_usage_enabled", "Emoji usage"),
                ("gif_responses_enabled", "GIF responses"),
                ("youtube_enabled", "YouTube processing"),
            ],
        ),
        (
            "Memory & learning",
            [
                ("self_teaching_enabled", "Self teaching"),
                ("pin_message_enabled", "Pin message"),
            ],
        ),
        (
            "Safety & moderation",
            [
                ("url_safety_enabled", "URL safety"),
            ],
        ),
    ]
)

KEY_FIELDS = OrderedDict(
    [
        ("general", ["gemini_api_key", "gemini_api_key_2", "gemini_api_key_3", "gemini_api_key_4", "gemini_api_key_5"]),
        ("translate", ["gemini_translate_key", "gemini_translate_key_2", "gemini_translate_key_3", "gemini_translate_key_4", "gemini_translate_key_5"]),
        ("summarize", ["gemini_summarize_key", "gemini_summarize_key_2", "gemini_summarize_key_3", "gemini_summarize_key_4", "gemini_summarize_key_5"]),
        ("profile", ["gemini_profile_key"]),
        ("uncensored", ["openrouter_api_key", "openrouter_api_key_2", "openrouter_api_key_3", "openrouter_api_key_4", "openrouter_api_key_5"]),
    ]
)

MODEL_FIELDS = OrderedDict(
    [
        ("general", "gemini_model"),
        ("translate", "gemini_translate_model"),
        ("summarize", "gemini_summarize_model"),
        ("uncensored", "openrouter_model"),
    ]
)

COOLDOWN_TYPES = ["off", "per_user", "per_channel", "server_wide", "strict_server_wide"]
THOUGHT_LOG_LEVELS = ["off", "summary", "raw_debug"]
URL_SAFETY_ACTIONS = ["warn", "delete"]


def _mask_secret(value: Optional[str]) -> str:
    if not value:
        return "Not set"
    try:
        decrypted = encryption.decrypt(value)
    except Exception:
        return "Stored"
    return encryption.mask_key(decrypted)


def _parse_json_id_list(raw: Optional[str]) -> list[int]:
    if not raw:
        return []
    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        return []
    if not isinstance(data, list):
        return []
    parsed: list[int] = []
    for item in data:
        try:
            parsed.append(int(item))
        except (TypeError, ValueError):
            continue
    return list(dict.fromkeys(parsed))


def _dump_json_id_list(values: Sequence[int]) -> Optional[str]:
    if not values:
        return None
    return json.dumps([int(value) for value in values])


def _channel_label(guild: discord.Guild, channel_id: int) -> str:
    channel = guild.get_channel(channel_id)
    if channel is not None:
        return f"#{channel.name} ({channel.id})"
    return f"Unknown channel ({channel_id})"


def _role_label(guild: discord.Guild, role_id: int) -> str:
    role = guild.get_role(role_id)
    if role is not None:
        return f"{role.name} ({role.id})"
    return f"Unknown role ({role_id})"


def _require_manage_guild(interaction: discord.Interaction) -> bool:
    permissions = getattr(interaction.user, "guild_permissions", None)
    return bool(permissions and permissions.manage_guild)


def _require_administrator(interaction: discord.Interaction) -> bool:
    permissions = getattr(interaction.user, "guild_permissions", None)
    return bool(permissions and permissions.administrator)


async def _ensure_low_risk_permissions(interaction: discord.Interaction) -> bool:
    if _require_manage_guild(interaction):
        return True
    await interaction.response.send_message("You need Manage Server for this action.", ephemeral=True)
    return False


async def _maybe_send_auth_modal(
    interaction: discord.Interaction,
    *,
    action_key: str,
    next_modal_factory: Callable[[], discord.ui.Modal] | None = None,
) -> bool:
    if not requires_auth_for_action(action_key):
        return True
    if not _require_administrator(interaction):
        await interaction.response.send_message("You need Administrator for this high-risk action.", ephemeral=True)
        return False
    if not await has_password(interaction.guild.id):
        await interaction.response.send_message(
            "This action requires a config password. Use `/config password set` first.",
            ephemeral=True,
        )
        return False
    if await is_authenticated(interaction.guild.id, interaction.user.id):
        return True
    await interaction.response.send_modal(
        _ConfigPasswordModal(
            guild_id=interaction.guild.id,
            user_id=interaction.user.id,
            next_modal_factory=next_modal_factory,
        )
    )
    return False


async def _audit_bulk_toggle_save(guild_id: int, user_id: int, diff: Mapping[str, tuple[Any, Any]]) -> None:
    await add_guild_config_audit(
        guild_id,
        user_id,
        "tool_flags_save",
        category=AUDIT_CATEGORY_TOOLS_CONFIG,
        summary=f"Updated {len(diff)} capability flag(s).",
        detail={key: {"old": old, "new": new} for key, (old, new) in diff.items()},
    )


async def _send_panel_message(
    interaction: discord.Interaction,
    *,
    embed: discord.Embed,
    view: AdminPanelView,
) -> None:
    await interaction.response.send_message(embed=embed, view=view, ephemeral=True)
    try:
        view.bind_message(await interaction.original_response())
    except Exception:
        pass


async def _swap_panel(
    interaction: discord.Interaction,
    *,
    embed: discord.Embed,
    view: AdminPanelView,
    previous: AdminPanelView,
) -> None:
    view.bind_message(getattr(previous, "_message", None))
    await interaction.response.edit_message(embed=embed, view=view)


class _ConfigPasswordModal(discord.ui.Modal):
    def __init__(
        self,
        *,
        guild_id: int,
        user_id: int,
        next_modal_factory: Callable[[], discord.ui.Modal] | None = None,
    ) -> None:
        super().__init__(title="Authenticate")
        self.guild_id = guild_id
        self.user_id = user_id
        self.next_modal_factory = next_modal_factory
        self.password = discord.ui.TextInput(
            label="Config password",
            style=discord.TextStyle.short,
            required=True,
        )
        self.add_item(self.password)

    async def on_submit(self, interaction: discord.Interaction) -> None:
        ok = await verify_and_create_session(
            self.guild_id,
            self.user_id,
            self.password.value,
        )
        if not ok:
            await interaction.response.send_message("Authentication failed.", ephemeral=True)
            return
        if self.next_modal_factory is not None:
            await interaction.response.send_modal(self.next_modal_factory())
            return
        await interaction.response.send_message(
            "Authenticated. Continue in the open panel.",
            ephemeral=True,
        )


class _BackButton(discord.ui.Button):
    def __init__(self, callback: Callable[[discord.Interaction], Any]) -> None:
        super().__init__(label="Back", style=discord.ButtonStyle.secondary, row=4)
        self._callback = callback

    async def callback(self, interaction: discord.Interaction) -> None:  # type: ignore[override]
        await self._callback(interaction)


class _CapabilitySelect(discord.ui.Select):
    def __init__(self, parent: "CapabilityEditorView") -> None:
        self.parent_view = parent
        super().__init__(
            placeholder="Select flags on this page",
            min_values=1,
            max_values=1,
            options=[discord.SelectOption(label="Loading", value="loading")],
        )

    async def callback(self, interaction: discord.Interaction) -> None:
        self.parent_view.selected_fields = list(self.values)
        await interaction.response.edit_message(view=self.parent_view)


class ConfigPanelHomeView(AdminPanelView):
    def __init__(self, *, guild_id: int, user_id: int, locale: str) -> None:
        super().__init__(user_id=user_id, timeout=300)
        self.guild_id = guild_id
        self.locale = locale

    async def build_embed(self) -> discord.Embed:
        config = await get_guild_config(self.guild_id)
        whitelist = _parse_json_id_list(config.get("ai_channel_whitelist"))
        auto_channels = _parse_json_id_list(config.get("ai_auto_channels"))
        embed = discord.Embed(
            title="Config Panel",
            description=(
                "Primary admin surface for guild configuration.\n"
                "Use the buttons below to manage capabilities, AI behavior, providers, and server routing."
            ),
            color=discord.Color.blurple(),
        )
        embed.add_field(name="Capabilities", value="Bulk toggle tools and feature flags.", inline=False)
        embed.add_field(
            name="AI settings",
            value=f"Whitelist: {len(whitelist)} channel(s)\nAuto channels: {len(auto_channels)}",
            inline=False,
        )
        embed.add_field(name="Providers", value="Secrets, models, and custom endpoint routing.", inline=False)
        embed.add_field(name="Server settings", value="Welcome, autorole, modlog, staff, and URL safety.", inline=False)
        return embed

    @discord.ui.button(label="Capabilities", style=discord.ButtonStyle.primary, row=0)
    async def open_capabilities(self, interaction: discord.Interaction, button: discord.ui.Button) -> None:
        if not await _ensure_low_risk_permissions(interaction):
            return
        view = CapabilityEditorView(guild_id=self.guild_id, user_id=self.user_id, locale=self.locale, home_view=self)
        await _swap_panel(interaction, embed=await view.build_embed(), view=view, previous=self)

    @discord.ui.button(label="AI Settings", style=discord.ButtonStyle.primary, row=0)
    async def open_ai(self, interaction: discord.Interaction, button: discord.ui.Button) -> None:
        if not await _ensure_low_risk_permissions(interaction):
            return
        view = AISettingsHomeView(guild_id=self.guild_id, user_id=self.user_id, locale=self.locale, home_view=self)
        await _swap_panel(interaction, embed=await view.build_embed(), view=view, previous=self)

    @discord.ui.button(label="Providers", style=discord.ButtonStyle.primary, row=1)
    async def open_providers(self, interaction: discord.Interaction, button: discord.ui.Button) -> None:
        if not await _ensure_low_risk_permissions(interaction):
            return
        view = ProvidersHomeView(guild_id=self.guild_id, user_id=self.user_id, locale=self.locale, home_view=self)
        await _swap_panel(interaction, embed=await view.build_embed(), view=view, previous=self)

    @discord.ui.button(label="Server Settings", style=discord.ButtonStyle.primary, row=1)
    async def open_server_settings(self, interaction: discord.Interaction, button: discord.ui.Button) -> None:
        if not await _ensure_low_risk_permissions(interaction):
            return
        view = ServerSettingsHomeView(guild_id=self.guild_id, user_id=self.user_id, locale=self.locale, home_view=self)
        await _swap_panel(interaction, embed=await view.build_embed(), view=view, previous=self)


class CapabilityEditorView(AdminPanelView):
    def __init__(
        self,
        *,
        guild_id: int,
        user_id: int,
        locale: str,
        home_view: ConfigPanelHomeView,
    ) -> None:
        super().__init__(user_id=user_id, timeout=300)
        self.guild_id = guild_id
        self.locale = locale
        self.home_view = home_view
        self.group_names = list(CAPABILITY_GROUPS.keys())
        self.group_index = 0
        self.selected_fields: list[str] = []
        self.current_values: dict[str, int] = {}
        self.draft_values: dict[str, int] = {}
        self.toggle_select = _CapabilitySelect(self)
        self.add_item(self.toggle_select)
        self.add_item(_BackButton(self._go_back))

    async def _ensure_state(self) -> None:
        if self.current_values:
            return
        config = await get_guild_config(self.guild_id)
        for group in CAPABILITY_GROUPS.values():
            for field, _label in group:
                current = config.get(field)
                if current is None:
                    current = DEFAULT_FLAG_VALUES.get(field, 1)
                self.current_values[field] = int(current)
        self.draft_values = dict(self.current_values)
        self._refresh_select()

    def _current_group_entries(self) -> list[tuple[str, str]]:
        return list(CAPABILITY_GROUPS[self.group_names[self.group_index]])

    def _refresh_select(self) -> None:
        entries = self._current_group_entries()
        self.toggle_select.options = [
            discord.SelectOption(
                label=f"{label} [{'ON' if self.draft_values.get(field, 0) else 'OFF'}]",
                value=field,
                default=field in self.selected_fields,
            )
            for field, label in entries
        ]
        self.toggle_select.max_values = len(entries)

    async def build_embed(self) -> discord.Embed:
        await self._ensure_state()
        group_name = self.group_names[self.group_index]
        lines = []
        for field, label in self._current_group_entries():
            state = "ON" if self.draft_values.get(field, 0) else "OFF"
            changed = self.current_values.get(field) != self.draft_values.get(field)
            marker = " *" if changed else ""
            lines.append(f"- {label}: **{state}**{marker}")
        changed_count = sum(1 for key, value in self.draft_values.items() if self.current_values.get(key) != value)
        embed = discord.Embed(
            title=f"Capabilities: {group_name}",
            description="\n".join(lines),
            color=discord.Color.blue(),
        )
        embed.set_footer(text=f"Group {self.group_index + 1}/{len(self.group_names)} | Unsaved changes: {changed_count}")
        return embed

    async def _go_back(self, interaction: discord.Interaction) -> None:
        await _swap_panel(interaction, embed=await self.home_view.build_embed(), view=self.home_view, previous=self)

    @discord.ui.button(label="Toggle Selected", style=discord.ButtonStyle.primary, row=1)
    async def toggle_selected_button(self, interaction: discord.Interaction, button: discord.ui.Button) -> None:
        await self._ensure_state()
        for field in self.selected_fields:
            self.draft_values[field] = 0 if self.draft_values.get(field, 0) else 1
        self._refresh_select()
        await interaction.response.edit_message(embed=await self.build_embed(), view=self)

    @discord.ui.button(label="Previous Group", style=discord.ButtonStyle.secondary, row=1)
    async def previous_group_button(self, interaction: discord.Interaction, button: discord.ui.Button) -> None:
        await self._ensure_state()
        self.group_index = (self.group_index - 1) % len(self.group_names)
        self.selected_fields = []
        self._refresh_select()
        await interaction.response.edit_message(embed=await self.build_embed(), view=self)

    @discord.ui.button(label="Next Group", style=discord.ButtonStyle.secondary, row=1)
    async def next_group_button(self, interaction: discord.Interaction, button: discord.ui.Button) -> None:
        await self._ensure_state()
        self.group_index = (self.group_index + 1) % len(self.group_names)
        self.selected_fields = []
        self._refresh_select()
        await interaction.response.edit_message(embed=await self.build_embed(), view=self)

    @discord.ui.button(label="Reset Defaults", style=discord.ButtonStyle.secondary, row=2)
    async def reset_defaults_button(self, interaction: discord.Interaction, button: discord.ui.Button) -> None:
        await self._ensure_state()
        for field, _label in self._current_group_entries():
            self.draft_values[field] = int(DEFAULT_FLAG_VALUES.get(field, 1))
        self.selected_fields = []
        self._refresh_select()
        await interaction.response.edit_message(embed=await self.build_embed(), view=self)

    @discord.ui.button(label="Save", style=discord.ButtonStyle.success, row=2)
    async def save_button(self, interaction: discord.Interaction, button: discord.ui.Button) -> None:
        await self._ensure_state()
        diff = diff_config_values(self.current_values, self.draft_values, keys=self.draft_values.keys())
        if not diff:
            await interaction.response.send_message("No capability changes to save.", ephemeral=True)
            return
        if not await _ensure_low_risk_permissions(interaction):
            return
        await update_guild_config(self.guild_id, {key: new for key, (_old, new) in diff.items()})
        await _audit_bulk_toggle_save(self.guild_id, interaction.user.id, diff)
        self.current_values = dict(self.draft_values)
        self._refresh_select()
        await interaction.response.edit_message(
            embed=await self.build_embed(),
            view=self,
        )

    @discord.ui.button(label="Cancel", style=discord.ButtonStyle.secondary, row=2)
    async def cancel_button(self, interaction: discord.Interaction, button: discord.ui.Button) -> None:
        await self._ensure_state()
        self.draft_values = dict(self.current_values)
        self.selected_fields = []
        self._refresh_select()
        await interaction.response.edit_message(embed=await self.build_embed(), view=self)


class AIScalarsModal(discord.ui.Modal):
    def __init__(self, *, guild_id: int) -> None:
        super().__init__(title="AI Scalars")
        self.guild_id = guild_id
        self.cooldown = discord.ui.TextInput(label="Cooldown seconds", required=False, placeholder="0-3600")
        self.cooldown_type = discord.ui.TextInput(label="Cooldown scope", required=False, placeholder="off, per_user, per_channel, server_wide")
        self.self_reply_limit = discord.ui.TextInput(label="Self reply limit", required=False, placeholder="1-20")
        self.auto_threshold = discord.ui.TextInput(label="Auto-channel threshold", required=False, placeholder="0-20")
        self.add_item(self.cooldown)
        self.add_item(self.cooldown_type)
        self.add_item(self.self_reply_limit)
        self.add_item(self.auto_threshold)

    async def on_submit(self, interaction: discord.Interaction) -> None:
        updates: dict[str, Any] = {}
        if self.cooldown.value.strip():
            cooldown = int(self.cooldown.value.strip())
            if cooldown < 0 or cooldown > 3600:
                await interaction.response.send_message("Cooldown must be between 0 and 3600.", ephemeral=True)
                return
            updates["ai_reply_cooldown_seconds"] = cooldown
        if self.cooldown_type.value.strip():
            scope = self.cooldown_type.value.strip().lower()
            if scope not in COOLDOWN_TYPES:
                await interaction.response.send_message("Invalid cooldown scope.", ephemeral=True)
                return
            updates["ai_reply_cooldown_type"] = scope
        if self.self_reply_limit.value.strip():
            limit = int(self.self_reply_limit.value.strip())
            if limit < 1 or limit > 20:
                await interaction.response.send_message("Self reply limit must be between 1 and 20.", ephemeral=True)
                return
            updates["ai_self_reply_limit"] = limit
        if self.auto_threshold.value.strip():
            threshold = int(self.auto_threshold.value.strip())
            if threshold < 0 or threshold > 20:
                await interaction.response.send_message("Auto-channel threshold must be between 0 and 20.", ephemeral=True)
                return
            updates["ai_auto_threshold"] = threshold
        if not updates:
            await interaction.response.send_message("No AI scalar changes submitted.", ephemeral=True)
            return
        await update_guild_config(self.guild_id, updates)
        await add_guild_config_audit(
            self.guild_id,
            interaction.user.id,
            "ai_scalar_update",
            category=AUDIT_CATEGORY_CONFIG_GENERAL,
            summary="Updated AI scalar settings.",
            detail=updates,
        )
        await interaction.response.send_message("AI scalar settings updated.", ephemeral=True)


class StreamBudgetModal(discord.ui.Modal):
    def __init__(self, *, guild_id: int) -> None:
        super().__init__(title="Streaming Budget")
        self.guild_id = guild_id
        self.min_flush_chars = discord.ui.TextInput(label="Min flush chars", required=False, placeholder="20-1000")
        self.stall_seconds = discord.ui.TextInput(label="Stall seconds", required=False, placeholder="1-30")
        self.min_interval_seconds = discord.ui.TextInput(label="Min interval seconds", required=False, placeholder="0-10")
        self.max_messages = discord.ui.TextInput(label="Max messages", required=False, placeholder="1-20")
        self.max_total_chars = discord.ui.TextInput(label="Max total chars", required=False, placeholder="500-20000")
        self.add_item(self.min_flush_chars)
        self.add_item(self.stall_seconds)
        self.add_item(self.min_interval_seconds)
        self.add_item(self.max_messages)
        self.add_item(self.max_total_chars)

    async def on_submit(self, interaction: discord.Interaction) -> None:
        updates: dict[str, Any] = {}
        if self.min_flush_chars.value.strip():
            value = int(self.min_flush_chars.value.strip())
            if not 20 <= value <= 1000:
                await interaction.response.send_message("Min flush chars must be between 20 and 1000.", ephemeral=True)
                return
            updates["ai_stream_min_flush_chars"] = value
        if self.stall_seconds.value.strip():
            value = float(self.stall_seconds.value.strip())
            if not 1 <= value <= 30:
                await interaction.response.send_message("Stall seconds must be between 1 and 30.", ephemeral=True)
                return
            updates["ai_stream_stall_seconds"] = value
        if self.min_interval_seconds.value.strip():
            value = float(self.min_interval_seconds.value.strip())
            if not 0 <= value <= 10:
                await interaction.response.send_message("Min interval seconds must be between 0 and 10.", ephemeral=True)
                return
            updates["ai_stream_min_interval_seconds"] = value
        if self.max_messages.value.strip():
            value = int(self.max_messages.value.strip())
            if not 1 <= value <= 20:
                await interaction.response.send_message("Max messages must be between 1 and 20.", ephemeral=True)
                return
            updates["ai_stream_max_messages"] = value
        if self.max_total_chars.value.strip():
            value = int(self.max_total_chars.value.strip())
            if not 500 <= value <= 20000:
                await interaction.response.send_message("Max total chars must be between 500 and 20000.", ephemeral=True)
                return
            updates["ai_stream_max_total_chars"] = value
        if not updates:
            await interaction.response.send_message("No streaming budget changes submitted.", ephemeral=True)
            return
        await update_guild_config(self.guild_id, updates)
        await add_guild_config_audit(
            self.guild_id,
            interaction.user.id,
            "stream_budget_update",
            category=AUDIT_CATEGORY_CONFIG_GENERAL,
            summary="Updated streaming budget.",
            detail=updates,
        )
        await interaction.response.send_message("Streaming budget updated.", ephemeral=True)


class _AddChannelSelect(discord.ui.ChannelSelect):
    def __init__(self, parent: "ChannelListPanelView") -> None:
        self.parent_view = parent
        super().__init__(
            placeholder="Add channels",
            min_values=1,
            max_values=10,
            channel_types=[discord.ChannelType.text],
            row=0,
        )

    async def callback(self, interaction: discord.Interaction) -> None:
        action_key = f"{self.parent_view.field_name}_add"
        if not await self.parent_view._ensure_auth(interaction, action_key=action_key):
            return
        current = [int(item) for item in self.parent_view.items]
        additions = [int(channel.id) for channel in self.values]
        updated = apply_id_list_changes(current, add=additions)
        await update_guild_config(self.parent_view.guild_id, {self.parent_view.field_name: _dump_json_id_list(updated)})
        self.parent_view.items = [str(item) for item in updated]
        self.parent_view._rebuild()
        await add_guild_config_audit(
            self.parent_view.guild_id,
            interaction.user.id,
            f"{self.parent_view.field_name}_add",
            category=self.parent_view.audit_category,
            summary=f"Added {len(additions)} channel(s) to {self.parent_view.field_name}.",
            detail={"added": additions},
        )
        await interaction.response.edit_message(embed=await self.parent_view.build_embed(), view=self.parent_view)


class ChannelListPanelView(PagedItemEditorView):
    def __init__(
        self,
        *,
        guild_id: int,
        user_id: int,
        locale: str,
        home_view: AdminPanelView,
        field_name: str,
        title: str,
        audit_category: str,
        require_auth: bool,
    ) -> None:
        self.guild_id = guild_id
        self.locale = locale
        self.home_view = home_view
        self.field_name = field_name
        self.title = title
        self.audit_category = audit_category
        self.require_auth = require_auth
        super().__init__(
            user_id=user_id,
            items=[],
            page_size=10,
            on_remove=self._apply_remove,
            on_clear=self._apply_clear,
            auth_checker=self._auth_checker,
            remove_requires_auth=require_auth,
            clear_requires_auth=require_auth,
            auth_required_message="Authentication required before changing this list.",
        )
        self.add_item(_AddChannelSelect(self))
        self.add_item(_BackButton(self._go_back))

    async def _auth_checker(self) -> bool:
        return await is_authenticated(self.guild_id, self.user_id)

    async def _ensure_auth(self, interaction: discord.Interaction, *, action_key: str) -> bool:
        if not self.require_auth:
            return True
        return await _maybe_send_auth_modal(interaction, action_key=action_key)

    async def load_items(self) -> None:
        config = await get_guild_config(self.guild_id)
        raw = _parse_json_id_list(config.get(self.field_name))
        self.items = [str(item) for item in raw]
        self._rebuild()

    async def build_embed(self) -> discord.Embed:
        await self.load_items()
        lines = [_channel_label(self.home_view._message.guild if getattr(self.home_view._message, "guild", None) else None, 0)] if False else []
        guild = getattr(self.home_view, "guild", None)
        embed = discord.Embed(title=self.title, color=discord.Color.blue())
        if not self.items:
            embed.description = "No channels configured."
        else:
            guild_obj = getattr(self.home_view, "guild_obj", None)
            if guild_obj is None and hasattr(self.home_view, "guild_id"):
                guild_obj = None
            labels = []
            source_guild = None
            if getattr(self._message, "guild", None) is not None:
                source_guild = self._message.guild
            for item in self._page_slice():
                labels.append(_channel_label(source_guild, int(item)) if source_guild else f"Channel {item}")
            embed.description = "\n".join(f"- {label}" for label in labels)
        embed.set_footer(text=f"Page {self.page}/{paginate_sequence(self.items, page=self.page, page_size=self.page_size).total_pages}")
        return embed

    async def _go_back(self, interaction: discord.Interaction) -> None:
        await _swap_panel(interaction, embed=await self.home_view.build_embed(), view=self.home_view, previous=self)

    async def _apply_remove(self, values: list[str]) -> None:
        current = [int(item) for item in self.items]
        updated = apply_id_list_changes(current, remove=[int(value) for value in values])
        await update_guild_config(self.guild_id, {self.field_name: _dump_json_id_list(updated)})
        self.items = [str(item) for item in updated]

    async def _apply_clear(self) -> None:
        await update_guild_config(self.guild_id, {self.field_name: None})
        self.items = []


class AISettingsHomeView(AdminPanelView):
    def __init__(self, *, guild_id: int, user_id: int, locale: str, home_view: ConfigPanelHomeView) -> None:
        super().__init__(user_id=user_id, timeout=300)
        self.guild_id = guild_id
        self.locale = locale
        self.home_view = home_view
        self.add_item(_BackButton(self._go_back))

    async def _go_back(self, interaction: discord.Interaction) -> None:
        await _swap_panel(interaction, embed=await self.home_view.build_embed(), view=self.home_view, previous=self)

    async def build_embed(self) -> discord.Embed:
        config = await get_guild_config(self.guild_id)
        whitelist = _parse_json_id_list(config.get("ai_channel_whitelist"))
        auto_channels = _parse_json_id_list(config.get("ai_auto_channels"))
        embed = discord.Embed(title="AI Settings", color=discord.Color.blue())
        embed.add_field(name="Cooldown", value=f"{config.get('ai_reply_cooldown_seconds') or 0}s / {config.get('ai_reply_cooldown_type') or 'per_user'}", inline=False)
        embed.add_field(name="Self reply limit", value=str(config.get("ai_self_reply_limit") or 3), inline=True)
        embed.add_field(name="Auto threshold", value=str(config.get("ai_auto_threshold") or 0), inline=True)
        embed.add_field(name="Whitelist channels", value=str(len(whitelist)), inline=True)
        embed.add_field(name="Auto channels", value=str(len(auto_channels)), inline=True)
        embed.add_field(name="Streaming", value="Enabled" if config.get("ai_streaming_enabled", 1) else "Disabled", inline=True)
        embed.add_field(name="Thought log", value=str(config.get("ai_thought_log_level") or "off"), inline=True)
        return embed

    @discord.ui.button(label="Scalars", style=discord.ButtonStyle.primary, row=0)
    async def scalars_button(self, interaction: discord.Interaction, button: discord.ui.Button) -> None:
        if not await _ensure_low_risk_permissions(interaction):
            return
        await interaction.response.send_modal(AIScalarsModal(guild_id=self.guild_id))

    @discord.ui.button(label="Whitelist", style=discord.ButtonStyle.primary, row=1)
    async def whitelist_button(self, interaction: discord.Interaction, button: discord.ui.Button) -> None:
        if not await _ensure_low_risk_permissions(interaction):
            return
        view = ChannelListPanelView(
            guild_id=self.guild_id,
            user_id=self.user_id,
            locale=self.locale,
            home_view=self,
            field_name="ai_channel_whitelist",
            title="AI Channel Whitelist",
            audit_category=AUDIT_CATEGORY_CONFIG_SECURITY,
            require_auth=True,
        )
        await _swap_panel(interaction, embed=await view.build_embed(), view=view, previous=self)

    @discord.ui.button(label="Auto Channels", style=discord.ButtonStyle.primary, row=1)
    async def auto_channels_button(self, interaction: discord.Interaction, button: discord.ui.Button) -> None:
        if not await _ensure_low_risk_permissions(interaction):
            return
        view = ChannelListPanelView(
            guild_id=self.guild_id,
            user_id=self.user_id,
            locale=self.locale,
            home_view=self,
            field_name="ai_auto_channels",
            title="AI Auto Channels",
            audit_category=AUDIT_CATEGORY_CONFIG_ROUTING,
            require_auth=False,
        )
        await _swap_panel(interaction, embed=await view.build_embed(), view=view, previous=self)

    @discord.ui.button(label="Streaming", style=discord.ButtonStyle.primary, row=2)
    async def streaming_button(self, interaction: discord.Interaction, button: discord.ui.Button) -> None:
        if not await _ensure_low_risk_permissions(interaction):
            return
        view = StreamingSettingsView(guild_id=self.guild_id, user_id=self.user_id, locale=self.locale, home_view=self)
        await _swap_panel(interaction, embed=await view.build_embed(), view=view, previous=self)

    @discord.ui.button(label="Thought Logs", style=discord.ButtonStyle.primary, row=2)
    async def thought_logs_button(self, interaction: discord.Interaction, button: discord.ui.Button) -> None:
        if not await _ensure_low_risk_permissions(interaction):
            return
        view = ThoughtLogSettingsView(guild_id=self.guild_id, user_id=self.user_id, locale=self.locale, home_view=self)
        await _swap_panel(interaction, embed=await view.build_embed(), view=view, previous=self)

class StreamingSettingsView(AdminPanelView):
    def __init__(self, *, guild_id: int, user_id: int, locale: str, home_view: AISettingsHomeView) -> None:
        super().__init__(user_id=user_id, timeout=300)
        self.guild_id = guild_id
        self.locale = locale
        self.home_view = home_view
        self.add_item(_BackButton(self._go_back))

    async def _go_back(self, interaction: discord.Interaction) -> None:
        await _swap_panel(interaction, embed=await self.home_view.build_embed(), view=self.home_view, previous=self)

    async def build_embed(self) -> discord.Embed:
        config = await get_guild_config(self.guild_id)
        embed = discord.Embed(title="Streaming Settings", color=discord.Color.blue())
        embed.add_field(name="Enabled", value="Yes" if config.get("ai_streaming_enabled", 1) else "No", inline=True)
        embed.add_field(name="Min flush chars", value=str(config.get("ai_stream_min_flush_chars") or 120), inline=True)
        embed.add_field(name="Stall seconds", value=str(config.get("ai_stream_stall_seconds") or 2.0), inline=True)
        embed.add_field(name="Min interval", value=str(config.get("ai_stream_min_interval_seconds") or 1.0), inline=True)
        embed.add_field(name="Max messages", value=str(config.get("ai_stream_max_messages") or 6), inline=True)
        embed.add_field(name="Max total chars", value=str(config.get("ai_stream_max_total_chars") or 6000), inline=True)
        return embed

    @discord.ui.button(label="Toggle Streaming", style=discord.ButtonStyle.primary, row=0)
    async def toggle_streaming(self, interaction: discord.Interaction, button: discord.ui.Button) -> None:
        config = await get_guild_config(self.guild_id)
        enabled = not bool(config.get("ai_streaming_enabled", 1))
        await update_guild_config(self.guild_id, {"ai_streaming_enabled": int(enabled)})
        await add_guild_config_audit(
            self.guild_id,
            interaction.user.id,
            "ai_streaming_toggle",
            category=AUDIT_CATEGORY_CONFIG_GENERAL,
            detail={"ai_streaming_enabled": int(enabled)},
        )
        await interaction.response.edit_message(embed=await self.build_embed(), view=self)

    @discord.ui.button(label="Edit Budget", style=discord.ButtonStyle.primary, row=0)
    async def edit_budget(self, interaction: discord.Interaction, button: discord.ui.Button) -> None:
        await interaction.response.send_modal(StreamBudgetModal(guild_id=self.guild_id))


class _ThoughtLevelSelect(discord.ui.Select):
    def __init__(self, parent: "ThoughtLogSettingsView") -> None:
        self.parent_view = parent
        super().__init__(
            placeholder="Thought log level",
            min_values=1,
            max_values=1,
            options=[discord.SelectOption(label=level, value=level) for level in THOUGHT_LOG_LEVELS],
            row=1,
        )

    async def callback(self, interaction: discord.Interaction) -> None:
        level = self.values[0]
        await update_guild_config(self.parent_view.guild_id, {"ai_thought_log_level": level})
        await add_guild_config_audit(
            self.parent_view.guild_id,
            interaction.user.id,
            "ai_thought_log_level_update",
            category=AUDIT_CATEGORY_CONFIG_GENERAL,
            detail={"ai_thought_log_level": level},
        )
        await interaction.response.edit_message(embed=await self.parent_view.build_embed(), view=self.parent_view)


class _ThoughtChannelSelect(discord.ui.ChannelSelect):
    def __init__(self, parent: "ThoughtLogSettingsView") -> None:
        self.parent_view = parent
        super().__init__(
            placeholder="Set thought-log channel",
            min_values=1,
            max_values=1,
            channel_types=[discord.ChannelType.text],
            row=0,
        )

    async def callback(self, interaction: discord.Interaction) -> None:
        channel = self.values[0]
        await update_guild_config(self.parent_view.guild_id, {"ai_thought_channel_id": int(channel.id)})
        await add_guild_config_audit(
            self.parent_view.guild_id,
            interaction.user.id,
            "ai_thought_channel_update",
            category=AUDIT_CATEGORY_CONFIG_GENERAL,
            detail={"ai_thought_channel_id": int(channel.id)},
        )
        await interaction.response.edit_message(embed=await self.parent_view.build_embed(), view=self.parent_view)


class ThoughtLogSettingsView(AdminPanelView):
    def __init__(self, *, guild_id: int, user_id: int, locale: str, home_view: AISettingsHomeView) -> None:
        super().__init__(user_id=user_id, timeout=300)
        self.guild_id = guild_id
        self.locale = locale
        self.home_view = home_view
        self.add_item(_ThoughtChannelSelect(self))
        self.add_item(_ThoughtLevelSelect(self))
        self.add_item(_BackButton(self._go_back))

    async def _go_back(self, interaction: discord.Interaction) -> None:
        await _swap_panel(interaction, embed=await self.home_view.build_embed(), view=self.home_view, previous=self)

    async def build_embed(self) -> discord.Embed:
        config = await get_guild_config(self.guild_id)
        embed = discord.Embed(title="Thought Logs", color=discord.Color.blue())
        channel_id = config.get("ai_thought_channel_id")
        embed.add_field(name="Channel", value=f"<#{channel_id}>" if channel_id else "Not set", inline=True)
        embed.add_field(name="Level", value=str(config.get("ai_thought_log_level") or "off"), inline=True)
        embed.add_field(
            name="Reuse modlog",
            value="Yes" if config.get("ai_thought_log_allow_mod_log") else "No",
            inline=True,
        )
        return embed

    @discord.ui.button(label="Toggle Modlog Reuse", style=discord.ButtonStyle.primary, row=2)
    async def toggle_modlog_reuse(self, interaction: discord.Interaction, button: discord.ui.Button) -> None:
        config = await get_guild_config(self.guild_id)
        enabled = not bool(config.get("ai_thought_log_allow_mod_log") or 0)
        await update_guild_config(self.guild_id, {"ai_thought_log_allow_mod_log": int(enabled)})
        await add_guild_config_audit(
            self.guild_id,
            interaction.user.id,
            "ai_thought_modlog_toggle",
            category=AUDIT_CATEGORY_CONFIG_GENERAL,
            detail={"ai_thought_log_allow_mod_log": int(enabled)},
        )
        await interaction.response.edit_message(embed=await self.build_embed(), view=self)

    @discord.ui.button(label="Clear Channel", style=discord.ButtonStyle.secondary, row=2)
    async def clear_channel(self, interaction: discord.Interaction, button: discord.ui.Button) -> None:
        await update_guild_config(self.guild_id, {"ai_thought_channel_id": None})
        await add_guild_config_audit(
            self.guild_id,
            interaction.user.id,
            "ai_thought_channel_clear",
            category=AUDIT_CATEGORY_CONFIG_GENERAL,
        )
        await interaction.response.edit_message(embed=await self.build_embed(), view=self)


class ProviderSecretModal(discord.ui.Modal):
    def __init__(self, *, guild_id: int) -> None:
        super().__init__(title="Provider Secret")
        self.guild_id = guild_id
        self.category = discord.ui.TextInput(label="Category", placeholder="general, translate, summarize, profile, uncensored")
        self.slot = discord.ui.TextInput(label="Slot", required=False, placeholder="1-5")
        self.value = discord.ui.TextInput(label="Secret", required=False, style=discord.TextStyle.paragraph)
        self.clear_value = discord.ui.TextInput(label="Clear?", required=False, placeholder="type clear to remove")
        self.add_item(self.category)
        self.add_item(self.slot)
        self.add_item(self.value)
        self.add_item(self.clear_value)

    async def on_submit(self, interaction: discord.Interaction) -> None:
        category = self.category.value.strip().lower()
        fields = KEY_FIELDS.get(category)
        if not fields:
            await interaction.response.send_message("Unknown provider category.", ephemeral=True)
            return
        slot_index = 0
        if self.slot.value.strip():
            slot_index = int(self.slot.value.strip()) - 1
        if slot_index < 0 or slot_index >= len(fields):
            await interaction.response.send_message("Invalid slot for that category.", ephemeral=True)
            return
        field = fields[slot_index]
        if self.clear_value.value.strip().lower() == "clear":
            update_value = None
        elif self.value.value.strip():
            update_value = encryption.encrypt(self.value.value.strip())
        else:
            await interaction.response.send_message("Provide a secret or type clear.", ephemeral=True)
            return
        await update_guild_config(self.guild_id, {field: update_value})
        await add_guild_config_audit(
            self.guild_id,
            interaction.user.id,
            "provider_secret_update",
            category=AUDIT_CATEGORY_CONFIG_SECURITY,
            field=field,
            summary=f"Updated provider secret {field}.",
        )
        await interaction.response.send_message("Provider secret updated.", ephemeral=True)


class ProviderModelsModal(discord.ui.Modal):
    def __init__(self, *, guild_id: int) -> None:
        super().__init__(title="Provider Models")
        self.guild_id = guild_id
        self.general = discord.ui.TextInput(label="General Gemini model", required=False)
        self.translate = discord.ui.TextInput(label="Translate Gemini model", required=False)
        self.summarize = discord.ui.TextInput(label="Summarize Gemini model", required=False)
        self.uncensored = discord.ui.TextInput(label="OpenRouter model", required=False)
        self.fallbacks = discord.ui.TextInput(label="OpenRouter fallbacks", required=False, style=discord.TextStyle.paragraph)
        self.add_item(self.general)
        self.add_item(self.translate)
        self.add_item(self.summarize)
        self.add_item(self.uncensored)
        self.add_item(self.fallbacks)

    async def on_submit(self, interaction: discord.Interaction) -> None:
        updates: dict[str, Any] = {}
        if self.general.value.strip():
            updates["gemini_model"] = normalize_gemini_model(self.general.value.strip()) or self.general.value.strip()
        if self.translate.value.strip():
            updates["gemini_translate_model"] = normalize_gemini_model(self.translate.value.strip()) or self.translate.value.strip()
        if self.summarize.value.strip():
            updates["gemini_summarize_model"] = normalize_gemini_model(self.summarize.value.strip()) or self.summarize.value.strip()
        if self.uncensored.value.strip():
            updates["openrouter_model"] = normalize_openrouter_model(self.uncensored.value.strip()) or self.uncensored.value.strip()
        if self.fallbacks.value.strip():
            updates["openrouter_fallback_models"] = self.fallbacks.value.strip()
        if not updates:
            await interaction.response.send_message("No model changes submitted.", ephemeral=True)
            return
        await update_guild_config(self.guild_id, updates)
        await add_guild_config_audit(
            self.guild_id,
            interaction.user.id,
            "provider_models_update",
            category=AUDIT_CATEGORY_CONFIG_GENERAL,
            summary="Updated provider models.",
            detail=updates,
        )
        await interaction.response.send_message("Provider models updated.", ephemeral=True)


class CustomEndpointModal(discord.ui.Modal):
    def __init__(self, *, guild_id: int) -> None:
        super().__init__(title="Custom Endpoint")
        self.guild_id = guild_id
        self.url = discord.ui.TextInput(label="Endpoint URL", required=False)
        self.model = discord.ui.TextInput(label="Model name", required=False)
        self.capabilities = discord.ui.TextInput(label="Capabilities", required=False, placeholder="openai_compat, streaming, tools, vision")
        self.enabled = discord.ui.TextInput(label="Enabled", required=False, placeholder="on/off")
        self.api_key = discord.ui.TextInput(label="API key", required=False, style=discord.TextStyle.paragraph)
        self.add_item(self.url)
        self.add_item(self.model)
        self.add_item(self.capabilities)
        self.add_item(self.enabled)
        self.add_item(self.api_key)

    async def on_submit(self, interaction: discord.Interaction) -> None:
        updates: dict[str, Any] = {}
        if self.url.value.strip():
            updates["custom_endpoint_url"] = self.url.value.strip()
        if self.model.value.strip():
            updates["custom_model_name"] = self.model.value.strip()
        if self.capabilities.value.strip():
            updates["custom_model_capabilities"] = self.capabilities.value.strip()
        if self.enabled.value.strip():
            enabled = self.enabled.value.strip().lower()
            if enabled not in {"on", "off", "true", "false", "enable", "disable"}:
                await interaction.response.send_message("Enabled must be on/off.", ephemeral=True)
                return
            updates["custom_endpoint_enabled"] = 1 if enabled in {"on", "true", "enable"} else 0
        if self.api_key.value.strip():
            updates["custom_endpoint_api_key"] = encryption.encrypt(self.api_key.value.strip())
        if not updates:
            await interaction.response.send_message("No endpoint changes submitted.", ephemeral=True)
            return
        await update_guild_config(self.guild_id, updates)
        await add_guild_config_audit(
            self.guild_id,
            interaction.user.id,
            "custom_endpoint_update",
            category=AUDIT_CATEGORY_CONFIG_SECURITY,
            summary="Updated custom endpoint configuration.",
            detail={key: "***" if "key" in key else value for key, value in updates.items()},
        )
        await interaction.response.send_message("Custom endpoint updated.", ephemeral=True)


class ProvidersHomeView(AdminPanelView):
    def __init__(self, *, guild_id: int, user_id: int, locale: str, home_view: ConfigPanelHomeView) -> None:
        super().__init__(user_id=user_id, timeout=300)
        self.guild_id = guild_id
        self.locale = locale
        self.home_view = home_view
        self.add_item(_BackButton(self._go_back))

    async def _go_back(self, interaction: discord.Interaction) -> None:
        await _swap_panel(interaction, embed=await self.home_view.build_embed(), view=self.home_view, previous=self)

    async def build_embed(self) -> discord.Embed:
        config = await get_guild_config(self.guild_id)
        embed = discord.Embed(title="Providers & Models", color=discord.Color.blue())
        for category, fields in KEY_FIELDS.items():
            masked = [_mask_secret(config.get(field)) for field in fields]
            embed.add_field(name=f"{category.title()} secrets", value="\n".join(masked), inline=False)
        embed.add_field(name="Gemini (general)", value=config.get("gemini_model") or "Not set", inline=False)
        embed.add_field(name="Gemini (translate)", value=config.get("gemini_translate_model") or "Not set", inline=False)
        embed.add_field(name="Gemini (summarize)", value=config.get("gemini_summarize_model") or "Not set", inline=False)
        embed.add_field(name="OpenRouter", value=config.get("openrouter_model") or "Not set", inline=False)
        embed.add_field(
            name="Custom endpoint",
            value=(
                f"Enabled: {'Yes' if config.get('custom_endpoint_enabled') else 'No'}\n"
                f"URL: {config.get('custom_endpoint_url') or 'Not set'}\n"
                f"Model: {config.get('custom_model_name') or 'Not set'}"
            ),
            inline=False,
        )
        return embed

    @discord.ui.button(label="Edit Secret", style=discord.ButtonStyle.primary, row=0)
    async def edit_secret(self, interaction: discord.Interaction, button: discord.ui.Button) -> None:
        if not await _maybe_send_auth_modal(
            interaction,
            action_key="provider_secret_update",
            next_modal_factory=lambda: ProviderSecretModal(guild_id=self.guild_id),
        ):
            return
        await interaction.response.send_modal(ProviderSecretModal(guild_id=self.guild_id))

    @discord.ui.button(label="Edit Models", style=discord.ButtonStyle.primary, row=0)
    async def edit_models(self, interaction: discord.Interaction, button: discord.ui.Button) -> None:
        if not await _ensure_low_risk_permissions(interaction):
            return
        await interaction.response.send_modal(ProviderModelsModal(guild_id=self.guild_id))

    @discord.ui.button(label="Edit Endpoint", style=discord.ButtonStyle.primary, row=1)
    async def edit_endpoint(self, interaction: discord.Interaction, button: discord.ui.Button) -> None:
        if not await _maybe_send_auth_modal(
            interaction,
            action_key="custom_endpoint_update",
            next_modal_factory=lambda: CustomEndpointModal(guild_id=self.guild_id),
        ):
            return
        await interaction.response.send_modal(CustomEndpointModal(guild_id=self.guild_id))


class ServerSettingsHomeView(AdminPanelView):
    def __init__(self, *, guild_id: int, user_id: int, locale: str, home_view: ConfigPanelHomeView) -> None:
        super().__init__(user_id=user_id, timeout=300)
        self.guild_id = guild_id
        self.locale = locale
        self.home_view = home_view
        self.add_item(_BackButton(self._go_back))

    async def _go_back(self, interaction: discord.Interaction) -> None:
        await _swap_panel(interaction, embed=await self.home_view.build_embed(), view=self.home_view, previous=self)

    async def build_embed(self) -> discord.Embed:
        welcome = await get_welcome_config(self.guild_id)
        autorole = await get_autorole_config(self.guild_id)
        modlog_channel_id = await get_mod_log_channel_id(self.guild_id)
        staff_roles = await get_staff_roles(self.guild_id)
        url_safety = await get_url_safety_config(self.guild_id)
        embed = discord.Embed(title="Server Settings", color=discord.Color.blue())
        embed.add_field(name="Welcome", value="Enabled" if welcome.get("welcome_enabled") else "Disabled", inline=True)
        embed.add_field(name="Autorole", value="Enabled" if autorole.get("autorole_enabled") else "Disabled", inline=True)
        embed.add_field(name="Modlog", value=f"<#{modlog_channel_id}>" if modlog_channel_id else "Not set", inline=True)
        embed.add_field(name="Staff roles", value=str(len(staff_roles)), inline=True)
        embed.add_field(name="URL safety", value=url_safety.get("url_safety_action") or "warn", inline=True)
        return embed

    @discord.ui.button(label="Welcome", style=discord.ButtonStyle.primary, row=0)
    async def open_welcome(self, interaction: discord.Interaction, button: discord.ui.Button) -> None:
        view = WelcomeSettingsView(guild_id=self.guild_id, user_id=self.user_id, locale=self.locale, home_view=self)
        await _swap_panel(interaction, embed=await view.build_embed(), view=view, previous=self)

    @discord.ui.button(label="Autorole", style=discord.ButtonStyle.primary, row=0)
    async def open_autorole(self, interaction: discord.Interaction, button: discord.ui.Button) -> None:
        view = AutoroleSettingsView(guild_id=self.guild_id, user_id=self.user_id, locale=self.locale, home_view=self)
        await _swap_panel(interaction, embed=await view.build_embed(), view=view, previous=self)

    @discord.ui.button(label="Staff", style=discord.ButtonStyle.primary, row=1)
    async def open_staff(self, interaction: discord.Interaction, button: discord.ui.Button) -> None:
        view = StaffSettingsView(guild_id=self.guild_id, user_id=self.user_id, locale=self.locale, home_view=self)
        await _swap_panel(interaction, embed=await view.build_embed(), view=view, previous=self)

    @discord.ui.button(label="Modlog", style=discord.ButtonStyle.primary, row=1)
    async def open_modlog(self, interaction: discord.Interaction, button: discord.ui.Button) -> None:
        view = ModlogSettingsView(guild_id=self.guild_id, user_id=self.user_id, locale=self.locale, home_view=self)
        await _swap_panel(interaction, embed=await view.build_embed(), view=view, previous=self)

    @discord.ui.button(label="URL Safety", style=discord.ButtonStyle.primary, row=2)
    async def open_url_safety(self, interaction: discord.Interaction, button: discord.ui.Button) -> None:
        view = URLSafetySettingsView(guild_id=self.guild_id, user_id=self.user_id, locale=self.locale, home_view=self)
        await _swap_panel(interaction, embed=await view.build_embed(), view=view, previous=self)
async def open_config_panel(interaction: discord.Interaction) -> None:
    locale = get_locale_from_interaction(interaction)
    view = ConfigPanelHomeView(guild_id=interaction.guild.id, user_id=interaction.user.id, locale=locale)
    await _send_panel_message(interaction, embed=await view.build_embed(), view=view)


async def open_tools_manage(interaction: discord.Interaction) -> None:
    locale = get_locale_from_interaction(interaction)
    home_view = ConfigPanelHomeView(guild_id=interaction.guild.id, user_id=interaction.user.id, locale=locale)
    view = CapabilityEditorView(guild_id=interaction.guild.id, user_id=interaction.user.id, locale=locale, home_view=home_view)
    await _send_panel_message(interaction, embed=await view.build_embed(), view=view)
