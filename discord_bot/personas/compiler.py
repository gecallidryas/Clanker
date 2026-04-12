from __future__ import annotations

from dataclasses import dataclass

from .definition import PersonaDefinition


@dataclass(frozen=True, slots=True)
class PersonaSection:
    title: str
    body: str


def _section(title: str, lines: list[str]) -> PersonaSection | None:
    cleaned = [line.strip() for line in lines if line and line.strip()]
    if not cleaned:
        return None
    return PersonaSection(title=title, body="\n".join(cleaned))


def compile_persona_sections(persona: PersonaDefinition, evil_mode: bool = False) -> list[PersonaSection]:
    sections: list[PersonaSection] = []

    contract = _section(
        "ROLEPLAY CONTRACT",
        [
            "Stay in character.",
            "Balance roleplay immersion with practical usefulness.",
            "Preserve response coherence across turns.",
        ],
    )
    if contract:
        sections.append(contract)

    identity_lines = [f"Name: {persona.identity.display_name}"]
    if persona.identity.aliases:
        identity_lines.append(f"Aliases: {', '.join(persona.identity.aliases)}")
    if persona.identity.bio:
        identity_lines.append(f"Bio: {persona.identity.bio}")
    identity = _section("ACTIVE PERSONA IDENTITY", identity_lines)
    if identity:
        sections.append(identity)

    voice_lines = []
    if persona.voice.tone:
        voice_lines.append(f"Tone: {persona.voice.tone}")
    if persona.voice.cadence:
        voice_lines.append(f"Cadence: {persona.voice.cadence}")
    if persona.voice.signature_phrases:
        voice_lines.append(f"Signature phrases: {', '.join(persona.voice.signature_phrases)}")
    if persona.voice.forbidden_phrases:
        voice_lines.append(f"Forbidden phrases: {', '.join(persona.voice.forbidden_phrases)}")
    voice = _section("VOICE AND CADENCE", voice_lines)
    if voice:
        sections.append(voice)

    worldview = _section("WORLDVIEW AND SUBTEXT", [persona.worldview.description])
    if worldview:
        sections.append(worldview)

    relationship = _section("RELATIONSHIP RULES", [persona.relationship.description])
    if relationship:
        sections.append(relationship)

    normal_lines = [persona.scene_rules.normal]
    normal_scene = _section("NORMAL MODE SCENE RULES", normal_lines)
    if normal_scene:
        sections.append(normal_scene)

    if evil_mode:
        evil_scene = _section("EVIL MODE SCENE RULES", [persona.scene_rules.evil])
        if evil_scene:
            sections.append(evil_scene)

    utility = _section(
        "TASK AND TOOL COMPETENCE RULES",
        [persona.utility.description or "Be competent, direct, and tool-aware."],
    )
    if utility:
        sections.append(utility)

    constraints = _section("HARD CONSTRAINTS", list(persona.constraints.hard_rules))
    if constraints:
        sections.append(constraints)

    example_lines: list[str] = []
    if persona.examples.normal:
        example_lines.append("Normal:")
        example_lines.extend(f"- {item}" for item in persona.examples.normal)
    if evil_mode and persona.examples.evil:
        example_lines.append("Evil:")
        example_lines.extend(f"- {item}" for item in persona.examples.evil)
    examples = _section("EXAMPLE REPLIES", example_lines)
    if examples:
        sections.append(examples)

    return sections
