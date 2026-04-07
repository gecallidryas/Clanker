import sys
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "discord_bot"))

from utils import admin_actions  # noqa: E402


def _guild() -> SimpleNamespace:
    class _FakeRole:
        def __init__(self, role_id: int, name: str):
            self.id = role_id
            self.name = name
            self.delete = AsyncMock()

    class _FakeMember:
        def __init__(self, member_id: int, name: str):
            self.id = member_id
            self.display_name = name
            self.add_roles = AsyncMock()
            self.remove_roles = AsyncMock()

    class _FakeChannel:
        def __init__(self, channel_id: int, name: str):
            self.id = channel_id
            self.name = name
            self.delete = AsyncMock()

    class _FakeGuild(SimpleNamespace):
        def __init__(self):
            super().__init__(
                id=123,
                roles=[_FakeRole(444, "Members"), _FakeRole(555, "Temp")],
                channels=[_FakeChannel(222, "announcements"), _FakeChannel(333, "music")],
                categories=[_FakeChannel(777, "events")],
                members=[_FakeMember(666, "Raider")],
                create_text_channel=AsyncMock(return_value=_FakeChannel(901, "announcements")),
                create_voice_channel=AsyncMock(return_value=_FakeChannel(902, "music")),
                create_category=AsyncMock(return_value=_FakeChannel(903, "events")),
                fetch_channel=AsyncMock(return_value=None),
                fetch_member=AsyncMock(return_value=None),
                emojis=[],
            )

        def get_role(self, role_id: int):
            for role in self.roles:
                if role.id == role_id:
                    return role
            return None

        def get_member(self, member_id: int):
            for member in self.members:
                if member.id == member_id:
                    return member
            return None

        def get_channel(self, channel_id: int):
            for channel in [*self.channels, *self.categories]:
                if channel.id == channel_id:
                    return channel
            return None

    return _FakeGuild()


def _executor() -> SimpleNamespace:
    return SimpleNamespace(
        id=999,
        guild_permissions=SimpleNamespace(administrator=True, manage_guild=True),
    )


