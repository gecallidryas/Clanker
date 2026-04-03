from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Optional


class StrEnum(str, Enum):
    def __str__(self) -> str:
        return self.value


class ToolSourceType(StrEnum):
    BUILTIN = "builtin"
    REST = "rest"
    MCP = "mcp"


class ToolScopeType(StrEnum):
    GLOBAL = "global"
    ADMIN_GLOBAL = "admin_global"
    GUILD = "guild"


class ToolPolicyMode(StrEnum):
    ALLOW = "allow"
    DENY = "deny"
    ADMIN_ONLY = "admin_only"
    MANUAL_ONLY = "manual_only"


class ToolOperationalState(StrEnum):
    ACTIVE = "active"
    DISABLED = "disabled"
    DISCOVERED = "discovered"
    QUARANTINED = "quarantined"


class ToolTrustRequirement(StrEnum):
    NONE = "none"
    EXPLICIT_TRUST = "explicit_trust"
    DISCOVERY_APPROVAL = "discovery_approval"


class ToolInvocationMode(StrEnum):
    MODEL = "model"
    MANUAL = "manual"
    DEBUG = "debug"


class ToolStability(StrEnum):
    STABLE = "stable"
    EXPERIMENTAL = "experimental"
    LEGACY = "legacy"


class DmPolicy(StrEnum):
    ALLOW = "allow"
    DENY = "deny"


@dataclass(slots=True, frozen=True)
class ToolDescriptor:
    tool_id: str
    public_name: str
    description: str
    source_type: ToolSourceType
    category: str
    display_name: Optional[str] = None
    aliases: tuple[str, ...] = ()
    source_ref: Optional[str] = None
    scope_type: ToolScopeType = ToolScopeType.GLOBAL
    guild_id: Optional[int] = None
    tags: tuple[str, ...] = ()
    input_schema: dict[str, Any] = field(default_factory=dict)
    output_schema: dict[str, Any] = field(default_factory=dict)
    required_user_permission: Optional[str] = None
    required_bot_permissions: tuple[str, ...] = ()
    dm_policy: DmPolicy = DmPolicy.DENY
    provider_requirements: tuple[str, ...] = ()
    model_requirements: tuple[str, ...] = ()
    runtime_requirements: tuple[str, ...] = ()
    rate_limit_policy: dict[str, Any] = field(default_factory=dict)
    cooldown_policy: dict[str, Any] = field(default_factory=dict)
    side_effect_level: str = "read"
    default_policy_mode: ToolPolicyMode = ToolPolicyMode.ALLOW
    supports_model_invocation: bool = True
    supports_manual_invocation: bool = True
    stability: ToolStability = ToolStability.STABLE
    operational_state: ToolOperationalState = ToolOperationalState.ACTIVE
    trust_requirement: ToolTrustRequirement = ToolTrustRequirement.NONE

    def __post_init__(self) -> None:
        if not self.tool_id or ":" not in self.tool_id:
            raise ValueError("tool_id must be non-empty and namespaced.")
        if not self.public_name.strip():
            raise ValueError("public_name must be non-empty.")
        if not self.description.strip():
            raise ValueError("description must be non-empty.")
        if not self.category.strip():
            raise ValueError("category must be non-empty.")

    @property
    def effective_display_name(self) -> str:
        return (self.display_name or self.public_name).strip()


@dataclass(slots=True)
class ToolTurnContext:
    request_id: Optional[str]
    turn_id: Optional[str]
    guild_id: Optional[int]
    channel_id: Optional[int]
    thread_id: Optional[int]
    user_id: Optional[int]
    guild: Any = None
    channel: Any = None
    member: Any = None
    guild_config: dict[str, Any] = field(default_factory=dict)
    provider_name: Optional[str] = None
    model_name: Optional[str] = None
    provider_capabilities: dict[str, Any] = field(default_factory=dict)
    model_capabilities: dict[str, Any] = field(default_factory=dict)
    rate_limit_snapshot: dict[str, Any] = field(default_factory=dict)
    cooldown_snapshot: dict[str, Any] = field(default_factory=dict)
    debug_mode: bool = False
    timestamp: Optional[str] = None


@dataclass(slots=True, frozen=True)
class ToolAvailabilityDecision:
    tool_id: str
    public_name: str
    category: str
    candidate: bool
    allowed: bool
    effective_policy_mode: ToolPolicyMode
    is_quarantined: bool = False
    decision_layers: tuple[dict[str, Any], ...] = ()
    primary_reason_code: Optional[str] = None
    reason_detail: Optional[str] = None
    admin_visible_metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True, frozen=True)
class ToolCallEnvelope:
    call_id: Optional[str]
    tool_name: str
    arguments: dict[str, Any]
    invocation_mode: ToolInvocationMode = ToolInvocationMode.MODEL
    tool_id: Optional[str] = None
    raw_payload: Optional[dict[str, Any]] = None
    transport_metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True, frozen=True)
class ToolExecutionResult:
    status: str
    summary: str
    model_visible_output: Optional[str] = None
    user_visible_override: Optional[str] = None
    structured_output: dict[str, Any] = field(default_factory=dict)
    side_effects: tuple[dict[str, Any], ...] = ()
    latency_ms: Optional[int] = None
    error_category: Optional[str] = None
    retryable: bool = False
    redacted_args_summary: dict[str, Any] = field(default_factory=dict)
    redacted_result_summary: dict[str, Any] = field(default_factory=dict)
    raw_capture_eligible: bool = False
    backend_metadata: dict[str, Any] = field(default_factory=dict)
