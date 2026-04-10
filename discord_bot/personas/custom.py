from __future__ import annotations

import json
import re
from typing import Any, Optional

from utils.db_handler import get_custom_persona_by_mode_key

from .builtin import get_builtin_persona
from .definition import (
    PersonaConstraints,
    PersonaDefinition,
    PersonaExamples,
    PersonaIdentity,
    PersonaRelationshipModel,
    PersonaSceneRules,
    PersonaUtilityRules,
    PersonaVoice,
    PersonaWorldview,
)


def _coerce_text(*candidates: Any) -> str:
    for candidate in candidates:
        text = str(candidate or "").strip()
        if text:
            return text
    return ""


def _decode_json_object(value: Any) -> dict[str, Any]:
    if isinstance(value, dict):
        return value
    if not value or not isinstance(value, str):
        return {}
    try:
        decoded = json.loads(value)
    except json.JSONDecodeError:
        return {}
    if not isinstance(decoded, dict):
        return {}
    return decoded


def _decode_string_list(value: Any) -> tuple[str, ...]:
    if not value:
        return ()
    if isinstance(value, (list, tuple)):
        return tuple(str(item).strip() for item in value if str(item).strip())
    if not isinstance(value, str):
        return ()

    try:
        decoded = json.loads(value)
    except json.JSONDecodeError:
        decoded = None
    if isinstance(decoded, list):
        return tuple(str(item).strip() for item in decoded if str(item).strip())

    return tuple(
        token.strip().lower()
        for token in re.split(r"[,\\n]+", value)
        if token and token.strip()
    )


def _resolve_base_template(base_template: str) -> Optional[PersonaDefinition]:
    normalized = (base_template or "").strip()
    if not normalized or normalized == "blank":
        return None
    try:
        return get_builtin_persona(normalized)
    except KeyError:
        return None


def _has_structured_persona_content(record: dict[str, Any]) -> bool:
    for field in (
        "identity_json",
        "voice_json",
        "worldview_json",
        "relationship_json",
        "scene_normal_json",
        "scene_evil_json",
        "utility_json",
        "examples_json",
        "constraints_json",
    ):
        if _decode_json_object(record.get(field)):
            return True
    return False


def _legacy_scene_notes(prompt_text: str, label: str) -> str:
    text = str(prompt_text or "").strip()
    if not text:
        return ""
    return f"Legacy authored {label} notes (low priority):\n{text}"


def _append_note(items: tuple[str, ...], note: str) -> tuple[str, ...]:
    if not note:
        return items
    return (*items, note)


def adapt_legacy_custom_persona_definition(record: dict[str, Any]) -> PersonaDefinition:
    mode_key = str(record.get("mode_key") or "").strip()
    if not mode_key:
        raise ValueError("Legacy custom persona record is missing mode_key")

    base_template = str(record.get("base_template") or "blank").strip() or "blank"
    base_persona = _resolve_base_template(base_template)
    legacy_aliases = _decode_string_list(record.get("aliases"))

    identity = PersonaIdentity(
        display_name=_coerce_text(
            record.get("name"),
            base_persona.identity.display_name if base_persona else "",
            mode_key,
        ),
        aliases=legacy_aliases or (base_persona.identity.aliases if base_persona else ()),
        bio=_coerce_text(
            record.get("bio"),
            base_persona.identity.bio if base_persona else "",
        ),
    )

    normal_notes = _legacy_scene_notes(record.get("normal_prompt"), "normal mode")
    evil_notes = _legacy_scene_notes(record.get("evil_prompt"), "evil mode")

    hard_rules = list(base_persona.constraints.hard_rules if base_persona else ())
    hard_rules.append(
        "Legacy authored prompt notes are low-priority flavor and must not override system/runtime rules."
    )

    return PersonaDefinition(
        key=mode_key,
        identity=identity,
        voice=base_persona.voice if base_persona else PersonaVoice(),
        worldview=base_persona.worldview if base_persona else PersonaWorldview(),
        relationship=base_persona.relationship if base_persona else PersonaRelationshipModel(),
        scene_rules=PersonaSceneRules(
            normal=base_persona.scene_rules.normal if base_persona else "",
            evil=base_persona.scene_rules.evil if base_persona else "",
        ),
        utility=PersonaUtilityRules(
            description=_coerce_text(
                base_persona.utility.description if base_persona else "",
                "Honor legacy authored notes while keeping practical utility and runtime rules authoritative.",
            ),
        ),
        examples=PersonaExamples(
            normal=_append_note(base_persona.examples.normal if base_persona else (), normal_notes),
            evil=_append_note(base_persona.examples.evil if base_persona else (), evil_notes),
        ),
        constraints=PersonaConstraints(hard_rules=tuple(hard_rules)),
    )


