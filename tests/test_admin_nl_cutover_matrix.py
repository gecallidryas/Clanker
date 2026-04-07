import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "discord_bot"))

from utils.admin_nl import AdminNLContext, interpret_admin_request  # noqa: E402


@pytest.mark.parametrize(
    ("text", "intent"),
    [
        ("create channel announcements", "channel.create_text"),
        ("create category events", "channel.create_category"),
        ("create role VIP", "role.create"),
        ("give @Members to @Raider", "role.assign"),
        ("remove @Members from @Raider", "role.remove"),
        ("delete role Temp", "role.delete"),
        ("create starboard in #logs", "starboard.configure"),
        ("timeout @Raider for 10 minutes", "moderation.timeout"),
        ("kick @Raider", "moderation.kick"),
        ("unban <@666>", "moderation.unban"),
    ],
)
def test_cutover_matrix_intents(text, intent):
    context = AdminNLContext(
        current_channel_id=111,
        channel_mentions={"logs": 333},
        role_mentions={"members": 444},
        member_mentions={"raider": 666},
    )
    result = interpret_admin_request(text, context)
    assert result is not None
    assert result.intent == intent


@pytest.mark.parametrize(
    "text",
    [
        "what is the welcome message in #logs?",
        "show me the modlog channel",
        "what is the url safety action?",
    ],
)
def test_cutover_matrix_read_only_questions_do_not_parse(text):
    context = AdminNLContext(current_channel_id=111, channel_mentions={"logs": 333})
    assert interpret_admin_request(text, context) is None
