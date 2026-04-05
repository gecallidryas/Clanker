from __future__ import annotations

import os
from dataclasses import dataclass, field
from time import perf_counter
from typing import Any, Awaitable, Callable, Optional

import discord

from tools.availability import compute_tool_availability_decisions
from tools.audit import record_tool_execution
from tools.compat import legacy_tool_to_descriptor
from tools.contracts import ToolTurnContext
from tools.quarantine import update_quarantine_from_execution
from tools.registry import get_tool_registry as get_unified_tool_registry
from utils.db_handler import get_staff_roles
from utils.logger import get_logger
from utils.tool_context import ToolContext
from utils.tool_flags import DEFAULT_FLAG_VALUES, get_tool_flag

logger = get_logger(__name__)


ToolHandler = Callable[[ToolContext, dict[str, Any]], Awaitable["ToolResult"]]


@dataclass(slots=True)
class ToolDefinition:
    name: str
    description: str
    args_schema: dict[str, str]
    handler: ToolHandler
    feature_flag: Optional[str] = None
    required_permission: Optional[str] = None  # "mod" | "admin" | None
    allow_in_dms: bool = False


@dataclass(slots=True)
class ToolResult:
    ok: bool
    summary: str
    data: dict[str, Any] = field(default_factory=dict)
    user_message: Optional[str] = None
    skip_model: bool = False

    def to_prompt(self) -> str:
        data = {"ok": self.ok, "summary": self.summary, "data": self.data}
        return f"[TOOL RESULT] {data}"


_registry: dict[str, ToolDefinition] = {}
_initialized = False


def register_tool(tool: ToolDefinition) -> None:
    name = tool.name.strip()
    if not name:
        raise ValueError("Tool name cannot be empty.")
    _registry[name] = tool
    get_unified_tool_registry().register_descriptor(legacy_tool_to_descriptor(tool))


def get_tool(name: str) -> Optional[ToolDefinition]:
    return _registry.get(name)


def list_tools() -> list[ToolDefinition]:
    return list(_registry.values())


def list_tool_descriptors():
    return get_unified_tool_registry().list_descriptors()


async def get_shadow_availability_report(context: ToolContext) -> dict[str, Any]:
    legacy_enabled = {tool.name for tool in get_available_tools(context.guild_config)}
    decisions = await compute_tool_availability_decisions(context=context)
    shadow_allowed = {decision.public_name for decision in decisions if decision.allowed}
    return {
        "legacy_enabled": sorted(legacy_enabled),
        "shadow_allowed": sorted(shadow_allowed),
        "only_legacy": sorted(legacy_enabled - shadow_allowed),
        "only_shadow": sorted(shadow_allowed - legacy_enabled),
        "decisions": decisions,
    }


async def get_runtime_available_tools(context: ToolContext | ToolTurnContext) -> list[ToolDefinition]:
    decisions = await compute_tool_availability_decisions(context=context)
    allowed_names = {decision.public_name for decision in decisions if decision.allowed}
    tools: list[ToolDefinition] = [tool for tool in _registry.values() if tool.name in allowed_names]
    missing_names = sorted(allowed_names - {tool.name for tool in tools})

    async def _unsupported_handler(context: ToolContext, args: dict[str, Any]) -> ToolResult:
        return ToolResult(ok=False, summary="Tool backend is unavailable.")

    registry = get_unified_tool_registry()
    for name in missing_names:
        descriptor = registry.resolve_descriptor(name)
        if descriptor is None:
            continue
        input_schema = descriptor.input_schema if isinstance(descriptor.input_schema, dict) else {}
        tools.append(
            ToolDefinition(
                name=descriptor.public_name,
                description=descriptor.description,
                args_schema={str(key): str(value) for key, value in input_schema.items()},
                handler=_unsupported_handler,
            )
        )
    return tools


async def render_runtime_tool_definitions(context: ToolContext | ToolTurnContext) -> str:
    return render_tool_definitions(await get_runtime_available_tools(context))


def _is_rag_env_enabled() -> bool:
    return str(os.getenv("ACTIVATE_LOCAL_RAG", "")).lower() in {"1", "true", "yes", "on"}


