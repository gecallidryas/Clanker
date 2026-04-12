from __future__ import annotations

from dataclasses import dataclass, field


def _tuple_or_empty(values: tuple[str, ...] | list[str] | None) -> tuple[str, ...]:
    if not values:
        return ()
    return tuple(str(value).strip() for value in values if str(value).strip())


@dataclass(frozen=True, slots=True)
class PersonaIdentity:
    display_name: str
    aliases: tuple[str, ...] = ()
    bio: str = ""

    def __post_init__(self) -> None:
        object.__setattr__(self, "aliases", _tuple_or_empty(self.aliases))


@dataclass(frozen=True, slots=True)
class PersonaVoice:
    tone: str = ""
    cadence: str = ""
    signature_phrases: tuple[str, ...] = ()
    forbidden_phrases: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        object.__setattr__(self, "signature_phrases", _tuple_or_empty(self.signature_phrases))
        object.__setattr__(self, "forbidden_phrases", _tuple_or_empty(self.forbidden_phrases))


@dataclass(frozen=True, slots=True)
class PersonaWorldview:
    description: str = ""


@dataclass(frozen=True, slots=True)
class PersonaRelationshipModel:
    description: str = ""


@dataclass(frozen=True, slots=True)
class PersonaSceneRules:
    normal: str = ""
    evil: str = ""


@dataclass(frozen=True, slots=True)
class PersonaUtilityRules:
    description: str = ""


@dataclass(frozen=True, slots=True)
class PersonaExamples:
    normal: tuple[str, ...] = ()
    evil: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        object.__setattr__(self, "normal", _tuple_or_empty(self.normal))
        object.__setattr__(self, "evil", _tuple_or_empty(self.evil))


@dataclass(frozen=True, slots=True)
class PersonaConstraints:
    hard_rules: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        object.__setattr__(self, "hard_rules", _tuple_or_empty(self.hard_rules))


@dataclass(frozen=True, slots=True)
class PersonaDefinition:
    key: str
    identity: PersonaIdentity
    voice: PersonaVoice = field(default_factory=PersonaVoice)
    worldview: PersonaWorldview = field(default_factory=PersonaWorldview)
    relationship: PersonaRelationshipModel = field(default_factory=PersonaRelationshipModel)
    scene_rules: PersonaSceneRules = field(default_factory=PersonaSceneRules)
    utility: PersonaUtilityRules = field(default_factory=PersonaUtilityRules)
    examples: PersonaExamples = field(default_factory=PersonaExamples)
    constraints: PersonaConstraints = field(default_factory=PersonaConstraints)
