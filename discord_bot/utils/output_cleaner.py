from __future__ import annotations

import re
from typing import Mapping, Sequence, Set


_CODE_BLOCK_RE = re.compile(r"```[\s\S]*?```")
_INLINE_CODE_RE = re.compile(r"`[^`]*`")
_CUSTOM_EMOJI_TAG_RE = re.compile(r"<a?:([^:>]+):\d{5,}>")
_CUSTOM_EMOJI_ANY_TAG_RE = re.compile(r"<[^:>\s]*:([A-Za-z0-9_]+):(\d+)>")
_RAW_EMOJI_TAG_RE = re.compile(r"<a?:[^:>]+:\d+>")
_MALFORMED_CUSTOM_TAG_RE = re.compile(r"<a?:([^>]+)>")
_VALID_CUSTOM_TAG_PAYLOAD_RE = re.compile(r"^[A-Za-z0-9_]+:\d{5,}$")
_SHORTCODE_NO_TRAILING_COLON_RE = re.compile(r"^:([A-Za-z0-9_]+)$")


def _protect_code(text: str) -> tuple[str, list[tuple[str, str]]]:
    replacements: list[tuple[str, str]] = []

    def replace_block(match: re.Match[str]) -> str:
        key = f"__CODE_BLOCK_{len(replacements)}__"
        replacements.append((key, match.group(0)))
        return key

    protected = _CODE_BLOCK_RE.sub(replace_block, text)

    def replace_inline(match: re.Match[str]) -> str:
        key = f"__INLINE_CODE_{len(replacements)}__"
        replacements.append((key, match.group(0)))
        return key

    protected = _INLINE_CODE_RE.sub(replace_inline, protected)
    return protected, replacements


def _restore_code(text: str, replacements: list[tuple[str, str]]) -> str:
    restored = text
    for key, original in reversed(replacements):
        restored = restored.replace(key, original)
    return restored


def _normalize_emoji_tail(emoji_tail: str) -> str:
    compact = (emoji_tail or "").strip()
    if not compact:
        return ""
    match = _SHORTCODE_NO_TRAILING_COLON_RE.fullmatch(compact)
    if match:
        return f":{match.group(1)}:"
    return compact


def normalize_custom_emojis_for_llm(text: str) -> str:
    if not text:
        return text
    protected, replacements = _protect_code(text)
    protected = _CUSTOM_EMOJI_TAG_RE.sub(lambda m: f":{m.group(1)}:", protected)
    return _restore_code(protected, replacements)


def replace_mention_handles(
    text: str,
    mention_map: Mapping[str, Sequence[str]] | None = None,
    mention_id_set: Set[str] | None = None,
) -> str:
    if not text or (not mention_map and not mention_id_set):
        return text
    mention_map = mention_map or {}
    mention_id_set = mention_id_set or set()
    protected, replacements = _protect_code(text)

    def replace_braced(match: re.Match[str]) -> str:
        handle = (match.group(1) or "").strip()
        if not handle:
            return match.group(0)

        if "|" in handle:
            maybe_id = handle.rsplit("|", 1)[-1].strip()
            if maybe_id.isdigit() and maybe_id in mention_id_set:
                return f"<@{maybe_id}>"
        if handle.isdigit() and handle in mention_id_set:
            return f"<@{handle}>"

        ids = list(mention_map.get(handle.lower(), []))
        if len(ids) == 1:
            return f"<@{ids[0]}>"
        return "{" + handle + "}"

    protected = re.sub(r"@\{([^}]+)\}", replace_braced, protected)

    def replace_handle_pipe(match: re.Match[str]) -> str:
        prefix = match.group(1)
        _name = (match.group(2) or "").strip()
        maybe_id = (match.group(3) or "").strip()
        if maybe_id.isdigit() and maybe_id in mention_id_set:
            return f"{prefix}<@{maybe_id}>"
        return match.group(0)

    protected = re.sub(
        r"(^|[^\w<])@([\w][\w -]*)\|(\d{5,20})",
        replace_handle_pipe,
        protected,
        flags=re.MULTILINE,
    )

    def replace_bare_handle(match: re.Match[str]) -> str:
        prefix = match.group(1)
        handle = (match.group(2) or "").strip()
        if not handle:
            return match.group(0)
        if handle.lower() in {"everyone", "here"}:
            return match.group(0)
        ids = list(mention_map.get(handle.lower(), []))
        if len(ids) == 1:
            return f"{prefix}<@{ids[0]}>"
        return match.group(0)

    protected = re.sub(
        r"(^|[^\w<])@([A-Za-z0-9_][A-Za-z0-9_-]{0,31})",
        replace_bare_handle,
        protected,
        flags=re.MULTILINE,
    )

    return _restore_code(protected, replacements)


def clean_llm_output(
    text: str,
    bot_name: str | None = None,
    emoji_usage_enabled: bool = True,
    mention_map: Mapping[str, Sequence[str]] | None = None,
    mention_id_set: Set[str] | None = None,
) -> str:
    if not text:
        return text

    cleaned = re.sub(r"\[system:[\s\S]*?\]", "", text, flags=re.IGNORECASE)
    cleaned = re.sub(r"\[system:[\s\S]*$", "", cleaned, flags=re.IGNORECASE)
    cleaned = cleaned.replace("<|im_end|>", "").replace("<|file_separator|>", "")
    cleaned = re.sub(r"\n{3,}", "\n\n", cleaned)
    cleaned = re.sub(r"\*\*<(.*?)>\*\*", r"<\1>", cleaned)
    cleaned = re.sub(r"\*<(.*?)>\*", r"<\1>", cleaned)
    cleaned = re.sub(r"<([a-zA-Z0-9_]+)>[\s\S]*?</\1>", "", cleaned)

    name = bot_name or "Tomori"
    prefix_re = re.compile(
        rf"^(\*\*{re.escape(name)}:\*\*|\*\*{re.escape(name)}\*\*:|{re.escape(name)}:)\s*",
        flags=re.IGNORECASE,
    )
    cleaned = prefix_re.sub("", cleaned).strip()

    protected, replacements = _protect_code(cleaned)
    protected = _CUSTOM_EMOJI_ANY_TAG_RE.sub(r"<:\1:\2>", protected)

    def _repair_malformed_custom_tag(match: re.Match[str]) -> str:
        payload = (match.group(1) or "").strip()
        if not payload:
            return ""
        if _VALID_CUSTOM_TAG_PAYLOAD_RE.fullmatch(payload):
            return match.group(0)
        payload = payload.strip(":")
        if not payload:
            return ""
        if re.fullmatch(r"[A-Za-z0-9_]+", payload):
            return f":{payload}:"
        emoji_tail = re.sub(r"^[A-Za-z0-9_\-]+", "", payload).strip()
        if emoji_tail:
            return _normalize_emoji_tail(emoji_tail)
        return payload

    protected = _MALFORMED_CUSTOM_TAG_RE.sub(_repair_malformed_custom_tag, protected)
    if not emoji_usage_enabled:
        protected = _RAW_EMOJI_TAG_RE.sub("", protected)

    protected = replace_mention_handles(
        protected,
        mention_map=mention_map,
        mention_id_set=mention_id_set,
    )
    cleaned = _restore_code(protected, replacements)
    cleaned = re.sub(r"\s{2,}", " ", cleaned).strip()
    return cleaned
