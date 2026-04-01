import sys
from pathlib import Path
import unittest
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "discord_bot"))

from utils import rag_store


class RagStoreTests(unittest.IsolatedAsyncioTestCase):
    async def test_get_rag_context(self):
        with mock.patch.object(rag_store, "ensure_pg_schema", new=mock.AsyncMock(return_value=True)), \
            mock.patch.object(rag_store, "embed_texts", new=mock.AsyncMock(return_value=[[0.1, 0.2]])), \
            mock.patch.object(
                rag_store,
                "query_similar_chunks",
                new=mock.AsyncMock(return_value=[{"content": "chunk", "score": 0.9}]),
            ):
            result = await rag_store.get_rag_context(123, "query")

        self.assertIn("chunk", result)


if __name__ == "__main__":
    unittest.main()
