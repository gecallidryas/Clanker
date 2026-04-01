import importlib
import os
import sys
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "discord_bot"))


def _make_context(
    *,
    guild_id: int | None,
    user_role_ids: list[int] | None = None,
    guild_config: dict | None = None,
):
    role_ids = user_role_ids or []
    guild = SimpleNamespace(id=guild_id) if guild_id is not None else None
    roles = [SimpleNamespace(id=role_id) for role_id in role_ids]
    user = SimpleNamespace(
        id=999,
        guild=guild,
        roles=roles,
        guild_permissions=SimpleNamespace(administrator=False),
    )
    return SimpleNamespace(
        guild=guild,
        channel=SimpleNamespace(id=555),
        user=user,
        message=None,
        guild_config=dict(guild_config or {}),
        provider_name=None,
        model_name=None,
        request_id=None,
        turn_id=None,
        debug_mode=False,
    )


class ToolAvailabilityTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self._env = os.environ.copy()
        self._tmp = tempfile.TemporaryDirectory()
        os.environ["DATABASE_DIR"] = self._tmp.name

        from utils import db_handler as db_handler_mod
        from utils import tool_registry as tool_registry_mod
        from tools import availability as availability_mod
        from tools import policy_engine as policy_engine_mod

        self.db_handler = importlib.reload(db_handler_mod)
        self.tool_registry = importlib.reload(tool_registry_mod)
        self.availability = importlib.reload(availability_mod)
        self.policy_engine = importlib.reload(policy_engine_mod)
        self.tool_registry._reset_registry_for_tests()

    def tearDown(self):
        os.environ.clear()
        os.environ.update(self._env)
        self._tmp.cleanup()

    async def test_shadow_report_matches_legacy_feature_flag_filtering(self):
        async def _noop(context, args):
            return self.tool_registry.ToolResult(ok=True, summary="ok")

        self.tool_registry.register_tool(
            self.tool_registry.ToolDefinition(
                name="web_search",
                description="Search",
                args_schema={},
                handler=_noop,
                feature_flag="web_search_enabled",
            )
        )
        self.tool_registry.register_tool(
            self.tool_registry.ToolDefinition(
                name="pin_message",
                description="Pin",
                args_schema={},
                handler=_noop,
                feature_flag="pin_message_enabled",
            )
        )

        context = _make_context(guild_id=111)
        report = await self.tool_registry.get_shadow_availability_report(context)

        assert report["legacy_enabled"] == ["web_search"]
        assert report["shadow_allowed"] == ["web_search"]
        assert report["only_legacy"] == []
        assert report["only_shadow"] == []

    async def test_manual_only_policy_hides_tool_from_shadow_allowed_set(self):
        async def _noop(context, args):
            return self.tool_registry.ToolResult(ok=True, summary="ok")

        self.tool_registry.register_tool(
            self.tool_registry.ToolDefinition(
                name="web_search",
                description="Search",
                args_schema={},
                handler=_noop,
                feature_flag="web_search_enabled",
            )
        )
        await self.db_handler.init_db()
        await self.policy_engine.upsert_tool_policy_rule(
            subject_type=self.policy_engine.POLICY_SUBJECT_TOOL,
            subject_id="rest:web_search",
            policy_mode="manual_only",
        )

        decisions = await self.availability.compute_tool_availability_decisions(context=_make_context(guild_id=111))
        decision = next(item for item in decisions if item.public_name == "web_search")

        assert decision.allowed is False
        assert decision.effective_policy_mode.value == "manual_only"
        assert decision.primary_reason_code == "manual_only"

    async def test_admin_only_policy_uses_level_two_staff(self):
        async def _noop(context, args):
            return self.tool_registry.ToolResult(ok=True, summary="ok")

        self.tool_registry.register_tool(
            self.tool_registry.ToolDefinition(
                name="pin_message",
                description="Pin",
                args_schema={},
                handler=_noop,
            )
        )
        guild_id = 777
        await self.db_handler.init_guild_db(guild_id)
        await self.db_handler.add_staff_role(guild_id, 10, 1)
        await self.db_handler.add_staff_role(guild_id, 20, 2)
        await self.policy_engine.upsert_tool_policy_rule(
            subject_type=self.policy_engine.POLICY_SUBJECT_TOOL,
            subject_id="builtin:pin_message",
            policy_mode="admin_only",
        )

        mod_context = _make_context(
            guild_id=guild_id,
            user_role_ids=[10],
            guild_config={"pin_message_enabled": 1},
        )
        admin_context = _make_context(
            guild_id=guild_id,
            user_role_ids=[20],
            guild_config={"pin_message_enabled": 1},
        )
        mod_decision = next(
            item
            for item in await self.availability.compute_tool_availability_decisions(context=mod_context)
            if item.public_name == "pin_message"
        )
        admin_decision = next(
            item
            for item in await self.availability.compute_tool_availability_decisions(context=admin_context)
            if item.public_name == "pin_message"
        )

        assert mod_decision.allowed is False
        assert mod_decision.primary_reason_code == "admin_only_not_qualified"
        assert admin_decision.allowed is True
