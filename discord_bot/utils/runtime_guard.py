from __future__ import annotations

import os
from contextlib import contextmanager
from pathlib import Path
from typing import Iterator, Optional, TextIO

if os.name == "nt":
    import msvcrt
else:  # pragma: no cover
    import fcntl


class RuntimeInstanceGuard:
    def __init__(self, lock_path: Path | str) -> None:
        self.lock_path = Path(lock_path)
        self._handle: Optional[TextIO] = None

    @property
    def is_claimed(self) -> bool:
        return self._handle is not None

    @contextmanager
    def claim(self) -> Iterator["RuntimeInstanceGuard"]:
        self.acquire()
        try:
            yield self
        finally:
            self.release()

    def acquire(self) -> None:
        if self._handle is not None:
            return

        self.lock_path.parent.mkdir(parents=True, exist_ok=True)
        handle = self.lock_path.open("a+", encoding="utf-8")
        try:
            self._lock_handle(handle)
            handle.seek(0)
            handle.truncate()
            handle.write(f"{os.getpid()}\n")
            handle.flush()
        except OSError as exc:
            handle.close()
            raise RuntimeError(f"Bot runtime guard already running for {self.lock_path}") from exc

        self._handle = handle

    def release(self) -> None:
        handle = self._handle
        if handle is None:
            return

        try:
            self._unlock_handle(handle)
        finally:
            handle.close()
            self._handle = None
            try:
                self.lock_path.unlink(missing_ok=True)
            except OSError:
                pass

    def _lock_handle(self, handle: TextIO) -> None:
        handle.seek(0)
        handle.write("0")
        handle.flush()
        handle.seek(0)
        if os.name == "nt":
            msvcrt.locking(handle.fileno(), msvcrt.LK_NBLCK, 1)
            return
        fcntl.flock(handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)  # pragma: no cover

    def _unlock_handle(self, handle: TextIO) -> None:
        handle.seek(0)
        if os.name == "nt":
            msvcrt.locking(handle.fileno(), msvcrt.LK_UNLCK, 1)
            return
        fcntl.flock(handle.fileno(), fcntl.LOCK_UN)  # pragma: no cover
