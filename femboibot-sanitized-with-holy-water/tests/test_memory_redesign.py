import importlib
import os
import sqlite3
import sys
import tempfile
import unittest
from datetime import datetime, timedelta
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "discord_bot"))


class MemoryRedesignTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self._env = os.environ.copy()
        self._tmp = tempfile.TemporaryDirectory()
        os.environ["DATABASE_DIR"] = self._tmp.name

        from utils import db_handler as db_handler_mod

        self.db_handler = importlib.reload(db_handler_mod)

    def tearDown(self):
        os.environ.clear()
        os.environ.update(self._env)
        self._tmp.cleanup()

    def _legacy_db_path(self, guild_id: int) -> str:
        return str(Path(self._tmp.name) / f"guild_{guild_id}.db")

    def _seed_legacy_memory_db(self, guild_id: int) -> None:
        path = self._legacy_db_path(guild_id)
        conn = sqlite3.connect(path)
        conn.execute(
            """
            CREATE TABLE users (
                user_id INTEGER PRIMARY KEY,
                timezone TEXT DEFAULT 'UTC',
                birthday TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE user_profiles (
                guild_id INTEGER NOT NULL,
                user_id INTEGER NOT NULL,
                timezone TEXT DEFAULT 'UTC',
                birthday TEXT,
                personal_memory_opt_out INTEGER DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                PRIMARY KEY (guild_id, user_id)
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE user_facts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                guild_id INTEGER NOT NULL,
                user_id INTEGER NOT NULL,
                fact TEXT NOT NULL,
                source TEXT DEFAULT 'manual',
                learned_from_user_id INTEGER,
                memory_type TEXT DEFAULT 'personal',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """
        )
        conn.execute(
            "INSERT INTO users (user_id) VALUES (111), (222)"
        )
        conn.execute(
            "INSERT INTO user_profiles (guild_id, user_id) VALUES (?, ?), (?, ?)",
            (guild_id, 111, guild_id, 222),
        )
        conn.execute(
            """
            INSERT INTO user_facts (guild_id, user_id, fact, source, learned_from_user_id, memory_type, created_at)
            VALUES (?, 111, 'likes tea', 'manual', 111, 'personal', '2026-01-01 00:00:00'),
                   (?, 111, 'prefers DMs for mod issues', 'learned', 222, 'long_term', '2026-01-02 00:00:00'),
                   (?, 0, 'server runs game night on Fridays', 'manual', 222, 'server', '2026-01-03 00:00:00'),
                   (?, 111, 'working on ticket 7', 'learned|short_term:channel:444', 111, 'short_term', '2026-01-04 00:00:00')
            """,
            (guild_id, guild_id, guild_id, guild_id),
        )
        conn.commit()
        conn.close()

    async def test_migrates_legacy_fact_tables_into_new_memory_tables(self):
        guild_id = 9001
        self._seed_legacy_memory_db(guild_id)

        await self.db_handler.init_guild_db(guild_id)

        personal = await self.db_handler.get_personal_memory_records(guild_id, 111, include_private=True)
        server = await self.db_handler.get_server_memory_records(guild_id)
        short_term = await self.db_handler.get_short_term_memory_records(
            guild_id, scope_kind="channel", channel_id=444, include_expired=True
        )

        self.assertEqual({row["content"] for row in personal}, {"likes tea", "prefers DMs for mod issues"})
        self.assertTrue(all(row["legacy_fact_id"] for row in personal))
        self.assertEqual(server[0]["content"], "server runs game night on Fridays")
        self.assertEqual(short_term[0]["content"], "working on ticket 7")
        self.assertEqual(short_term[0]["scope_kind"], "channel")
        self.assertEqual(short_term[0]["memory_kind"], "observation")

    async def test_personal_memory_opt_out_blocks_writes_and_reads(self):
        guild_id = 42
        user_id = 1001
        await self.db_handler.init_guild_db(guild_id)
        await self.db_handler.create_user(guild_id, user_id)

        inserted = await self.db_handler.add_personal_memory(
            guild_id,
            user_id,
            "legacy row that must stay hidden",
            created_by_user_id=user_id,
            source="manual",
        )
        self.assertGreater(inserted, 0)

        await self.db_handler.set_personal_memory_opt_out(guild_id, user_id, True)

        with self.assertRaises(PermissionError):
            await self.db_handler.add_personal_memory(
                guild_id,
                user_id,
                "loves mango soda",
                created_by_user_id=user_id,
                source="manual",
            )

        visible = await self.db_handler.get_personal_memories(guild_id, user_id)
        hidden = await self.db_handler.get_personal_memories(guild_id, user_id, include_private=True)
        self.assertEqual(visible, [])
        self.assertEqual(hidden, ["legacy row that must stay hidden"])

    async def test_mention_lookup_requires_explicit_allowance_and_respects_opt_out(self):
        guild_id = 77
        owner_id = 2001
        await self.db_handler.init_guild_db(guild_id)
        await self.db_handler.create_user(guild_id, owner_id)
        await self.db_handler.add_personal_memory(
            guild_id,
            owner_id,
            "goes by they/them",
            created_by_user_id=owner_id,
            source="manual",
            bypass_privacy=True,
        )

        denied = await self.db_handler.get_mention_lookup_personal_memories(guild_id, owner_id)
        self.assertEqual(denied, [])

        await self.db_handler.set_allow_mention_fact_lookup(guild_id, owner_id, True)
        allowed = await self.db_handler.get_mention_lookup_personal_memories(guild_id, owner_id)
        self.assertEqual(allowed, ["goes by they/them"])

        await self.db_handler.set_personal_memory_opt_out(guild_id, owner_id, True)
        blocked = await self.db_handler.get_mention_lookup_personal_memories(guild_id, owner_id)
        self.assertEqual(blocked, [])

    async def test_admin_personal_memory_view_is_metadata_only_and_delete_by_id_works(self):
        guild_id = 88
        user_id = 3001
        await self.db_handler.init_guild_db(guild_id)
        await self.db_handler.create_user(guild_id, user_id)

        memory_id = await self.db_handler.add_personal_memory(
            guild_id,
            user_id,
            "private favorite karaoke song",
            created_by_user_id=user_id,
            source="manual",
            bypass_privacy=True,
        )

        metadata = await self.db_handler.get_admin_personal_memory_index(guild_id, user_id)
        self.assertEqual(len(metadata), 1)
        self.assertEqual(metadata[0]["id"], memory_id)
        self.assertNotIn("content", metadata[0])

        deleted = await self.db_handler.delete_personal_memory_by_id(guild_id, memory_id, deleted_by_user_id=9999)
        self.assertTrue(deleted)
        remaining = await self.db_handler.get_admin_personal_memory_index(guild_id, user_id)
        self.assertEqual(remaining, [])

    async def test_channel_and_guild_recency_summaries_are_stored_separately(self):
        guild_id = 55
        channel_id = 1234
        await self.db_handler.init_guild_db(guild_id)

        await self.db_handler.upsert_short_term_summary(
            guild_id,
            content="Channel is coordinating the release checklist.",
            scope_kind="channel",
            channel_id=channel_id,
            memory_kind="summary",
            expires_at=datetime.utcnow() + timedelta(hours=6),
        )
        await self.db_handler.upsert_short_term_summary(
            guild_id,
            content="Guild-wide topic: migration is in progress.",
            scope_kind="guild",
            memory_kind="summary",
            expires_at=datetime.utcnow() + timedelta(hours=2),
        )

        channel_summary = await self.db_handler.get_channel_recency_summary(guild_id, channel_id)
        guild_summary = await self.db_handler.get_guild_recency_summary(guild_id)

        self.assertEqual(channel_summary, ["Channel is coordinating the release checklist."])
        self.assertEqual(guild_summary, ["Guild-wide topic: migration is in progress."])

    async def test_document_rag_stays_separate_from_fact_memory(self):
        guild_id = 66
        user_id = 4400
        await self.db_handler.init_guild_db(guild_id)
        await self.db_handler.create_user(guild_id, user_id)
        await self.db_handler.add_personal_memory(
            guild_id,
            user_id,
            "favorite snack is mochi",
            created_by_user_id=user_id,
            source="manual",
            bypass_privacy=True,
        )

        personal = await self.db_handler.get_personal_memories(guild_id, user_id, include_private=True)
        server = await self.db_handler.get_server_memory(guild_id)

        self.assertEqual(personal, ["favorite snack is mochi"])
        self.assertEqual(server, [])

    async def test_admin_cannot_write_personal_memory_for_opted_out_user(self):
        guild_id = 123
        user_id = 456
        await self.db_handler.init_guild_db(guild_id)
        await self.db_handler.create_user(guild_id, user_id)
        await self.db_handler.set_personal_memory_opt_out(guild_id, user_id, True)

        with self.assertRaises(PermissionError):
            await self.db_handler.add_personal_memory(
                guild_id,
                user_id,
                "admin should not bypass opt-out",
                source="admin",
                created_by_user_id=999,
                confirmed_by_user_id=999,
                bypass_privacy=True,
            )

    async def test_partial_migration_reads_merge_new_and_legacy_personal_rows(self):
        guild_id = 90210
        self._seed_legacy_memory_db(guild_id)
        await self.db_handler.init_guild_db(guild_id)

        path = self._legacy_db_path(guild_id)
        conn = sqlite3.connect(path)
        conn.execute(
            """
            INSERT INTO user_facts (guild_id, user_id, fact, source, learned_from_user_id, memory_type, created_at)
            VALUES (?, ?, ?, 'manual', ?, 'personal', '2026-01-05 00:00:00')
            """,
            (guild_id, 111, "legacy-only row after migration", 111),
        )
        conn.commit()
        conn.close()

        records = await self.db_handler.get_personal_memory_records(guild_id, 111, include_private=True)
        contents = {row["content"] for row in records}
        self.assertIn("likes tea", contents)
        self.assertIn("prefers DMs for mod issues", contents)
        self.assertIn("legacy-only row after migration", contents)


