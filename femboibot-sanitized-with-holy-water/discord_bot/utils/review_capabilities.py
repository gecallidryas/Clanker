from __future__ import annotations

from typing import Any

from utils.tool_context import ToolContext
from utils.tool_registry import ToolDefinition, ToolResult, get_available_tools, render_tool_definitions


async def _handle_review_capabilities(context: ToolContext, args: dict[str, Any]) -> ToolResult:
    capability_type = (args.get("capability_type") or "chat").strip().lower()
    tools = get_available_tools(context.guild_config)
    summary = (
        f"Capabilities review ({capability_type}). "
        f"Tools available: {', '.join(t.name for t in tools) if tools else 'none'}."
    )
    details = render_tool_definitions(tools)
    return ToolResult(
        ok=True,
        summary=summary,
        data={
            "capability_type": capability_type,
            "tools": [tool.name for tool in tools],
            "details": details,
        },
    )


tool_review_capabilities = ToolDefinition(
    name="review_capabilities",
    description="Report available tools and capabilities for this server.",
    args_schema={"capability_type": "chat|vision|video (optional)"},
    handler=_handle_review_capabilities,
)
