from __future__ import annotations

from typing import Any, Optional

from utils.db_handler import (
    add_fact_with_source,
    add_short_term_fact,
    create_user,
    get_personal_memory_opt_out,
)
from utils.memory_limits import (
    get_memory_limit_error_message,
    validate_fact_content,
)
from utils.tool_context import ToolContext
from utils.tool_registry import ToolDefinition, ToolResult


async def _store_fact(
    context: ToolContext,
    args: dict[str, Any],
    memory_type: str,
) -> ToolResult:
    fact = (args.get("fact") or "").strip()
    if not fact:
        return ToolResult(ok=False, summary="Missing fact.")
    validation = validate_fact_content(fact)
    if not validation.is_valid:
        return ToolResult(ok=False, summary=get_memory_limit_error_message(validation))
    user_id = args.get("user_id") or context.user.id
    try:
        user_id = int(user_id)
    except (TypeError, ValueError):
        user_id = context.user.id

    if memory_type in {"personal", "short_term", "long_term"}:
        opted_out = await get_personal_memory_opt_out(context.guild.id, user_id)
        if opted_out:
            return ToolResult(
                ok=False,
                summary="User opted out of personal memory; personal/short/long self-teaching is blocked.",
            )

    await create_user(context.guild.id, user_id)
    if memory_type == "short_term":
        await add_short_term_fact(
            context.guild.id,
            user_id,
            fact,
            channel_id=context.channel.id,
            source="learned",
            learned_from_user_id=context.user.id,
        )
    else:
        await add_fact_with_source(
            context.guild.id,
            user_id,
            fact,
            source="learned",
            learned_from_user_id=context.user.id,
            memory_type=memory_type,
        )
    scope_summary = {
        "personal": "Stored personal memory (durable unless deleted).",
        "short_term": "Stored short-term memory (temporary working context).",
        "long_term": "Stored long-term memory (durable preference/fact).",
    }.get(memory_type, f"Stored {memory_type} memory.")
    return ToolResult(ok=True, summary=scope_summary, data={"user_id": user_id, "fact": fact})


async def _handle_remember_this_fact(context: ToolContext, args: dict[str, Any]) -> ToolResult:
    return await _store_fact(context, args, "personal")


async def _handle_update_short_term(context: ToolContext, args: dict[str, Any]) -> ToolResult:
    return await _store_fact(context, args, "short_term")


async def _handle_update_long_term(context: ToolContext, args: dict[str, Any]) -> ToolResult:
    return await _store_fact(context, args, "long_term")


tool_remember_this_fact = ToolDefinition(
    name="remember_this_fact",
    description="Store a personal fact about a user.",
    args_schema={"fact": "fact text", "user_id": "optional target user id"},
    handler=_handle_remember_this_fact,
)

tool_update_short_term_memory = ToolDefinition(
    name="update_short_term_memory",
    description="Store short-term temporary memory about a user (subject to personal memory opt-out).",
    args_schema={"fact": "fact text", "user_id": "optional target user id"},
    handler=_handle_update_short_term,
)

tool_update_long_term_memory = ToolDefinition(
    name="update_long_term_memory",
    description="Store durable long-term memory about a user (subject to personal memory opt-out).",
    args_schema={"fact": "fact text", "user_id": "optional target user id"},
    handler=_handle_update_long_term,
)
