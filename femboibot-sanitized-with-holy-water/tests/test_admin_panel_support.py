import importlib
import os
import sqlite3
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "discord_bot"))


class AdminPanelSupportTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self._env = os.environ.copy()
        self._tmp = tempfile.TemporaryDirectory()
        os.environ["DATABASE_DIR"] = self._tmp.name

        from utils import admin_panel_support as panel_support_mod
        from utils import db_handler as db_handler_mod

        self.panel_support = importlib.reload(panel_support_mod)
        self.db_handler = importlib.reload(db_handler_mod)

    def tearDown(self):
        os.environ.clear()
        os.environ.update(self._env)
        self._tmp.cleanup()

    def test_risk_classification(self):
        self.assertEqual(
            self.panel_support.classify_action_risk("provider_secret_update"),
            self.panel_support.RISK_HIGH,
        )
        self.assertEqual(
            self.panel_support.classify_action_risk("staff_role_add"),
            self.panel_support.RISK_HIGH,
        )
        self.assertEqual(
            self.panel_support.classify_action_risk("persona_activate"),
            self.panel_support.RISK_LOW,
        )

    def test_auth_gating(self):
        self.assertTrue(self.panel_support.requires_auth_for_action("provider_secret_update"))
        self.assertTrue(self.panel_support.requires_auth_for_action("modlog_channel_set"))
        self.assertTrue(self.panel_support.requires_auth_for_action("persona_delete"))
        self.assertFalse(self.panel_support.requires_auth_for_action("persona_activate"))
        self.assertFalse(self.panel_support.requires_auth_for_action("tool_flags_save"))

    def test_bulk_diff_logic(self):
        before = {"web_search_enabled": 1, "image_gen_enabled": 1, "rag_enabled": 0}
        after = {"web_search_enabled": 0, "image_gen_enabled": 1, "rag_enabled": 1}
        diff = self.panel_support.diff_config_values(
            before,
            after,
            keys=["web_search_enabled", "image_gen_enabled", "rag_enabled"],
        )
        self.assertEqual(
            diff,
            {
                "web_search_enabled": (1, 0),
                "rag_enabled": (0, 1),
            },
        )

    def test_list_add_remove_clear_logic(self):
        self.assertEqual(
            self.panel_support.apply_id_list_changes([1, 2], add=[2, 3, 4]),
            [1, 2, 3, 4],
        )
        self.assertEqual(
            self.panel_support.apply_id_list_changes([1, 2, 3, 4], remove=[2, 4]),
            [1, 3],
        )
        self.assertEqual(
            self.panel_support.apply_id_list_changes([1, 2, 3], clear=True),
            [],
        )

    def test_pagination_boundaries(self):
        page = self.panel_support.paginate_sequence(list(range(7)), page=99, page_size=3)
        self.assertEqual(page.page, 3)
        self.assertEqual(page.total_pages, 3)
        self.assertEqual(page.items, [6])

        empty_page = self.panel_support.paginate_sequence([], page=-5, page_size=3)
        self.assertEqual(empty_page.page, 1)
        self.assertEqual(empty_page.total_pages, 1)
        self.assertEqual(empty_page.items, [])

    def test_audit_category_normalization(self):
        self.assertEqual(
            self.panel_support.normalize_audit_category("persona_presentation"),
            "persona_presentation",
        )
        self.assertEqual(
            self.panel_support.normalize_audit_category(None, action="evil_mode_on"),
            "persona_presentation",
        )
        self.assertEqual(
            self.panel_support.normalize_audit_category(None, action="key_clear"),
            "config_destructive",
        )
        with self.assertRaises(ValueError):
            self.panel_support.normalize_audit_category("free_form_value")

    async def test_audit_schema_compatibility_migration_behavior(self):
        guild_id = 222
        db_path = Path(self._tmp.name) / f"guild_{guild_id}.db"
        conn = sqlite3.connect(db_path)
        conn.execute(
            """
            CREATE TABLE guild_config_audit (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                guild_id INTEGER NOT NULL,
                user_id INTEGER NOT NULL,
                action TEXT NOT NULL,
                field TEXT,
                old_value TEXT,
                new_value TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """
        )
        conn.execute(
            """
            INSERT INTO guild_config_audit (guild_id, user_id, action, field, old_value, new_value)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (guild_id, 7, "legacy_action", "field_a", "old", "new"),
        )
        conn.commit()
        conn.close()

        await self.db_handler.init_guild_db(guild_id)
        entries = await self.db_handler.get_guild_config_audit_entries(guild_id)
        self.assertEqual(len(entries), 1)
        self.assertEqual(entries[0]["action"], "legacy_action")
        self.assertEqual(entries[0]["category"], "config_general")
        self.assertEqual(entries[0]["field"], "field_a")

    async def test_persona_presentation_audit_routing(self):
        guild_id = 333
        await self.db_handler.init_guild_db(guild_id)
        await self.db_handler.add_guild_config_audit(
            guild_id,
            42,
            "evil_mode_on",
        )
        entries = await self.db_handler.get_guild_config_audit_entries(guild_id)
        self.assertEqual(entries[0]["category"], "persona_presentation")

    async def test_audit_helper_rejects_invalid_category(self):
        guild_id = 444
        await self.db_handler.init_guild_db(guild_id)
        with self.assertRaises(ValueError):
            await self.db_handler.add_guild_config_audit(
                guild_id,
                9,
                "bad_action",
                category="anything_goes",
            )

    def test_persona_grouping(self):
        builtins = [
            {"mode_key": "mode_default", "name": "Clanker", "source": "builtin"},
            {"mode_key": "mode_femboy", "name": "Femmy", "source": "builtin"},
        ]
        customs = [
            {"mode_key": "custom_1_alpha", "name": "Alpha", "source": "custom"},
            {"mode_key": "custom_1_beta", "name": "Beta", "source": "custom"},
        ]
        options = self.panel_support.build_persona_selector_options(
            current_mode="custom_1_beta",
            builtins=builtins,
            customs=customs,
        )
        self.assertEqual(options[0]["group"], "active")
        self.assertEqual(options[0]["mode_key"], "custom_1_beta")
        self.assertEqual(options[1]["group"], "builtin")
        self.assertEqual(options[-1]["group"], "custom")


if __name__ == "__main__":
    unittest.main()
