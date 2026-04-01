import sys
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "discord_bot"))

from utils.context_builder import (  # noqa: E402
    ContextSection,
    build_structured_prompt,
    render_structured_context,
    section_from_lines,
)


class ContextBuilderTests(unittest.TestCase):
    def test_render_sections_in_order(self):
        sections = [
            ContextSection("A", "first"),
            ContextSection("B", "second"),
        ]
        rendered = render_structured_context(sections)
        self.assertIn("=== A ===\nfirst", rendered)
        self.assertIn("=== B ===\nsecond", rendered)
        self.assertLess(rendered.index("=== A ==="), rendered.index("=== B ==="))

    def test_build_structured_prompt_uses_response_style_before_message(self):
        sections = [ContextSection("CTX", "context body")]
        prompt = build_structured_prompt(
            persona="persona",
            sections=sections,
            current_message="hello",
            final_instruction="be concise",
        )
        self.assertIn("=== RESPONSE STYLE ===", prompt)
        self.assertIn("=== CURRENT MESSAGE ===", prompt)
        self.assertLess(prompt.index("=== RESPONSE STYLE ==="), prompt.index("=== CURRENT MESSAGE ==="))

    def test_section_from_lines_drops_empty_values(self):
        section = section_from_lines("Facts", ["", "A", " ", "B"])
        self.assertIsNotNone(section)
        assert section is not None
        self.assertEqual(section.body, "- A\n- B")


if __name__ == "__main__":
    unittest.main()

