import importlib
import os
import sys
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "discord_bot"))

from tools.contracts import ToolCallEnvelope, ToolDescriptor, ToolInvocationMode, ToolSourceType


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


class ToolExecutorTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self._env = os.environ.copy()
        self._tmp = tempfile.TemporaryDirectory()
        os.environ["DATABASE_DIR"] = self._tmp.name

        from utils import db_handler as db_handler_mod
        from utils import tool_registry as tool_registry_mod
        from tools import executor as executor_mod
        from tools import policy_engine as policy_engine_mod

        self.db_handler = importlib.reload(db_handler_mod)
        self.tool_registry = importlib.reload(tool_registry_mod)
        self.executor = importlib.reload(executor_mod)
        self.policy_engine = importlib.reload(policy_engine_mod)
        self.tool_registry._reset_registry_for_tests()

    def tearDown(self):
        os.environ.clear()
        os.environ.update(self._env)
        self._tmp.cleanup()

    async def test_executor_blocks_manual_only_before_legacy_handler_runs(self):
        calls = {"count": 0}

        async def _handler(context, args):
            calls["count"] += 1
            return self.tool_registry.ToolResult(ok=True, summary="ok")

        self.tool_registry.register_tool(
            self.tool_registry.ToolDefinition(
                name="web_search",
                description="Search",
                args_schema={},
                handler=_handler,
                feature_flag="web_search_enabled",
            )
        )
        await self.db_handler.init_db()
        await self.policy_engine.upsert_tool_policy_rule(
            subject_type=self.policy_engine.POLICY_SUBJECT_TOOL,
            subject_id="rest:web_search",
            policy_mode="manual_only",
        )

        envelope = ToolCallEnvelope(
            call_id="abc",
            tool_name="web_search",
            arguments={"query": "cats"},
            invocation_mode=ToolInvocationMode.MODEL,
            raw_payload={"name": "web_search", "arguments": {"query": "cats"}},
        )
        result = await self.executor.execute_tool_envelope(envelope, _make_context(111))

        assert result.ok is False
        assert result.data["reason_code"] == "manual_only"
        assert calls["count"] == 0

    async def test_executor_rejects_invalid_arguments_before_backend_runs(self):
        await self.db_handler.init_db()
        descriptor = ToolDescriptor(
            tool_id="builtin:sum_numbers",
            public_name="sum_numbers",
            description="Add two integers",
            source_type=ToolSourceType.BUILTIN,
            category="discovery",
            input_schema={
                "type": "object",
                "properties": {
                    "a": {"type": "integer"},
                    "b": {"type": "integer"},
                },
                "required": ["a", "b"],
                "additionalProperties": False,
            },
        )
        self.executor.get_tool_registry().register_descriptor(descriptor)

        envelope = ToolCallEnvelope(
            call_id="bad-1",
            tool_name="sum_numbers",
            arguments={"a": "1", "b": 2},
            invocation_mode=ToolInvocationMode.MODEL,
        )
        result = await self.executor.execute_tool_envelope(envelope, _make_context(111))

        assert result.ok is False
        assert result.data["reason_code"] == "invalid_arguments"
