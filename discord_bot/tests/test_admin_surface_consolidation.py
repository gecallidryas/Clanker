import sys
import unittest

sys.path.insert(0, "/mnt/e/femboibot/discord_bot")

from cogs.config import Config


class AdminSurfaceConsolidationTests(unittest.TestCase):
    def test_config_root_exposes_panel_and_setup_commands_without_legacy_ui(self) -> None:
        command_names = [command.name for command in Config.config.commands]
        for required in ["auth", "panel", "password", "keys", "model", "env", "toggle", "ai", "url_safety", "custom_endpoint"]:
            self.assertIn(required, command_names)
        self.assertNotIn("ui", command_names)

    def test_config_ai_group_only_exposes_manage(self) -> None:
        command_names = [command.name for command in Config.ai_group.commands]
        self.assertEqual(command_names, ["manage"])

    def test_config_toggle_group_only_exposes_manage(self) -> None:
        command_names = [command.name for command in Config.toggle_group.commands]
        self.assertEqual(command_names, ["manage"])

    def test_config_url_safety_group_only_exposes_manage(self) -> None:
        command_names = [command.name for command in Config.url_safety_group.commands]
        self.assertEqual(command_names, ["manage"])

    def test_config_custom_endpoint_group_only_exposes_manage(self) -> None:
        command_names = [command.name for command in Config.custom_endpoint_group.commands]
        self.assertEqual(command_names, ["manage"])

    def test_config_keys_group_only_exposes_manage(self) -> None:
        command_names = [command.name for command in Config.keys_group.commands]
        self.assertEqual(command_names, ["manage"])

    def test_config_model_group_only_exposes_manage(self) -> None:
        command_names = [command.name for command in Config.model_group.commands]
        self.assertEqual(command_names, ["manage"])

    def test_config_env_group_keeps_setup_commands(self) -> None:
        command_names = [command.name for command in Config.env_group.commands]
        self.assertEqual(command_names, ["example", "upload"])

    def test_config_password_group_keeps_password_commands(self) -> None:
        command_names = [command.name for command in Config.password_group.commands]
        self.assertEqual(command_names, ["set", "change", "reset"])

    def test_autorole_group_only_exposes_manage(self) -> None:
        command_names = [command.name for command in Config.autorole_group.commands]
        self.assertEqual(command_names, ["manage"])

    def test_manage_group_no_longer_exposes_structure_commands(self) -> None:
        self.assertFalse(hasattr(Config, "manage_group"))


if __name__ == "__main__":
    unittest.main()
