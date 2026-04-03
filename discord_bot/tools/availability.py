from __future__ import annotations

import os
from datetime import datetime, timezone
from typing import Any, Optional

from tools.compat import legacy_context_to_turn_context
from tools.contracts import (
    DmPolicy,
    ToolAvailabilityDecision,
    ToolDescriptor,
    ToolOperationalState,
    ToolPolicyMode,
    ToolSourceType,
    ToolTurnContext,
)
from tools.mcp.control_plane import get_mcp_runtime_metadata
from tools.policy_engine import (
    list_tool_policy_rules,
    resolve_tool_policy_from_rules,
    user_qualifies_for_admin_only,
)
from tools.quarantine import list_quarantine_states
from tools.registry import get_tool_registry
from utils.db_handler import get_staff_roles
from utils.tool_flags import DEFAULT_FLAG_VALUES, get_tool_flag


def _rag_enabled() -> bool:
    return str(os.getenv("ACTIVATE_LOCAL_RAG", "")).lower() in {"1", "true", "yes", "on"}


def _feature_flag_enabled(flag: str, guild_config: dict[str, Any]) -> bool:
    if flag == "rag_enabled" and not _rag_enabled():
        return False
    value = guild_config.get(flag)
    if value is None:
        value = DEFAULT_FLAG_VALUES.get(flag, 1)
    try:
        return bool(int(value))
    except (TypeError, ValueError):
        return bool(value)


async def _user_permission_level(member: Any) -> int:
    if not member or not getattr(member, "guild", None):
        return 0
    permissions = getattr(member, "guild_permissions", None)
    if permissions and bool(getattr(permissions, "administrator", False)):
        return 2
    roles = getattr(member, "roles", None) or []
    role_ids = {int(getattr(role, "id", 0)) for role in roles if getattr(role, "id", None) is not None}
    if not role_ids:
        return 0
    staff_roles = await get_staff_roles(int(member.guild.id))
    level = 0
    for role_id, permission_level in staff_roles:
        if int(role_id) in role_ids:
            level = max(level, int(permission_level))
    return level


def _required_permission_level(required_permission: Optional[str]) -> int:
    normalized = str(required_permission or "").strip().lower()
    if normalized == "mod":
        return 1
    if normalized == "admin":
        return 2
    return 0


def _normalize_turn_context(context: ToolTurnContext | Any | None) -> ToolTurnContext:
    if isinstance(context, ToolTurnContext):
        return context
    if context is None:
        return ToolTurnContext(
            request_id=None,
            turn_id=None,
            guild_id=None,
            channel_id=None,
            thread_id=None,
            user_id=None,
        )
    return legacy_context_to_turn_context(context)


def _is_future_iso_timestamp(raw: Optional[str]) -> bool:
    if not raw:
        return False
    try:
        parsed = datetime.fromisoformat(str(raw))
    except ValueError:
        return False
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed > datetime.now(timezone.utc)


