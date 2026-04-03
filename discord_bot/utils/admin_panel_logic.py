from __future__ import annotations

import json
from dataclasses import dataclass
from enum import StrEnum
from math import ceil
from typing import Any, Iterable, Mapping, Sequence


class AuditCategory(StrEnum):
    CONFIG_GENERAL = "config_general"
    CONFIG_SECURITY = "config_security"
    CONFIG_ROUTING = "config_routing"
    CONFIG_DESTRUCTIVE = "config_destructive"
    PERSONA_PRESENTATION = "persona_presentation"
    PERSONA_CRUD = "persona_crud"
    TOOLS_CONFIG = "tools_config"


ALLOWED_AUDIT_CATEGORIES = tuple(category.value for category in AuditCategory)
AUDIT_CATEGORIES = ALLOWED_AUDIT_CATEGORIES


class ConfigAction(StrEnum):
    SET_SECRET = "provider_secret_update"
    CLEAR_LIST = "clear_all"
    UPDATE_MODLOG = "modlog_update"
    UPDATE_STAFF_ROLE = "staff_roles_update"
    UPDATE_ACTIVE_MODE = "persona_activate"
    TOGGLE_CAPABILITY = "capabilities_save"


class RiskLevel(StrEnum):
    LOW = "low"
    HIGH = "high"


class AuthGateState(StrEnum):
    ALLOWED = "allowed"
    AUTH_REQUIRED = "auth_required"
    PASSWORD_SETUP_REQUIRED = "password_setup_required"


@dataclass(frozen=True)
class ActionPolicy:
    risk: RiskLevel
    category: AuditCategory
    requires_auth: bool = False


ACTION_POLICIES: dict[str, ActionPolicy] = {
    "capabilities_save": ActionPolicy(
        risk=RiskLevel.LOW,
        category=AuditCategory.TOOLS_CONFIG,
    ),
    "tools_manage_save": ActionPolicy(
        risk=RiskLevel.LOW,
        category=AuditCategory.TOOLS_CONFIG,
    ),
    "ai_settings_save": ActionPolicy(
        risk=RiskLevel.LOW,
        category=AuditCategory.CONFIG_GENERAL,
    ),
    "ai_whitelist_save": ActionPolicy(
        risk=RiskLevel.LOW,
        category=AuditCategory.CONFIG_ROUTING,
    ),
    "ai_auto_channels_save": ActionPolicy(
        risk=RiskLevel.LOW,
        category=AuditCategory.CONFIG_ROUTING,
    ),
    "provider_secret_update": ActionPolicy(
        risk=RiskLevel.HIGH,
        category=AuditCategory.CONFIG_SECURITY,
        requires_auth=True,
    ),
    "provider_endpoint_update": ActionPolicy(
        risk=RiskLevel.HIGH,
        category=AuditCategory.CONFIG_SECURITY,
        requires_auth=True,
    ),
    "staff_roles_update": ActionPolicy(
        risk=RiskLevel.HIGH,
        category=AuditCategory.CONFIG_SECURITY,
        requires_auth=True,
    ),
    "modlog_update": ActionPolicy(
        risk=RiskLevel.HIGH,
        category=AuditCategory.CONFIG_SECURITY,
        requires_auth=True,
    ),
    "clear_all": ActionPolicy(
        risk=RiskLevel.HIGH,
        category=AuditCategory.CONFIG_DESTRUCTIVE,
        requires_auth=True,
    ),
    "welcome_settings_save": ActionPolicy(
        risk=RiskLevel.LOW,
        category=AuditCategory.CONFIG_ROUTING,
    ),
    "autorole_settings_save": ActionPolicy(
        risk=RiskLevel.LOW,
        category=AuditCategory.CONFIG_ROUTING,
    ),
    "persona_activate": ActionPolicy(
        risk=RiskLevel.LOW,
        category=AuditCategory.PERSONA_PRESENTATION,
    ),
    "persona_toggle_evil": ActionPolicy(
        risk=RiskLevel.LOW,
        category=AuditCategory.PERSONA_PRESENTATION,
    ),
    "persona_create": ActionPolicy(
        risk=RiskLevel.LOW,
        category=AuditCategory.PERSONA_CRUD,
    ),
    "persona_duplicate": ActionPolicy(
        risk=RiskLevel.LOW,
        category=AuditCategory.PERSONA_CRUD,
    ),
    "persona_edit": ActionPolicy(
        risk=RiskLevel.LOW,
        category=AuditCategory.PERSONA_CRUD,
    ),
    "persona_delete": ActionPolicy(
        risk=RiskLevel.HIGH,
        category=AuditCategory.PERSONA_CRUD,
        requires_auth=True,
    ),
}


