from __future__ import annotations

import random
from dataclasses import dataclass, replace
from datetime import datetime, timezone
from typing import Dict, Iterable, List, Optional

import discord

from utils.db_handler import (
    EXPRESSION_KIND_EMOJI,
    EXPRESSION_KIND_STICKER,
    EXPRESSION_SCOPE_APPLICATION,
    EXPRESSION_SCOPE_GUILD,
    _parse_timestamp,
    get_expression_sync_state,
    has_persisted_expressions,
    list_expressions,
    prune_deleted_expressions,
    upsert_expression_catalog,
)
from utils.expression_sync import (
    build_application_expression_rows,
    build_effective_description,
    build_guild_expression_rows,
    expression_requests_tool_prompt,
    fetch_application_emojis_live,
    fetch_guild_assets_live,
    parse_admin_tags,
    rank_expressions,
)
from utils.logger import get_logger

logger = get_logger(__name__)

DEFAULT_GUILD_SNAPSHOT_TTL_SECONDS = 300
DEFAULT_APP_SNAPSHOT_TTL_SECONDS = 600
DEFAULT_EMOJI_SHORTLIST_LIMIT = 6
DEFAULT_STICKER_SHORTLIST_LIMIT = 3


@dataclass(frozen=True)
class ExpressionRecord:
    catalog_id: int
    scope_type: str
    scope_id: int
    kind: str
    source: str
    discord_expression_id: str
    name: str
    normalized_name: str
    animated: bool
    format_type: Optional[int]
    discord_description: Optional[str]
    available: bool
    snapshot_version: int
    first_seen_at: Optional[datetime]
    last_seen_at: Optional[datetime]
    deleted_at: Optional[datetime]
    admin_description: Optional[str]
    admin_tags: tuple[str, ...]

    @classmethod
    def from_row(cls, row: Dict[str, object]) -> "ExpressionRecord":
        return cls(
            catalog_id=int(row.get("id") or 0),
            scope_type=str(row.get("scope_type") or ""),
            scope_id=int(row.get("scope_id") or 0),
            kind=str(row.get("kind") or ""),
            source=str(row.get("source") or ""),
            discord_expression_id=str(row.get("discord_expression_id") or ""),
            name=str(row.get("name") or ""),
            normalized_name=str(row.get("normalized_name") or ""),
            animated=bool(row.get("animated")),
            format_type=int(row["format_type"]) if row.get("format_type") is not None else None,
            discord_description=str(row.get("discord_description") or "").strip() or None,
            available=bool(row.get("available")),
            snapshot_version=int(row.get("snapshot_version") or 0),
            first_seen_at=_parse_timestamp(row.get("first_seen_at")),
            last_seen_at=_parse_timestamp(row.get("last_seen_at")),
            deleted_at=_parse_timestamp(row.get("deleted_at")),
            admin_description=str(row.get("admin_description") or "").strip() or None,
            admin_tags=parse_admin_tags(row.get("admin_tags_json")),
        )

    @property
    def id(self) -> int:
        try:
            return int(self.discord_expression_id)
        except Exception:
            return 0

    @property
    def effective_description(self) -> str:
        return build_effective_description(
            name=self.name,
            discord_description=self.discord_description,
            admin_description=self.admin_description,
        )

    def matches_query(self, query: Optional[str]) -> bool:
        if not query:
            return True
        query_lower = query.lower()
        return query_lower in self.name.lower() or query_lower in self.effective_description.lower()


@dataclass(frozen=True)
class ExpressionSnapshot:
    scope_type: str
    scope_id: int
    snapshot_version: int
    refreshed_at: datetime
    stale: bool
    expressions_by_catalog_id: Dict[int, ExpressionRecord]
    expressions_by_discord_id: Dict[str, ExpressionRecord]
    expressions_by_normalized_name: Dict[str, tuple[ExpressionRecord, ...]]
    prompt_material: tuple[ExpressionRecord, ...]
    counts_by_kind: Dict[str, int]
    counts_by_source: Dict[str, int]

    @classmethod
    def empty(cls, scope_type: str, scope_id: int, *, stale: bool = False) -> "ExpressionSnapshot":
        return cls(
            scope_type=scope_type,
            scope_id=int(scope_id),
            snapshot_version=0,
            refreshed_at=datetime.now(timezone.utc),
            stale=stale,
            expressions_by_catalog_id={},
            expressions_by_discord_id={},
            expressions_by_normalized_name={},
            prompt_material=(),
            counts_by_kind={},
            counts_by_source={},
        )

    def of_kind(self, kind: str) -> List[ExpressionRecord]:
        return [record for record in self.prompt_material if record.kind == kind]


