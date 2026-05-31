from __future__ import annotations

import json
import re
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any


DEFAULT_TECHNOLOGY_KEYWORDS_PATH = (
    Path(__file__).resolve().parent.parent.parent
    / "data"
    / "samples"
    / "experience_bank_technology_keywords.json"
)

ACTION_PATTERN = (
    r"\b(built|created|developed|implemented|designed|improved|optimized|deployed|"
    r"tested|collaborated|automated|analyzed)\b"
)
IMPACT_PATTERN = r"\b(improved|reduced|increased|saved|enabled|supported|impact|result|outcome)\b"
METRIC_PATTERN = (
    r"(?:\b\d+(?:\.\d+)?%|\$\d+|\b\d+(?:\.\d+)?\s*"
    r"(?:users?|records?|hours?|minutes?|seconds?|requests?|items?)\b)"
)


@dataclass
class ExtractedEvidence:
    action_lines: list[str] = field(default_factory=list)
    impact_lines: list[str] = field(default_factory=list)
    metric_lines: list[str] = field(default_factory=list)
    technology_lines: list[str] = field(default_factory=list)
    technologies: list[str] = field(default_factory=list)
    evidence_lines: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


class EvidenceExtractor:
    """Extract obvious evidence for fallback structuring and AI guardrails."""

    def __init__(self, technology_keywords_path: Path = DEFAULT_TECHNOLOGY_KEYWORDS_PATH) -> None:
        self.technology_keywords = load_technology_keywords(technology_keywords_path)

    def extract(self, clean_note: str) -> ExtractedEvidence:
        lines = [line.strip() for line in clean_note.splitlines() if line.strip()]
        technologies = _extract_keywords(clean_note, self.technology_keywords)
        return ExtractedEvidence(
            action_lines=_extract_matching_lines(lines, ACTION_PATTERN),
            impact_lines=_extract_matching_lines(lines, IMPACT_PATTERN),
            metric_lines=_extract_matching_lines(lines, METRIC_PATTERN),
            technology_lines=_extract_technology_lines(lines, technologies),
            technologies=technologies,
            evidence_lines=lines,
        )


def load_technology_keywords(path: Path) -> list[str]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    technologies = payload.get("technologies")
    if not isinstance(technologies, list) or not all(
        isinstance(technology, str) and technology.strip() for technology in technologies
    ):
        raise ValueError(f"Invalid technology keyword configuration: {path}")
    return technologies


def _extract_matching_lines(lines: list[str], pattern: str) -> list[str]:
    return [line for line in lines if re.search(pattern, line, re.IGNORECASE)]


def _extract_keywords(text: str, keywords: list[str]) -> list[str]:
    return [
        keyword
        for keyword in keywords
        if re.search(rf"(?<![A-Za-z0-9+#]){re.escape(keyword)}(?![A-Za-z0-9+#])", text, re.IGNORECASE)
    ]


def _extract_technology_lines(lines: list[str], technologies: list[str]) -> list[str]:
    return [
        line
        for line in lines
        if any(
            re.search(rf"(?<![A-Za-z0-9+#]){re.escape(keyword)}(?![A-Za-z0-9+#])", line, re.IGNORECASE)
            for keyword in technologies
        )
    ]
