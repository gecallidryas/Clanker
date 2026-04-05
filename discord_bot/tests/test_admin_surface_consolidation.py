import sys
import unittest

sys.path.insert(0, "/mnt/e/femboibot/discord_bot")

from cogs.config import Config


class AdminSurfaceConsolidationTests(unittest.TestCase):
    def test_autorole_group_only_exposes_manage(self) -> None:
        command_names = [command.name for command in Config.autorole_group.commands]
        self.assertEqual(command_names, ["manage"])

    def test_manage_group_no_longer_exposes_structure_commands(self) -> None:
        self.assertFalse(hasattr(Config, "manage_group"))


if __name__ == "__main__":
    unittest.main()