@dataclass(frozen=True)
class ExpressionPromptContext:
    snapshot_version: int
    summary_lines: List[str]
    emoji_lines: List[str]
    sticker_lines: List[str]


class ExpressionService:
    def __init__(
        self,
        bot,
        *,
        guild_ttl_seconds: int = DEFAULT_GUILD_SNAPSHOT_TTL_SECONDS,
        app_ttl_seconds: int = DEFAULT_APP_SNAPSHOT_TTL_SECONDS,
    ) -> None:
        self.bot = bot
        self.guild_ttl_seconds = int(guild_ttl_seconds)
        self.app_ttl_seconds = int(app_ttl_seconds)
        self._guild_snapshots: Dict[int, ExpressionSnapshot] = {}
        self._guild_suspect: set[int] = set()
        self._app_snapshot: Optional[ExpressionSnapshot] = None

    def _application_scope_id(self) -> int:
        return int(
            getattr(self.bot, "application_id", None)
            or getattr(getattr(self.bot, "application", None), "id", None)
            or 0
        )

    def mark_guild_suspect(self, guild_id: int) -> None:
        normalized = int(guild_id)
        self._guild_suspect.add(normalized)
        snapshot = self._guild_snapshots.get(normalized)
        if snapshot:
            self._guild_snapshots[normalized] = replace(snapshot, stale=True)

    def mark_all_guilds_suspect(self) -> None:
        for guild_id in list(self._guild_snapshots):
            self.mark_guild_suspect(guild_id)

    def mark_application_stale(self) -> None:
        if self._app_snapshot:
            self._app_snapshot = replace(self._app_snapshot, stale=True)

    def _snapshot_expired(self, snapshot: ExpressionSnapshot, ttl_seconds: int) -> bool:
        if snapshot.stale:
            return True
        age = (datetime.now(timezone.utc) - snapshot.refreshed_at).total_seconds()
        return age > ttl_seconds

    async def _load_snapshot_from_db(self, scope_type: str, scope_id: int) -> ExpressionSnapshot:
        rows = await list_expressions(scope_type, scope_id, include_unavailable=False)
        sync_state = await get_expression_sync_state(scope_type, scope_id)
        records = [ExpressionRecord.from_row(row) for row in rows]
        by_catalog = {record.catalog_id: record for record in records}
        by_discord = {record.discord_expression_id: record for record in records}
        by_name: Dict[str, list[ExpressionRecord]] = {}
        counts_by_kind: Dict[str, int] = {}
        counts_by_source: Dict[str, int] = {}
        for record in records:
            by_name.setdefault(record.normalized_name, []).append(record)
            counts_by_kind[record.kind] = counts_by_kind.get(record.kind, 0) + 1
            counts_by_source[record.source] = counts_by_source.get(record.source, 0) + 1
        refreshed_at = _parse_timestamp(sync_state.get("last_sync_at")) or datetime.now(timezone.utc)
        return ExpressionSnapshot(
            scope_type=scope_type,
            scope_id=int(scope_id),
            snapshot_version=int(sync_state.get("snapshot_version") or 0),
            refreshed_at=refreshed_at,
            stale=False,
            expressions_by_catalog_id=by_catalog,
            expressions_by_discord_id=by_discord,
            expressions_by_normalized_name={key: tuple(value) for key, value in by_name.items()},
            prompt_material=tuple(records),
            counts_by_kind=counts_by_kind,
            counts_by_source=counts_by_source,
        )

    async def refresh_application_emojis(self, *, background_refresh: bool = False) -> ExpressionSnapshot:
        scope_id = self._application_scope_id()
        emojis = await fetch_application_emojis_live(self.bot, raise_on_failure=True)
        rows = build_application_expression_rows(scope_id, emojis)
        await upsert_expression_catalog(
            EXPRESSION_SCOPE_APPLICATION,
            scope_id,
            rows,
            managed_kinds=(EXPRESSION_KIND_EMOJI,),
            background_refresh=background_refresh,
        )
        await prune_deleted_expressions(EXPRESSION_SCOPE_APPLICATION, scope_id)
        snapshot = await self._load_snapshot_from_db(EXPRESSION_SCOPE_APPLICATION, scope_id)
        self._app_snapshot = snapshot
        return snapshot

    async def refresh_guild_snapshot(
        self,
        guild: discord.Guild,
        *,
        force_fetch: bool = False,
    ) -> ExpressionSnapshot:
        expect_emojis = await has_persisted_expressions(EXPRESSION_SCOPE_GUILD, guild.id, kind=EXPRESSION_KIND_EMOJI)
        expect_stickers = await has_persisted_expressions(EXPRESSION_SCOPE_GUILD, guild.id, kind=EXPRESSION_KIND_STICKER)
        emojis, stickers = await fetch_guild_assets_live(
            guild,
            force_fetch=force_fetch,
            expect_emojis=expect_emojis,
            expect_stickers=expect_stickers,
        )
        rows = build_guild_expression_rows(guild.id, emojis, stickers)
        await upsert_expression_catalog(
            EXPRESSION_SCOPE_GUILD,
            guild.id,
            rows,
            managed_kinds=(EXPRESSION_KIND_EMOJI, EXPRESSION_KIND_STICKER),
        )
        await prune_deleted_expressions(EXPRESSION_SCOPE_GUILD, guild.id)
        snapshot = await self._load_snapshot_from_db(EXPRESSION_SCOPE_GUILD, guild.id)
        self._guild_snapshots[guild.id] = snapshot
        self._guild_suspect.discard(guild.id)
        return snapshot

    async def get_application_snapshot(self, *, force_refresh: bool = False) -> ExpressionSnapshot:
        scope_id = self._application_scope_id()
        snapshot = self._app_snapshot
        if snapshot is None:
            snapshot = await self._load_snapshot_from_db(EXPRESSION_SCOPE_APPLICATION, scope_id)
            if snapshot.snapshot_version or snapshot.prompt_material:
                self._app_snapshot = snapshot

        needs_refresh = force_refresh or snapshot is None
        if snapshot is not None and self._snapshot_expired(snapshot, self.app_ttl_seconds):
            needs_refresh = True
        if snapshot is not None and snapshot.snapshot_version == 0 and not snapshot.prompt_material:
            needs_refresh = True

        if needs_refresh:
            try:
                return await self.refresh_application_emojis(background_refresh=False)
            except Exception as exc:
                logger.warning("Application emoji refresh failed: %s", exc)
                if snapshot is not None:
                    stale_snapshot = replace(snapshot, stale=True)
                    self._app_snapshot = stale_snapshot
                    return stale_snapshot
        return snapshot or ExpressionSnapshot.empty(EXPRESSION_SCOPE_APPLICATION, scope_id, stale=True)

    async def get_guild_snapshot(
        self,
        guild: Optional[discord.Guild],
        *,
        force_refresh: bool = False,
    ) -> ExpressionSnapshot:
        if guild is None:
            return ExpressionSnapshot.empty(EXPRESSION_SCOPE_GUILD, 0, stale=True)

        snapshot = self._guild_snapshots.get(guild.id)
        if snapshot is None:
            snapshot = await self._load_snapshot_from_db(EXPRESSION_SCOPE_GUILD, guild.id)
            if snapshot.snapshot_version or snapshot.prompt_material:
                self._guild_snapshots[guild.id] = snapshot

        needs_refresh = force_refresh or guild.id in self._guild_suspect or snapshot is None
        if snapshot is not None and self._snapshot_expired(snapshot, self.guild_ttl_seconds):
            needs_refresh = True
        if snapshot is not None and snapshot.snapshot_version == 0 and not snapshot.prompt_material:
            needs_refresh = True

        if needs_refresh:
            try:
                return await self.refresh_guild_snapshot(guild, force_fetch=force_refresh or guild.id in self._guild_suspect)
            except Exception as exc:
                logger.warning("Guild expression refresh failed for %s: %s", getattr(guild, "id", "?"), exc)
                if snapshot is not None:
                    stale_snapshot = replace(snapshot, stale=True)
                    self._guild_snapshots[guild.id] = stale_snapshot
                    return stale_snapshot
        return snapshot or ExpressionSnapshot.empty(EXPRESSION_SCOPE_GUILD, guild.id, stale=True)

    async def get_guild_emojis(self, guild: Optional[discord.Guild]) -> List[ExpressionRecord]:
        snapshot = await self.get_guild_snapshot(guild)
        return snapshot.of_kind(EXPRESSION_KIND_EMOJI)

    async def get_guild_stickers(self, guild: Optional[discord.Guild]) -> List[ExpressionRecord]:
        snapshot = await self.get_guild_snapshot(guild)
        return snapshot.of_kind(EXPRESSION_KIND_STICKER)

    async def get_application_emojis(self) -> List[ExpressionRecord]:
        snapshot = await self.get_application_snapshot()
        return snapshot.of_kind(EXPRESSION_KIND_EMOJI)

    async def get_combined_emoji_expressions(self, guild: Optional[discord.Guild], *, force_refresh: bool = False) -> List[ExpressionRecord]:
        guild_snapshot = await self.get_guild_snapshot(guild, force_refresh=force_refresh)
        app_snapshot = await self.get_application_snapshot(force_refresh=force_refresh)
        combined: Dict[str, ExpressionRecord] = {}
        for record in guild_snapshot.of_kind(EXPRESSION_KIND_EMOJI):
            combined[record.discord_expression_id] = record
        for record in app_snapshot.of_kind(EXPRESSION_KIND_EMOJI):
            combined.setdefault(record.discord_expression_id, record)
        return list(combined.values())

    async def select_guild_emoji(self, guild: Optional[discord.Guild], query: Optional[str] = None) -> Optional[ExpressionRecord]:
        if guild is None:
            return None
        emojis = await self.get_guild_emojis(guild)
        matches = [emoji for emoji in emojis if emoji.matches_query(query)]
        pool = matches or emojis
        return random.choice(pool) if pool else None

    async def select_guild_sticker(self, guild: Optional[discord.Guild], query: Optional[str] = None) -> Optional[ExpressionRecord]:
        if guild is None:
            return None
        stickers = await self.get_guild_stickers(guild)
        matches = [sticker for sticker in stickers if sticker.matches_query(query)]
        pool = matches or stickers
        return random.choice(pool) if pool else None

    async def resolve_sticker_for_send(self, guild: Optional[discord.Guild], sticker_id: int) -> Optional[discord.StickerItem]:
        if guild is None:
            return None
        sticker = discord.utils.get(getattr(guild, "stickers", []) or [], id=int(sticker_id))
        if sticker:
            return sticker

        try:
            await self.refresh_guild_snapshot(guild, force_fetch=True)
        except Exception as exc:
            logger.warning("Failed to refresh guild stickers for send recovery: %s", exc)

        sticker = discord.utils.get(getattr(guild, "stickers", []) or [], id=int(sticker_id))
        if sticker:
            return sticker

        try:
            _emojis, stickers = await fetch_guild_assets_live(guild, force_fetch=True, expect_stickers=True)
        except Exception:
            stickers = []
        return discord.utils.get(stickers, id=int(sticker_id))

    async def build_prompt_context(
        self,
        guild: Optional[discord.Guild],
        *,
        message_text: str,
        mode: str,
        affection_points: int,
        recent_context_text: str = "",
        emoji_limit: int = DEFAULT_EMOJI_SHORTLIST_LIMIT,
        sticker_limit: int = DEFAULT_STICKER_SHORTLIST_LIMIT,
    ) -> ExpressionPromptContext:
        guild_snapshot = await self.get_guild_snapshot(guild)
        app_snapshot = await self.get_application_snapshot()
        combined_version = max(guild_snapshot.snapshot_version, app_snapshot.snapshot_version)
        combined_emojis = await self.get_combined_emoji_expressions(guild)
        ranked_emojis = rank_expressions(
            combined_emojis,
            query=message_text,
            mode=mode,
            affection_points=affection_points,
            recent_context_text=recent_context_text,
            limit=emoji_limit,
        )
        emoji_lines = [
            f":{record.name}: -> {record.effective_description} [{record.source.replace('_', ' ')}]"
            for record in ranked_emojis
        ]

        sticker_lines: List[str] = []
        if expression_requests_tool_prompt(message_text):
            ranked_stickers = rank_expressions(
                guild_snapshot.of_kind(EXPRESSION_KIND_STICKER),
                query=message_text,
                mode=mode,
                affection_points=affection_points,
                recent_context_text=recent_context_text,
                limit=sticker_limit,
            )
            sticker_lines = [
                f"{record.name} -> {record.effective_description}"
                for record in ranked_stickers
            ]

        summary_lines = [
            (
                "Expression snapshot "
                f"v{combined_version}: {guild_snapshot.counts_by_source.get('guild_emoji', 0)} guild emojis, "
                f"{guild_snapshot.counts_by_source.get('guild_sticker', 0)} stickers, "
                f"{app_snapshot.counts_by_source.get('app_emoji', 0)} application emojis."
            ),
            "Use `select_sticker_for_response` for stickers and `react_with_emoji` for reactions when expression tools are available.",
        ]
        if not sticker_lines:
            summary_lines.append("Stickers stay tool-first; only a narrow shortlist appears on explicit emote requests.")

        return ExpressionPromptContext(
            snapshot_version=combined_version,
            summary_lines=summary_lines,
            emoji_lines=emoji_lines,
            sticker_lines=sticker_lines,
        )


def get_expression_service(bot) -> Optional[ExpressionService]:
    return getattr(bot, "expression_service", None)
