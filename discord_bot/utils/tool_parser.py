from __future__ import annotations

import json
import re
from typing import Any, Optional


TOOL_BLOCK_PATTERN = re.compile(r"```tool\s*(\{.*?\})\s*```", re.DOTALL | re.IGNORECASE)
JSON_BLOCK_PATTERN = re.compile(r"```json\s*(\{.*?\})\s*```", re.DOTALL | re.IGNORECASE)


def extract_tool_call(text: str) -> Optional[dict[str, Any]]:
    if not text:
        return None
    match = TOOL_BLOCK_PATTERN.search(text)
    if not match:
        match = JSON_BLOCK_PATTERN.search(text)
    if not match:
        return None
    payload = match.group(1)
    try:
        data = json.loads(payload)
    except json.JSONDecodeError:
        return None
    if not isinstance(data, dict):
        return None
    if "tool" not in data:
        return None
    return {
        "tool": data.get("tool"),
        "args": data.get("args") or {},
    }


def strip_tool_call(text: str) -> str:
    if not text:
        return ""
    text = TOOL_BLOCK_PATTERN.sub("", text)
    def _strip_json(match: re.Match) -> str:
        payload = match.group(1) or ""
        if "\"tool\"" in payload:
            return ""
        return match.group(0)
    text = JSON_BLOCK_PATTERN.sub(_strip_json, text)
    return text.strip()
