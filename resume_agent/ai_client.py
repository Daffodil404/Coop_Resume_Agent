from __future__ import annotations

from typing import Any, Protocol


class AIClient(Protocol):
    """Interface for JD analysis clients."""

    def analyze_jd(self, clean_jd: str) -> dict[str, Any]:
        """Return structured analysis for cleaned JD text."""
        ...
