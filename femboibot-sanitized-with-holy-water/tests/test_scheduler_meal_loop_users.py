import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "discord_bot"))

from cogs.scheduler import Scheduler  # noqa: E402


class _FakeBot:
    pass


def test_parse_user_timezone_row_dict_shape():
    scheduler = Scheduler(_FakeBot())
    parsed = scheduler._parse_user_timezone_row({"user_id": 123, "timezone": "America/New_York"})
    assert parsed == (123, "America/New_York")


def test_parse_user_timezone_row_tuple_shape():
    scheduler = Scheduler(_FakeBot())
    parsed = scheduler._parse_user_timezone_row((456, "UTC"))
    assert parsed == (456, "UTC")


def test_parse_user_timezone_row_malformed_returns_none():
    scheduler = Scheduler(_FakeBot())
    assert scheduler._parse_user_timezone_row({"user_id": None, "timezone": "UTC"}) is None
    assert scheduler._parse_user_timezone_row(("not-an-int", "UTC")) is None
