from __future__ import annotations

from typing import Any

from tools.contracts import DmPolicy, ToolDescriptor, ToolTurnContext
from tools.descriptors import (
    get_legacy_category,
    get_legacy_side_effect_level,
    get_legacy_source_type,
)


def legacy_tool_to_descriptor(legacy_tool: Any) -> ToolDescriptor:
    name = str(getattr(legacy_tool, "name", "") or "").strip()
    source_type = get_legacy_source_type(name)
    args_schema = dict(getattr(legacy_tool, "args_schema", {}) or {})
    input_schema = {
        "type": "object",
        "properties": {
            str(key): {
                "type": "string",
                "description": str(value),
            }
            for key, value in args_schema.items()
        },
        "additionalProperties": False,
    }
    return ToolDescriptor(
        tool_id=f"{source_type.value}:{name}",
        public_name=name,
        display_name=name.replace("_", " ").title(),
        description=str(getattr(legacy_tool, "description", "") or "").strip() or name,
        source_type=source_type,
        source_ref=name,
        category=get_legacy_category(name),
        input_schema=input_schema,
        required_user_permission=getattr(legacy_tool, "required_permission", None),
        dm_policy=DmPolicy.ALLOW if bool(getattr(legacy_tool, "allow_in_dms", False)) else DmPolicy.DENY,
        side_effect_level=get_legacy_side_effect_level(name),
    )


def legacy_context_to_turn_context(context: Any) -> ToolTurnContext:
    guild = getattr(context, "guild", None)
    channel = getattr(context, "channel", None)
    user = getattr(context, "user", None)
    message = getattr(context, "message", None)
    return ToolTurnContext(
        request_id=getattr(context, "request_id", None),
        turn_id=getattr(context, "turn_id", None),
        guild_id=getattr(guild, "id", None),
        channel_id=getattr(channel, "id", None),
        thread_id=getattr(message, "thread", None) and getattr(message.thread, "id", None),
        user_id=getattr(user, "id", None),
        guild=guild,
        channel=channel,
        member=user,
        guild_config=dict(getattr(context, "guild_config", {}) or {}),
        provider_name=getattr(context, "provider_name", None),
        model_name=getattr(context, "model_name", None),
        provider_capabilities={},
        model_capabilities={},
        debug_mode=bool(getattr(context, "debug_mode", False)),
    )
