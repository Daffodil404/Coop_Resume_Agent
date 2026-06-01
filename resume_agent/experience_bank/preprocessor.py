from __future__ import annotations

import re


class RawNotePreprocessor:
    """Normalize pasted transcripts before any structuring engine sees them."""

    def preprocess(self, raw_note: str) -> str:
        normalized = raw_note.replace("\r\n", "\n").replace("\r", "\n")
        normalized = re.sub(r"[ \t]+", " ", normalized)
        normalized = re.sub(r"\n{3,}", "\n\n", normalized)
        return "\n".join(line.strip() for line in normalized.splitlines()).strip()
