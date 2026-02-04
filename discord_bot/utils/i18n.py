from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path
from typing import Any

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
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}


def t(key: str, locale: str = "en", **vars: Any) -> str:
    data = _load_locale(locale)
    value = data.get(key, key)
    try:
        return value.format(**vars)
    except Exception:
        return value
