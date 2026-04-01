import importlib
import json
import os
import sys
import tempfile
import unittest
import asyncio
from pathlib import Path
from types import SimpleNamespace

import aiosqlite


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "discord_bot"))


class ToolAuditTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self._env = os.environ.copy()
        self._tmp = tempfile.TemporaryDirectory()
        os.environ["DATABASE_DIR"] = self._tmp.name

        from utils import db_handler as db_handler_mod
        from utils import tool_registry as tool_registry_mod
        from tools import audit as audit_mod

        self.db_handler = importlib.reload(db_handler_mod)
        self.tool_registry = importlib.reload(tool_registry_mod)
        self.audit = importlib.reload(audit_mod)
        self.tool_registry._reset_registry_for_tests()

    def tearDown(self):
        os.environ.clear()
        os.environ.update(self._env)
        self._tmp.cleanup()

    async def test_execute_tool_writes_privacy_safe_log_entry(self):
        async def _handler(context, args):
            return self.tool_registry.ToolResult(ok=True, summary="Completed", data={"echo": args.get("query")})

        self.tool_registry.register_tool(
            self.tool_registry.ToolDefinition(
                name="web_search",
                description="Search the web",
                args_schema={"query": "query"},
                handler=_handler,
                feature_flag="web_search_enabled",
            )
        )

        await self.db_handler.init_db()
        context = SimpleNamespace(
            guild=SimpleNamespace(id=321),
            channel=SimpleNamespace(id=654),
            user=SimpleNamespace(id=987),
            guild_config={"web_search_enabled": 1},
            provider_name=None,
            model_name=None,
            request_id=None,
            turn_id=None,
        )
        await self.tool_registry.execute_tool("web_search", {"query": "super secret phrase"}, context)

        async with self.db_handler.global_db() as db:
            db.row_factory = aiosqlite.Row
            async with db.execute(
                "SELECT * FROM tool_execution_log ORDER BY id DESC LIMIT 1"
            ) as cursor:
                row = await cursor.fetchone()

        assert row is not None
        args_summary = json.loads(row["args_summary_json"])
        assert args_summary["arg_shape"]["query"] == {"type": "string", "length": 19}
        assert "super secret phrase" not in row["args_summary_json"]
        assert row["execution_outcome"] == "success"
        assert row["debug_capture_id"] is None

    async def test_raw_capture_requires_explicit_temporary_enablement(self):
        async def _handler(context, args):
            return self.tool_registry.ToolResult(ok=True, summary="Completed", data={"echo": "done"})

        self.tool_registry.register_tool(
            self.tool_registry.ToolDefinition(
                name="web_search",
                description="Search the web",
                args_schema={"query": "query"},
                handler=_handler,
                feature_flag="web_search_enabled",
            )
        )

        await self.db_handler.init_db()
        await self.audit.set_debug_capture_window(guild_id=222, enabled_by=1, ttl_seconds=60, note="test")

        context = SimpleNamespace(
            guild=SimpleNamespace(id=222),
            channel=SimpleNamespace(id=333),
            user=SimpleNamespace(id=444),
            guild_config={"web_search_enabled": 1},
            provider_name=None,
            model_name=None,
            request_id=None,
            turn_id=None,
        )
        await self.tool_registry.execute_tool("web_search", {"query": "capture me"}, context)

        async with self.db_handler.global_db() as db:
            db.row_factory = aiosqlite.Row
            async with db.execute(
                "SELECT * FROM tool_execution_log ORDER BY id DESC LIMIT 1"
            ) as cursor:
                log_row = await cursor.fetchone()
            async with db.execute(
                "SELECT * FROM tool_debug_capture ORDER BY id DESC LIMIT 1"
            ) as cursor:
                capture_row = await cursor.fetchone()

        assert log_row is not None
        assert capture_row is not None
        assert log_row["debug_capture_id"] == capture_row["id"]

    async def test_expired_debug_capture_window_cleans_up_settings_and_raw_rows(self):
        async def _handler(context, args):
            return self.tool_registry.ToolResult(ok=True, summary="Completed", data={"echo": "done"})

        self.tool_registry.register_tool(
            self.tool_registry.ToolDefinition(
                name="web_search",
                description="Search the web",
                args_schema={"query": "query"},
                handler=_handler,
                feature_flag="web_search_enabled",
            )
        )

        await self.db_handler.init_db()
        await self.audit.set_debug_capture_window(guild_id=222, enabled_by=1, ttl_seconds=1, note="test")

        context = SimpleNamespace(
            guild=SimpleNamespace(id=222),
            channel=SimpleNamespace(id=333),
            user=SimpleNamespace(id=444),
            guild_config={"web_search_enabled": 1},
            provider_name=None,
            model_name=None,
            request_id=None,
            turn_id=None,
        )
        await self.tool_registry.execute_tool("web_search", {"query": "capture me"}, context)
        await asyncio.sleep(2)

        enabled = await self.audit.is_debug_capture_enabled(guild_id=222)
        assert enabled is False

        async with self.db_handler.global_db() as db:
            async with db.execute("SELECT COUNT(*) FROM tool_debug_capture WHERE guild_id = 222") as cursor:
                raw_count = (await cursor.fetchone())[0]
            async with db.execute("SELECT COUNT(*) FROM tool_debug_capture_settings WHERE guild_id = 222") as cursor:
                settings_count = (await cursor.fetchone())[0]

        assert raw_count == 0
        assert settings_count == 0
