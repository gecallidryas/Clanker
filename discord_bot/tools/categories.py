from __future__ import annotations


TOOL_CATEGORIES = frozenset(
    {
        "admin",
        "discovery",
        "expression",
        "media",
        "memory",
        "moderation",
        "uncategorized",
        "utility",
    }
)


def normalize_tool_category(category: str) -> str:
    normalized = str(category or "").strip().lower().replace("-", "_").replace(" ", "_")
    if normalized not in TOOL_CATEGORIES:
        raise ValueError(f"Unsupported tool category: {category}")
    return normalized