class MemoryCommandPrivacyTests(unittest.IsolatedAsyncioTestCase):
    async def test_prefix_remember_rejects_cross_user_durable_write_for_non_admin(self):
        from cogs.memories import Memories

        cog = Memories(bot=None)
        ctx = SimpleNamespace(
            guild=SimpleNamespace(id=1),
            author=SimpleNamespace(
                id=10,
                display_name="Author",
                guild_permissions=SimpleNamespace(manage_guild=False),
            ),
            sent=[],
        )

        async def _send(message: str):
            ctx.sent.append(str(message))

        ctx.send = _send
        target = SimpleNamespace(id=99, display_name="Target")

        with (
            patch("cogs.memories.create_user", new=AsyncMock()),
            patch("cogs.memories.get_personal_memory_opt_out", new=AsyncMock(return_value=False)),
            patch("cogs.memories.get_personal_memories", new=AsyncMock(return_value=[])),
            patch("cogs.memories.add_fact", new=AsyncMock()) as add_fact_mock,
        ):
            await cog._remember_fact_for(ctx, target, "private detail")

        add_fact_mock.assert_not_awaited()
        self.assertTrue(any("yourself" in message.lower() or "admin" in message.lower() for message in ctx.sent))

    async def test_admin_setfact_command_respects_opt_out(self):
        from cogs.admin import Admin

        cog = Admin(bot=None)
        ctx = SimpleNamespace(
            guild=SimpleNamespace(id=1),
            author=SimpleNamespace(id=10, guild_permissions=SimpleNamespace(manage_guild=True)),
            sent=[],
        )

        async def _send(message: str):
            ctx.sent.append(str(message))

        ctx.send = _send
        member = SimpleNamespace(id=99, display_name="Target")

        with patch("cogs.admin.add_personal_memory", new=AsyncMock(side_effect=PermissionError("opted out"))):
            await Admin.set_fact.callback(cog, ctx, member, fact="private detail")

        self.assertTrue(any("opted out" in message.lower() for message in ctx.sent))


if __name__ == "__main__":
    unittest.main()
