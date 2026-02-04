from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Iterable, Optional
from urllib.parse import urlparse


URL_REGEX = re.compile(r"(https?://[^\s<>()]+)", re.IGNORECASE)
TRAILING_PUNCTUATION = ".,!?)]}\"'"


@dataclass(frozen=True)
class UrlCheckResult:
    url: str
    reason: str


def _split_patterns(raw: Optional[str]) -> list[str]:
    if not raw:
        return []
    parts = []
    for line in raw.splitlines():
        for part in line.split(","):
            cleaned = part.strip()
            if cleaned:
                parts.append(cleaned)
    return parts


def compile_patterns(raw: Optional[str]) -> list[re.Pattern[str]]:
    patterns = []
    for pattern in _split_patterns(raw):
        try:
            patterns.append(re.compile(pattern, re.IGNORECASE))
        except re.error:
            continue
    return patterns


def _matches_any(patterns: Iterable[re.Pattern[str]], text: str) -> bool:
    for pattern in patterns:
        if pattern.search(text):
            return True
    return False


def extract_urls(text: str) -> list[str]:
    if not text:
        return []
    urls = []
    for match in URL_REGEX.findall(text):
        url = match.rstrip(TRAILING_PUNCTUATION)
        if url and url not in urls:
            urls.append(url)
    return urls


def _is_ip_address(host: str) -> bool:
    if not host:
        return False
    if re.fullmatch(r"\d{1,3}(?:\.\d{1,3}){3}", host):
        return True
    return False


def check_url(
    url: str,
    allowlist: Iterable[re.Pattern[str]],
    blocklist: Iterable[re.Pattern[str]],
) -> Optional[str]:
    if _matches_any(blocklist, url):
        return "blocklist"

    parsed = urlparse(url)
    host = parsed.hostname or ""

    if allowlist and not _matches_any(allowlist, url):
        return "allowlist"

    if "xn--" in host:
        return "punycode"
    if _is_ip_address(host):
        return "ip"
    if "@" in url:
        return "credentials"

    return None


def check_message_urls(
    content: str,
    allowlist_raw: Optional[str],
    blocklist_raw: Optional[str],
) -> list[UrlCheckResult]:
    allowlist = compile_patterns(allowlist_raw)
    blocklist = compile_patterns(blocklist_raw)
    results: list[UrlCheckResult] = []
    for url in extract_urls(content):
        reason = check_url(url, allowlist, blocklist)
        if reason:
            results.append(UrlCheckResult(url=url, reason=reason))
    return results


def describe_reason(reason: str) -> str:
    return {
        "blocklist": "Matches blocklist",
        "allowlist": "Not in allowlist",
        "punycode": "Punycode domain",
        "ip": "IP address URL",
        "credentials": "Contains credentials",
    }.get(reason, "Suspicious URL")