async def compute_tool_availability_decisions(
    *,
    context: ToolTurnContext | Any | None = None,
    descriptors: Optional[list[ToolDescriptor]] = None,
) -> list[ToolAvailabilityDecision]:
    turn_context = _normalize_turn_context(context)
    active_descriptors = descriptors if descriptors is not None else get_tool_registry().list_descriptors()
    policy_rules = await list_tool_policy_rules(guild_id=turn_context.guild_id, include_global=True)
    quarantine_states = {
        state.tool_id: state
        for state in await list_quarantine_states(guild_id=int(turn_context.guild_id or 0), active_only=True)
    } if turn_context.guild_id else {}
    decisions: list[ToolAvailabilityDecision] = []

    for descriptor in active_descriptors:
        layers: list[dict[str, Any]] = []
        allowed = True
        reason_code: Optional[str] = None
        reason_detail: Optional[str] = None

        if descriptor.operational_state != ToolOperationalState.ACTIVE:
            allowed = False
            reason_code = "operational_state_inactive"
            reason_detail = descriptor.operational_state.value
        layers.append(
            {
                "layer": "operational_state",
                "allowed": descriptor.operational_state == ToolOperationalState.ACTIVE,
                "value": descriptor.operational_state.value,
            }
        )

        quarantine_state = quarantine_states.get(descriptor.tool_id)
        layers.append(
            {
                "layer": "quarantine",
                "allowed": quarantine_state is None,
                "quarantined_until": quarantine_state.quarantined_until if quarantine_state else None,
            }
        )
        if allowed and quarantine_state is not None:
            allowed = False
            reason_code = "quarantined"
            reason_detail = quarantine_state.quarantined_until

        if descriptor.source_type == ToolSourceType.MCP:
            runtime = await get_mcp_runtime_metadata(descriptor)
            registration = runtime.get("registration")
            health = runtime.get("health") or {}
            registration_allowed = bool(registration and int(registration.get("enabled") or 0) and int(registration.get("trusted") or 0))
            cooldown_active = _is_future_iso_timestamp(health.get("cooldown_until"))
            layers.append(
                {
                    "layer": "mcp_registration",
                    "allowed": registration_allowed,
                    "scope_type": runtime.get("scope_type"),
                    "server_slug": runtime.get("server_slug"),
                    "trusted": bool(registration and int(registration.get("trusted") or 0)),
                    "enabled": bool(registration and int(registration.get("enabled") or 0)),
                }
            )
            layers.append(
                {
                    "layer": "mcp_health",
                    "allowed": not cooldown_active,
                    "cooldown_until": health.get("cooldown_until"),
                    "last_call_status": health.get("last_call_status"),
                }
            )
            if allowed and not registration_allowed:
                allowed = False
                if not registration:
                    reason_code = "mcp_unregistered"
                    reason_detail = runtime.get("server_slug")
                elif not int(registration.get("trusted") or 0):
                    reason_code = "mcp_untrusted"
                    reason_detail = runtime.get("server_slug")
                else:
                    reason_code = "mcp_disabled"
                    reason_detail = runtime.get("server_slug")
            if allowed and cooldown_active:
                allowed = False
                reason_code = "mcp_cooldown_active"
                reason_detail = str(health.get("cooldown_until") or "")

        if allowed and descriptor.provider_requirements:
            provider_name = str(turn_context.provider_name or "").strip().lower()
            expected = {item.strip().lower() for item in descriptor.provider_requirements if item.strip()}
            provider_allowed = provider_name in expected
            layers.append(
                {
                    "layer": "provider",
                    "allowed": provider_allowed,
                    "provider_name": provider_name,
                    "expected": sorted(expected),
                }
            )
            if not provider_allowed:
                allowed = False
                reason_code = "provider_not_supported"
                reason_detail = provider_name or "unknown"

        if allowed and descriptor.model_requirements:
            model_name = str(turn_context.model_name or "").strip().lower()
            expected_models = {item.strip().lower() for item in descriptor.model_requirements if item.strip()}
            model_allowed = model_name in expected_models
            layers.append(
                {
                    "layer": "model",
                    "allowed": model_allowed,
                    "model_name": model_name,
                    "expected": sorted(expected_models),
                }
            )
            if not model_allowed:
                allowed = False
                reason_code = "model_not_supported"
                reason_detail = model_name or "unknown"

        feature_flag = get_tool_flag(descriptor.public_name)
        if feature_flag:
            flag_allowed = _feature_flag_enabled(feature_flag, turn_context.guild_config)
            layers.append(
                {
                    "layer": "feature_flag",
                    "allowed": flag_allowed,
                    "flag": feature_flag,
                }
            )
            if allowed and not flag_allowed:
                allowed = False
                reason_code = "feature_flag_disabled"
                reason_detail = feature_flag

        resolved_policy = resolve_tool_policy_from_rules(
            descriptor,
            rules=policy_rules,
            guild_id=turn_context.guild_id,
        )
        layers.append(
            {
                "layer": "policy",
                "allowed": resolved_policy.effective_mode == ToolPolicyMode.ALLOW,
                "effective_mode": resolved_policy.effective_mode.value,
                "source": resolved_policy.source,
            }
        )
        if allowed:
            if resolved_policy.effective_mode == ToolPolicyMode.DENY:
                allowed = False
                reason_code = "policy_denied"
                reason_detail = resolved_policy.source
            elif resolved_policy.effective_mode == ToolPolicyMode.MANUAL_ONLY:
                allowed = False
                reason_code = "manual_only"
                reason_detail = resolved_policy.source
            elif resolved_policy.effective_mode == ToolPolicyMode.ADMIN_ONLY:
                qualifies = await user_qualifies_for_admin_only(turn_context.member)
                layers.append(
                    {
                        "layer": "admin_only",
                        "allowed": qualifies,
                    }
                )
                if not qualifies:
                    allowed = False
                    reason_code = "admin_only_not_qualified"
                    reason_detail = resolved_policy.source

        required_permission_level = _required_permission_level(descriptor.required_user_permission)
        if required_permission_level:
            user_level = await _user_permission_level(turn_context.member)
            permission_allowed = user_level >= required_permission_level
            layers.append(
                {
                    "layer": "user_permission",
                    "allowed": permission_allowed,
                    "required_level": required_permission_level,
                    "user_level": user_level,
                }
            )
            if allowed and not permission_allowed:
                allowed = False
                reason_code = "user_permission_denied"
                reason_detail = descriptor.required_user_permission

        if descriptor.dm_policy == DmPolicy.DENY:
            dm_allowed = turn_context.guild_id is not None
            layers.append(
                {
                    "layer": "dm_policy",
                    "allowed": dm_allowed,
                    "dm_policy": descriptor.dm_policy.value,
                }
            )
            if allowed and not dm_allowed:
                allowed = False
                reason_code = "dm_not_allowed"
                reason_detail = descriptor.public_name

        decisions.append(
            ToolAvailabilityDecision(
                tool_id=descriptor.tool_id,
                public_name=descriptor.public_name,
                category=descriptor.category,
                candidate=True,
                allowed=allowed,
                effective_policy_mode=resolved_policy.effective_mode,
                is_quarantined=quarantine_state is not None,
                decision_layers=tuple(layers),
                primary_reason_code=reason_code,
                reason_detail=reason_detail,
                admin_visible_metadata={
                    "policy_source": resolved_policy.source,
                    "feature_flag": feature_flag,
                    "required_permission": descriptor.required_user_permission,
                },
            )
        )

    return decisions


async def get_allowed_tool_descriptors(
    *,
    context: ToolTurnContext | Any | None = None,
    descriptors: Optional[list[ToolDescriptor]] = None,
) -> list[ToolDescriptor]:
    decisions = await compute_tool_availability_decisions(context=context, descriptors=descriptors)
    registry = get_tool_registry()
    allowed: list[ToolDescriptor] = []
    for decision in decisions:
        if not decision.allowed:
            continue
        descriptor = registry.get_descriptor(decision.tool_id)
        if descriptor is not None:
            allowed.append(descriptor)
    return allowed
