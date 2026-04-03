from __future__ import annotations

import re


_SENTENCE_BOUNDARY_RE = re.compile(r"(?<=[.!?])[\"'\)\]]*\s+")
_TAIL_INCOMPLETE_URL_RE = re.compile(r"(https?://[^\s]*)$")


class SemanticBuffer:
    def __init__(
        self,
        *,
        min_flush_chars: int = 80,
        target_flush_chars: int = 220,
        max_buffer_chars: int = 900,
    ) -> None:
        self.min_flush_chars = max(1, int(min_flush_chars))
        self.target_flush_chars = max(self.min_flush_chars, int(target_flush_chars))
        self.max_buffer_chars = max(self.target_flush_chars, int(max_buffer_chars))
        self.pending_text = ""

    def add_text(self, text: str) -> None:
        if text:
            self.pending_text += text

    def has_meaningful_text(self) -> bool:
        return any(char.isalnum() for char in self.pending_text)

    def pop_flushable(self, *, force: bool = False) -> str | None:
        if not self.pending_text:
            return None
        if force:
            flushed = self._close_open_structures(self.pending_text)
            self.pending_text = ""
            return flushed.rstrip()
        if len(self.pending_text) < self.min_flush_chars:
            return None
        if self._has_incomplete_structure(self.pending_text):
            return None

        boundary = self._find_soft_boundary(self.pending_text)
        if boundary is None and len(self.pending_text) >= self.max_buffer_chars:
            boundary = self._find_overflow_boundary(self.pending_text)
        if boundary is None or boundary <= 0:
            return None

        flushed = self.pending_text[:boundary].rstrip()
        self.pending_text = self.pending_text[boundary:]
        return flushed or None

    def pop_stalled(self) -> str | None:
        if not self.pending_text:
            return None
        if not self.has_meaningful_text():
            return None
        if self._has_incomplete_structure(self.pending_text):
            return None
        boundary = self._find_soft_boundary(self.pending_text)
        if boundary is None:
            boundary = len(self.pending_text)
        if boundary is None or boundary <= 0:
            boundary = len(self.pending_text)
        flushed = self.pending_text[:boundary].rstrip()
        self.pending_text = self.pending_text[boundary:]
        return flushed or None

    def _find_soft_boundary(self, text: str) -> int | None:
        paragraph_index = text.find("\n\n")
        if paragraph_index >= self.min_flush_chars:
            return paragraph_index + 2

        newline_index = text.find("\n")
        if newline_index >= self.min_flush_chars:
            return newline_index + 1

        match = None
        for candidate in _SENTENCE_BOUNDARY_RE.finditer(text):
            if candidate.start() >= self.min_flush_chars:
                match = candidate
                if candidate.start() >= self.target_flush_chars:
                    break
        if match:
            return match.start()

        if text.rstrip().endswith((".", "!", "?")) and len(text.rstrip()) >= self.min_flush_chars:
            return len(text.rstrip())
        return None

    def _find_overflow_boundary(self, text: str) -> int:
        preferred = min(len(text), self.target_flush_chars)
        search_window = text[: min(len(text), self.max_buffer_chars)]
        forward_sentence = _SENTENCE_BOUNDARY_RE.search(search_window, pos=preferred)
        if forward_sentence:
            return forward_sentence.start()

        backward_text = search_window[:preferred]
        candidates = list(_SENTENCE_BOUNDARY_RE.finditer(backward_text))
        if candidates:
            return candidates[-1].start()

        whitespace = search_window.rfind(" ", 0, preferred)
        if whitespace > 0:
            return whitespace + 1
        return preferred

    def _has_incomplete_structure(self, text: str) -> bool:
        if text.count("```") % 2 == 1:
            return True
        if self._has_unclosed_markdown_link(text):
            return True
        tail_url = _TAIL_INCOMPLETE_URL_RE.search(text)
        if tail_url and ")" not in tail_url.group(1):
            return True
        return False

    def _has_unclosed_markdown_link(self, text: str) -> bool:
        last_open = text.rfind("[")
        if last_open < 0:
            return False
        last_close_bracket = text.rfind("]")
        if last_close_bracket < last_open:
            return True
        last_open_paren = text.rfind("(", last_close_bracket)
        if last_open_paren < last_close_bracket:
            return False
        last_close_paren = text.rfind(")")
        return last_close_paren < last_open_paren

    def _close_open_structures(self, text: str) -> str:
        closed = text.rstrip()
        if closed.count("```") % 2 == 1:
            if not closed.endswith("\n"):
                closed += "\n"
            closed += "```"
        return closed