def _flag_enabled(flag: str, guild_config: dict[str, Any]) -> bool:
    if flag == "rag_enabled" and not _is_rag_env_enabled():
        return False
    value = guild_config.get(flag)
    if value is None:
        default_value = DEFAULT_FLAG_VALUES.get(flag, 1)
        return bool(default_value)
    try:
        return bool(int(value))
    except (TypeError, ValueError):
        return bool(value)


def is_tool_enabled(tool: ToolDefinition, guild_config: dict[str, Any]) -> bool:
    flag = tool.feature_flag or get_tool_flag(tool.name)
    if not flag:
        return True
    return _flag_enabled(flag, guild_config)


async def _get_permission_level(member: Optional[discord.Member]) -> int:
    if not member or not member.guild:
        return 0
    if member.guild_permissions.administrator:
        return 2
    staff_roles = await get_staff_roles(member.guild.id)
    user_role_ids = {role.id for role in member.roles}
    level = 0
    for role_id, permission_level in staff_roles:
        if role_id in user_role_ids:
            level = max(level, int(permission_level))
    return level


def _requires_permission(tool: ToolDefinition) -> int:
    required = (tool.required_permission or "").lower().strip()
    if required == "mod":
        return 1
    if required == "admin":
        return 2
    return 0


async def execute_tool(name: str, args: dict[str, Any], context: ToolContext) -> ToolResult:
    tool = _registry.get(name)
    descriptor = get_unified_tool_registry().resolve_descriptor(name)
    timer_started = perf_counter()
    if not tool:
        result = ToolResult(ok=False, summary="Unknown tool.", data={"tool": name})
        await record_tool_execution(
            descriptor=descriptor,
            context=context,
            arguments=args if isinstance(args, dict) else {},
            result=result,
            tool_name=name,
            invocation_mode="model",
            decision_outcome="unknown",
            execution_outcome="unavailable",
            reason_codes=["unknown_tool"],
            latency_ms=max(0, int((perf_counter() - timer_started) * 1000)),
            raw_payload=args if isinstance(args, dict) else {},
            raw_result={"ok": result.ok, "summary": result.summary, "data": result.data},
        )
        return result
    if not isinstance(args, dict):
        args = {}
    if not context.guild and not tool.allow_in_dms:
        result = ToolResult(ok=False, summary="This tool is only available in servers.")
        await record_tool_execution(
            descriptor=descriptor,
            context=context,
            arguments=args,
            result=result,
            tool_name=name,
            invocation_mode="model",
            decision_outcome="denied",
            execution_outcome="unavailable",
            reason_codes=["dm_not_allowed"],
            latency_ms=max(0, int((perf_counter() - timer_started) * 1000)),
            raw_payload=args,
            raw_result={"ok": result.ok, "summary": result.summary, "data": result.data},
        )
        return result
    if not is_tool_enabled(tool, context.guild_config):
        result = ToolResult(ok=False, summary="This tool is disabled for this server.")
        await record_tool_execution(
            descriptor=descriptor,
            context=context,
            arguments=args,
            result=result,
            tool_name=name,
            invocation_mode="model",
            decision_outcome="denied",
            execution_outcome="unavailable",
            reason_codes=["feature_flag_disabled"],
            latency_ms=max(0, int((perf_counter() - timer_started) * 1000)),
            raw_payload=args,
            raw_result={"ok": result.ok, "summary": result.summary, "data": result.data},
        )
        return result

    required_level = _requires_permission(tool)
    if required_level:
        level = await _get_permission_level(context.user)
        if level < required_level:
            result = ToolResult(ok=False, summary="You do not have permission to use this tool.")
            await record_tool_execution(
                descriptor=descriptor,
                context=context,
                arguments=args,
                result=result,
                tool_name=name,
                invocation_mode="model",
                decision_outcome="denied",
                execution_outcome="denied",
                reason_codes=["user_permission_denied"],
                latency_ms=max(0, int((perf_counter() - timer_started) * 1000)),
                raw_payload=args,
                raw_result={"ok": result.ok, "summary": result.summary, "data": result.data},
            )
            return result

    try:
        result = await tool.handler(context, args)
        if not isinstance(result, ToolResult):
            result = ToolResult(ok=False, summary="Tool returned no result.")
            outcome = "error"
            error_category = "invalid_result"
            reason_codes = ["invalid_tool_result"]
        else:
            outcome = "success" if result.ok else "error"
            error_category = None if result.ok else "tool_error"
            reason_codes = [] if result.ok else ["tool_returned_error"]
        await record_tool_execution(
            descriptor=descriptor,
            context=context,
            arguments=args,
            result=result,
            tool_name=name,
            invocation_mode="model",
            decision_outcome="allowed",
            execution_outcome=outcome,
            reason_codes=reason_codes,
            error_category=error_category,
            latency_ms=max(0, int((perf_counter() - timer_started) * 1000)),
            raw_payload=args,
            raw_result={"ok": result.ok, "summary": result.summary, "data": result.data},
        )
        await update_quarantine_from_execution(
            descriptor=descriptor,
            guild_id=getattr(getattr(context, "guild", None), "id", None) or getattr(context, "guild_id", None),
            execution_outcome=outcome,
            error_category=error_category,
        )
        return result
    except Exception as exc:
        logger.error("Tool %s failed: %s", name, exc, exc_info=True)
        result = ToolResult(ok=False, summary="Tool execution failed.", data={"error": str(exc)})
        await record_tool_execution(
            descriptor=descriptor,
            context=context,
            arguments=args,
            result=result,
            tool_name=name,
            invocation_mode="model",
            decision_outcome="allowed",
            execution_outcome="error",
            reason_codes=["tool_exception"],
            error_category="exception",
            latency_ms=max(0, int((perf_counter() - timer_started) * 1000)),
            raw_payload=args,
            raw_result={"ok": result.ok, "summary": result.summary, "data": result.data},
        )
        await update_quarantine_from_execution(
            descriptor=descriptor,
            guild_id=getattr(getattr(context, "guild", None), "id", None) or getattr(context, "guild_id", None),
            execution_outcome="error",
            error_category="exception",
        )
        return result


