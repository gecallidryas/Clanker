from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path
from typing import Any, Optional

BASE_DIR = Path(__file__).resolve().parent.parent
LOCALES_DIR = BASE_DIR / "locales"


@lru_cache(maxsize=8)
def _load_locale(locale: str) -> dict[str, Any]:
    path = LOCALES_DIR / f"{locale}.json"
    if not path.exists():
        path = LOCALES_DIR / "en.json"
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8-sig"))
    except Exception:
        return {}


def normalize_locale(locale: Optional[str]) -> str:
    if not locale:
        return "en"
    value = str(locale)
    if "-" in value:
        value = value.split("-", 1)[0]
    return value or "en"


def get_locale_from_interaction(interaction: Any) -> str:
    locale = getattr(interaction, "locale", None) or getattr(interaction, "guild_locale", None)
    return normalize_locale(locale)


def get_locale_from_guild(guild: Any) -> str:
    locale = getattr(guild, "preferred_locale", None)
    return normalize_locale(locale)


def t(key: str, locale: str = "en", **vars: Any) -> str:
    locale = normalize_locale(locale)
    data = _load_locale(locale)
    value = data.get(key)
    if value is None and locale != "en":
        value = _load_locale("en").get(key)
    if value is None:
        value = key
    try:
        return value.format(**vars)
    except Exception:
        return value
