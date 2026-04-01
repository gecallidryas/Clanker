import importlib
import os
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "discord_bot"))

from tools.contracts import ToolDescriptor, ToolPolicyMode, ToolSourceType


class _FakePermissions:
    def __init__(self, administrator: bool = False):
        self.administrator = administrator


class _FakeRole:
    def __init__(self, role_id: int):
        self.id = role_id


class _FakeGuild:
    def __init__(self, guild_id: int):
        self.id = guild_id


class _FakeMember:
    def __init__(self, guild_id: int, role_ids: list[int], administrator: bool = False):
        self.guild = _FakeGuild(guild_id)
        self.roles = [_FakeRole(role_id) for role_id in role_ids]
        self.guild_permissions = _FakePermissions(administrator=administrator)


class ToolPolicyEngineTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self._env = os.environ.copy()
        self._tmp = tempfile.TemporaryDirectory()
        os.environ["DATABASE_DIR"] = self._tmp.name

        from utils import db_handler as db_handler_mod
        from tools import policy_engine as policy_engine_mod

        self.db_handler = importlib.reload(db_handler_mod)
        self.policy_engine = importlib.reload(policy_engine_mod)

    def tearDown(self):
        os.environ.clear()
        os.environ.update(self._env)
        self._tmp.cleanup()

    async def test_policy_precedence_prefers_guild_tool_over_global_category(self):
        descriptor = ToolDescriptor(
            tool_id="rest:web_search",
            public_name="web_search",
            description="Search the web",
            source_type=ToolSourceType.REST,
            category="discovery",
        )

        await self.db_handler.init_db()
        await self.policy_engine.upsert_tool_policy_rule(
            subject_type=self.policy_engine.POLICY_SUBJECT_CATEGORY,
            subject_id="discovery",
            policy_mode="deny",
        )
        await self.policy_engine.upsert_tool_policy_rule(
            subject_type=self.policy_engine.POLICY_SUBJECT_TOOL,
            subject_id="rest:web_search",
            policy_mode="allow",
            scope_type=self.policy_engine.POLICY_SCOPE_GUILD,
            guild_id=123,
        )

        resolved = await self.policy_engine.resolve_tool_policy(descriptor, guild_id=123)

        assert resolved.effective_mode == ToolPolicyMode.ALLOW
        assert resolved.source == "guild:tool"

    async def test_policy_uses_descriptor_default_when_no_rules_match(self):
        descriptor = ToolDescriptor(
            tool_id="builtin:pin_message",
            public_name="pin_message",
            description="Pin a message",
            source_type=ToolSourceType.BUILTIN,
            category="moderation",
            default_policy_mode=ToolPolicyMode.ADMIN_ONLY,
        )

        await self.db_handler.init_db()
        resolved = await self.policy_engine.resolve_tool_policy(descriptor, guild_id=999)

        assert resolved.effective_mode == ToolPolicyMode.ADMIN_ONLY
        assert resolved.source == "descriptor_default"

    async def test_admin_only_qualification_requires_admin_or_level_two_staff(self):
        guild_id = 456
        await self.db_handler.init_guild_db(guild_id)
        await self.db_handler.add_staff_role(guild_id, 1001, 1)
        await self.db_handler.add_staff_role(guild_id, 1002, 2)

        admin_member = _FakeMember(guild_id, role_ids=[], administrator=True)
        level_two_member = _FakeMember(guild_id, role_ids=[1002])
        level_one_member = _FakeMember(guild_id, role_ids=[1001])

        assert await self.policy_engine.user_qualifies_for_admin_only(admin_member) is True
        assert await self.policy_engine.user_qualifies_for_admin_only(level_two_member) is True
        assert await self.policy_engine.user_qualifies_for_admin_only(level_one_member) is False
