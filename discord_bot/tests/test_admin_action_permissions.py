import unittest
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

from utils.admin_actions import execute_admin_intent


class AdminActionPermissionTests(unittest.IsolatedAsyncioTestCase):
    async def test_level_2_staff_role_can_execute_config_intent(self) -> None:
        guild = SimpleNamespace(id=321, owner_id=999)
        executor = SimpleNamespace(
            id=111,
            guild=guild,
            guild_permissions=SimpleNamespace(administrator=False, manage_guild=False),
            roles=[SimpleNamespace(id=10)],
        )

        with patch(
            "utils.admin_actions.get_staff_roles",
            new=AsyncMock(return_value=[(10, 2)]),
        ), patch(
            "utils.admin_actions.execute_config_mode",
            new=AsyncMock(return_value={"success": True, "message": "ok"}),
        ) as execute_config_mode:
            result = await execute_admin_intent(
                "config.mode",
                {"mode": "femboy"},
                guild,
                executor,
            )

        self.assertTrue(result["success"])
        execute_config_mode.assert_awaited_once()

    async def test_level_1_staff_role_can_execute_timeout_intent(self) -> None:
        target_member = SimpleNamespace(id=222, timeout=AsyncMock())
        guild = SimpleNamespace(
            id=321,
            owner_id=999,
            get_member=lambda user_id: target_member if user_id == 222 else None,
        )
        executor = SimpleNamespace(
            id=111,
            guild=guild,
            guild_permissions=SimpleNamespace(administrator=False, manage_guild=False),
            roles=[SimpleNamespace(id=10)],
        )

        with patch(
            "utils.admin_actions.get_staff_roles",
            new=AsyncMock(return_value=[(10, 1)]),
        ):
            result = await execute_admin_intent(
                "moderation.timeout",
                {"target_id": 222, "duration": 5},
                guild,
                executor,
            )

        self.assertTrue(result["success"])
        target_member.timeout.assert_awaited_once()


if __name__ == "__main__":
    unittest.main()
