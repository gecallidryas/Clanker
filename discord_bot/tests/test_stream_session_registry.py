import unittest
import sys

sys.path.insert(0, "/mnt/e/femboibot/discord_bot")

from utils.streaming.session_registry import ChannelStreamBusyError, ChannelStreamRegistry


class ChannelStreamRegistryTests(unittest.IsolatedAsyncioTestCase):
    async def test_allows_different_users_in_same_channel(self) -> None:
        registry = ChannelStreamRegistry()

        token_a = await registry.acquire(channel_id=10, user_id=100)
        token_b = await registry.acquire(channel_id=10, user_id=200)

        self.assertNotEqual(token_a, token_b)
        self.assertTrue(registry.is_active(channel_id=10, user_id=100))
        self.assertTrue(registry.is_active(channel_id=10, user_id=200))

    async def test_blocks_duplicate_claim_for_same_user_in_same_channel(self) -> None:
        registry = ChannelStreamRegistry()

        await registry.acquire(channel_id=10, user_id=100)

        with self.assertRaises(ChannelStreamBusyError):
            await registry.acquire(channel_id=10, user_id=100)

    async def test_release_is_scoped_to_channel_and_user(self) -> None:
        registry = ChannelStreamRegistry()

        token_a = await registry.acquire(channel_id=10, user_id=100)
        await registry.acquire(channel_id=10, user_id=200)

        await registry.release(channel_id=10, user_id=100, token=token_a)

        self.assertFalse(registry.is_active(channel_id=10, user_id=100))
        self.assertTrue(registry.is_active(channel_id=10, user_id=200))

    async def test_claim_releases_after_exception(self) -> None:
        registry = ChannelStreamRegistry()

        with self.assertRaises(RuntimeError):
            async with registry.claim(channel_id=10, user_id=100):
                raise RuntimeError("boom")

        self.assertFalse(registry.is_active(channel_id=10, user_id=100))


if __name__ == "__main__":
    unittest.main()
