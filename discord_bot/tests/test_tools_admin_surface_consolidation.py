import sys
import unittest

sys.path.insert(0, "/mnt/e/femboibot/discord_bot")

from cogs.tools_admin import ToolsAdmin


class ToolsAdminSurfaceConsolidationTests(unittest.TestCase):
    def test_tools_root_exposes_manage_and_grouped_surfaces(self) -> None:
        command_names = [command.name for command in ToolsAdmin.tools_group.commands]
        self.assertEqual(
            command_names,
            ["info", "context", "policy", "debug", "quarantine", "mcp", "manage"],
        )

    def test_tools_info_group_exposes_status_and_inspect(self) -> None:
        command_names = [command.name for command in ToolsAdmin.info_group.commands]
        self.assertEqual(command_names, ["status", "inspect"])

    def test_tools_context_group_exposes_context_resets(self) -> None:
        command_names = [command.name for command in ToolsAdmin.context_group.commands]
        self.assertEqual(command_names, ["refresh", "clear-guild-recency"])


if __name__ == "__main__":
    unittest.main()
