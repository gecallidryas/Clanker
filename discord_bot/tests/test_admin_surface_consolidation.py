import ast
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "discord_bot"))

from cogs.config import Config


def _load_help_commands() -> dict:
    source = (ROOT / "discord_bot" / "cogs" / "utilities.py").read_text(encoding="utf-8")
    tree = ast.parse(source)
    for node in tree.body:
        if isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Name) and target.id == "HELP_COMMANDS":
                    return ast.literal_eval(node.value)
    raise AssertionError("HELP_COMMANDS not found in utilities.py")


HELP_COMMANDS = _load_help_commands()


def _load_group_command_names(path_str: str, group_attr: str) -> list[str]:
    source = Path(path_str).read_text(encoding="utf-8-sig")
    tree = ast.parse(source)
    groups: dict[str, tuple[str, str | None]] = {}
    commands: list[tuple[str, str]] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Assign) and isinstance(node.value, ast.Call):
            func = node.value.func
            if isinstance(func, ast.Attribute) and func.attr == "Group":
                group_name = None
                parent = None
                for kw in node.value.keywords:
                    if kw.arg == "name" and isinstance(kw.value, ast.Constant):
                        group_name = kw.value.value
                    if kw.arg == "parent":
                        if isinstance(kw.value, ast.Name):
                            parent = kw.value.id
                        elif isinstance(kw.value, ast.Attribute):
                            parent = kw.value.attr
                for target in node.targets:
                    if isinstance(target, ast.Name) and group_name:
                        groups[target.id] = (group_name, parent)
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            for dec in node.decorator_list:
                if isinstance(dec, ast.Call) and isinstance(dec.func, ast.Attribute) and dec.func.attr == "command":
                    owner = dec.func.value.id if isinstance(dec.func.value, ast.Name) else None
                    if owner is None:
                        continue
                    for kw in dec.keywords:
                        if kw.arg == "name" and isinstance(kw.value, ast.Constant):
                            commands.append((owner, kw.value.value))
    return [name for owner, name in commands if owner == group_attr]


def _load_action_option_values(path_str: str, function_name: str) -> list[str]:
    source = Path(path_str).read_text(encoding="utf-8-sig")
    tree = ast.parse(source)
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name == function_name:
            values: list[str] = []
            for child in ast.walk(node):
                if not isinstance(child, ast.Call):
                    continue
                if not isinstance(child.func, ast.Name) or child.func.id != "ActionOption":
                    continue
                if len(child.args) < 2:
                    continue
                if isinstance(child.args[1], ast.Constant) and isinstance(child.args[1].value, str):
                    values.append(child.args[1].value)
            return values
    raise AssertionError(f"{function_name} not found in {path_str}")


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

    def test_welcome_group_only_exposes_manage(self) -> None:
        command_names = [command.name for command in Config.welcome_group.commands]
        self.assertEqual(command_names, ["manage"])

    def test_help_inventory_only_lists_welcome_manage(self) -> None:
        self.assertEqual(HELP_COMMANDS["welcome"]["prefix"], [])
        self.assertEqual(HELP_COMMANDS["welcome"]["slash"], ["/welcome manage"])

    def test_welcome_manage_panel_exposes_integrated_actions(self) -> None:
        action_values = _load_action_option_values(
            str(ROOT / "discord_bot" / "cogs" / "config.py"),
            "_send_welcome_panel",
        )
        self.assertEqual(
            action_values,
            [
                "set_channel",
                "toggle_enabled",
                "disable",
                "edit_welcome_message",
                "clear_welcome_message",
                "edit_dm_message",
                "clear_dm_message",
                "toggle_dm",
                "toggle_image",
                "edit_image_template",
                "edit_image_destination",
                "set_image_channel",
                "test_message",
                "test_image",
            ],
        )

    def test_manage_group_no_longer_exposes_structure_commands(self) -> None:
        self.assertFalse(hasattr(Config, "manage_group"))


if __name__ == "__main__":
    unittest.main()
