import asyncio
import sys
import unittest
from pathlib import Path

import discord


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "discord_bot"))

from utils.admin_panel_views import (  # noqa: E402
    AdminPanelView,
    AuthHandoffView,
    PagedItemEditorView,
    SaveCancelView,
)


class _FakeResponse:
    def __init__(self):
        self.messages: list[str] = []
        self.edits: list[dict] = []
        self.modals: list[discord.ui.Modal] = []

    async def send_message(self, message: str, ephemeral: bool = False, view=None):
        self.messages.append(str(message))

    async def edit_message(self, *, content=None, embed=None, view=None):
        self.edits.append({"content": content, "embed": embed, "view": view})

    async def send_modal(self, modal: discord.ui.Modal):
        self.modals.append(modal)


class _FakeFollowup:
    def __init__(self):
        self.messages: list[str] = []

    async def send(self, message: str, ephemeral: bool = False):
        self.messages.append(str(message))


class _FakeMessage:
    def __init__(self):
        self.edits: list[dict] = []

    async def edit(self, **kwargs):
        self.edits.append(kwargs)


class _FakeInteraction:
    def __init__(self, user_id: int):
        self.user = type("User", (), {"id": user_id})()
        self.response = _FakeResponse()
        self.followup = _FakeFollowup()


class _DummyModal(discord.ui.Modal, title="Dummy"):
    pass


class _TestPanel(AdminPanelView):
    pass


class _TestSaveView(SaveCancelView):
    pass


class AdminPanelViewTests(unittest.TestCase):
    def test_invoker_only_enforcement(self):
        async def _run():
            view = _TestPanel(user_id=1)
            allowed = await view.interaction_check(_FakeInteraction(user_id=1))
            blocked_interaction = _FakeInteraction(user_id=2)
            blocked = await view.interaction_check(blocked_interaction)
            self.assertTrue(allowed)
            self.assertFalse(blocked)
            self.assertEqual(
                blocked_interaction.response.messages[-1],
                "Only the original admin can use this panel. Open your own panel instead.",
            )

        asyncio.run(_run())

    def test_timeout_behavior_disables_view(self):
        async def _run():
            view = _TestPanel(user_id=1, timeout=30)
            button = discord.ui.Button(label="Click")
            view.add_item(button)
            message = _FakeMessage()
            view.bind_message(message)
            await view.on_timeout()
            self.assertTrue(button.disabled)
            self.assertEqual(message.edits[-1]["content"], "This panel expired. Re-run the command to open a fresh panel.")

        asyncio.run(_run())


class SaveCancelViewTests(unittest.TestCase):
    def test_save_and_cancel(self):
        async def _run():
            saved: list[str] = []
            cancelled: list[str] = []

            async def _on_save(interaction):
                saved.append("saved")
                return "Saved draft."

            async def _on_cancel(interaction):
                cancelled.append("cancelled")
                return "Cancelled draft."

            save_view = _TestSaveView(user_id=5, on_save=_on_save, on_cancel=_on_cancel)
            save_button = next(item for item in save_view.children if isinstance(item, discord.ui.Button) and item.label == "Save")
            interaction = _FakeInteraction(user_id=5)
            await save_button.callback(interaction)
            self.assertEqual(saved, ["saved"])
            self.assertEqual(interaction.response.edits[-1]["content"], "Saved draft.")

            cancel_view = _TestSaveView(user_id=5, on_save=_on_save, on_cancel=_on_cancel)
            cancel_button = next(item for item in cancel_view.children if isinstance(item, discord.ui.Button) and item.label == "Cancel")
            interaction = _FakeInteraction(user_id=5)
            await cancel_button.callback(interaction)
            self.assertEqual(cancelled, ["cancelled"])
            self.assertEqual(interaction.response.edits[-1]["content"], "Cancelled draft.")

        asyncio.run(_run())


class PagedItemEditorViewTests(unittest.TestCase):
    def test_next_previous_remove_selected_clear_all(self):
        async def _run():
            removed_calls: list[list[str]] = []
            cleared_calls: list[bool] = []

            async def _on_remove(values: list[str]):
                removed_calls.append(list(values))

            async def _on_clear():
                cleared_calls.append(True)

            view = PagedItemEditorView(
                user_id=10,
                items=["one", "two", "three", "four", "five"],
                page_size=2,
                on_remove=_on_remove,
                on_clear=_on_clear,
            )
            self.assertEqual(view.page, 1)

            next_button = next(item for item in view.children if isinstance(item, discord.ui.Button) and item.label == "Next")
            prev_button = next(item for item in view.children if isinstance(item, discord.ui.Button) and item.label == "Previous")
            remove_button = next(item for item in view.children if isinstance(item, discord.ui.Button) and item.label == "Remove Selected")
            clear_button = next(item for item in view.children if isinstance(item, discord.ui.Button) and item.label == "Clear All")
            select = next(item for item in view.children if isinstance(item, discord.ui.Select))

            interaction = _FakeInteraction(user_id=10)
            await next_button.callback(interaction)
            self.assertEqual(view.page, 2)
            await prev_button.callback(interaction)
            self.assertEqual(view.page, 1)

            select._values = ["one", "two"]
            await select.callback(interaction)
            await remove_button.callback(interaction)
            self.assertEqual(removed_calls, [["one", "two"]])
            self.assertEqual(view.items, ["three", "four", "five"])

            await clear_button.callback(interaction)
            self.assertEqual(cleared_calls, [True])
            self.assertEqual(view.items, [])

        asyncio.run(_run())


class AuthHandoffViewTests(unittest.TestCase):
    def test_auth_required_flow_and_provider_modal_handoff(self):
        async def _run():
            auth_state = {"ok": False}

            async def _is_authenticated():
                return auth_state["ok"]

            async def _authenticate(password: str) -> bool:
                auth_state["ok"] = password == "letmein"
                return auth_state["ok"]

            view = AuthHandoffView(
                user_id=77,
                auth_checker=_is_authenticated,
                auth_submitter=_authenticate,
                modal_factory=_DummyModal,
                auth_required_message="Authentication required before editing providers.",
            )

            launch_button = next(item for item in view.children if isinstance(item, discord.ui.Button))
            interaction = _FakeInteraction(user_id=77)
            await launch_button.callback(interaction)
            self.assertEqual(
                interaction.response.messages[-1],
                "Authentication required before editing providers.",
            )
            self.assertEqual(len(interaction.response.modals), 0)

            auth_modal = view.auth_modal_factory()
            auth_modal.password.default = "letmein"
            auth_modal.password._value = "letmein"
            interaction = _FakeInteraction(user_id=77)
            await auth_modal.on_submit(interaction)
            self.assertTrue(auth_state["ok"])
            self.assertEqual(len(interaction.response.modals), 1)
            self.assertIsInstance(interaction.response.modals[0], _DummyModal)

        asyncio.run(_run())


if __name__ == "__main__":
    unittest.main()
