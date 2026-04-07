import unittest
from types import SimpleNamespace

from utils.turn_coalescer import TurnCoordinator, TurnKey


class TurnCoalescerTests(unittest.TestCase):
    def _message(self, message_id: int) -> SimpleNamespace:
        return SimpleNamespace(id=message_id)

    def test_upsert_pending_extends_version_and_merges_fragments(self) -> None:
        coordinator = TurnCoordinator(debounce_window=2.0)
        key = TurnKey(channel_id=10, user_id=20)

        first = coordinator.upsert_pending(
            key,
            fragment_text="I WANT TO",
            source_message=self._message(1),
            now=10.0,
        )
        second = coordinator.upsert_pending(
            key,
            fragment_text="COOK",
            source_message=self._message(2),
            attachments=[{"name": "beef.jpg"}],
            now=11.0,
        )

        self.assertEqual(first.version, 1)
        self.assertEqual(first.merged_text, "I WANT TO")
        self.assertEqual(second.version, 2)
        self.assertEqual(second.merged_text, "I WANT TO\nCOOK")
        self.assertEqual(second.fragments, ["I WANT TO", "COOK"])
        self.assertEqual(second.source_message.id, 2)
        self.assertEqual(second.attachments, [{"name": "beef.jpg"}])
        self.assertAlmostEqual(second.deadline, 13.0)

    def test_take_pending_ignores_stale_version_after_new_fragment(self) -> None:
        coordinator = TurnCoordinator(debounce_window=2.0)
        key = TurnKey(channel_id=10, user_id=20)

        coordinator.upsert_pending(
            key,
            fragment_text="I WANT TO",
            source_message=self._message(1),
            now=10.0,
        )
        coordinator.upsert_pending(
            key,
            fragment_text="COOK",
            source_message=self._message(2),
            now=11.0,
        )

        self.assertIsNone(coordinator.take_pending(key, version=1, now=14.0))

        ready = coordinator.take_pending(key, version=2, now=14.0)
        self.assertIsNotNone(ready)
        self.assertEqual(ready.version, 2)
        self.assertEqual(ready.merged_text, "I WANT TO\nCOOK")

    def test_restart_before_visible_replaces_stale_generation(self) -> None:
        coordinator = TurnCoordinator(debounce_window=2.0)
        key = TurnKey(channel_id=10, user_id=20)

        pending = coordinator.upsert_pending(
            key,
            fragment_text="I WANT TO",
            source_message=self._message(1),
            now=10.0,
        )
        active = coordinator.mark_active(pending, now=12.0)
        self.assertFalse(coordinator.has_visible_output(key))
        self.assertEqual(active.version, 1)

        restarted = coordinator.request_restart_before_visible(
            key,
            fragment_text="COOK",
            source_message=self._message(2),
            now=12.5,
        )

        self.assertIsNotNone(restarted)
        self.assertEqual(restarted.version, 2)
        self.assertEqual(restarted.merged_text, "I WANT TO\nCOOK")
        self.assertEqual(restarted.source_message.id, 2)
        self.assertFalse(coordinator.mark_visible(key, version=1))
        self.assertTrue(coordinator.mark_visible(key, version=2))
        self.assertTrue(coordinator.has_visible_output(key))

    def test_buffer_follow_up_collapses_same_user_messages(self) -> None:
        coordinator = TurnCoordinator(debounce_window=2.0)
        key = TurnKey(channel_id=10, user_id=20)

        pending = coordinator.upsert_pending(
            key,
            fragment_text="I WANT TO",
            source_message=self._message(1),
            now=10.0,
        )
        coordinator.mark_active(pending, now=12.0)
        coordinator.mark_visible(key, version=1)

        first = coordinator.buffer_follow_up(
            key,
            fragment_text="BEEF TODAY",
            source_message=self._message(2),
            now=13.0,
        )
        second = coordinator.buffer_follow_up(
            key,
            fragment_text="CAN YOU HELP ME",
            source_message=self._message(3),
            attachments=[{"name": "note.txt"}],
            now=14.0,
        )

        self.assertEqual(first.version, 1)
        self.assertEqual(first.merged_text, "BEEF TODAY")
        self.assertEqual(second.version, 2)
        self.assertEqual(second.merged_text, "BEEF TODAY\nCAN YOU HELP ME")
        self.assertEqual(second.source_message.id, 3)
        self.assertEqual(second.attachments, [{"name": "note.txt"}])
        self.assertIsNone(coordinator.take_buffered_follow_up(key, version=1, now=20.0))

        ready = coordinator.take_buffered_follow_up(key, version=2, now=20.0)
        self.assertIsNotNone(ready)
        self.assertEqual(ready.version, 2)
        self.assertEqual(ready.merged_text, "BEEF TODAY\nCAN YOU HELP ME")

    def test_different_users_do_not_share_state(self) -> None:
        coordinator = TurnCoordinator(debounce_window=2.0)
        key_a = TurnKey(channel_id=10, user_id=20)
        key_b = TurnKey(channel_id=10, user_id=30)

        pending_a = coordinator.upsert_pending(
            key_a,
            fragment_text="FIRST",
            source_message=self._message(1),
            now=10.0,
        )
        pending_b = coordinator.upsert_pending(
            key_b,
            fragment_text="SECOND",
            source_message=self._message(2),
            now=10.0,
        )

        self.assertEqual(pending_a.version, 1)
        self.assertEqual(pending_b.version, 1)
        self.assertEqual(coordinator.get_pending(key_a).merged_text, "FIRST")
        self.assertEqual(coordinator.get_pending(key_b).merged_text, "SECOND")

    def test_clear_finished_removes_active_and_buffer(self) -> None:
        coordinator = TurnCoordinator(debounce_window=2.0)
        key = TurnKey(channel_id=10, user_id=20)

        pending = coordinator.upsert_pending(
            key,
            fragment_text="FIRST",
            source_message=self._message(1),
            now=10.0,
        )
        coordinator.mark_active(pending, now=12.0)
        coordinator.mark_visible(key, version=1)
        coordinator.buffer_follow_up(
            key,
            fragment_text="SECOND",
            source_message=self._message(2),
            now=13.0,
        )

        coordinator.clear_finished(key)

        self.assertIsNone(coordinator.get_active(key))
        self.assertIsNone(coordinator.get_buffered_follow_up(key))
        self.assertIsNone(coordinator.get_pending(key))


if __name__ == "__main__":
    unittest.main()