def get_available_tools(guild_config: dict[str, Any]) -> list[ToolDefinition]:
    tools: list[ToolDefinition] = []
    for tool in _registry.values():
        if is_tool_enabled(tool, guild_config):
            tools.append(tool)
    return tools


def render_tool_definitions(tools: list[ToolDefinition]) -> str:
    if not tools:
        return "No tools available."
    lines = []
    for tool in tools:
        args_desc = ", ".join(f"{k}: {v}" for k, v in tool.args_schema.items()) or "none"
        perm_note = f", permission: {tool.required_permission}" if tool.required_permission else ""
        lines.append(f"- {tool.name}: {tool.description} (args: {args_desc}{perm_note})")
    return "\n".join(lines)


def register_builtin_tools() -> None:
    global _initialized
    if _initialized:
        return

    from utils.time_tools import tool_get_current_time
    from utils.web_search import tool_web_search, tool_fetch_url
    from utils.image_generation import tool_generate_image
    from utils.expression_tools import (
        tool_select_sticker_for_response,
        tool_react_with_emoji,
    )
    from utils.media_context import tool_increase_media_context
    from utils.gif_processor import tool_process_gif
    from utils.gif_reply import tool_send_gif
    from utils.youtube import tool_process_youtube
    from utils.profile_peek import tool_peek_profile_picture
    from utils.self_teaching import (
        tool_remember_this_fact,
        tool_update_short_term_memory,
        tool_update_long_term_memory,
    )
    from utils.review_capabilities import tool_review_capabilities
    from utils.pin_tool import tool_pin_message

    for tool in [
        tool_review_capabilities,
        tool_get_current_time,
        tool_web_search,
        tool_fetch_url,
        tool_generate_image,
        tool_select_sticker_for_response,
        tool_react_with_emoji,
        tool_increase_media_context,
        tool_process_gif,
        tool_send_gif,
        tool_process_youtube,
        tool_pin_message,
        tool_peek_profile_picture,
        tool_remember_this_fact,
        tool_update_short_term_memory,
        tool_update_long_term_memory,
    ]:
        register_tool(tool)

    _initialized = True


def _reset_registry_for_tests() -> None:
    global _initialized
    _registry.clear()
    get_unified_tool_registry().clear()
    _initialized = False
