import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "discord_bot"))

from utils.admin_nl import (  # noqa: E402
    AdminNLContext,
    PendingAdminRequest,
    interpret_admin_request,
    resume_admin_request,
)


def _context() -> AdminNLContext:
    return AdminNLContext(
        current_channel_id=111,
        channel_mentions={"highlights": 222, "logs": 333},
        role_mentions={"members": 444, "moderators": 555},
        member_mentions={"raider": 666},
        reply_member_id=777,
    )


def test_follow_up_completes_pending_starboard_request():
    initial = interpret_admin_request(
        "set up starboard with any emoji at 5 reactions",
        _context(),
    )

    assert initial is not None
    assert initial.missing == ["channel_id"]

    pending = PendingAdminRequest(
        intent=initial.intent,
        params=dict(initial.params),
        missing=list(initial.missing),
        requires_confirmation=initial.requires_confirmation,
        confirmation_scope=initial.confirmation_scope,
    )

    resumed = resume_admin_request(
        pending,
        "use #highlights",
        _context(),
    )

    assert resumed.intent == "starboard.configure"
    assert resumed.params["channel_id"] == 222
    assert resumed.params["emoji_mode"] == "any"
    assert resumed.params["threshold"] == 5
    assert resumed.missing == []
    assert resumed.follow_up_question is None


def test_create_channel_follow_up_resolves_missing_name():
    initial = interpret_admin_request("create channel", _context())

    assert initial is not None
    assert initial.intent == "channel.create_text"
    assert initial.missing == ["channel_name"]

    pending = PendingAdminRequest(
        intent=initial.intent,
        params=dict(initial.params),
        missing=list(initial.missing),
        requires_confirmation=initial.requires_confirmation,
        confirmation_scope=initial.confirmation_scope,
    )

    resumed = resume_admin_request(
        pending,
        "announcements",
        _context(),
    )

    assert resumed.intent == "channel.create_text"
    assert resumed.params["channel_name"] == "announcements"
    assert resumed.missing == []
    assert resumed.follow_up_question is None


def test_create_role_follow_up_resolves_missing_name():
    initial = interpret_admin_request("create role", _context())

    assert initial is not None
    assert initial.intent == "role.create"
    assert initial.missing == ["role_name"]

    pending = PendingAdminRequest(
        intent=initial.intent,
        params=dict(initial.params),
        missing=list(initial.missing),
        requires_confirmation=initial.requires_confirmation,
        confirmation_scope=initial.confirmation_scope,
    )

    resumed = resume_admin_request(
        pending,
        "VIP",
        _context(),
    )

    assert resumed.intent == "role.create"
    assert resumed.params["role_name"] == "VIP"
    assert resumed.missing == []


def test_assign_role_follow_up_resolves_missing_target():
    initial = interpret_admin_request("give @Members", _context())

    assert initial is not None
    assert initial.intent == "role.assign"
    assert initial.params["role_id"] == 444
    assert initial.missing == ["target_id"]

    pending = PendingAdminRequest(
        intent=initial.intent,
        params=dict(initial.params),
        missing=list(initial.missing),
        requires_confirmation=initial.requires_confirmation,
        confirmation_scope=initial.confirmation_scope,
    )

    resumed = resume_admin_request(
        pending,
        "@Raider",
        _context(),
    )

    assert resumed.params["target_id"] == 666
    assert resumed.missing == []


def test_follow_up_keeps_asking_when_required_slot_is_still_missing():
    initial = interpret_admin_request(
        "set the autorole",
        _context(),
    )

    assert initial is not None
    assert initial.missing == ["role_id"]

    pending = PendingAdminRequest(
        intent=initial.intent,
        params=dict(initial.params),
        missing=list(initial.missing),
        requires_confirmation=initial.requires_confirmation,
        confirmation_scope=initial.confirmation_scope,
    )

    resumed = resume_admin_request(
        pending,
        "yes do it",
        _context(),
    )

    assert resumed.intent == "autorole.set"
    assert resumed.missing == ["role_id"]
    assert resumed.follow_up_question == "Which role should I set as the autorole?"


