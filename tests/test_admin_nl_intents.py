import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "discord_bot"))

from utils.admin_nl import AdminNLContext, interpret_admin_request  # noqa: E402


def _context() -> AdminNLContext:
    return AdminNLContext(
        current_channel_id=111,
        channel_mentions={"highlights": 222, "logs": 333, "general": 123},
        role_mentions={"members": 444, "moderators": 555},
        member_mentions={"raider": 666},
        reply_member_id=777,
    )


def test_parse_starboard_any_emoji_threshold_and_channel_name():
    result = interpret_admin_request(
        "set up starboard in #highlights with any emoji at 4 reactions",
        _context(),
    )

    assert result is not None
    assert result.intent == "starboard.configure"
    assert result.params["channel_id"] == 222
    assert result.params["emoji_mode"] == "any"
    assert result.params["threshold"] == 4
    assert result.missing == []
    assert result.follow_up_question is None


def test_parse_create_text_channel_request():
    result = interpret_admin_request("create channel announcements", _context())

    assert result is not None
    assert result.intent == "channel.create_text"
    assert result.params["channel_name"] == "announcements"


def test_parse_create_voice_channel_request():
    result = interpret_admin_request("create voice channel music", _context())

    assert result is not None
    assert result.intent == "channel.create_voice"
    assert result.params["channel_name"] == "music"


def test_parse_create_category_request():
    result = interpret_admin_request("create category events", _context())

    assert result is not None
    assert result.intent == "channel.create_category"
    assert result.params["channel_name"] == "events"


def test_parse_create_role_request():
    result = interpret_admin_request("create role VIP", _context())

    assert result is not None
    assert result.intent == "role.create"
    assert result.params["role_name"] == "VIP"


def test_parse_assign_role_request():
    result = interpret_admin_request("give @Members to @Raider", _context())

    assert result is not None
    assert result.intent == "role.assign"
    assert result.params["role_id"] == 444
    assert result.params["target_id"] == 666


def test_parse_remove_role_request():
    result = interpret_admin_request("remove @Members from @Raider", _context())

    assert result is not None
    assert result.intent == "role.remove"
    assert result.params["role_id"] == 444
    assert result.params["target_id"] == 666


def test_parse_delete_role_request():
    result = interpret_admin_request("delete role Temp", _context())

    assert result is not None
    assert result.intent == "role.delete"
    assert result.params["role_name"] == "Temp"


def test_parse_welcome_dm_disable_request():
    result = interpret_admin_request(
        "turn off dm welcomes",
        _context(),
    )

    assert result is not None
    assert result.intent == "welcome.dm.toggle"
    assert result.params["dm_enabled"] is False
    assert result.requires_confirmation is False


def test_parse_welcome_dm_message_request():
    result = interpret_admin_request(
        'set the dm welcome message to "check the rules and enjoy your stay"',
        _context(),
    )

    assert result is not None
    assert result.intent == "welcome.dm.configure"
    assert result.params["dm_message"] == "check the rules and enjoy your stay"


def test_parse_welcome_public_channel_and_message():
    result = interpret_admin_request(
        'set the welcome message in #highlights to "welcome {member} to {guild}"',
        _context(),
    )

    assert result is not None
    assert result.intent == "welcome.configure"
    assert result.params["channel_id"] == 222
    assert result.params["message"] == "welcome {member} to {guild}"


def test_parse_spam_config_request():
    result = interpret_admin_request(
        "timeout spammers after 6 messages in 10 seconds for 15 minutes",
        _context(),
    )

    assert result is not None
    assert result.intent == "automod.spam.configure"
    assert result.params["spam_max_messages"] == 6
    assert result.params["spam_window_seconds"] == 10
    assert result.params["spam_timeout_minutes"] == 15
    assert result.params["spam_timeout_enabled"] is True


def test_parse_url_safety_delete_request():
    result = interpret_admin_request(
        "make url safety delete blocked links",
        _context(),
    )

    assert result is not None
    assert result.intent == "url_safety.configure"
    assert result.params["url_safety_enabled"] is True
    assert result.params["url_safety_action"] == "delete"


def test_parse_url_safety_warn_with_allowlist_entry():
    result = interpret_admin_request(
        "warn on unsafe urls and allow example.com",
        _context(),
    )

    assert result is not None
    assert result.intent == "url_safety.configure"
    assert result.params["url_safety_enabled"] is True
    assert result.params["url_safety_action"] == "warn"
    assert result.params["url_allowlist"] == "example.com"


def test_parse_url_safety_allow_links_from_domain():
    result = interpret_admin_request(
        "allow links from example.com in url safety",
        _context(),
    )

    assert result is not None
    assert result.intent == "url_safety.configure"
    assert result.params["url_allowlist"] == "example.com"


def test_parse_url_safety_blocklist_entry():
    result = interpret_admin_request(
        "block bad.com in url safety",
        _context(),
    )

    assert result is not None
    assert result.intent == "url_safety.configure"
    assert result.params["url_safety_enabled"] is True
    assert result.params["url_blocklist"] == "bad.com"
    assert result.missing == []


