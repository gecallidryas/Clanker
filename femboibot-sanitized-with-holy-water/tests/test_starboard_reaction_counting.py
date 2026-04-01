import sys
import unittest
from pathlib import Path

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


if __name__ == "__main__":
    unittest.main()