def test_starboard_follow_up_can_fill_emoji_and_threshold_after_create_phrase():
    initial = interpret_admin_request("create starboard in #logs", _context())

    assert initial is not None
    assert initial.intent == "starboard.configure"
    assert initial.missing == ["emoji_mode", "threshold"]

    pending = PendingAdminRequest(
        intent=initial.intent,
        params=dict(initial.params),
        missing=list(initial.missing),
        requires_confirmation=initial.requires_confirmation,
        confirmation_scope=initial.confirmation_scope,
    )

    resumed = resume_admin_request(
        pending,
        "use any emoji and 5 reactions",
        _context(),
    )

    assert resumed.params["channel_id"] == 333
    assert resumed.params["emoji_mode"] == "any"
    assert resumed.params["threshold"] == 5
    assert resumed.missing == []


def test_delete_channel_follow_up_keeps_confirmation_requirement():
    initial = interpret_admin_request("delete channel", _context())

    assert initial is not None
    assert initial.missing == ["channel_id"]
    assert initial.requires_confirmation is True

    pending = PendingAdminRequest(
        intent=initial.intent,
        params=dict(initial.params),
        missing=list(initial.missing),
        requires_confirmation=initial.requires_confirmation,
        confirmation_scope=initial.confirmation_scope,
    )

    resumed = resume_admin_request(
        pending,
        "use #logs",
        _context(),
    )

    assert resumed.intent == "channel.delete"
    assert resumed.params["channel_id"] == 333
    assert resumed.missing == []
    assert resumed.requires_confirmation is True
    assert resumed.confirmation_scope == "delete_channel_or_category"


def test_ban_follow_up_resolves_target_member():
    context = AdminNLContext(
        current_channel_id=111,
        channel_mentions={"highlights": 222, "logs": 333},
        role_mentions={"members": 444, "moderators": 555},
        member_mentions={"raider": 666},
    )
    initial = interpret_admin_request("ban", context)

    assert initial is not None
    assert initial.intent == "moderation.ban"
    assert initial.missing == ["target_id"]

    pending = PendingAdminRequest(
        intent=initial.intent,
        params=dict(initial.params),
        missing=list(initial.missing),
        requires_confirmation=initial.requires_confirmation,
        confirmation_scope=initial.confirmation_scope,
    )

    resumed = resume_admin_request(
        pending,
        "@Raider",
        context,
    )

    assert resumed.params["target_id"] == 666
    assert resumed.missing == []


def test_staff_remove_follow_up_resolves_role():
    initial = interpret_admin_request("remove bot staff", _context())

    assert initial is not None
    assert initial.intent == "staff.remove"
    assert initial.missing == ["role_id"]

    pending = PendingAdminRequest(
        intent=initial.intent,
        params=dict(initial.params),
        missing=list(initial.missing),
        requires_confirmation=initial.requires_confirmation,
        confirmation_scope=initial.confirmation_scope,
    )

    resumed = resume_admin_request(
        pending,
        "@Moderators",
        _context(),
    )

    assert resumed.params["role_id"] == 555
    assert resumed.missing == []


def test_url_safety_follow_up_resolves_action():
    initial = interpret_admin_request("make url safety", _context())

    assert initial is not None
    assert initial.intent == "url_safety.configure"
    assert initial.missing == ["url_safety_action"]

    pending = PendingAdminRequest(
        intent=initial.intent,
        params=dict(initial.params),
        missing=list(initial.missing),
        requires_confirmation=initial.requires_confirmation,
        confirmation_scope=initial.confirmation_scope,
    )

    resumed = resume_admin_request(
        pending,
        "delete",
        _context(),
    )

    assert resumed.params["url_safety_action"] == "delete"
    assert resumed.missing == []