def test_parse_url_safety_block_links_from_domain():
    result = interpret_admin_request(
        "block links from bad.com in url safety",
        _context(),
    )

    assert result is not None
    assert result.intent == "url_safety.configure"
    assert result.params["url_blocklist"] == "bad.com"
    assert result.missing == []


def test_parse_url_safety_multiple_domains():
    result = interpret_admin_request(
        "allow example.com and bad.com in url safety",
        _context(),
    )

    assert result is not None
    assert result.intent == "url_safety.configure"
    assert result.params["url_allowlist"] == "example.com,bad.com"


def test_parse_modlog_set_to_this_channel():
    result = interpret_admin_request(
        "set the mod log to this channel",
        _context(),
    )

    assert result is not None
    assert result.intent == "modlog.set"
    assert result.params["channel_id"] == 111


def test_parse_modlog_single_token_spelling():
    result = interpret_admin_request(
        "set modlog to #logs",
        _context(),
    )

    assert result is not None
    assert result.intent == "modlog.set"
    assert result.params["channel_id"] == 333


def test_read_only_modlog_question_is_not_parsed_as_mutation():
    result = interpret_admin_request(
        "show me the modlog channel",
        _context(),
    )

    assert result is None


def test_parse_modlog_set_to_bare_channel_name():
    result = interpret_admin_request(
        "set mod log to general",
        _context(),
    )

    assert result is not None
    assert result.intent == "modlog.set"
    assert result.params["channel_id"] == 123


def test_parse_autorole_set_with_role_mention_name():
    result = interpret_admin_request(
        "set the autorole to @Members",
        _context(),
    )

    assert result is not None
    assert result.intent == "autorole.set"
    assert result.params["role_id"] == 444


def test_parse_autorole_set_with_raw_role_mention():
    result = interpret_admin_request(
        "set the autorole to <@&444>",
        _context(),
    )

    assert result is not None
    assert result.intent == "autorole.set"
    assert result.params["role_id"] == 444


def test_parse_staff_add_with_level():
    result = interpret_admin_request(
        "make @Moderators bot staff level 1",
        _context(),
    )

    assert result is not None
    assert result.intent == "staff.add"
    assert result.params["role_id"] == 555
    assert result.params["permission_level"] == 1


def test_parse_starboard_ignore_channel_request():
    result = interpret_admin_request(
        "make starboard ignore #logs",
        _context(),
    )

    assert result is not None
    assert result.intent == "starboard.ignore_channel"
    assert result.params["channel_id"] == 333


def test_parse_starboard_unignore_channel_request():
    result = interpret_admin_request(
        "make starboard unignore #logs",
        _context(),
    )

    assert result is not None
    assert result.intent == "starboard.unignore_channel"
    assert result.params["channel_id"] == 333


def test_parse_starboard_toggle_off_request():
    result = interpret_admin_request(
        "turn off starboard",
        _context(),
    )

    assert result is not None
    assert result.intent == "starboard.toggle"
    assert result.params["enabled"] is False


def test_parse_welcome_toggle_off_request():
    result = interpret_admin_request(
        "turn off welcome messages",
        _context(),
    )

    assert result is not None
    assert result.intent == "welcome.toggle"
    assert result.params["welcome_enabled"] is False
    assert result.missing == []


def test_parse_remove_welcome_messages_disables_welcomes():
    result = interpret_admin_request(
        "remove welcome messages",
        _context(),
    )

    assert result is not None
    assert result.intent == "welcome.toggle"
    assert result.params["welcome_enabled"] is False


def test_parse_clear_welcome_messages_with_channel_disables_welcomes():
    result = interpret_admin_request(
        "clear welcome messages in #general",
        _context(),
    )

    assert result is not None
    assert result.intent == "welcome.toggle"
    assert result.params["welcome_enabled"] is False


def test_read_only_welcome_question_is_not_parsed_as_mutation():
    result = interpret_admin_request(
        "what is the welcome message in #logs?",
        _context(),
    )

    assert result is None


def test_parse_clear_welcome_message_request():
    result = interpret_admin_request(
        "clear welcome message",
        _context(),
    )

    assert result is not None
    assert result.intent == "welcome.message.clear"
    assert result.missing == []


def test_parse_clear_dm_welcome_message_request():
    result = interpret_admin_request(
        "clear dm welcome message",
        _context(),
    )

    assert result is not None
    assert result.intent == "welcome.dm.message.clear"
    assert result.missing == []


def test_parse_automod_keyword_add_request():
    result = interpret_admin_request(
        'delete messages containing "spoiler slur"',
        _context(),
    )

    assert result is not None
    assert result.intent == "automod.keyword.add"
    assert result.params["keyword"] == "spoiler slur"
    assert result.params["action"] == "delete"


def test_parse_ban_request_without_confirmation():
    result = interpret_admin_request(
        "ban <@666> for raids",
        _context(),
    )

    assert result is not None
    assert result.intent == "moderation.ban"
    assert result.params["target_id"] == 666
    assert result.params["reason"] == "raids"
    assert result.requires_confirmation is False


