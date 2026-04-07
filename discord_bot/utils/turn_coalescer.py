from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Optional, Sequence


@dataclass(slots=True, frozen=True)
class TurnKey:
    channel_id: int
    user_id: int


@dataclass(slots=True)
class PendingTurn:
    key: TurnKey
    version: int
    fragments: list[str] = field(default_factory=list)
    attachments: list[Any] = field(default_factory=list)
    source_message: Any = None
    created_at: float = 0.0
    deadline: float = 0.0

    @property
    def merged_text(self) -> str:
        return "\n".join(fragment for fragment in self.fragments if fragment)


@dataclass(slots=True)
class ActiveTurn:
    key: TurnKey
    version: int
    fragments: list[str] = field(default_factory=list)
    attachments: list[Any] = field(default_factory=list)
    source_message: Any = None
    created_at: float = 0.0
    last_updated_at: float = 0.0
    visible_output: bool = False
    restarted_from_version: Optional[int] = None

    @property
    def merged_text(self) -> str:
        return "\n".join(fragment for fragment in self.fragments if fragment)


@dataclass(slots=True)
class BufferedFollowUp:
    key: TurnKey
    version: int
    fragments: list[str] = field(default_factory=list)
    attachments: list[Any] = field(default_factory=list)
    source_message: Any = None
    created_at: float = 0.0
    deadline: float = 0.0

    @property
    def merged_text(self) -> str:
        return "\n".join(fragment for fragment in self.fragments if fragment)


class TurnCoordinator:
    def __init__(self, debounce_window: float = 2.0, merge_delimiter: str = "\n") -> None:
        self.debounce_window = float(debounce_window)
        self.merge_delimiter = merge_delimiter
        self._pending: dict[TurnKey, PendingTurn] = {}
        self._active: dict[TurnKey, ActiveTurn] = {}
        self._buffered_follow_ups: dict[TurnKey, BufferedFollowUp] = {}

    def get_pending(self, key: TurnKey) -> Optional[PendingTurn]:
        return self._pending.get(key)

    def get_active(self, key: TurnKey) -> Optional[ActiveTurn]:
        return self._active.get(key)

    def get_buffered_follow_up(self, key: TurnKey) -> Optional[BufferedFollowUp]:
        return self._buffered_follow_ups.get(key)

    def upsert_pending(
        self,
        key: TurnKey,
        *,
        fragment_text: str,
        source_message: Any,
        attachments: Optional[Sequence[Any]] = None,
        now: float,
    ) -> PendingTurn:
        current = self._pending.get(key)
        fragments = list(current.fragments) if current else []
        if fragment_text:
            fragments.append(fragment_text)
        merged_attachments = list(current.attachments) if current else []
        if attachments:
            merged_attachments.extend(attachments)
        pending = PendingTurn(
            key=key,
            version=(current.version + 1) if current else 1,
            fragments=fragments,
            attachments=merged_attachments,
            source_message=source_message,
            created_at=now if current is None else current.created_at,
            deadline=now + self.debounce_window,
        )
        self._pending[key] = pending
        return pending

    def take_pending(self, key: TurnKey, *, version: int, now: float) -> Optional[PendingTurn]:
        pending = self._pending.get(key)
        if pending is None or pending.version != version or pending.deadline > now:
            return None
        return self._pending.pop(key)

    def pop_ready_pending(self, *, now: float) -> list[PendingTurn]:
        ready_keys = [key for key, pending in self._pending.items() if pending.deadline <= now]
        ready: list[PendingTurn] = []
        for key in ready_keys:
            ready.append(self._pending.pop(key))
        return ready

    def mark_active(self, pending: PendingTurn, *, now: float) -> ActiveTurn:
        active = ActiveTurn(
            key=pending.key,
            version=pending.version,
            fragments=list(pending.fragments),
            attachments=list(pending.attachments),
            source_message=pending.source_message,
            created_at=now,
            last_updated_at=now,
            visible_output=False,
            restarted_from_version=None,
        )
        self._active[pending.key] = active
        return active

    def has_visible_output(self, key: TurnKey) -> bool:
        active = self._active.get(key)
        return bool(active and active.visible_output)

    def mark_visible(self, key: TurnKey, *, version: int) -> bool:
        active = self._active.get(key)
        if active is None or active.version != version:
            return False
        active.visible_output = True
        return True

    def is_current_active_version(self, key: TurnKey, *, version: int) -> bool:
        active = self._active.get(key)
        return active is not None and active.version == version

    def request_restart_before_visible(
        self,
        key: TurnKey,
        *,
        fragment_text: str,
        source_message: Any,
        attachments: Optional[Sequence[Any]] = None,
        now: float,
    ) -> Optional[ActiveTurn]:
        active = self._active.get(key)
        if active is None or active.visible_output:
            return None

        new_fragments = list(active.fragments)
        if fragment_text:
            new_fragments.append(fragment_text)
        new_attachments = list(active.attachments)
        if attachments:
            new_attachments.extend(attachments)

        restarted = ActiveTurn(
            key=key,
            version=active.version + 1,
            fragments=new_fragments,
            attachments=new_attachments,
            source_message=source_message,
            created_at=active.created_at,
            last_updated_at=now,
            visible_output=False,
            restarted_from_version=active.version,
        )
        self._active[key] = restarted
        return restarted

    def buffer_follow_up(
        self,
        key: TurnKey,
        *,
        fragment_text: str,
        source_message: Any,
        attachments: Optional[Sequence[Any]] = None,
        now: float,
    ) -> Optional[BufferedFollowUp]:
        active = self._active.get(key)
        if active is None or not active.visible_output:
            return None

        current = self._buffered_follow_ups.get(key)
        fragments = list(current.fragments) if current else []
        if fragment_text:
            fragments.append(fragment_text)
        merged_attachments = list(current.attachments) if current else []
        if attachments:
            merged_attachments.extend(attachments)
        follow_up = BufferedFollowUp(
            key=key,
            version=(current.version + 1) if current else 1,
            fragments=fragments,
            attachments=merged_attachments,
            source_message=source_message,
            created_at=now if current is None else current.created_at,
            deadline=now + self.debounce_window,
        )
        self._buffered_follow_ups[key] = follow_up
        return follow_up

    def take_buffered_follow_up(
        self,
        key: TurnKey,
        *,
        version: int,
        now: float,
    ) -> Optional[BufferedFollowUp]:
        follow_up = self._buffered_follow_ups.get(key)
        if follow_up is None or follow_up.version != version or follow_up.deadline > now:
            return None
        return self._buffered_follow_ups.pop(key)

    def pop_buffered_follow_up(self, *, now: float) -> list[BufferedFollowUp]:
        ready_keys = [
            key for key, follow_up in self._buffered_follow_ups.items() if follow_up.deadline <= now
        ]
        ready: list[BufferedFollowUp] = []
        for key in ready_keys:
            ready.append(self._buffered_follow_ups.pop(key))
        return ready

    def clear_finished(self, key: TurnKey) -> None:
        self._pending.pop(key, None)
        self._active.pop(key, None)
        self._buffered_follow_ups.pop(key, None)

    def clear_active(self, key: TurnKey) -> None:
        self._active.pop(key, None)

    def clear_buffered_follow_up(self, key: TurnKey) -> None:
        self._buffered_follow_ups.pop(key, None)
