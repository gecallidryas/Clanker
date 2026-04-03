from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any

from tools.audit import record_tool_execution
from tools.mcp.control_plane import get_mcp_runtime_metadata, record_mcp_call_health
from tools.mcp.manager import call_tool
from tools.quarantine import update_quarantine_from_execution
from utils.tool_registry import ToolResult


def _context_guild_id(context: Any) -> int | None:
    guild = getattr(context, "guild", None)
    guild_id = getattr(guild, "id", None)
    if guild_id:
        return int(guild_id)
    direct_guild_id = getattr(context, "guild_id", None)
    return int(direct_guild_id) if direct_guild_id else None


def _extract_summary(result: dict[str, Any]) -> str:
    content = result.get("content")
    if isinstance(content, list):
        texts = [
            str(item.get("text") or "").strip()
            for item in content
            if isinstance(item, dict) and item.get("type") == "text"
        ]
        joined = "\n".join(text for text in texts if text)
        if joined:
            return joined
    structured = result.get("structuredContent")
    if isinstance(structured, dict) and structured:
        return json.dumps(structured, ensure_ascii=True, sort_keys=True)
    return "MCP tool completed."


def _cooldown_active(raw: Any) -> bool:
    if not raw:
        return False
    try:
        parsed = datetime.fromisoformat(str(raw))
    except ValueError:
        return False
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed > datetime.now(timezone.utc)


async def execute_mcp_descriptor(descriptor, envelope, context) -> ToolResult:
    try:
        runtime = await get_mcp_runtime_metadata(descriptor)
    except ValueError:
        result = ToolResult(ok=False, summary="MCP tool is misconfigured.")
        await record_tool_execution(
            descriptor=descriptor,
            context=context,
            arguments=envelope.arguments,
            result=result,
            tool_name=envelope.tool_name,
            invocation_mode=envelope.invocation_mode.value,
            decision_outcome="allowed",
            execution_outcome="error",
            reason_codes=["mcp_misconfigured"],
            error_category="backend_error",
            raw_payload=envelope.raw_payload or envelope.arguments,
            raw_result={"ok": result.ok, "summary": result.summary, "data": result.data},
        )
        return result

    registration = runtime["registration"]
    health = runtime["health"] or {}
    server_slug = runtime["server_slug"]
    remote_tool_name = runtime["remote_tool_name"]
    scope_type = runtime["scope_type"]
    guild_id = runtime["guild_id"]

    if registration is None:
        result = ToolResult(ok=False, summary="MCP server is not registered.")
        await record_tool_execution(
            descriptor=descriptor,
            context=context,
            arguments=envelope.arguments,
            result=result,
            tool_name=envelope.tool_name,
            invocation_mode=envelope.invocation_mode.value,
            decision_outcome="denied",
            execution_outcome="denied",
            reason_codes=["mcp_unregistered"],
            raw_payload=envelope.raw_payload or envelope.arguments,
            raw_result={"ok": result.ok, "summary": result.summary, "data": result.data},
        )
        return result

    if not int(registration.get("trusted") or 0):
        result = ToolResult(ok=False, summary="MCP server is not trusted.")
        await record_tool_execution(
            descriptor=descriptor,
            context=context,
            arguments=envelope.arguments,
            result=result,
            tool_name=envelope.tool_name,
            invocation_mode=envelope.invocation_mode.value,
            decision_outcome="denied",
            execution_outcome="denied",
            reason_codes=["mcp_untrusted"],
            raw_payload=envelope.raw_payload or envelope.arguments,
            raw_result={"ok": result.ok, "summary": result.summary, "data": result.data},
        )
        return result

    if not int(registration.get("enabled") or 0):
        result = ToolResult(ok=False, summary="MCP server is disabled.")
        await record_tool_execution(
            descriptor=descriptor,
            context=context,
            arguments=envelope.arguments,
            result=result,
            tool_name=envelope.tool_name,
            invocation_mode=envelope.invocation_mode.value,
            decision_outcome="denied",
            execution_outcome="denied",
            reason_codes=["mcp_disabled"],
            raw_payload=envelope.raw_payload or envelope.arguments,
            raw_result={"ok": result.ok, "summary": result.summary, "data": result.data},
        )
        return result

    cooldown_until = health.get("cooldown_until")
    if _cooldown_active(cooldown_until):
        result = ToolResult(ok=False, summary="MCP server is cooling down after recent failures.")
        await record_tool_execution(
            descriptor=descriptor,
            context=context,
            arguments=envelope.arguments,
            result=result,
            tool_name=envelope.tool_name,
            invocation_mode=envelope.invocation_mode.value,
            decision_outcome="denied",
            execution_outcome="denied",
            reason_codes=["mcp_cooldown_active"],
            raw_payload=envelope.raw_payload or envelope.arguments,
            raw_result={"ok": result.ok, "summary": result.summary, "data": result.data},
        )
        return result

    command = json.loads(registration["command_json"])
    env = json.loads(registration["env_json"] or "{}")
    try:
        payload = await call_tool(
            command=command,
            env=env,
            tool_name=remote_tool_name,
            arguments=envelope.arguments,
        )
        is_error = bool(payload.get("isError"))
        summary = _extract_summary(payload)
        result = ToolResult(
            ok=not is_error,
            summary=summary,
            data={"mcp": payload},
        )
        await record_tool_execution(
            descriptor=descriptor,
            context=context,
            arguments=envelope.arguments,
            result=result,
            tool_name=envelope.tool_name,
            invocation_mode=envelope.invocation_mode.value,
            decision_outcome="allowed",
            execution_outcome="success" if result.ok else "error",
            error_category=None if result.ok else "backend_error",
            raw_payload=envelope.raw_payload or envelope.arguments,
            raw_result={"ok": result.ok, "summary": result.summary, "data": result.data},
        )
        await record_mcp_call_health(
            scope_type=scope_type,
            guild_id=guild_id,
            server_slug=server_slug,
            status="ok" if result.ok else "error",
            error=None if result.ok else "mcp_result_error",
            cooldown_seconds=0 if not result.ok else 60,
        )
        await update_quarantine_from_execution(
            descriptor=descriptor,
            guild_id=_context_guild_id(context),
            execution_outcome="success" if result.ok else "error",
            error_category=None if result.ok else "backend_error",
        )
        return result
    except Exception as exc:
        result = ToolResult(ok=False, summary="MCP tool execution failed.", data={"error": str(exc)})
        await record_mcp_call_health(
            scope_type=scope_type,
            guild_id=guild_id,
            server_slug=server_slug,
            status="error",
            error=str(exc),
        )
        await record_tool_execution(
            descriptor=descriptor,
            context=context,
            arguments=envelope.arguments,
            result=result,
            tool_name=envelope.tool_name,
            invocation_mode=envelope.invocation_mode.value,
            decision_outcome="allowed",
            execution_outcome="error",
            reason_codes=["mcp_call_failed"],
            error_category="transport_error",
            raw_payload=envelope.raw_payload or envelope.arguments,
            raw_result={"ok": result.ok, "summary": result.summary, "data": result.data},
        )
        await update_quarantine_from_execution(
            descriptor=descriptor,
            guild_id=_context_guild_id(context),
            execution_outcome="error",
            error_category="transport_error",
        )
        return result