LEGACY_CATEGORY_HINTS: tuple[tuple[tuple[str, ...], AuditCategory], ...] = (
    (("auth", "password", "secret", "key", "endpoint", "staff", "modlog"), AuditCategory.CONFIG_SECURITY),
    (("delete", "clear", "reset"), AuditCategory.CONFIG_DESTRUCTIVE),
    (
        (
            "persona_activate",
            "persona_mode",
            "persona_toggle_evil",
            "evil_mode",
            "mode_switch",
        ),
        AuditCategory.PERSONA_PRESENTATION,
    ),
    (("persona_",), AuditCategory.PERSONA_CRUD),
    (
        (
            "tool",
            "capabilities",
            "web_search",
            "image_gen",
            "youtube",
            "gif_responses",
            "self_teaching",
            "profile_peek",
            "pin_message",
            "rag",
            "emoji_usage",
            "sticker_usage",
        ),
        AuditCategory.TOOLS_CONFIG,
    ),
    (
        (
            "welcome",
            "autorole",
            "channel",
            "whitelist",
            "routing",
        ),
        AuditCategory.CONFIG_ROUTING,
    ),
)


@dataclass(frozen=True)
class ListOperationResult:
    updated: list[int]
    added: list[int]
    removed: list[int]
    cleared: bool


@dataclass(frozen=True)
class PaginationResult:
    items: list[Any]
    page: int
    page_size: int
    total_items: int
    total_pages: int
    has_previous: bool
    has_next: bool


def resolve_risk_level(action: str) -> RiskLevel:
    policy = ACTION_POLICIES.get((action or "").strip().lower())
    if policy:
        return policy.risk
    return RiskLevel.LOW


def action_requires_auth(action: str) -> bool:
    policy = ACTION_POLICIES.get((action or "").strip().lower())
    return bool(policy and policy.requires_auth)


def resolve_auth_gate(
    action: str,
    *,
    password_configured: bool,
    authenticated: bool,
) -> AuthGateState:
    if not action_requires_auth(action):
        return AuthGateState.ALLOWED
    if not password_configured:
        return AuthGateState.PASSWORD_SETUP_REQUIRED
    if not authenticated:
        return AuthGateState.AUTH_REQUIRED
    return AuthGateState.ALLOWED


def normalize_audit_category(
    category: str | AuditCategory | None,
    *,
    action: str | None = None,
) -> str:
    if category is not None:
        normalized = str(category).strip().lower()
        if normalized not in ALLOWED_AUDIT_CATEGORIES:
            raise ValueError(f"Unsupported audit category: {category}")
        return normalized

    action_key = (action or "").strip().lower()
    if action_key in ACTION_POLICIES:
        return ACTION_POLICIES[action_key].category.value

    for fragments, inferred_category in LEGACY_CATEGORY_HINTS:
        if any(fragment in action_key for fragment in fragments):
            return inferred_category.value
    return AuditCategory.CONFIG_GENERAL.value


def diff_toggle_states(
    current: Mapping[str, Any],
    proposed: Mapping[str, Any],
) -> dict[str, dict[str, Any]]:
    changed: dict[str, dict[str, Any]] = {}
    for key, new_value in proposed.items():
        raw_old = current.get(key)
        old_state = None if key not in current else _coerce_bool(raw_old)
        new_state = _coerce_bool(new_value)
        if old_state != new_state:
            changed[key] = {"old": old_state, "new": new_state}
    return dict(sorted(changed.items()))


