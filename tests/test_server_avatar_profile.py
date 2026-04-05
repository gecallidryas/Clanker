import asyncio
import sys
import types
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "discord_bot"))

if "aiosqlite" not in sys.modules:
    aiosqlite_stub = types.ModuleType("aiosqlite")

    class _Connection:
        pass

    async def _connect(*args, **kwargs):
        raise RuntimeError("aiosqlite stub should not be used in this test")

    aiosqlite_stub.Connection = _Connection
    aiosqlite_stub.Row = object
    aiosqlite_stub.connect = _connect
    sys.modules["aiosqlite"] = aiosqlite_stub

from utils import server_avatar, server_profile


class FakeUser:
    def __init__(self):
        self.edits = []

    async def edit(self, **kwargs):
        self.edits.append(kwargs)
        return self


class FakeMember:
    def __init__(self):
        self.edits = []

    async def edit(self, *, nick=..., avatar=..., banner=..., bio=...):
        payload = {}
        if nick is not ...:
            payload["nick"] = nick
        if avatar is not ...:
            payload["avatar"] = avatar
        if banner is not ...:
            payload["banner"] = banner
        if bio is not ...:
            payload["bio"] = bio
        self.edits.append(payload)
        return self


class LegacyMember:
    def __init__(self):
        self.edits = []

    async def edit(self, *, nick=None):
        self.edits.append({"nick": nick})
        return self


class FakeGuild:
    def __init__(self, member):
        self.me = member

    def get_member(self, user_id: int):
        return self.me


class FakeBot:
    def __init__(self, member=None):
        self.user = FakeUser()
        self._guild = FakeGuild(member) if member is not None else object()

    def get_guild(self, guild_id: int):
        if guild_id == 123:
            return self._guild
        return None


def test_set_server_avatar_prefers_member_profile_edit_when_supported():
    async def _run():
        member = FakeMember()
        bot = FakeBot(member=member)
        with mock.patch.object(
            server_avatar,
            "can_update_guild_avatar",
            new=mock.AsyncMock(return_value=(True, "ok")),
        ), mock.patch.object(
            server_avatar,
            "record_guild_avatar_update",
            new=mock.AsyncMock(),
        ) as record_update:
            success, reason = await server_avatar.set_server_avatar(bot, 123, b"avatar-bytes")

        assert (success, reason) == (True, "ok")
        assert member.edits == [{"avatar": b"avatar-bytes"}]
        assert bot.user.edits == []
        record_update.assert_awaited_once_with(123)

    asyncio.run(_run())


def test_set_server_avatar_falls_back_to_client_user_profile_edit_for_legacy_member_api():
    async def _run():
        bot = FakeBot(member=LegacyMember())
        with mock.patch.object(
            server_avatar,
            "can_update_guild_avatar",
            new=mock.AsyncMock(return_value=(True, "ok")),
        ), mock.patch.object(
            server_avatar,
            "record_guild_avatar_update",
            new=mock.AsyncMock(),
        ) as record_update:
            success, reason = await server_avatar.set_server_avatar(bot, 123, b"avatar-bytes")

        assert (success, reason) == (True, "ok")
        assert bot.user.edits == [{"avatar": b"avatar-bytes"}]
        record_update.assert_awaited_once_with(123)

    asyncio.run(_run())


def test_clear_server_avatar_prefers_member_profile_edit_when_supported():
    async def _run():
        member = FakeMember()
        bot = FakeBot(member=member)
        with mock.patch.object(
            server_avatar,
            "can_update_guild_avatar",
            new=mock.AsyncMock(return_value=(True, "ok")),
        ), mock.patch.object(
            server_avatar,
            "record_guild_avatar_update",
            new=mock.AsyncMock(),
        ) as record_update:
            success, reason = await server_avatar.clear_server_avatar(bot, 123)

        assert (success, reason) == (True, "ok")
        assert member.edits == [{"avatar": None}]
        assert bot.user.edits == []
        record_update.assert_awaited_once_with(123)

    asyncio.run(_run())


def test_set_member_profile_prefers_member_profile_edit_when_supported():
    async def _run():
        member = FakeMember()
        bot = FakeBot(member=member)
        success, reason = await server_profile.set_member_profile(
            bot,
            123,
            banner_bytes=b"banner-bytes",
            bio="guild bio",
        )

        assert (success, reason) == (True, "ok")
        assert member.edits == [{"banner": b"banner-bytes", "bio": "guild bio"}]
        assert bot.user.edits == []

    asyncio.run(_run())


def test_set_member_profile_falls_back_to_client_user_banner_edit_for_legacy_member_api():
    async def _run():
        bot = FakeBot(member=LegacyMember())
        success, reason = await server_profile.set_member_profile(
            bot,
            123,
            banner_bytes=b"banner-bytes",
            bio="ignored on legacy member api",
        )

        assert (success, reason) == (True, "ok")
        assert bot.user.edits == [{"banner": b"banner-bytes"}]

    asyncio.run(_run())
