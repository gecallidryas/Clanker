from __future__ import annotations

from ..definition import PersonaDefinition
from .default import PERSONA as DEFAULT_PERSONA
from .femboy import PERSONA as FEMBOY_PERSONA
from .oneesan import PERSONA as ONEESAN_PERSONA
from .tsundere import PERSONA as TSUNDERE_PERSONA

BUILTIN_PERSONAS: dict[str, PersonaDefinition] = {
    DEFAULT_PERSONA.key: DEFAULT_PERSONA,
    FEMBOY_PERSONA.key: FEMBOY_PERSONA,
    TSUNDERE_PERSONA.key: TSUNDERE_PERSONA,
    ONEESAN_PERSONA.key: ONEESAN_PERSONA,
}


def get_builtin_persona(mode_key: str) -> PersonaDefinition:
    try:
        return BUILTIN_PERSONAS[mode_key]
    except KeyError as error:
        raise KeyError(f"Unknown builtin persona key: {mode_key}") from error


__all__ = [
    "BUILTIN_PERSONAS",
    "get_builtin_persona",
]
