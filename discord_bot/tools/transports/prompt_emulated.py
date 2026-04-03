from __future__ import annotations

from typing import Any, Optional

from tools.contracts import ToolCallEnvelope, ToolInvocationMode
from utils.tool_parser import extract_tool_call, strip_tool_call as _strip_tool_call


async def render_prompt_tool_definitions(context: Any) -> str:
    from tools.availability import get_allowed_tool_descriptors

    descriptors = await get_allowed_tool_descriptors(context=context)
    if not descriptors:
        return "No tools available."
    lines = []
    for descriptor in descriptors:
        input_schema = descriptor.input_schema if isinstance(descriptor.input_schema, dict) else {}
        properties = input_schema.get("properties") if isinstance(input_schema, dict) else {}
        if isinstance(properties, dict) and properties:
            args_desc = ", ".join(
                f"{key}: {str((value or {}).get('description') or (value or {}).get('type') or '').strip()}"
                for key, value in properties.items()
            )
        else:
            args_desc = "none"
        lines.append(f"- {descriptor.public_name}: {descriptor.description} (args: {args_desc})")
    return "\n".join(lines)


async def build_prompt_tool_schemas(context: Any) -> list[dict[str, Any]]:
    from tools.availability import get_allowed_tool_descriptors

    schemas: list[dict[str, Any]] = []
    for descriptor in await get_allowed_tool_descriptors(context=context):
        parameters = descriptor.input_schema if isinstance(descriptor.input_schema, dict) else {}
        if not parameters:
            parameters = {"type": "object", "properties": {}, "additionalProperties": False}
        schemas.append(
            {
                "name": descriptor.public_name,
                "description": descriptor.description,
                "parameters": parameters,
            }
        )
    return schemas


def parse_prompt_tool_call(
    text: str,
    *,
    invocation_mode: ToolInvocationMode = ToolInvocationMode.MODEL,
) -> Optional[ToolCallEnvelope]:
    payload = extract_tool_call(text)
    if not payload:
        return None
    return ToolCallEnvelope(
        call_id=payload.get("call_id"),
        tool_name=str(payload.get("name") or payload.get("tool") or "").strip(),
        arguments=payload.get("arguments") or payload.get("args") or {},
        invocation_mode=invocation_mode,
        raw_payload=payload,
    )


def strip_prompt_tool_call(text: str) -> str:
    return _strip_tool_call(text)