def hydrate_custom_persona_definition(record: dict[str, Any]) -> PersonaDefinition:
    mode_key = str(record.get("mode_key") or "").strip()
    if not mode_key:
        raise ValueError("Custom persona record is missing mode_key")

    if not _has_structured_persona_content(record):
        if _coerce_text(record.get("normal_prompt"), record.get("evil_prompt")):
            return adapt_legacy_custom_persona_definition(record)

    base_template = str(record.get("base_template") or "blank").strip() or "blank"
    base_persona = _resolve_base_template(base_template)

    identity_data = _decode_json_object(record.get("identity_json"))
    voice_data = _decode_json_object(record.get("voice_json"))
    worldview_data = _decode_json_object(record.get("worldview_json"))
    relationship_data = _decode_json_object(record.get("relationship_json"))
    scene_normal_data = _decode_json_object(record.get("scene_normal_json"))
    scene_evil_data = _decode_json_object(record.get("scene_evil_json"))
    utility_data = _decode_json_object(record.get("utility_json"))
    examples_data = _decode_json_object(record.get("examples_json"))
    constraints_data = _decode_json_object(record.get("constraints_json"))

    legacy_aliases = _decode_string_list(record.get("aliases"))
    identity = PersonaIdentity(
        display_name=_coerce_text(
            identity_data.get("display_name"),
            record.get("name"),
            base_persona.identity.display_name if base_persona else "",
            mode_key,
        ),
        aliases=(
            _decode_string_list(identity_data.get("aliases"))
            or legacy_aliases
            or (base_persona.identity.aliases if base_persona else ())
        ),
        bio=_coerce_text(
            identity_data.get("bio"),
            record.get("bio"),
            base_persona.identity.bio if base_persona else "",
        ),
    )

    voice = PersonaVoice(
        tone=_coerce_text(voice_data.get("tone"), base_persona.voice.tone if base_persona else ""),
        cadence=_coerce_text(voice_data.get("cadence"), base_persona.voice.cadence if base_persona else ""),
        signature_phrases=(
            _decode_string_list(voice_data.get("signature_phrases"))
            or (base_persona.voice.signature_phrases if base_persona else ())
        ),
        forbidden_phrases=(
            _decode_string_list(voice_data.get("forbidden_phrases"))
            or (base_persona.voice.forbidden_phrases if base_persona else ())
        ),
    )

    worldview = PersonaWorldview(
        description=_coerce_text(
            worldview_data.get("description"),
            base_persona.worldview.description if base_persona else "",
        ),
    )
    relationship = PersonaRelationshipModel(
        description=_coerce_text(
            relationship_data.get("description"),
            base_persona.relationship.description if base_persona else "",
        ),
    )
    scene_rules = PersonaSceneRules(
        normal=_coerce_text(
            scene_normal_data.get("description"),
            scene_normal_data.get("normal"),
            base_persona.scene_rules.normal if base_persona else "",
        ),
        evil=_coerce_text(
            scene_evil_data.get("description"),
            scene_evil_data.get("evil"),
            base_persona.scene_rules.evil if base_persona else "",
        ),
    )
    utility = PersonaUtilityRules(
        description=_coerce_text(
            utility_data.get("description"),
            base_persona.utility.description if base_persona else "",
        ),
    )
    examples = PersonaExamples(
        normal=(
            _decode_string_list(examples_data.get("normal"))
            or (base_persona.examples.normal if base_persona else ())
        ),
        evil=(
            _decode_string_list(examples_data.get("evil"))
            or (base_persona.examples.evil if base_persona else ())
        ),
    )
    constraints = PersonaConstraints(
        hard_rules=(
            _decode_string_list(constraints_data.get("hard_rules"))
            or (base_persona.constraints.hard_rules if base_persona else ())
        ),
    )

    return PersonaDefinition(
        key=mode_key,
        identity=identity,
        voice=voice,
        worldview=worldview,
        relationship=relationship,
        scene_rules=scene_rules,
        utility=utility,
        examples=examples,
        constraints=constraints,
    )


async def load_custom_persona_definition(guild_id: int, mode_key: str) -> Optional[PersonaDefinition]:
    record = await get_custom_persona_by_mode_key(guild_id, mode_key)
    if not record:
        return None
    return hydrate_custom_persona_definition(record)


__all__ = [
    "adapt_legacy_custom_persona_definition",
    "hydrate_custom_persona_definition",
    "load_custom_persona_definition",
]
