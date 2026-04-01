from __future__ import annotations

import json
import os

import discord
from discord import app_commands
from discord.ext import commands

from tools.audit import (
    disable_debug_capture_window,
    is_debug_capture_enabled,
    set_debug_capture_window,
)
from tools.availability import compute_tool_availability_decisions
from tools.categories import normalize_tool_category
from tools.contracts import ToolTurnContext
from tools.mcp.control_plane import (
    ADMIN_GLOBAL_SCOPE,
    GUILD_SCOPE,
    approve_mcp_tool,
    discover_mcp_tools,
    list_mcp_registrations,
    list_mcp_server_health,
    list_mcp_tools,
    register_admin_global_mcp_server,
    register_guild_mcp_server,
    set_mcp_registration_enabled,
    set_mcp_registration_trust,
)
from tools.policy_engine import (
    delete_tool_policy_rule,
    list_tool_policy_rules,
    upsert_tool_policy_rule,
)
from tools.quarantine import clear_quarantine_state, list_quarantine_states
from tools.registry import get_tool_registry
from utils.admin_panel_logic import diff_toggle_states
from utils.config_panel_ui import ActionMenuView, ActionOption, FeatureGroupView, FeatureOption
from utils.db_handler import (
    add_guild_config_audit,
    delete_short_term_memory_scope,
    get_guild_config,
    update_guild_config,
)
from utils.tool_flags import DEFAULT_FLAG_VALUES, get_tool_flag
from utils.tool_registry import list_tools, register_builtin_tools
from utils.i18n import get_locale_from_interaction, t


async def _is_owner_check(interaction: discord.Interaction) -> bool:
    return await interaction.client.is_owner(interaction.user)


TOOL_GROUPS: dict[str, dict[str, object]] = {
    "ai_tools": {
        "label": "AI tools",
        "description": "Search, retrieval, and generation capabilities.",
        "flags": ["web_search_enabled", "image_gen_enabled", "rag_enabled"],
    },
    "discovery": {
        "label": "Discovery",
        "description": "Search and retrieval capabilities.",
        "flags": ["web_search_enabled", "rag_enabled"],
    },
    "media": {
        "label": "Media",
        "description": "Images, GIFs, YouTube, stickers, and emoji tooling.",
        "flags": [
            "image_gen_enabled",
            "gif_responses_enabled",
            "youtube_enabled",
            "profile_peek_enabled",
            "sticker_usage_enabled",
            "emoji_usage_enabled",
            "pin_message_enabled",
        ],
    },
    "memory": {
        "label": "Memory",
        "description": "Long-term and short-term memory updates.",
        "flags": ["self_teaching_enabled"],
    },
}

FLAG_LABELS = {
    "web_search_enabled": "Web Search",
    "rag_enabled": "Local RAG",
    "image_gen_enabled": "Image Generation",
    "gif_responses_enabled": "GIF Replies",
    "youtube_enabled": "YouTube Processing",
    "profile_peek_enabled": "Profile Peek",
    "sticker_usage_enabled": "Sticker Usage",
    "emoji_usage_enabled": "Emoji Usage",
    "pin_message_enabled": "Pin Message",
    "self_teaching_enabled": "Self Teaching",
}