class AdminActionIntentTests(unittest.IsolatedAsyncioTestCase):
    async def test_execute_admin_intent_can_configure_starboard_from_typed_params(self):
        guild = _guild()
        get_settings = AsyncMock(return_value=None)
        upsert = AsyncMock()
        original_get = admin_actions.get_starboard_settings
        original_upsert = admin_actions.upsert_starboard_settings
        original_text_channel = admin_actions.discord.TextChannel
        fake_text_channel_type = type(guild.channels[1])
        admin_actions.get_starboard_settings = get_settings
        admin_actions.upsert_starboard_settings = upsert
        admin_actions.discord.TextChannel = fake_text_channel_type
        try:
            result = await admin_actions.execute_admin_intent(
                "starboard.configure",
                {"channel_id": 333, "emoji_mode": "any", "threshold": 5},
                guild,
                _executor(),
            )
        finally:
            admin_actions.get_starboard_settings = original_get
            admin_actions.upsert_starboard_settings = original_upsert
            admin_actions.discord.TextChannel = original_text_channel

        upsert.assert_awaited_once_with(
            123,
            333,
            [],
            5,
            allow_self_star=False,
            enabled=True,
            emoji_mode="any",
        )
        self.assertTrue(result["success"])

    async def test_execute_admin_intent_can_create_text_channel(self):
        guild = _guild()

        result = await admin_actions.execute_admin_intent(
            "channel.create_text",
            {"channel_name": "announcements"},
            guild,
            _executor(),
        )

        guild.create_text_channel.assert_awaited_once_with("announcements")
        self.assertTrue(result["success"])

    async def test_execute_admin_intent_can_create_voice_channel(self):
        guild = _guild()

        result = await admin_actions.execute_admin_intent(
            "channel.create_voice",
            {"channel_name": "music"},
            guild,
            _executor(),
        )

        guild.create_voice_channel.assert_awaited_once_with("music")
        self.assertTrue(result["success"])

    async def test_execute_admin_intent_can_create_category(self):
        guild = _guild()

        result = await admin_actions.execute_admin_intent(
            "channel.create_category",
            {"channel_name": "events"},
            guild,
            _executor(),
        )

        guild.create_category.assert_awaited_once_with("events")
        self.assertTrue(result["success"])

    async def test_execute_admin_intent_can_delete_channel_by_name(self):
        guild = _guild()
        channel = guild.channels[0]

        result = await admin_actions.execute_admin_intent(
            "channel.delete",
            {"channel_name": "announcements"},
            guild,
            _executor(),
        )

        channel.delete.assert_awaited_once()
        self.assertTrue(result["success"])

    async def test_execute_admin_intent_can_create_role(self):
        guild = _guild()
        guild.create_role = AsyncMock()

        result = await admin_actions.execute_admin_intent(
            "role.create",
            {"role_name": "VIP"},
            guild,
            _executor(),
        )

        guild.create_role.assert_awaited_once_with(name="VIP")
        self.assertTrue(result["success"])

    async def test_execute_admin_intent_can_delete_role(self):
        guild = _guild()
        role = guild.roles[1]

        result = await admin_actions.execute_admin_intent(
            "role.delete",
            {"role_name": "Temp"},
            guild,
            _executor(),
        )

        role.delete.assert_awaited_once()
        self.assertTrue(result["success"])

    async def test_execute_admin_intent_can_assign_role(self):
        guild = _guild()
        member = guild.members[0]
        role = guild.roles[0]

        result = await admin_actions.execute_admin_intent(
            "role.assign",
            {"role_id": 444, "target_id": 666},
            guild,
            _executor(),
        )

        member.add_roles.assert_awaited_once_with(role)
        self.assertTrue(result["success"])

    async def test_execute_admin_intent_can_remove_role(self):
        guild = _guild()
        member = guild.members[0]
        role = guild.roles[0]

        result = await admin_actions.execute_admin_intent(
            "role.remove",
            {"role_id": 444, "target_id": 666},
            guild,
            _executor(),
        )

        member.remove_roles.assert_awaited_once_with(role)
        self.assertTrue(result["success"])

    async def test_execute_admin_intent_channel_delete_errors_are_stable(self):
        guild = _guild()

        missing_result = await admin_actions.execute_admin_intent(
            "channel.delete",
            {},
            guild,
            _executor(),
        )
        not_found_result = await admin_actions.execute_admin_intent(
            "channel.delete",
            {"channel_name": "missing"},
            guild,
            _executor(),
        )

        self.assertEqual(missing_result, {"success": False, "error": "Missing channel target."})
        self.assertEqual(not_found_result, {"success": False, "error": "I couldn't find that channel."})

    async def test_execute_admin_intent_role_assignment_errors_are_stable(self):
        guild = _guild()

        missing_result = await admin_actions.execute_admin_intent(
            "role.assign",
            {"role_id": 444},
            guild,
            _executor(),
        )
        missing_role_result = await admin_actions.execute_admin_intent(
            "role.assign",
            {"role_name": "Missing", "target_id": 666},
            guild,
            _executor(),
        )
        missing_member_result = await admin_actions.execute_admin_intent(
            "role.assign",
            {"role_id": 444, "target_id": 999},
            guild,
            _executor(),
        )

        self.assertEqual(missing_result, {"success": False, "error": "Missing target_id."})
        self.assertEqual(missing_role_result, {"success": False, "error": "I couldn't find that role."})
        self.assertEqual(missing_member_result, {"success": False, "error": "I couldn't find that member."})

    async def test_execute_admin_intent_can_toggle_starboard_ignore_channel(self):
        add_ignore = AsyncMock()
        set_enabled = AsyncMock()
        original = admin_actions.add_starboard_ignored_channel
        original_enabled = admin_actions.set_starboard_enabled
        admin_actions.add_starboard_ignored_channel = add_ignore
        admin_actions.set_starboard_enabled = set_enabled
        try:
            ignore_result = await admin_actions.execute_admin_intent(
                "starboard.ignore_channel",
                {"channel_id": 222},
                _guild(),
                _executor(),
            )
            toggle_result = await admin_actions.execute_admin_intent(
                "starboard.toggle",
                {"enabled": False},
                _guild(),
                _executor(),
            )
        finally:
            admin_actions.add_starboard_ignored_channel = original
            admin_actions.set_starboard_enabled = original_enabled

        add_ignore.assert_awaited_once_with(123, 222)
        set_enabled.assert_awaited_once_with(123, False)
        self.assertTrue(ignore_result["success"])
        self.assertTrue(toggle_result["success"])

    async def test_execute_admin_intent_can_update_spam_config(self):
        set_spam = AsyncMock()
        original = admin_actions.set_spam_config
        admin_actions.set_spam_config = set_spam
        try:
            result = await admin_actions.execute_admin_intent(
                "automod.spam.configure",
                {
                    "spam_timeout_enabled": True,
                    "spam_max_messages": 6,
                    "spam_window_seconds": 10,
                    "spam_timeout_minutes": 15,
                },
                _guild(),
                _executor(),
            )
        finally:
            admin_actions.set_spam_config = original

        set_spam.assert_awaited_once_with(
            123,
            {
                "spam_timeout_enabled": 1,
                "spam_max_messages": 6,
                "spam_window_seconds": 10,
                "spam_timeout_minutes": 15,
            },
        )
        self.assertTrue(result["success"])

    async def test_execute_admin_intent_can_update_url_safety(self):
        set_url_safety = AsyncMock()
        original = admin_actions.set_url_safety_config
        admin_actions.set_url_safety_config = set_url_safety
        try:
            result = await admin_actions.execute_admin_intent(
                "url_safety.configure",
                {"url_safety_enabled": True, "url_safety_action": "delete"},
                _guild(),
                _executor(),
            )
        finally:
            admin_actions.set_url_safety_config = original

        set_url_safety.assert_awaited_once_with(
            123,
            {"url_safety_enabled": 1, "url_safety_action": "delete"},
        )
        self.assertTrue(result["success"])

    async def test_execute_admin_intent_can_update_url_safety_lists(self):
        set_url_safety = AsyncMock()
        original = admin_actions.set_url_safety_config
        admin_actions.set_url_safety_config = set_url_safety
        try:
            result = await admin_actions.execute_admin_intent(
                "url_safety.configure",
                {
                    "url_safety_enabled": True,
                    "url_safety_action": "warn",
                    "url_allowlist": "example.com",
                    "url_blocklist": "bad.com",
                },
                _guild(),
                _executor(),
            )
        finally:
            admin_actions.set_url_safety_config = original

        set_url_safety.assert_awaited_once_with(
            123,
            {
                "url_safety_enabled": 1,
                "url_safety_action": "warn",
                "url_allowlist": "example.com",
                "url_blocklist": "bad.com",
            },
        )
        self.assertTrue(result["success"])

    async def test_execute_admin_intent_can_update_dm_welcome_message(self):
        set_dm_message = AsyncMock()
        original = admin_actions.set_dm_welcome_message
        admin_actions.set_dm_welcome_message = set_dm_message
        try:
            result = await admin_actions.execute_admin_intent(
                "welcome.dm.configure",
                {"dm_message": "check the rules"},
                _guild(),
                _executor(),
            )
        finally:
            admin_actions.set_dm_welcome_message = original

        set_dm_message.assert_awaited_once_with(123, "check the rules")
        self.assertTrue(result["success"])

    async def test_execute_admin_intent_can_clear_welcome_messages(self):
        set_welcome_message = AsyncMock()
        set_dm_message = AsyncMock()
        original_public = admin_actions.set_welcome_message_template
        original_dm = admin_actions.set_dm_welcome_message
        admin_actions.set_welcome_message_template = set_welcome_message
        admin_actions.set_dm_welcome_message = set_dm_message
        try:
            public_result = await admin_actions.execute_admin_intent(
                "welcome.message.clear",
                {},
                _guild(),
                _executor(),
            )
            dm_result = await admin_actions.execute_admin_intent(
                "welcome.dm.message.clear",
                {},
                _guild(),
                _executor(),
            )
        finally:
            admin_actions.set_welcome_message_template = original_public
            admin_actions.set_dm_welcome_message = original_dm

        set_welcome_message.assert_awaited_once_with(123, None)
        set_dm_message.assert_awaited_once_with(123, None)
        self.assertTrue(public_result["success"])
        self.assertTrue(dm_result["success"])

    async def test_execute_admin_intent_can_set_and_clear_autorole(self):
        set_autorole_id = AsyncMock()
        set_autorole_enabled = AsyncMock()
        original_set_id = admin_actions.set_autorole_id
        original_set_enabled = admin_actions.set_autorole_enabled
        admin_actions.set_autorole_id = set_autorole_id
        admin_actions.set_autorole_enabled = set_autorole_enabled
        try:
            set_result = await admin_actions.execute_admin_intent(
                "autorole.set",
                {"role_id": 444},
                _guild(),
                _executor(),
            )
            clear_result = await admin_actions.execute_admin_intent(
                "autorole.clear",
                {},
                _guild(),
                _executor(),
            )
        finally:
            admin_actions.set_autorole_id = original_set_id
            admin_actions.set_autorole_enabled = original_set_enabled

        set_autorole_id.assert_any_await(123, 444)
        set_autorole_id.assert_any_await(123, None)
        set_autorole_enabled.assert_any_await(123, True)
        set_autorole_enabled.assert_any_await(123, False)
        self.assertTrue(set_result["success"])
        self.assertTrue(clear_result["success"])

    async def test_execute_admin_intent_can_manage_staff_roles(self):
        add_staff_role = AsyncMock()
        remove_staff_role = AsyncMock(return_value=True)
        original_add = admin_actions.add_staff_role
        original_remove = admin_actions.remove_staff_role
        admin_actions.add_staff_role = add_staff_role
        admin_actions.remove_staff_role = remove_staff_role
        try:
            add_result = await admin_actions.execute_admin_intent(
                "staff.add",
                {"role_id": 555, "permission_level": 1},
                _guild(),
                _executor(),
            )
            remove_result = await admin_actions.execute_admin_intent(
                "staff.remove",
                {"role_id": 555},
                _guild(),
                _executor(),
            )
        finally:
            admin_actions.add_staff_role = original_add
            admin_actions.remove_staff_role = original_remove

        add_staff_role.assert_awaited_once_with(123, 555, 1)
        remove_staff_role.assert_awaited_once_with(123, 555)
        self.assertTrue(add_result["success"])
        self.assertTrue(remove_result["success"])

    async def test_execute_admin_action_routes_expanded_admin_action_names(self):
        set_spam = AsyncMock()
        original = admin_actions.set_spam_config
        admin_actions.set_spam_config = set_spam
        try:
            result = await admin_actions.execute_admin_action(
                "SPAM_CONFIG",
                {
                    "spam_timeout_enabled": True,
                    "spam_max_messages": 7,
                    "spam_window_seconds": 12,
                    "spam_timeout_minutes": 20,
                },
                _guild(),
                _executor(),
            )
        finally:
            admin_actions.set_spam_config = original

        set_spam.assert_awaited_once_with(
            123,
            {
                "spam_timeout_enabled": 1,
                "spam_max_messages": 7,
                "spam_window_seconds": 12,
                "spam_timeout_minutes": 20,
            },
        )
        self.assertTrue(result["success"])


if __name__ == "__main__":
    unittest.main()
