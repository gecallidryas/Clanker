import sys
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "discord_bot"))

from cogs.starboard import Starboard  # noqa: E402


class _FakeBot:
    pass


class _FakeUser:
    def __init__(self, user_id: int):
        self.id = user_id


class _FakeReaction:
    def __init__(self, emoji, count: int, users):
        self.emoji = emoji
        self.count = count
        self._users = users

    async def users(self):
        for user in self._users:
            yield user


class _FakeMessage:
    def __init__(self, author_id: int, reactions):
        self.author = _FakeUser(author_id)
        self.reactions = reactions


class _FakeCustomEmoji:
    def __init__(self, emoji_id: int, name: str):
        self.id = emoji_id
        self.name = name

    def __str__(self):
        return f"<:{self.name}:{self.id}>"


class _FakeTextChannel:
    mention = "#channel"


class _FakeStarboardMessage:
    def __init__(self):
        self.delete = AsyncMock()


class _FakeStarboardChannel(_FakeTextChannel):
    def __init__(self, message):
        self._message = message

    async def fetch_message(self, _message_id: int):
        return self._message


class StarboardReactionCountingTests(unittest.IsolatedAsyncioTestCase):
    def test_reaction_matches_unicode_trigger(self):
        starboard = Starboard(_FakeBot())
        assert starboard._reaction_matches_trigger("\u2b50", "\u2b50")

    def test_reaction_matches_custom_trigger(self):
        starboard = Starboard(_FakeBot())
        custom = _FakeCustomEmoji(12345, "party")
        assert starboard._reaction_matches_trigger(custom, "<:party:12345>")

    def test_reaction_matches_variation_selector(self):
        starboard = Starboard(_FakeBot())
        assert starboard._reaction_matches_trigger("⭐️", "⭐")
        assert starboard._reaction_matches_trigger("⭐", "⭐️")

    def test_split_emoji_input_keeps_compound_unicode(self):
        starboard = Starboard(_FakeBot())
        assert starboard._split_emoji_input("👍🏽") == ["👍🏽"]

    async def test_effective_count_excludes_self_star(self):
        starboard = Starboard(_FakeBot())
        message = _FakeMessage(7, [])
        reaction = _FakeReaction("\u2b50", 3, [_FakeUser(7), _FakeUser(8), _FakeUser(9)])
        count = await starboard._effective_count(message, reaction, allow_self_star=False)
        assert count == 2

    async def test_resolve_best_reaction_list_mode(self):
        starboard = Starboard(_FakeBot())
        reactions = [
            _FakeReaction("\u2b50", 2, [_FakeUser(1), _FakeUser(2)]),
            _FakeReaction("\U0001F31F", 4, [_FakeUser(1), _FakeUser(2), _FakeUser(3), _FakeUser(4)]),
        ]
        message = _FakeMessage(99, reactions)
        emoji, count = await starboard._resolve_best_reaction(
            message,
            emoji_mode="list",
            triggers=["\u2b50", "\U0001F31F"],
            allow_self_star=True,
            payload_emoji=None,
        )
        assert emoji == "\U0001F31F"
        assert count == 4

    async def test_existing_entry_is_removed_when_count_drops_below_threshold(self):
        starboard = Starboard(_FakeBot())
        source_channel = _FakeTextChannel()
        starboard_message = _FakeStarboardMessage()
        starboard_channel = _FakeStarboardChannel(starboard_message)
        source_message = SimpleNamespace(
            id=555,
            guild=SimpleNamespace(id=123),
            author=SimpleNamespace(bot=False, mention="@user"),
        )

        with (
            patch("cogs.starboard.discord.TextChannel", _FakeStarboardChannel),
            patch(
                "cogs.starboard.get_starboard_settings",
                AsyncMock(
                    return_value={
                        "enabled": 1,
                        "channel_id": 999,
                        "threshold": 3,
                        "allow_self_star": 0,
                        "emoji_mode": "list",
                        "emoji_triggers": ["\u2b50"],
                        "emoji_trigger": "\u2b50",
                    }
                ),
            ),
            patch("cogs.starboard.get_starboard_ignored_channels", AsyncMock(return_value=set())),
            patch(
                "cogs.starboard.get_starboard_entry",
                AsyncMock(
                    return_value={
                        "original_message_id": 555,
                        "starboard_message_id": 777,
                        "channel_id": 111,
                        "emoji_used": "\u2b50",
                        "is_deleted": 0,
                    }
                ),
            ),
            patch("cogs.starboard.clear_starboard_entry", AsyncMock()) as clear_entry,
            patch("cogs.starboard.upsert_starboard_entry", AsyncMock()) as upsert_entry,
        ):
            starboard._fetch_channel = AsyncMock(side_effect=[source_channel, starboard_channel])
            starboard._fetch_message = AsyncMock(return_value=source_message)
            starboard._resolve_best_reaction = AsyncMock(return_value=("\u2b50", 1))
            starboard._create_or_update_starboard_message = AsyncMock(return_value=777)

            await starboard._reconcile_message(123, 111, 555)

        starboard._create_or_update_starboard_message.assert_not_awaited()
        starboard_message.delete.assert_awaited_once()
        clear_entry.assert_awaited_once_with(123, 555)
        upsert_entry.assert_not_awaited()


if __name__ == "__main__":
    unittest.main()