def test_parse_timeout_request():
    result = interpret_admin_request(
        "timeout @Raider for 10 minutes",
        _context(),
    )

    assert result is not None
    assert result.intent == "moderation.timeout"
    assert result.params["target_id"] == 666
    assert result.params["duration"] == 10


def test_parse_timeout_request_uses_reply_target_when_present():
    result = interpret_admin_request(
        "timeout them for 10 minutes",
        _context(),
    )

    assert result is not None
    assert result.intent == "moderation.timeout"
    assert result.params["target_id"] == 777
    assert result.params["duration"] == 10


def test_parse_kick_request():
    result = interpret_admin_request(
        "kick @Raider",
        _context(),
    )

    assert result is not None
    assert result.intent == "moderation.kick"
    assert result.params["target_id"] == 666


def test_parse_kick_request_uses_reply_target_when_present():
    result = interpret_admin_request(
        "kick them",
        _context(),
    )

    assert result is not None
    assert result.intent == "moderation.kick"
    assert result.params["target_id"] == 777


def test_parse_unban_request():
    result = interpret_admin_request(
        "unban <@666>",
        _context(),
    )

    assert result is not None
    assert result.intent == "moderation.unban"
    assert result.params["target_id"] == 666


def test_parse_unban_request_uses_reply_target_when_present():
    result = interpret_admin_request(
        "unban them",
        _context(),
    )

    assert result is not None
    assert result.intent == "moderation.unban"
    assert result.params["target_id"] == 777


def test_parse_ban_request_uses_reply_target_when_present():
    result = interpret_admin_request(
        "ban them for raids",
        _context(),
    )

    assert result is not None
    assert result.intent == "moderation.ban"
    assert result.params["target_id"] == 777
    assert result.params["reason"] == "raids"


def test_parse_read_only_url_safety_question_is_not_parsed_as_mutation():
    result = interpret_admin_request(
        "what is the url safety action?",
        _context(),
    )

    assert result is None


def test_parse_delete_channel_requires_confirmation():
    result = interpret_admin_request(
        "delete channel #logs",
        _context(),
    )

    assert result is not None
    assert result.intent == "channel.delete"
    assert result.params["channel_id"] == 333
    assert result.requires_confirmation is True
    assert result.confirmation_scope == "delete_channel_or_category"


def test_parse_delete_channel_request():
    result = interpret_admin_request("delete channel announcements", _context())

    assert result is not None
    assert result.intent == "channel.delete"
    assert result.params["channel_name"] == "announcements"
    assert result.requires_confirmation is True


def test_parse_delete_channel_with_bare_name_requires_confirmation():
    result = interpret_admin_request(
        "delete channel general",
        _context(),
    )

    assert result is not None
    assert result.intent == "channel.delete"
    assert result.params["channel_id"] == 123
    assert result.requires_confirmation is True


def test_missing_starboard_channel_generates_follow_up_question():
    result = interpret_admin_request(
        "set up starboard with ⭐ at 3 reactions",
        _context(),
    )

    assert result is not None
    assert result.intent == "starboard.configure"
    assert result.missing == ["channel_id"]
    assert result.follow_up_question == "Which channel should I use for the starboard?"


def test_create_starboard_phrase_enters_follow_up_flow():
    result = interpret_admin_request(
        "create starboard in #logs",
        _context(),
    )

    assert result is not None
    assert result.intent == "starboard.configure"
    assert result.params["channel_id"] == 333
    assert result.missing == ["emoji_mode", "threshold"]
    assert result.follow_up_question == "Which emoji should trigger starboard, or should I allow any emoji?"


def test_send_posts_to_starboard_phrase_enters_follow_up_flow():
    result = interpret_admin_request(
        "send posts to starboard in #logs",
        _context(),
    )

    assert result is not None
    assert result.intent == "starboard.configure"
    assert result.params["channel_id"] == 333
    assert result.missing == ["emoji_mode", "threshold"]


def test_read_only_starboard_status_question_is_not_parsed():
    result = interpret_admin_request(
        "what channel is starboard using?",
        _context(),
    )

    assert result is None


def test_starboard_more_than_increments_threshold_and_still_requires_emoji_choice():
    result = interpret_admin_request(
        "set up starboard with more than 4 reactions in #highlights",
        _context(),
    )

    assert result is not None
    assert result.intent == "starboard.configure"
    assert result.params["channel_id"] == 222
    assert result.params["threshold"] == 5
    assert "emoji_mode" not in result.params
    assert result.missing == ["emoji_mode"]
    assert result.follow_up_question == "Which emoji should trigger starboard, or should I allow any emoji?"


def test_parse_mode_change_request():
    result = interpret_admin_request(
        "switch the server to tsundere mode",
        _context(),
    )

    assert result is not None
    assert result.intent == "config.mode"
    assert result.params["mode"] == "tsundere"


def test_read_only_starboard_question_stays_unparsed():
    result = interpret_admin_request(
        "what channels can starboard use?",
        _context(),
    )

    assert result is None
