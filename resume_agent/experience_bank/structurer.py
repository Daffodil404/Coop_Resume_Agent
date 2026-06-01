from __future__ import annotations

from typing import Protocol

from .evidence import ExtractedEvidence


class ExperienceStructurer(Protocol):
    """Interface for pluggable raw-note structuring engines."""

    name: str
    model: str | None

    def structure(
        self,
        clean_note: str,
        draft_id: str,
        evidence: ExtractedEvidence,
    ) -> dict[str, object]:
        """Return a conservative structured experience draft."""
        ...
