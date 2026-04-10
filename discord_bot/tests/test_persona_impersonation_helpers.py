import unittest

from utils.persona_impersonation import (
    choose_unique_persona_name,
    filter_impersonation_messages,
    parse_impersonation_payload,
)


class PersonaImpersonationHelperTests(unittest.TestCase):
    def test_filter_impersonation_messages_removes_low_signal_content(self) -> None:
        raw_messages = [
            "/help",
            "ok",
            "look at this",
            "look at this",
            "LMFAOOO absolutely not",
        ]

        filtered = filter_impersonation_messages(raw_messages)

        self.assertEqual(filtered, ["look at this", "LMFAOOO absolutely not"])

    def test_choose_unique_persona_name_adds_impersonation_suffix(self) -> None:
        existing = {"Tomori", "Tomori (impersonated)"}
        result = choose_unique_persona_name("Tomori", existing)
        self.assertEqual(result, "Tomori (impersonated 2)")

    def test_parse_impersonation_payload_requires_prompt_and_dialogues(self) -> None:
        payload = parse_impersonation_payload(
            '{"bio":"bio","normal_prompt":"prompt","sample_dialogues":["a","b"]}'
        )

        self.assertEqual(payload.normal_prompt, "prompt")
        self.assertEqual(payload.sample_dialogues, ["a", "b"])


if __name__ == "__main__":
    unittest.main()
