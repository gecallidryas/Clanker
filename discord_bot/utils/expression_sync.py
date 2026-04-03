from __future__ import annotations

import re
from types import SimpleNamespace
from typing import Iterable, List, Optional, Sequence

from utils.logger import get_logger

logger = get_logger(__name__)

DISCORD_API_BASE = "https://discord.com/api/v10"
EXPLICIT_EXPRESSION_TERMS = (
    "sticker",
    "emoji",
    "emote",
    "reaction",
    "react with",
    "reply with",
    "cute sticker",
    "funny sticker",
    "funny emote",
    "expressive",
)
AFFECTION_TOKENS = ("love", "heart", "hug", "kiss", "cute", "blush", "happy", "yay")
_TOKEN_PATTERN = re.compile(r"[a-z0-9_]+")


def normalize_expression_name(name: str) -> str:
    return re.sub(r"\s+", "_", (name or "").strip().lower())


def expression_name_fallback(name: str) -> str:
    cleaned = re.sub(r"[-0-9]+", "", name or "")
    normalized = cleaned.replace("_", " ").strip()
    return normalized or (name or "").strip()


def parse_admin_tags(raw_value: Optional[str]) -> tuple[str, ...]:
    if not raw_value:
        return ()
    try:
        import json

        parsed = json.loads(raw_value)
    except Exception:
        return ()
    if not isinstance(parsed, list):
        return ()
    tags = [str(item).strip().lower() for item in parsed if str(item).strip()]
    return tuple(dict.fromkeys(tags))


def build_effective_description(
    *,
    name: str,
    discord_description: Optional[str],
    admin_description: Optional[str] = None,
) -> str:
    if admin_description:
        return admin_description.strip()
    if discord_description:
        return discord_description.strip()
    return expression_name_fallback(name)


def tokenize_expression_text(value: str) -> set[str]:
    return {token for token in _TOKEN_PATTERN.findall((value or "").lower()) if len(token) > 1}


def expression_requests_tool_prompt(message_text: str) -> bool:
    lowered = (message_text or "").lower()
    return any(term in lowered for term in EXPLICIT_EXPRESSION_TERMS)


async def fetch_application_emojis_live(bot, *, raise_on_failure: bool = False) -> List:
    emojis: List = []
    last_error: Optional[Exception] = None
    existing = getattr(bot, "application_emojis", None)
    if existing:
        try:
            emojis = list(existing)
        except Exception:
            emojis = []

    if not emojis:
        fetcher = getattr(bot, "fetch_application_emojis", None)
        if fetcher:
            try:
                emojis = await fetcher()
            except Exception as exc:
                logger.warning("Failed to fetch application emojis: %s", exc)
                last_error = exc
                emojis = []

    if not emojis:
        application_id = getattr(bot, "application_id", None) or getattr(getattr(bot, "application", None), "id", None)
        token = getattr(getattr(bot, "http", None), "token", None)
        if application_id and token:
            try:
                import aiohttp

                url = f"{DISCORD_API_BASE}/applications/{application_id}/emojis"
                headers = {"Authorization": f"Bot {token}"}
                timeout = aiohttp.ClientTimeout(total=12)
                async with aiohttp.ClientSession(timeout=timeout) as session:
                    async with session.get(url, headers=headers) as response:
                        if response.status >= 400:
                            body = await response.text()
                            raise RuntimeError(f"HTTP {response.status}: {body[:200]}")
                        payload = await response.json()
                items = payload.get("items", []) if isinstance(payload, dict) else []
                emojis = [
                    SimpleNamespace(
                        id=int(item.get("id")),
                        name=str(item.get("name") or ""),
                        animated=bool(item.get("animated", False)),
                    )
                    for item in items
                    if item.get("id") and item.get("name")
                ]
            except Exception as exc:
                logger.warning("Failed REST fallback for application emojis: %s", exc)
                last_error = exc
                emojis = []
    if not emojis and raise_on_failure and last_error is not None:
        raise last_error
    return list(emojis)


async def fetch_guild_assets_live(
    guild,
    *,
    force_fetch: bool = False,
    expect_emojis: bool = False,
    expect_stickers: bool = False,
) -> tuple[List, List]:
    emojis: List = []
    stickers: List = []
    try:
        emojis = list(getattr(guild, "emojis", []) or [])
    except Exception:
        emojis = []
    try:
        stickers = list(getattr(guild, "stickers", []) or [])
    except Exception:
        stickers = []

    if force_fetch or (expect_emojis and not emojis):
        fetcher = getattr(guild, "fetch_emojis", None)
        if fetcher:
            try:
                emojis = await fetcher()
            except Exception as exc:
                logger.warning("Failed to fetch guild emojis for %s: %s", getattr(guild, "id", "?"), exc)

    if force_fetch or (expect_stickers and not stickers):
        fetcher = getattr(guild, "fetch_stickers", None)
        if fetcher:
            try:
                stickers = await fetcher()
            except Exception as exc:
                logger.warning("Failed to fetch guild stickers for %s: %s", getattr(guild, "id", "?"), exc)

    return list(emojis), list(stickers)