class ToolsAdmin(commands.Cog):
    tools_group = app_commands.Group(name="tools", description="Tool status and configuration")
    policy_group = app_commands.Group(name="policy", description="Tool policy controls", parent=tools_group)
    debug_group = app_commands.Group(name="debug", description="Tool debug controls", parent=tools_group)
    quarantine_group = app_commands.Group(name="quarantine", description="Tool quarantine controls", parent=tools_group)
    mcp_group = app_commands.Group(name="mcp", description="MCP registration, discovery, and approval controls", parent=tools_group)

    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot
        register_builtin_tools()

    async def _require_guild(self, interaction: discord.Interaction) -> bool:
        if interaction.guild:
            return True
        await interaction.response.send_message(
            t("common.server_only", get_locale_from_interaction(interaction)),
            ephemeral=True,
        )
        return False

    def _flag_enabled(self, config: dict[str, object], flag: str) -> bool:
        value = config.get(flag)
        if value is None:
            value = DEFAULT_FLAG_VALUES.get(flag, 0)
        try:
            return bool(int(value))
        except (TypeError, ValueError):
            return bool(value)

    def _build_turn_context(
        self,
        interaction: discord.Interaction,
        config: dict[str, object],
    ) -> ToolTurnContext:
        return ToolTurnContext(
            request_id=None,
            turn_id=None,
            guild_id=interaction.guild.id if interaction.guild else None,
            channel_id=interaction.channel_id,
            thread_id=None,
            user_id=interaction.user.id if interaction.user else None,
            guild=interaction.guild,
            channel=getattr(interaction, "channel", None),
            member=interaction.user,
            guild_config=dict(config),
        )

    def _format_decision_brief(self, decision) -> str:
        if decision.allowed:
            return f"{decision.public_name}: allow"
        reason = decision.primary_reason_code or "denied"
        return f"{decision.public_name}: {reason}"

    def _parse_env_json(self, env_json: str | None) -> dict[str, str]:
        if not env_json:
            return {}
        try:
            data = json.loads(env_json)
        except Exception:
            data = None
        if not isinstance(data, dict):
            return {}
        return {str(key): str(value) for key, value in data.items()}

    def _format_registration_line(self, row: dict[str, object]) -> str:
        scope_type = row.get("scope_type")
        guild_id = int(row.get("guild_id") or 0)
        scope_label = f"{scope_type}:{guild_id}" if scope_type == GUILD_SCOPE else str(scope_type)
        trusted = "trusted" if int(row.get("trusted") or 0) else "untrusted"
        enabled = "enabled" if int(row.get("enabled") or 0) else "disabled"
        return f"{scope_label}:{row.get('server_slug')} [{trusted}, {enabled}]"

    def _format_health_line(self, row: dict[str, object]) -> str:
        scope_type = row.get("scope_type")
        guild_id = int(row.get("guild_id") or 0)
        scope_label = f"{scope_type}:{guild_id}" if scope_type == GUILD_SCOPE else str(scope_type)
        discovery = row.get("last_discovery_status") or "unknown"
        call = row.get("last_call_status") or "unknown"
        cooldown = row.get("cooldown_until") or "-"
        return f"{scope_label}:{row.get('server_slug')} [discover={discovery}, call={call}, cooldown={cooldown}]"

    def _feature_options(self, config: dict[str, object], group_key: str) -> list[FeatureOption]:
        flags = TOOL_GROUPS[group_key]["flags"]
        return [
            FeatureOption(
                key=flag,
                label=FLAG_LABELS.get(flag, flag),
                enabled=self._flag_enabled(config, flag),
            )
            for flag in flags
        ]

    def _group_embed(
        self,
        locale: str,
        group_key: str,
        config: dict[str, object],
    ) -> discord.Embed:
        group = TOOL_GROUPS[group_key]
        embed = discord.Embed(
            title=f"{t('tools.manage.title', locale)}: {group['label']}",
            description=str(group["description"]),
            color=discord.Color.blurple(),
        )
        lines = []
        for option in self._feature_options(config, group_key):
            status = "ON" if option.enabled else "OFF"
            lines.append(f"`{status}` {option.label}")
        embed.add_field(name="Flags", value="\n".join(lines) if lines else "No configurable flags.", inline=False)
        embed.set_footer(text="Bulk toggle the selected flags, then reopen /tools manage for another group.")
        return embed

    def _overview_embed(self, locale: str, config: dict[str, object]) -> discord.Embed:
        embed = discord.Embed(
            title="Tools Management",
            description=t("tools.manage.description", locale),
            color=discord.Color.blue(),
        )
        for group_key, group in TOOL_GROUPS.items():
            flags = group["flags"]
            enabled_count = sum(1 for flag in flags if self._flag_enabled(config, flag))
            embed.add_field(
                name=str(group["label"]),
                value=f"{enabled_count}/{len(flags)} enabled\n{group['description']}",
                inline=False,
            )
        embed.set_footer(text="Use /tools refresh separately when you want to reset channel context.")
        return embed

    async def _apply_group_changes(
        self,
        interaction: discord.Interaction,
        group_key: str,
        changes: dict[str, bool],
    ) -> str:
        config = await get_guild_config(interaction.guild.id)
        proposed = {flag: int(value) for flag, value in changes.items()}
        diff = diff_toggle_states(config, proposed)
        if not diff:
            return "No tool flag changes were needed."

        await update_guild_config(interaction.guild.id, proposed)
        detail = {
            "group": group_key,
            "changes": diff,
        }
        await add_guild_config_audit(
            interaction.guild.id,
            interaction.user.id,
            "tools_manage_save",
            category="tools_config",
            target_type="tool_group",
            target_id=group_key,
            summary=f"Updated tool flags for {TOOL_GROUPS[group_key]['label']}",
            detail=detail,
        )
        changed_names = ", ".join(FLAG_LABELS.get(flag, flag) for flag in diff)
        return f"Updated {TOOL_GROUPS[group_key]['label']}: {changed_names}. Use `/tools manage` for another group."

    async def _send_feature_group_panel(self, interaction: discord.Interaction, group_key: str) -> None:
        locale = get_locale_from_interaction(interaction)
        config = await get_guild_config(interaction.guild.id)
        view = FeatureGroupView(
            invoker_id=interaction.user.id,
            title=str(TOOL_GROUPS[group_key]["label"]),
            options=self._feature_options(config, group_key),
            apply_changes=lambda changes, group_key=group_key, interaction=interaction: self._apply_group_changes(
                interaction,
                group_key,
                changes,
            ),
        )
        embed = self._group_embed(locale, group_key, config)
        if hasattr(interaction.response, "is_done") and interaction.response.is_done():
            await interaction.followup.send(embed=embed, view=view, ephemeral=True)
            return
        await interaction.response.send_message(embed=embed, view=view, ephemeral=True)
        try:
            message = await interaction.original_response()
            view.bind_message(message)
        except (AttributeError, discord.HTTPException):
            pass

    @tools_group.command(name="status", description="Show tool availability for this server.")
    async def tools_status(self, interaction: discord.Interaction):
        if not await self._require_guild(interaction):
            return

        config = await get_guild_config(interaction.guild.id)
        tools = list_tools()
        decisions = await compute_tool_availability_decisions(
            context=self._build_turn_context(interaction, config),
        )
        enabled_names = {decision.public_name for decision in decisions if decision.allowed}

        locale = get_locale_from_interaction(interaction)
        embed = discord.Embed(title=t("tools.status.title", locale), color=discord.Color.blue())
        embed.add_field(
            name=t("tools.status.enabled", locale),
            value=", ".join(sorted(enabled_names)) if enabled_names else "None",
            inline=False,
        )

        flag_lines = []
        for tool in tools:
            flag = tool.feature_flag or get_tool_flag(tool.name)
            if not flag:
                continue
            value = config.get(flag)
            if value is None:
                value = DEFAULT_FLAG_VALUES.get(flag, 1)
            status = "ON" if bool(int(value)) else "OFF"
            if flag == "rag_enabled":
                if str(os.getenv("ACTIVATE_LOCAL_RAG", "")).lower() not in {"1", "true", "yes", "on"}:
                    status = "OFF (env)"
            flag_lines.append(f"{flag}: {status}")
        if flag_lines:
            embed.add_field(
                name=t("tools.status.flags", locale),
                value="\n".join(sorted(set(flag_lines))),
                inline=False,
            )

        disabled = [tool.name for tool in tools if tool.name not in enabled_names]
        if disabled:
            embed.add_field(
                name=t("tools.status.disabled", locale),
                value=", ".join(sorted(disabled)),
                inline=False,
            )
        denied_lines = [self._format_decision_brief(decision) for decision in decisions if not decision.allowed]
        if denied_lines:
            embed.add_field(
                name="Denied For This Turn",
                value="\n".join(denied_lines[:10]),
                inline=False,
            )
        embed.set_footer(text="Use /tools manage to change grouped tool flags. /tools refresh stays separate.")

        await interaction.response.send_message(embed=embed, ephemeral=True)

    @tools_group.command(name="inspect", description="Inspect tool candidates, denied tools, and filtering reasons.")
    @app_commands.checks.has_permissions(administrator=True)
    async def tools_inspect(self, interaction: discord.Interaction, tool_name: str | None = None):
        if not await self._require_guild(interaction):
            return

        config = await get_guild_config(interaction.guild.id)
        context = self._build_turn_context(interaction, config)
        descriptors = None
        if tool_name:
            descriptor = get_tool_registry().resolve_descriptor(tool_name.strip())
            if descriptor is None:
                await interaction.response.send_message(
                    f"Unknown tool `{tool_name}`.",
                    ephemeral=True,
                )
                return
            descriptors = [descriptor]

        decisions = await compute_tool_availability_decisions(context=context, descriptors=descriptors)
        rules = await list_tool_policy_rules(guild_id=interaction.guild.id, include_global=True)
        embed = discord.Embed(
            title="Tool Inspection",
            description="Candidate tools with effective policy and filtering reasons.",
            color=discord.Color.dark_teal(),
        )

        if tool_name and decisions:
            decision = decisions[0]
            embed.add_field(name="Tool", value=decision.public_name, inline=False)
            embed.add_field(name="Allowed", value=str(decision.allowed), inline=True)
            embed.add_field(name="Policy", value=decision.effective_policy_mode.value, inline=True)
            embed.add_field(name="Reason", value=decision.primary_reason_code or "allow", inline=True)
            layer_lines = []
            for layer in decision.decision_layers:
                name = layer.get("layer")
                allowed = layer.get("allowed")
                detail = {k: v for k, v in layer.items() if k not in {"layer", "allowed"}}
                layer_lines.append(f"{name}: {allowed} {detail}".strip())
            embed.add_field(name="Decision Layers", value="\n".join(layer_lines) if layer_lines else "None", inline=False)
        else:
            allowed_lines = [decision.public_name for decision in decisions if decision.allowed]
            denied_lines = [self._format_decision_brief(decision) for decision in decisions if not decision.allowed]
            embed.add_field(name="Allowed", value=", ".join(allowed_lines) if allowed_lines else "None", inline=False)
            embed.add_field(name="Denied", value="\n".join(denied_lines[:20]) if denied_lines else "None", inline=False)
        if rules:
            rule_lines = [
                f"{rule.scope_type}:{rule.subject_type}:{rule.subject_id} -> {rule.policy_mode.value}"
                for rule in rules[:20]
            ]
            embed.add_field(name="Active Policy Rules", value="\n".join(rule_lines), inline=False)

        await interaction.response.send_message(embed=embed, ephemeral=True)

    async def tools_manage(self, interaction: discord.Interaction):
        if not await self._require_guild(interaction):
            return

        locale = get_locale_from_interaction(interaction)
        config = await get_guild_config(interaction.guild.id)
        options = [
            ActionOption(
                label=str(group["label"]),
                value=group_key,
                description=str(group["description"]),
            )
            for group_key, group in TOOL_GROUPS.items()
        ]
        view = ActionMenuView(
            invoker_id=interaction.user.id,
            options=options,
            on_action=self._send_feature_group_panel,
        )
        await interaction.response.send_message(
            embed=self._overview_embed(locale, config),
            view=view,
            ephemeral=True,
        )
        try:
            message = await interaction.original_response()
            view.bind_message(message)
        except (AttributeError, discord.HTTPException):
            pass

    @tools_group.command(name="manage", description="Open the Discord-native tool management panel.")
    async def tools_manage_command(self, interaction: discord.Interaction):
        await self.tools_manage(interaction)

    @tools_group.command(
        name="refresh",
        description="Clear short-term channel memory and set a new context boundary.",
    )
    async def tools_refresh(self, interaction: discord.Interaction):
        if not await self._require_guild(interaction):
            return
        if not interaction.user.guild_permissions.manage_guild:
            await interaction.response.send_message(
                "You need Manage Server to refresh channel context.",
                ephemeral=True,
            )
            return

        ai_brain = self.bot.get_cog("AIBrain")
        if ai_brain is None or not hasattr(ai_brain, "clear_channel_memory_boundary"):
            await interaction.response.send_message(
                "AI context manager is unavailable.",
                ephemeral=True,
            )
            return

        await interaction.response.send_message("Refreshing channel context...")
        marker_message = await interaction.original_response()
        deleted = await ai_brain.clear_channel_memory_boundary(
            guild_id=interaction.guild.id,
            channel_id=interaction.channel_id,
            marker_message_id=marker_message.id,
        )

        embed = discord.Embed(
            title="Conversation Refreshed",
            description=(
                "Short-term channel context was cleared and a new prompt boundary has been set.\n"
                f"Short-term memory records removed: **{deleted}**"
            ),
            color=discord.Color.blurple(),
        )
        await marker_message.edit(content=None, embed=embed)

    @tools_group.command(
        name="clear-guild-recency",
        description="Clear the guild-wide short-term recency summary.",
    )
    async def tools_clear_guild_recency(self, interaction: discord.Interaction):
        if not await self._require_guild(interaction):
            return
        if not interaction.user.guild_permissions.manage_guild:
            await interaction.response.send_message(
                "You need Manage Server to clear guild recency context.",
                ephemeral=True,
            )
            return

        deleted = await delete_short_term_memory_scope(
            interaction.guild.id,
            scope_kind="guild",
        )
        await interaction.response.send_message(
            f"Cleared guild-wide recency summaries: **{deleted}**",
            ephemeral=True,
        )

    @policy_group.command(name="set-category", description="Set guild policy for a tool category.")
    @app_commands.checks.has_permissions(administrator=True)
    async def tools_policy_set_category(self, interaction: discord.Interaction, category: str, mode: str):
        if not await self._require_guild(interaction):
            return
        try:
            normalized_category = normalize_tool_category(category)
            rule = await upsert_tool_policy_rule(
                subject_type="category",
                subject_id=normalized_category,
                policy_mode=mode,
                scope_type="guild",
                guild_id=interaction.guild.id,
                actor_id=interaction.user.id,
                note="Set via /tools policy set-category",
            )
        except ValueError as exc:
            await interaction.response.send_message(str(exc), ephemeral=True)
            return
        await interaction.response.send_message(
            f"Set guild category policy: `{rule.subject_id}` -> `{rule.policy_mode.value}`.",
            ephemeral=True,
        )

    @policy_group.command(name="clear-category", description="Clear guild policy for a tool category.")
    @app_commands.checks.has_permissions(administrator=True)
    async def tools_policy_clear_category(self, interaction: discord.Interaction, category: str):
        if not await self._require_guild(interaction):
            return
        try:
            normalized_category = normalize_tool_category(category)
        except ValueError as exc:
            await interaction.response.send_message(str(exc), ephemeral=True)
            return
        removed = await delete_tool_policy_rule(
            subject_type="category",
            subject_id=normalized_category,
            scope_type="guild",
            guild_id=interaction.guild.id,
            actor_id=interaction.user.id,
            note="Cleared via /tools policy clear-category",
        )
        await interaction.response.send_message(
            f"{'Cleared' if removed else 'No existing'} guild category policy for `{normalized_category}`.",
            ephemeral=True,
        )

    @policy_group.command(name="set-tool", description="Set guild policy for a specific tool.")
    @app_commands.checks.has_permissions(administrator=True)
    async def tools_policy_set_tool(self, interaction: discord.Interaction, tool_name: str, mode: str):
        if not await self._require_guild(interaction):
            return
        descriptor = get_tool_registry().resolve_descriptor(tool_name.strip())
        if descriptor is None:
            await interaction.response.send_message(f"Unknown tool `{tool_name}`.", ephemeral=True)
            return
        try:
            rule = await upsert_tool_policy_rule(
                subject_type="tool",
                subject_id=descriptor.tool_id,
                policy_mode=mode,
                scope_type="guild",
                guild_id=interaction.guild.id,
                actor_id=interaction.user.id,
                note="Set via /tools policy set-tool",
            )
        except ValueError as exc:
            await interaction.response.send_message(str(exc), ephemeral=True)
            return
        await interaction.response.send_message(
            f"Set guild tool policy: `{descriptor.public_name}` -> `{rule.policy_mode.value}`.",
            ephemeral=True,
        )

    @policy_group.command(name="clear-tool", description="Clear guild policy for a specific tool.")
    @app_commands.checks.has_permissions(administrator=True)
    async def tools_policy_clear_tool(self, interaction: discord.Interaction, tool_name: str):
        if not await self._require_guild(interaction):
            return
        descriptor = get_tool_registry().resolve_descriptor(tool_name.strip())
        if descriptor is None:
            await interaction.response.send_message(f"Unknown tool `{tool_name}`.", ephemeral=True)
            return
        removed = await delete_tool_policy_rule(
            subject_type="tool",
            subject_id=descriptor.tool_id,
            scope_type="guild",
            guild_id=interaction.guild.id,
            actor_id=interaction.user.id,
            note="Cleared via /tools policy clear-tool",
        )
        await interaction.response.send_message(
            f"{'Cleared' if removed else 'No existing'} guild tool policy for `{descriptor.public_name}`.",
            ephemeral=True,
        )

    @debug_group.command(name="raw-capture-status", description="Show whether temporary raw capture is enabled.")
    @app_commands.checks.has_permissions(administrator=True)
    async def tools_debug_raw_capture_status(self, interaction: discord.Interaction):
        if not await self._require_guild(interaction):
            return
        enabled = await is_debug_capture_enabled(guild_id=interaction.guild.id)
        await interaction.response.send_message(
            f"Raw capture is currently {'ENABLED' if enabled else 'DISABLED'} for this guild.",
            ephemeral=True,
        )

    @debug_group.command(name="raw-capture-enable", description="Temporarily enable raw tool capture for debugging.")
    @app_commands.checks.has_permissions(administrator=True)
    async def tools_debug_raw_capture_enable(
        self,
        interaction: discord.Interaction,
        ttl_minutes: app_commands.Range[int, 1, 120] = 15,
        note: str | None = None,
    ):
        if not await self._require_guild(interaction):
            return
        await set_debug_capture_window(
            guild_id=interaction.guild.id,
            enabled_by=interaction.user.id,
            ttl_seconds=int(ttl_minutes) * 60,
            note=note,
        )
        await interaction.response.send_message(
            f"Enabled raw capture for {ttl_minutes} minute(s).",
            ephemeral=True,
        )

    @debug_group.command(name="raw-capture-disable", description="Disable temporary raw tool capture.")
    @app_commands.checks.has_permissions(administrator=True)
    async def tools_debug_raw_capture_disable(self, interaction: discord.Interaction):
        if not await self._require_guild(interaction):
            return
        await disable_debug_capture_window(guild_id=interaction.guild.id)
        await interaction.response.send_message(
            "Disabled raw capture for this guild.",
            ephemeral=True,
        )

    @quarantine_group.command(name="status", description="Show active tool quarantine state for this guild.")
    @app_commands.checks.has_permissions(administrator=True)
    async def tools_quarantine_status(self, interaction: discord.Interaction):
        if not await self._require_guild(interaction):
            return
        states = await list_quarantine_states(guild_id=interaction.guild.id, active_only=True)
        if not states:
            await interaction.response.send_message("No tools are currently quarantined for this guild.", ephemeral=True)
            return
        lines = [
            f"{state.tool_id}: failures={state.failure_count}, until={state.quarantined_until}, reason={state.quarantine_reason}"
            for state in states
        ]
        embed = discord.Embed(
            title="Tool Quarantine",
            description="\n".join(lines[:20]),
            color=discord.Color.orange(),
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)

    @quarantine_group.command(name="clear", description="Clear quarantine state for a specific tool in this guild.")
    @app_commands.checks.has_permissions(administrator=True)
    async def tools_quarantine_clear(self, interaction: discord.Interaction, tool_name: str):
        if not await self._require_guild(interaction):
            return
        descriptor = get_tool_registry().resolve_descriptor(tool_name.strip())
        if descriptor is None:
            await interaction.response.send_message(f"Unknown tool `{tool_name}`.", ephemeral=True)
            return
        await clear_quarantine_state(
            guild_id=interaction.guild.id,
            tool_id=descriptor.tool_id,
            actor_id=interaction.user.id,
            note="Cleared via /tools quarantine clear",
        )
        await interaction.response.send_message(
            f"Cleared quarantine state for `{descriptor.public_name}` in this guild.",
            ephemeral=True,
        )

    @mcp_group.command(name="list-registrations", description="List MCP registrations visible from this server.")
    @app_commands.checks.has_permissions(administrator=True)
    async def tools_mcp_list_registrations(self, interaction: discord.Interaction):
        if not await self._require_guild(interaction):
            return
        global_rows = await list_mcp_registrations(scope_type=ADMIN_GLOBAL_SCOPE)
        guild_rows = await list_mcp_registrations(scope_type=GUILD_SCOPE, guild_id=interaction.guild.id)
        embed = discord.Embed(
            title="MCP Registrations",
            color=discord.Color.dark_blue(),
        )
        embed.add_field(
            name="Admin-Global",
            value="\n".join(self._format_registration_line(row) for row in global_rows[:15]) if global_rows else "None",
            inline=False,
        )
        embed.add_field(
            name="Guild",
            value="\n".join(self._format_registration_line(row) for row in guild_rows[:15]) if guild_rows else "None",
            inline=False,
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)

    @mcp_group.command(name="health", description="Show MCP discovery/call health and cooldown state.")
    @app_commands.checks.has_permissions(administrator=True)
    async def tools_mcp_health(self, interaction: discord.Interaction):
        if not await self._require_guild(interaction):
            return
        global_rows = await list_mcp_server_health(scope_type=ADMIN_GLOBAL_SCOPE)
        guild_rows = await list_mcp_server_health(scope_type=GUILD_SCOPE, guild_id=interaction.guild.id)
        embed = discord.Embed(
            title="MCP Health",
            color=discord.Color.orange(),
        )
        embed.add_field(
            name="Admin-Global",
            value="\n".join(self._format_health_line(row) for row in global_rows[:15]) if global_rows else "None",
            inline=False,
        )
        embed.add_field(
            name="Guild",
            value="\n".join(self._format_health_line(row) for row in guild_rows[:15]) if guild_rows else "None",
            inline=False,
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)

    @mcp_group.command(name="list-tools", description="List discovered MCP tools for admin-global and this guild.")
    @app_commands.checks.has_permissions(administrator=True)
    async def tools_mcp_list_tools(self, interaction: discord.Interaction):
        if not await self._require_guild(interaction):
            return
        global_rows = await list_mcp_tools(scope_type=ADMIN_GLOBAL_SCOPE)
        guild_rows = await list_mcp_tools(scope_type=GUILD_SCOPE, guild_id=interaction.guild.id)

        def _render(rows: list[dict[str, object]]) -> str:
            if not rows:
                return "None"
            lines = []
            for row in rows[:15]:
                approved = "approved" if int(row.get("approved") or 0) else "pending"
                lines.append(f"{row.get('server_slug')}:{row.get('remote_tool_name')} [{approved}] -> {row.get('public_name') or row.get('remote_tool_name')}")
            return "\n".join(lines)

        embed = discord.Embed(
            title="MCP Tool Inventory",
            description="Approved tools are eligible for descriptor promotion; guild-scoped approvals still default deny until policy allows them.",
            color=discord.Color.teal(),
        )
        embed.add_field(name="Admin-Global", value=_render(global_rows), inline=False)
        embed.add_field(name="Guild", value=_render(guild_rows), inline=False)
        await interaction.response.send_message(embed=embed, ephemeral=True)

    @mcp_group.command(name="register-global", description="Register an admin-global MCP server.")
    @app_commands.check(_is_owner_check)
    async def tools_mcp_register_global(
        self,
        interaction: discord.Interaction,
        server_slug: str,
        command_line: str,
        trusted: bool = False,
        env_json: str | None = None,
    ):
        await register_admin_global_mcp_server(
            server_slug=server_slug,
            command_line=command_line,
            env=self._parse_env_json(env_json),
            trusted=trusted,
            actor_id=interaction.user.id,
            note="Registered via /tools mcp register-global",
        )
        await interaction.response.send_message(
            f"Registered admin-global MCP server `{server_slug}` with trusted={trusted}.",
            ephemeral=True,
        )

    @mcp_group.command(name="trust-global", description="Set trust for an admin-global MCP server.")
    @app_commands.check(_is_owner_check)
    async def tools_mcp_trust_global(self, interaction: discord.Interaction, server_slug: str, trusted: bool):
        await set_mcp_registration_trust(
            scope_type=ADMIN_GLOBAL_SCOPE,
            server_slug=server_slug,
            trusted=trusted,
            actor_id=interaction.user.id,
        )
        await interaction.response.send_message(
            f"Set admin-global MCP trust for `{server_slug}` to `{trusted}`.",
            ephemeral=True,
        )

    @mcp_group.command(name="enable-global", description="Enable or disable an admin-global MCP server.")
    @app_commands.check(_is_owner_check)
    async def tools_mcp_enable_global(self, interaction: discord.Interaction, server_slug: str, enabled: bool):
        await set_mcp_registration_enabled(
            scope_type=ADMIN_GLOBAL_SCOPE,
            server_slug=server_slug,
            enabled=enabled,
            actor_id=interaction.user.id,
        )
        await interaction.response.send_message(
            f"Set admin-global MCP enabled state for `{server_slug}` to `{enabled}`.",
            ephemeral=True,
        )

    @mcp_group.command(name="discover-global", description="Discover tools from an admin-global MCP server.")
    @app_commands.check(_is_owner_check)
    async def tools_mcp_discover_global(self, interaction: discord.Interaction, server_slug: str):
        try:
            discovered = await discover_mcp_tools(scope_type=ADMIN_GLOBAL_SCOPE, server_slug=server_slug)
        except Exception as exc:
            await interaction.response.send_message(f"Discovery failed: {exc}", ephemeral=True)
            return
        names = ", ".join(tool["name"] for tool in discovered) if discovered else "no tools"
        await interaction.response.send_message(
            f"Discovered {len(discovered)} tool(s) from `{server_slug}`: {names}.",
            ephemeral=True,
        )

    @mcp_group.command(name="approve-global", description="Approve a discovered admin-global MCP tool.")
    @app_commands.check(_is_owner_check)
    async def tools_mcp_approve_global(
        self,
        interaction: discord.Interaction,
        server_slug: str,
        remote_tool_name: str,
        category: str,
        public_name: str | None = None,
    ):
        try:
            await approve_mcp_tool(
                scope_type=ADMIN_GLOBAL_SCOPE,
                server_slug=server_slug,
                remote_tool_name=remote_tool_name,
                category=category,
                public_name=public_name,
                actor_id=interaction.user.id,
            )
        except ValueError as exc:
            await interaction.response.send_message(str(exc), ephemeral=True)
            return
        await interaction.response.send_message(
            f"Approved admin-global MCP tool `{server_slug}:{remote_tool_name}`.",
            ephemeral=True,
        )

    @mcp_group.command(name="register-guild", description="Register a guild-scoped MCP server.")
    @app_commands.checks.has_permissions(administrator=True)
    async def tools_mcp_register_guild(
        self,
        interaction: discord.Interaction,
        server_slug: str,
        command_line: str,
        env_json: str | None = None,
    ):
        if not await self._require_guild(interaction):
            return
        await register_guild_mcp_server(
            guild_id=interaction.guild.id,
            server_slug=server_slug,
            command_line=command_line,
            env=self._parse_env_json(env_json),
            actor_id=interaction.user.id,
            note="Registered via /tools mcp register-guild",
        )
        await interaction.response.send_message(
            f"Registered guild MCP server `{server_slug}`. Approved tools will still default deny until you explicitly allow them via `/tools policy set-tool` or category policy.",
            ephemeral=True,
        )

    @mcp_group.command(name="enable-guild", description="Enable or disable a guild-scoped MCP server.")
    @app_commands.checks.has_permissions(administrator=True)
    async def tools_mcp_enable_guild(self, interaction: discord.Interaction, server_slug: str, enabled: bool):
        if not await self._require_guild(interaction):
            return
        await set_mcp_registration_enabled(
            scope_type=GUILD_SCOPE,
            guild_id=interaction.guild.id,
            server_slug=server_slug,
            enabled=enabled,
            actor_id=interaction.user.id,
        )
        await interaction.response.send_message(
            f"Set guild MCP enabled state for `{server_slug}` to `{enabled}`.",
            ephemeral=True,
        )

    @mcp_group.command(name="discover-guild", description="Discover tools from a guild-scoped MCP server.")
    @app_commands.checks.has_permissions(administrator=True)
    async def tools_mcp_discover_guild(self, interaction: discord.Interaction, server_slug: str):
        if not await self._require_guild(interaction):
            return
        try:
            discovered = await discover_mcp_tools(
                scope_type=GUILD_SCOPE,
                guild_id=interaction.guild.id,
                server_slug=server_slug,
            )
        except Exception as exc:
            await interaction.response.send_message(f"Discovery failed: {exc}", ephemeral=True)
            return
        names = ", ".join(tool["name"] for tool in discovered) if discovered else "no tools"
        await interaction.response.send_message(
            f"Discovered {len(discovered)} guild tool(s) from `{server_slug}`: {names}.",
            ephemeral=True,
        )

    @mcp_group.command(name="approve-guild", description="Approve a discovered guild-scoped MCP tool.")
    @app_commands.checks.has_permissions(administrator=True)
    async def tools_mcp_approve_guild(
        self,
        interaction: discord.Interaction,
        server_slug: str,
        remote_tool_name: str,
        category: str,
        public_name: str | None = None,
    ):
        if not await self._require_guild(interaction):
            return
        try:
            await approve_mcp_tool(
                scope_type=GUILD_SCOPE,
                guild_id=interaction.guild.id,
                server_slug=server_slug,
                remote_tool_name=remote_tool_name,
                category=category,
                public_name=public_name,
                actor_id=interaction.user.id,
            )
        except ValueError as exc:
            await interaction.response.send_message(str(exc), ephemeral=True)
            return
        await interaction.response.send_message(
            (
                f"Approved guild MCP tool `{server_slug}:{remote_tool_name}`. "
                "It remains denied by default until you allow it with `/tools policy set-tool` "
                f"for `{public_name or remote_tool_name}` or a matching category policy."
            ),
            ephemeral=True,
        )


async def setup(bot: commands.Bot):
    await bot.add_cog(ToolsAdmin(bot))
