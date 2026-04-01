import importlib
import os
import sys
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "discord_bot"))


def _make_context(guild_id: int):
    guild = SimpleNamespace(id=guild_id)
    return SimpleNamespace(
        guild=guild,
        channel=SimpleNamespace(id=222),
        user=SimpleNamespace(
            id=333,
            guild=guild,
            roles=[],
            guild_permissions=SimpleNamespace(administrator=False),
        ),
        message=None,
        guild_config={"web_search_enabled": 1},
        provider_name=None,
        model_name=None,
        request_id=None,
        turn_id=None,
        debug_mode=False,
    )


class ToolQuarantineTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self._env = os.environ.copy()
        self._tmp = tempfile.TemporaryDirectory()
        os.environ["DATABASE_DIR"] = self._tmp.name

        from utils import db_handler as db_handler_mod
        from utils import tool_registry as tool_registry_mod
        from tools import availability as availability_mod
        from tools import quarantine as quarantine_mod

        self.db_handler = importlib.reload(db_handler_mod)
        self.tool_registry = importlib.reload(tool_registry_mod)
        self.availability = importlib.reload(availability_mod)
        self.quarantine = importlib.reload(quarantine_mod)
        self.tool_registry._reset_registry_for_tests()

    def tearDown(self):
        os.environ.clear()
        os.environ.update(self._env)
        self._tmp.cleanup()

    async def test_repeated_exception_quarantines_tool_and_manual_clear_restores_it(self):
        async def _handler(context, args):
            raise RuntimeError("boom")

        self.tool_registry.register_tool(
            self.tool_registry.ToolDefinition(
                name="web_search",
                description="Search",
                args_schema={},
                handler=_handler,
                feature_flag="web_search_enabled",
            )
        )
        guild_id = 919
        context = _make_context(guild_id)
        await self.db_handler.init_db()

        for _ in range(3):
            await self.tool_registry.execute_tool("web_search", {"query": "cats"}, context)

        decisions = await self.availability.compute_tool_availability_decisions(context=context)
        decision = next(item for item in decisions if item.public_name == "web_search")
        assert decision.allowed is False
        assert decision.is_quarantined is True
        assert decision.primary_reason_code == "quarantined"

        await self.quarantine.clear_quarantine_state(guild_id=guild_id, tool_id="rest:web_search")
        decisions_after_clear = await self.availability.compute_tool_availability_decisions(context=context)
        decision_after_clear = next(item for item in decisions_after_clear if item.public_name == "web_search")
        assert decision_after_clear.allowed is True

    async def test_category_override_can_lower_threshold(self):
        async def _handler(context, args):
            raise RuntimeError("boom")

        self.tool_registry.register_tool(
            self.tool_registry.ToolDefinition(
                name="web_search",
                description="Search",
                args_schema={},
                handler=_handler,
                feature_flag="web_search_enabled",
            )
        )
        guild_id = 920
        context = _make_context(guild_id)
        await self.db_handler.init_db()
        await self.quarantine.set_quarantine_policy(
            category="discovery",
            failure_threshold=2,
            quarantine_minutes=10,
        )

        for _ in range(2):
            await self.tool_registry.execute_tool("web_search", {"query": "cats"}, context)

        decision = next(
            item
            for item in await self.availability.compute_tool_availability_decisions(context=context)
            if item.public_name == "web_search"
        )
        assert decision.allowed is False
        assert decision.primary_reason_code == "quarantined"