def build_guild_expression_rows(guild_id: int, emojis: Sequence, stickers: Sequence) -> List[dict]:
    rows: List[dict] = []
    for emoji in emojis:
        emoji_id = getattr(emoji, "id", None)
        name = str(getattr(emoji, "name", "") or "").strip()
        if not emoji_id or not name:
            continue
        rows.append(
            {
                "scope_type": "guild",
                "scope_id": int(guild_id),
                "kind": "emoji",
                "source": "guild_emoji",
                "discord_expression_id": str(int(emoji_id)),
                "name": name,
                "normalized_name": normalize_expression_name(name),
                "animated": int(bool(getattr(emoji, "animated", False))),
                "format_type": None,
                "discord_description": None,
            }
        )

    for sticker in stickers:
        sticker_id = getattr(sticker, "id", None)
        name = str(getattr(sticker, "name", "") or "").strip()
        if not sticker_id or not name:
            continue
        format_obj = getattr(sticker, "format", None)
        format_type = getattr(format_obj, "value", format_obj)
        description = str(getattr(sticker, "description", "") or "").strip() or None
        rows.append(
            {
                "scope_type": "guild",
                "scope_id": int(guild_id),
                "kind": "sticker",
                "source": "guild_sticker",
                "discord_expression_id": str(int(sticker_id)),
                "name": name,
                "normalized_name": normalize_expression_name(name),
                "animated": None,
                "format_type": int(format_type) if format_type is not None else None,
                "discord_description": description,
            }
        )
    return rows


def build_application_expression_rows(scope_id: int, emojis: Sequence) -> List[dict]:
    rows: List[dict] = []
    for emoji in emojis:
        emoji_id = getattr(emoji, "id", None)
        name = str(getattr(emoji, "name", "") or "").strip()
        if not emoji_id or not name:
            continue
        rows.append(
            {
                "scope_type": "application",
                "scope_id": int(scope_id),
                "kind": "emoji",
                "source": "app_emoji",
                "discord_expression_id": str(int(emoji_id)),
                "name": name,
                "normalized_name": normalize_expression_name(name),
                "animated": int(bool(getattr(emoji, "animated", False))),
                "format_type": None,
                "discord_description": None,
            }
        )
    return rows


def score_expression_match(
    expression,
    *,
    query: str,
    mode: str,
    affection_points: int,
    recent_context_text: str = "",
) -> int:
    name = str(getattr(expression, "name", "") or "")
    description = str(getattr(expression, "effective_description", "") or getattr(expression, "discord_description", "") or "")
    source = str(getattr(expression, "source", "") or "")
    query_lower = (query or "").lower()
    query_tokens = tokenize_expression_text(query_lower)
    name_tokens = tokenize_expression_text(name)
    description_tokens = tokenize_expression_text(description)
    score = 0

    if query_lower:
        if query_lower == name.lower():
            score += 20
        elif query_lower in name.lower():
            score += 10
        score += len(query_tokens & name_tokens) * 4
        score += len(query_tokens & description_tokens) * 3

    if source == "app_emoji":
        lowered_name = name.lower()
        if mode == "mode_femboy" and lowered_name.startswith("femmy"):
            score += 3
        elif mode == "mode_oneesan" and lowered_name.startswith("yumi"):
            score += 3

    if affection_points >= 500 and (name_tokens | description_tokens) & set(AFFECTION_TOKENS):
        score += 1

    recent_lower = (recent_context_text or "").lower()
    if recent_lower:
        if f":{name.lower()}:" in recent_lower:
            score -= 4
        elif name.lower() in recent_lower:
            score -= 2

    return score


def rank_expressions(
    expressions: Iterable,
    *,
    query: str,
    mode: str,
    affection_points: int,
    recent_context_text: str = "",
    limit: int,
) -> List:
    scored = []
    for expression in expressions:
        score = score_expression_match(
            expression,
            query=query,
            mode=mode,
            affection_points=affection_points,
            recent_context_text=recent_context_text,
        )
        scored.append((score, str(getattr(expression, "name", "") or "").lower(), expression))
    scored.sort(key=lambda item: (-item[0], item[1]))
    ranked = [expression for _score, _name, expression in scored[:limit]]
    if len(ranked) < limit:
        seen_ids = {getattr(item, "discord_expression_id", None) for item in ranked}
        for expression in expressions:
            expression_id = getattr(expression, "discord_expression_id", None)
            if expression_id in seen_ids:
                continue
            ranked.append(expression)
            seen_ids.add(expression_id)
            if len(ranked) >= limit:
                break
    return ranked[:limit]
