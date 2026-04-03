from __future__ import annotations

from typing import Any

from tools.audit import record_tool_execution
from tools.availability import compute_tool_availability_decisions
from tools.backends.mcp import execute_mcp_descriptor
from tools.contracts import ToolCallEnvelope
from tools.contracts import ToolSourceType
from tools.registry import get_tool_registry
from tools.validation import validate_arguments
from utils.tool_registry import ToolResult, execute_tool as execute_legacy_tool


_DENIAL_SUMMARIES = {
    "manual_only": "This tool is not available for automatic model use.",
    "admin_only_not_qualified": "You do not have permission to use this tool.",
    "feature_flag_disabled": "This tool is disabled for this server.",
    "dm_not_allowed": "This tool is only available in servers.",
    "user_permission_denied": "You do not have permission to use this tool.",
    "policy_denied": "This tool is disabled by policy.",
    "provider_not_supported": "This tool is unavailable for the current provider.",
    "model_not_supported": "This tool is unavailable for the current model.",
    "operational_state_inactive": "This tool is currently unavailable.",
    "invalid_arguments": "Tool arguments did not match the expected schema.",
}


def _denial_summary(reason_code: str | None) -> str:
    return _DENIAL_SUMMARIES.get(reason_code or "", "This tool is unavailable right now.")


async def execute_tool_envelope(envelope: ToolCallEnvelope, context: Any) -> ToolResult:
    registry = get_tool_registry()
    descriptor = registry.resolve_descriptor(envelope.tool_name)
    if descriptor is not None:
        decisions = await compute_tool_availability_decisions(context=context, descriptors=[descriptor])
        decision = decisions[0]
        if not decision.allowed:
            result = ToolResult(
                ok=False,
                summary=_denial_summary(decision.primary_reason_code),
                data={
                    "tool": descriptor.public_name,
                    "reason_code": decision.primary_reason_code,
                    "reason_detail": decision.reason_detail,
                },
            )
            await record_tool_execution(
                descriptor=descriptor,
                context=context,
                arguments=envelope.arguments,
                result=result,
                tool_name=envelope.tool_name,
                invocation_mode=envelope.invocation_mode.value,
                decision_outcome="denied",
                execution_outcome="denied",
                reason_codes=[decision.primary_reason_code] if decision.primary_reason_code else [],
                raw_payload=envelope.raw_payload or envelope.arguments,
                raw_result={"ok": result.ok, "summary": result.summary, "data": result.data},
            )
            return result

        validation_errors = validate_arguments(envelope.arguments, descriptor.input_schema)
        if validation_errors:
            error_payload = {
                "tool": descriptor.public_name,
                "reason_code": "invalid_arguments",
                "validation_errors": [
                    {"path": item.path, "message": item.message}
                    for item in validation_errors
                ],
            }
            result = ToolResult(
                ok=False,
                summary=_denial_summary("invalid_arguments"),
                data=error_payload,
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
                reason_codes=["invalid_arguments"],
                error_category="invalid_arguments",
                raw_payload=envelope.raw_payload or envelope.arguments,
                raw_result={"ok": result.ok, "summary": result.summary, "data": result.data},
            )
            return result

        if descriptor.source_type == ToolSourceType.MCP:
            return await execute_mcp_descriptor(descriptor, envelope, context)

    return await execute_legacy_tool(envelope.tool_name, envelope.arguments, context)
