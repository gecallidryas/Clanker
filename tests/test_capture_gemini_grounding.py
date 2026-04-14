import json
import sys
import tempfile
from pathlib import Path
import unittest
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from scripts import capture_gemini_grounding


class CaptureGeminiGroundingTests(unittest.TestCase):
    def test_main_refuses_to_overwrite_canonical_fixture_with_sample_payload(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            canonical_path = Path(temp_dir) / "gemini_grounding_response.json"
            canonical_path.write_text('{"live": true}\n', encoding="utf-8")

            with (
                mock.patch.object(capture_gemini_grounding, "DEFAULT_OUTPUT", canonical_path),
                mock.patch.dict("os.environ", {}, clear=True),
                mock.patch.object(
                    sys,
                    "argv",
                    ["capture_gemini_grounding.py", "--output", str(canonical_path)],
                ),
            ):
                exit_code = capture_gemini_grounding.main()

            self.assertEqual(exit_code, 1)
            self.assertEqual(canonical_path.read_text(encoding="utf-8"), '{"live": true}\n')

    def test_main_uses_numbered_gemini_keys_beyond_first_slot(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            output_path = Path(temp_dir) / "grounding.json"
            payload = {"candidates": [{"grounding_metadata": {"grounding_chunks": []}}]}

            with (
                mock.patch.dict("os.environ", {"GEMINI_API_KEY_2": "second-key"}, clear=True),
                mock.patch.object(capture_gemini_grounding, "_capture_live_payload", return_value=payload) as capture_mock,
                mock.patch.object(
                    sys,
                    "argv",
                    ["capture_gemini_grounding.py", "--output", str(output_path)],
                ),
            ):
                exit_code = capture_gemini_grounding.main()

            self.assertEqual(exit_code, 0)
            capture_mock.assert_called_once_with(
                "second-key",
                capture_gemini_grounding.DEFAULT_MODEL,
                capture_gemini_grounding.DEFAULT_QUERY,
            )
            self.assertEqual(json.loads(output_path.read_text(encoding="utf-8")), payload)


if __name__ == "__main__":
    unittest.main()
