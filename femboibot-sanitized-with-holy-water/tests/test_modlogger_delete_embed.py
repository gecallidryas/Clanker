import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "discord_bot"))

from cogs.logger import ModLogger  # noqa: E402


class _FakeBot:
    pass


class _FakeAuthor:
    def __init__(self, user_id: int):
        self.id = user_id

    def __str__(self):
        return "TestUser"


class _FakeChannel:
    def __init__(self, channel_id: int):
        self.id = channel_id
        self.mention = f"<#{channel_id}>"


class _FakeAttachment:
    def __init__(self, filename: str, url: str, size: int = 100):
        self.filename = filename
        self.url = url
        self.proxy_url = url
        self.size = size


class _FakeMessage:
    def __init__(self):
        self.id = 123
        self.author = _FakeAuthor(456)
        self.channel = _FakeChannel(789)
        self.content = "hello world"
        self.created_at = datetime.now(timezone.utc)
        self.attachments = [_FakeAttachment("img.png", "https://cdn.example/img.png")]


def test_build_message_delete_embed_contains_expected_fields():
    logger_cog = ModLogger(_FakeBot())
    embed = logger_cog._build_message_delete_embed(_FakeMessage())

    field_names = [field.name for field in embed.fields]
    assert "Author" in field_names
    assert "Channel" in field_names
    assert "Message ID" in field_names
    assert "Content" in field_names
    assert "Attachments" in field_names
