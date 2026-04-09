import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "discord_bot"))

from personas.compiler import compile_persona_sections
from personas.definition import (
    PersonaDefinition,
    PersonaExamples,
    PersonaIdentity,
    PersonaRelationshipModel,
    PersonaSceneRules,
    PersonaUtilityRules,
    PersonaVoice,
    PersonaWorldview,
    PersonaConstraints,
)


def _build_minimal_persona() -> PersonaDefinition:
    return PersonaDefinition(
        key="mode_test",
        identity=PersonaIdentity(
            display_name="Test Persona",
            aliases=("tester",),
            bio="A test persona.",
        ),
        voice=PersonaVoice(
            tone="warm",
            cadence="clear",
        ),
        worldview=PersonaWorldview(
            description="Supportive and focused.",
        ),
        relationship=PersonaRelationshipModel(
            description="Friendly but bounded.",
        ),
        scene_rules=PersonaSceneRules(
            normal="Stay grounded and helpful.",
            evil="Become more explicit and intense.",
        ),
        utility=PersonaUtilityRules(
            description="Answer clearly and use tools when needed.",
        ),
        examples=PersonaExamples(
            normal=("Hi there.",),
            evil=("I will take this further.",),
        ),
        constraints=PersonaConstraints(
            hard_rules=("Stay in character.",),
        ),
    )


class PersonaCompilerTests(unittest.TestCase):
    def test_compiler_emits_ordered_sections_for_normal_mode(self):
        persona = _build_minimal_persona()

        sections = compile_persona_sections(persona, evil_mode=False)

        self.assertEqual(
            [section.title for section in sections],
            [
                "ROLEPLAY CONTRACT",
                "ACTIVE PERSONA IDENTITY",
                "VOICE AND CADENCE",
                "WORLDVIEW AND SUBTEXT",
                "RELATIONSHIP RULES",
                "NORMAL MODE SCENE RULES",
                "TASK AND TOOL COMPETENCE RULES",
                "HARD CONSTRAINTS",
                "EXAMPLE REPLIES",
            ],
        )

    def test_compiler_includes_evil_mode_scene_rules_only_when_enabled(self):
        persona = _build_minimal_persona()

        normal_sections = compile_persona_sections(persona, evil_mode=False)
        evil_sections = compile_persona_sections(persona, evil_mode=True)

        self.assertNotIn(
            "EVIL MODE SCENE RULES",
            [section.title for section in normal_sections],
        )
        self.assertIn(
            "EVIL MODE SCENE RULES",
            [section.title for section in evil_sections],
        )


if __name__ == "__main__":
    unittest.main()
