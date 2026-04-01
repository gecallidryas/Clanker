import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "discord_bot"))

from utils.admin_panel_logic import (  # noqa: E402
    AUDIT_CATEGORIES,
    ConfigAction,
    diff_toggle_states,
    normalize_audit_category,
    paginate_items,
    reconcile_id_lists,
    requires_auth,
)


def test_requires_auth_follows_risk_model():
    assert requires_auth(ConfigAction.SET_SECRET) is True
    assert requires_auth(ConfigAction.CLEAR_LIST) is True
    assert requires_auth(ConfigAction.UPDATE_MODLOG) is True
    assert requires_auth(ConfigAction.UPDATE_STAFF_ROLE) is True
    assert requires_auth(ConfigAction.UPDATE_ACTIVE_MODE) is False
    assert requires_auth(ConfigAction.TOGGLE_CAPABILITY) is False


def test_diff_toggle_states_returns_only_changes():
    before = {"a": True, "b": False, "c": True}
    after = {"a": False, "b": False, "c": True, "d": True}

    diff = diff_toggle_states(before, after)

    assert diff == {
        "a": {"old": True, "new": False},
        "d": {"old": None, "new": True},
    }


def test_reconcile_id_lists_supports_add_remove_clear():
    current = [10, 20, 30]

    added = reconcile_id_lists(current, add=[40, 20])
    assert added == [10, 20, 30, 40]

    removed = reconcile_id_lists(current, remove=[20, 99])
    assert removed == [10, 30]

    cleared = reconcile_id_lists(current, clear=True)
    assert cleared == []


def test_paginate_items_handles_boundaries():
    items = ["a", "b", "c", "d", "e"]

    result = paginate_items(items, page=999, page_size=2)
    assert result.items == ["e"]
    assert result.page == 2
    assert result.total_pages == 3

    result = paginate_items(items, page=-4, page_size=2)
    assert result.items == ["a", "b"]
    assert result.page == 0
    assert result.total_pages == 3


def test_normalize_audit_category_maps_legacy_actions():
    assert normalize_audit_category(None, action="persona_mode_switch") == "persona_presentation"
    assert normalize_audit_category(None, action="staff_role_added") == "config_security"
    assert normalize_audit_category(None, action="modlog_set") == "config_security"
    assert normalize_audit_category(None, action="tool_toggle_save") == "tools_config"


def test_normalize_audit_category_rejects_invalid_values():
    try:
        normalize_audit_category("made_up_category")
    except ValueError:
        pass
    else:
        raise AssertionError("Expected invalid category to raise ValueError")

    assert "persona_presentation" in AUDIT_CATEGORIES
