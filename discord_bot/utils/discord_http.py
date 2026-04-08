from __future__ import annotations

from typing import Any


def describe_http_error(exc: Any) -> str:
    details: list[str] = []

    status = getattr(exc, "status", None)
    if status is not None:
        details.append(f"status={status}")

    code = getattr(exc, "code", None)
    if code not in (None, 0):
        details.append(f"code={code}")

    text = str(getattr(exc, "text", "") or "").strip()
    if text:
        compact = " ".join(text.split())
        details.append(f"text={compact[:200]}")

    if not details:
        return "http"
    return f"http ({', '.join(details)})"
