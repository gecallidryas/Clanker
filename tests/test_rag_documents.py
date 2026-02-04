import sys
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "discord_bot"))

from utils import rag_documents


class RagDocumentsTests(unittest.TestCase):
    def test_extract_text_from_txt(self):
        data = b"hello\nworld"
        result = rag_documents.extract_text_from_bytes(data, "test.txt")
        self.assertEqual(result, "hello world")

    def test_chunk_text(self):
        text = "one two three four five six"
        chunks = rag_documents.chunk_text(text, chunk_size=3, overlap=1)
        self.assertTrue(chunks)
        self.assertEqual(chunks[0], "one two three")


if __name__ == "__main__":
    unittest.main()
