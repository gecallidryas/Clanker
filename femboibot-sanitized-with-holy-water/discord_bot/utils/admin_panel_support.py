from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any, Iterable, Mapping, Sequence


RISK_LOW = "low"
RISK_HIGH = "high"


AUDIT_CATEGORY_CONFIG_GENERAL = "config_general"
AUDIT_CATEGORY_CONFIG_SECURITY = "config_security"
AUDIT_CATEGORY_CONFIG_ROUTING = "config_routing"
AUDIT_CATEGORY_CONFIG_DESTRUCTIVE = "config_destructive"
AUDIT_CATEGORY_PERSONA_PRESENTATION = "persona_presentation"
AUDIT_CATEGORY_PERSONA_CRUD = "persona_crud"
AUDIT_CATEGORY_TOOLS_CONFIG = "tools_config"

VALID_AUDIT_CATEGORIES = {
    AUDIT_CATEGORY_CONFIG_GENERAL,
    AUDIT_CATEGORY_CONFIG_SECURITY,
    AUDIT_CATEGORY_CONFIG_ROUTING,
    AUDIT_CATEGORY_CONFIG_DESTRUCTIVE,
    AUDIT_CATEGORY_PERSONA_PRESENTATION,
    AUDIT_CATEGORY_PERSONA_CRUD,
    AUDIT_CATEGORY_TOOLS_CONFIG,
}

HIGH_RISK_ACTION_MARKERS = (
    "secret",
    "password",
    "auth",
    "staff_role",
    "modlog",
    "allowlist",
    "blocklist",
    "whitelist",
    "destructive",
    "delete",
    "clear_all",
    "endpoint",
)

LOW_RISK_ACTION_MARKERS = (
    "persona_activate",
    "persona_preview",
    "persona_evil_toggle",
    "tool_flags_save",
    "welcome_message_update",
    "welcome_toggle",
    "autorole_toggle",
    "ai_scalar_update",
)


@dataclass(frozen=True)
class PaginationResult:
    items: list[Any]
    page: int
    page_size: int
    total_items: int
    total_pages: int


def classify_action_risk(action_key: str) -> str:
    normalized = (action_key or "").strip().lower()
    if any(marker in normalized for marker in LOW_RISK_ACTION_MARKERS):
        return RISK_LOW
    if any(marker in normalized for marker in HIGH_RISK_ACTION_MARKERS):
        return RISK_HIGH
    if normalized.startswith("persona_") and "delete" not in normalized:
        return RISK_LOW
    if normalized.startswith("tool_"):
        return RISK_LOW
    return RISK_LOW


def requires_auth_for_action(action_key: str) -> bool:
    return classify_action_risk(action_key) == RISK_HIGH


def diff_config_values(
    before: Mapping[str, Any],
    after: Mapping[str, Any],
    *,
    keys: Iterable[str],
) -> dict[str, tuple[Any, Any]]:
    diff: dict[str, tuple[Any, Any]] = {}
    for key in keys:
        old_value = before.get(key)
        new_value = after.get(key)
        if old_value != new_value:
            diff[key] = (old_value, new_value)
    return diff


def apply_id_list_changes(
    current: Sequence[int] | None,
    *,
    add: Sequence[int] | None = None,
    remove: Sequence[int] | None = None,
    clear: bool = False,
) -> list[int]:
    if clear:
        return []

    seen: dict[int, None] = {}
    for value in current or []:
        seen[int(value)] = None

    for value in add or []:
        seen[int(value)] = None

    for value in remove or []:
        seen.pop(int(value), None)

    return list(seen.keys())


def paginate_sequence(items: Sequence[Any], *, page: int, page_size: int) -> PaginationResult:
    if page_size <= 0:
        raise ValueError("page_size must be positive")

    total_items = len(items)
    total_pages = max(1, (total_items + page_size - 1) // page_size)
    current_page = min(max(1, int(page)), total_pages)
    start = (current_page - 1) * page_size
    end = start + page_size
    return PaginationResult(
        items=list(items[start:end]),
        page=current_page,
        page_size=page_size,
        total_items=total_items,
        total_pages=total_pages,
    )


def infer_audit_category_from_action(action: str | None) -> str:
    normalized = (action or "").strip().lower()
    if normalized.startswith("persona_"):
        if "delete" in normalized or "create" in normalized or "duplicate" in normalized or "edit" in normalized:
            return AUDIT_CATEGORY_PERSONA_CRUD
        return AUDIT_CATEGORY_PERSONA_PRESENTATION
    if normalized in {"evil_mode_on", "evil_mode_off", "mode_change"}:
        return AUDIT_CATEGORY_PERSONA_PRESENTATION
    if normalized.startswith("key_") or normalized.startswith("password_") or normalized.startswith("auth_"):
        if "clear" in normalized:
            return AUDIT_CATEGORY_CONFIG_DESTRUCTIVE
        return AUDIT_CATEGORY_CONFIG_SECURITY
    if "custom_endpoint" in normalized or "url_safety" in normalized:
        if "clear" in normalized:
            return AUDIT_CATEGORY_CONFIG_DESTRUCTIVE
        return AUDIT_CATEGORY_CONFIG_SECURITY
    if normalized.startswith("ai_whitelist") or normalized.startswith("ai_auto_channel"):
        if "clear" in normalized:
            return AUDIT_CATEGORY_CONFIG_DESTRUCTIVE
        return AUDIT_CATEGORY_CONFIG_SECURITY
    if normalized.startswith("welcome_") or normalized.startswith("autorole_") or normalized.startswith("modlog_"):
        return AUDIT_CATEGORY_CONFIG_ROUTING
    if normalized.startswith("staff_"):
        return AUDIT_CATEGORY_CONFIG_SECURITY
    if normalized.endswith("_ui") or normalized.endswith("_set"):
        if "enabled" in normalized or "toggle" in normalized or "tool" in normalized:
            return AUDIT_CATEGORY_TOOLS_CONFIG
    if "clear" in normalized or "delete" in normalized:
        return AUDIT_CATEGORY_CONFIG_DESTRUCTIVE
    return AUDIT_CATEGORY_CONFIG_GENERAL


def normalize_audit_category(category: str | None, *, action: str | None = None) -> str:
    if category is None:
        return infer_audit_category_from_action(action)
    normalized = category.strip().lower()
    if normalized not in VALID_AUDIT_CATEGORIES:
        raise ValueError(f"Invalid audit category: {category}")
    return normalized


def normalize_audit_detail(detail: Mapping[str, Any] | None) -> str | None:
    if not detail:
        return None
    return json.dumps(detail, sort_keys=True, ensure_ascii=True)


def build_persona_selector_options(
    *,
    current_mode: str,
    builtins: Sequence[Mapping[str, Any]],
    customs: Sequence[Mapping[str, Any]],
) -> list[dict[str, Any]]:
    options: list[dict[str, Any]] = []
    current = next(
        (item for item in [*builtins, *customs] if item.get("mode_key") == current_mode),
        None,
    )
    if current:
        options.append(
            {
                "group": "active",
                "mode_key": current.get("mode_key"),
                "name": current.get("name"),
                "source": current.get("source"),
            }
        )

    for item in builtins:
        if item.get("mode_key") == current_mode:
            continue
        options.append(
            {
                "group": "builtin",
                "mode_key": item.get("mode_key"),
                "name": item.get("name"),
                "source": item.get("source"),
            }
        )

    for item in customs:
        if item.get("mode_key") == current_mode:
            continue
        options.append(
            {
                "group": "custom",
                "mode_key": item.get("mode_key"),
                "name": item.get("name"),
                "source": item.get("source"),
            }
        )

    return options
