from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Iterable, List, Optional, Tuple

from utils.logger import get_logger

logger = get_logger(__name__)


@dataclass(frozen=True)
class ModeProfile:
    key: str
    display_name: str
    description: str
    aliases: Tuple[str, ...]
    triggers: Tuple[str, ...]
    prompt_file: str
    evil_prompt_file: str
    persona_fallback: str
    mention_reactions: Tuple[str, ...]
    switch_message: str
    emoji_prefix: Optional[str] = None
    activity_watching: Optional[str] = None


_REGISTRY: Dict[str, ModeProfile] = {}
_LOADED = False


def register_mode(profile: ModeProfile) -> None:
    _REGISTRY[profile.key] = profile


def _load_modes() -> None:
    global _LOADED
    if _LOADED:
        return
    # Import modules to register profiles
    from . import default  # noqa: F401
    from . import femboy  # noqa: F401
    from . import tsundere  # noqa: F401
    from . import oneesan  # noqa: F401
    _LOADED = True


def get_mode_profile(key: str) -> ModeProfile:
    _load_modes()
    if key in _REGISTRY:
        return _REGISTRY[key]
    # Default to femboy if unknown
    return _REGISTRY["mode_femboy"]


def get_all_modes() -> List[ModeProfile]:
    _load_modes()
    return list(_REGISTRY.values())


def resolve_mode_key(value: str) -> Optional[str]:
    if not value:
        return None
    _load_modes()
    token = value.lower().strip()
    if token in _REGISTRY:
        return token
    for profile in _REGISTRY.values():
        if token in profile.aliases:
            return profile.key
    return None


def validate_mode_registry() -> List[str]:
    _load_modes()
    issues: List[str] = []
    keys = [profile.key for profile in _REGISTRY.values()]
    if len(keys) != len(set(keys)):
        issues.append("Duplicate mode keys detected.")

    alias_map: Dict[str, str] = {}
    for profile in _REGISTRY.values():
        for alias in profile.aliases:
            if alias in alias_map and alias_map[alias] != profile.key:
                issues.append(f"Alias '{alias}' used by {alias_map[alias]} and {profile.key}.")
            alias_map[alias] = profile.key
        if not profile.prompt_file:
            issues.append(f"{profile.key} missing prompt_file.")
        if not profile.evil_prompt_file:
            issues.append(f"{profile.key} missing evil_prompt_file.")
    if issues:
        logger.warning("Mode registry validation issues: %s", "; ".join(issues))
    return issues
