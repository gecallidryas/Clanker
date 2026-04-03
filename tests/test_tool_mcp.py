import importlib
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "discord_bot"))
sys.path.insert(0, str(ROOT))


class ToolMcpTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self._env = os.environ.copy()
        self._tmp = tempfile.TemporaryDirectory()
        os.environ["DATABASE_DIR"] = self._tmp.name
        os.environ["GLOBAL_DATABASE_PATH"] = str(Path(self._tmp.name) / "global.db")

        import utils.db_handler as db_handler_mod
        import tools.registry as unified_registry_mod
        import utils.tool_registry as tool_registry_mod
        import tools.policy_engine as policy_engine_mod
        import tools.mcp.control_plane as control_plane_mod
        import tools.availability as availability_mod
        import tools.backends.mcp as mcp_backend_mod
        import tools.executor as executor_mod

        self.db_handler = importlib.reload(db_handler_mod)
        self.unified_registry = importlib.reload(unified_registry_mod)
        self.tool_registry = importlib.reload(tool_registry_mod)
        self.policy_engine = importlib.reload(policy_engine_mod)
        self.control_plane = importlib.reload(control_plane_mod)
        self.availability = importlib.reload(availability_mod)
        self.mcp_backend = importlib.reload(mcp_backend_mod)
        self.executor = importlib.reload(executor_mod)
        self.tool_registry._reset_registry_for_tests()
        self.unified_registry.get_tool_registry().clear()

        from tools.contracts import ToolCallEnvelope, ToolInvocationMode, ToolTurnContext

        self.ToolCallEnvelope = ToolCallEnvelope
        self.ToolInvocationMode = ToolInvocationMode
        self.ToolTurnContext = ToolTurnContext
        self.fake_server = ROOT / "tests" / "helpers" / "fake_mcp_server.py"

    def tearDown(self):
        self._tmp.cleanup()
        os.environ.clear()
        os.environ.update(self._env)

    def _command_for(self, mode: str) -> str:
        return subprocess.list2cmdline([sys.executable, str(self.fake_server), "--mode", mode])

    def _context(self, guild_id: int = 123):
        return self.ToolTurnContext(
            request_id="req-1",
            turn_id="turn-1",
            guild_id=guild_id,
            channel_id=456,
            thread_id=None,
            user_id=789,
            guild=SimpleNamespace(id=guild_id),
            channel=None,
            member=None,
            guild_config={},
        )

    async def test_admin_global_discovery_requires_trust_and_approval_before_runtime(self):
        await self.control_plane.register_admin_global_mcp_server(
            server_slug="fake",
            command_line=self._command_for("success"),
            trusted=False,
        )
        discovered = await self.control_plane.discover_mcp_tools(server_slug="fake")
        self.assertEqual([tool["name"] for tool in discovered], ["echo"])
        self.assertEqual(self.tool_registry.list_tool_descriptors(), [])

        await self.control_plane.set_mcp_registration_trust(server_slug="fake", trusted=True)
        await self.control_plane.approve_mcp_tool(
            server_slug="fake",
            remote_tool_name="echo",
            category="discovery",
        )

        descriptor = self.tool_registry.list_tool_descriptors()[0]
        self.assertIsNotNone(descriptor)

        context = self._context()
        decisions = await self.availability.compute_tool_availability_decisions(context=context)
        decision = next(item for item in decisions if item.public_name == "echo")
        self.assertTrue(decision.allowed)

        result = await self.executor.execute_tool_envelope(
            self.ToolCallEnvelope(
                call_id="call-1",
                tool_name="echo",
                arguments={"text": "hi"},
                invocation_mode=self.ToolInvocationMode.MODEL,
            ),
            context,
        )
        self.assertTrue(result.ok)
        self.assertIn("echo:hi", result.summary)

        health = await self.control_plane.get_mcp_health(
            scope_type=self.control_plane.ADMIN_GLOBAL_SCOPE,
            server_slug="fake",
        )
        self.assertEqual(health["last_call_status"], "ok")

    async def test_guild_scoped_mcp_defaults_deny_until_guild_policy_allows(self):
        guild_id = 321
        await self.control_plane.register_guild_mcp_server(
            guild_id=guild_id,
            server_slug="guildfake",
            command_line=self._command_for("success"),
        )
        await self.control_plane.discover_mcp_tools(
            scope_type=self.control_plane.GUILD_SCOPE,
            guild_id=guild_id,
            server_slug="guildfake",
        )
        await self.control_plane.approve_mcp_tool(
            scope_type=self.control_plane.GUILD_SCOPE,
            guild_id=guild_id,
            server_slug="guildfake",
            remote_tool_name="echo",
            category="discovery",
        )

        descriptor = self.tool_registry.list_tool_descriptors()[0]
        self.assertIsNotNone(descriptor)

        context = self._context(guild_id=guild_id)
        decisions = await self.availability.compute_tool_availability_decisions(context=context)
        denied = next(item for item in decisions if item.public_name == "echo")
        self.assertFalse(denied.allowed)
        self.assertEqual(denied.primary_reason_code, "policy_denied")

        await self.policy_engine.upsert_tool_policy_rule(
            subject_type="tool",
            subject_id=descriptor.tool_id,
            policy_mode="allow",
            scope_type="guild",
            guild_id=guild_id,
        )

        decisions_after_allow = await self.availability.compute_tool_availability_decisions(context=context)
        allowed = next(item for item in decisions_after_allow if item.public_name == "echo")
        self.assertTrue(allowed.allowed)

    async def test_repeated_mcp_backend_errors_quarantine_the_tool(self):
        await self.control_plane.register_admin_global_mcp_server(
            server_slug="errorfake",
            command_line=self._command_for("call_error"),
            trusted=True,
        )
        await self.control_plane.discover_mcp_tools(server_slug="errorfake")
        await self.control_plane.approve_mcp_tool(
            server_slug="errorfake",
            remote_tool_name="echo",
            category="discovery",
        )

        context = self._context()
        envelope = self.ToolCallEnvelope(
            call_id="call-1",
            tool_name="echo",
            arguments={"text": "boom"},
            invocation_mode=self.ToolInvocationMode.MODEL,
        )
        for _ in range(3):
            result = await self.executor.execute_tool_envelope(envelope, context)
            self.assertFalse(result.ok)

        decisions = await self.availability.compute_tool_availability_decisions(context=context)
        decision = next(item for item in decisions if item.public_name == "echo")
        self.assertFalse(decision.allowed)
        self.assertEqual(decision.primary_reason_code, "quarantined")

    async def test_transport_failure_sets_health_cooldown_and_blocks_runtime(self):
        await self.control_plane.register_admin_global_mcp_server(
            server_slug="flaky",
            command_line=self._command_for("success"),
            trusted=True,
        )
        await self.control_plane.discover_mcp_tools(server_slug="flaky")
        await self.control_plane.approve_mcp_tool(
            server_slug="flaky",
            remote_tool_name="echo",
            category="discovery",
        )
        await self.control_plane.register_admin_global_mcp_server(
            server_slug="flaky",
            command_line=self._command_for("transport_fail"),
            trusted=True,
        )

        context = self._context()
        result = await self.executor.execute_tool_envelope(
            self.ToolCallEnvelope(
                call_id="call-1",
                tool_name="echo",
                arguments={"text": "hi"},
                invocation_mode=self.ToolInvocationMode.MODEL,
            ),
            context,
        )
        self.assertFalse(result.ok)

        health = await self.control_plane.get_mcp_health(
            scope_type=self.control_plane.ADMIN_GLOBAL_SCOPE,
            server_slug="flaky",
        )
        self.assertEqual(health["last_call_status"], "error")
        self.assertTrue(bool(health["cooldown_until"]))

        decisions = await self.availability.compute_tool_availability_decisions(context=context)
        decision = next(item for item in decisions if item.public_name == "echo")
        self.assertFalse(decision.allowed)
        self.assertEqual(decision.primary_reason_code, "mcp_cooldown_active")


if __name__ == "__main__":
    unittest.main()