def apply_list_operation(
    current: Sequence[Any],
    *,
    add: Iterable[Any] = (),
    remove: Iterable[Any] = (),
    clear: bool = False,
) -> ListOperationResult:
    current_ids = _coerce_int_list(current)
    if clear:
        return ListOperationResult(
            updated=[],
            added=[],
            removed=current_ids,
            cleared=bool(current_ids),
        )

    updated = list(current_ids)
    added_items: list[int] = []
    for item in _coerce_int_list(add):
        if item not in updated:
            updated.append(item)
            added_items.append(item)

    removed_items: list[int] = []
    for item in _coerce_int_list(remove):
        if item in updated:
            updated.remove(item)
            removed_items.append(item)

    return ListOperationResult(
        updated=updated,
        added=added_items,
        removed=removed_items,
        cleared=False,
    )


def paginate_items(
    items: Sequence[Any],
    *,
    page: int,
    page_size: int,
) -> PaginationResult:
    if page_size <= 0:
        raise ValueError("page_size must be positive")

    total_items = len(items)
    total_pages = max(1, ceil(total_items / page_size))
    safe_page = min(max(page, 0), total_pages - 1)
    start = safe_page * page_size
    end = start + page_size
    page_items = list(items[start:end])
    return PaginationResult(
        items=page_items,
        page=safe_page,
        page_size=page_size,
        total_items=total_items,
        total_pages=total_pages,
        has_previous=safe_page > 0,
        has_next=safe_page < total_pages - 1,
    )


def serialize_audit_detail(detail: Mapping[str, Any] | None) -> str | None:
    if not detail:
        return None
    return json.dumps(detail, ensure_ascii=True, sort_keys=True)


def deserialize_audit_detail(raw: str | None) -> dict[str, Any] | None:
    if not raw:
        return None
    try:
        parsed = json.loads(raw)
    except json.JSONDecodeError:
        return None
    if not isinstance(parsed, dict):
        return None
    return parsed


# Compatibility aliases for in-flight panel code while the new API settles.
def classify_action_risk(action_key: str) -> str:
    return resolve_risk_level(action_key).value


def requires_auth_for_action(action_key: str) -> bool:
    return action_requires_auth(action_key)


def requires_auth(action: ConfigAction | str) -> bool:
    if isinstance(action, ConfigAction):
        return action_requires_auth(action.value)
    return action_requires_auth(str(action))


def diff_config_values(
    before: Mapping[str, Any],
    after: Mapping[str, Any],
    *,
    keys: Iterable[str],
) -> dict[str, tuple[Any, Any]]:
    return {
        key: (before.get(key), after.get(key))
        for key in keys
        if before.get(key) != after.get(key)
    }


def apply_id_list_changes(
    current: Sequence[Any] | None,
    *,
    add: Sequence[Any] | None = None,
    remove: Sequence[Any] | None = None,
    clear: bool = False,
) -> list[int]:
    return apply_list_operation(
        current or [],
        add=add or (),
        remove=remove or (),
        clear=clear,
    ).updated


def reconcile_id_lists(
    current: Sequence[Any] | None,
    *,
    add: Sequence[Any] | None = None,
    remove: Sequence[Any] | None = None,
    clear: bool = False,
) -> list[int]:
    return apply_id_list_changes(current, add=add, remove=remove, clear=clear)


def paginate_sequence(items: Sequence[Any], *, page: int, page_size: int) -> PaginationResult:
    return paginate_items(items, page=page, page_size=page_size)


def normalize_audit_detail(detail: Mapping[str, Any] | None) -> str | None:
    return serialize_audit_detail(detail)


def _coerce_bool(value: Any) -> bool:
    if isinstance(value, str):
        lowered = value.strip().lower()
        if lowered in {"0", "false", "off", "no"}:
            return False
        if lowered in {"1", "true", "on", "yes"}:
            return True
    try:
        return bool(int(value))
    except (TypeError, ValueError):
        return bool(value)


def _coerce_int_list(values: Iterable[Any]) -> list[int]:
    parsed: list[int] = []
    for value in values:
        try:
            coerced = int(value)
        except (TypeError, ValueError):
            continue
        if coerced not in parsed:
            parsed.append(coerced)
    return parsed
