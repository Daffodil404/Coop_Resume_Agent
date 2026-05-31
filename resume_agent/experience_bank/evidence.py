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
LOCAL_TECHNOLOGY_KEYWORDS_PATH = Path("data/private/experience_bank_technology_keywords.local.json")

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

    def __init__(
        self,
        technology_keywords_path: Path = DEFAULT_TECHNOLOGY_KEYWORDS_PATH,
        local_keywords_path: Path | None = None,
    ) -> None:
        self.local_keywords_path = local_keywords_path
        keywords = load_technology_keywords(technology_keywords_path)
        if local_keywords_path and local_keywords_path.is_file():
            keywords.extend(load_technology_keywords(local_keywords_path))
        self.technology_keywords = list(dict.fromkeys(keywords))

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

    def add_local_keyword(self, technology: str) -> None:
        """Persist a user-confirmed keyword outside the tracked base dictionary."""
        if not self.local_keywords_path:
            return
        keywords = []
        if self.local_keywords_path.is_file():
            keywords = load_technology_keywords(self.local_keywords_path)
        if technology not in keywords:
            keywords.append(technology)
            self.local_keywords_path.parent.mkdir(parents=True, exist_ok=True)
            self.local_keywords_path.write_text(
                json.dumps({"technologies": keywords}, indent=2, ensure_ascii=False) + "\n",
                encoding="utf-8",
            )
        if technology not in self.technology_keywords:
            self.technology_keywords.append(technology)


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
    return [keyword for keyword in keywords if technology_is_explicitly_mentioned(keyword, text)]


def _extract_technology_lines(lines: list[str], technologies: list[str]) -> list[str]:
    return [
        line
        for line in lines
        if any(technology_is_explicitly_mentioned(keyword, line) for keyword in technologies)
    ]


def include_explicit_technologies(
    evidence: ExtractedEvidence,
    clean_note: str,
    technologies: list[str],
) -> ExtractedEvidence:
    """Add raw-note-backed AI terms to evidence even when the local dictionary lacks them."""
    lines = [line.strip() for line in clean_note.splitlines() if line.strip()]
    for technology in technologies:
        if technology not in evidence.technologies:
            evidence.technologies.append(technology)
    evidence.technology_lines = _extract_technology_lines(lines, evidence.technologies)
    return evidence


def technology_is_explicitly_mentioned(technology: str, clean_note: str) -> bool:
    pattern = technology_literal_pattern(technology)
    normalized_note = normalize_technology_evidence_text(clean_note)
    normalized_technology = normalize_technology_evidence_text(technology)
    return bool(
        re.search(pattern, clean_note, re.IGNORECASE)
        or re.search(pattern, normalized_note, re.IGNORECASE)
        or re.search(technology_literal_pattern(normalized_technology), normalized_note, re.IGNORECASE)
    )


def normalize_technology_evidence_text(text: str) -> str:
    normalized = text.casefold()
    normalized = re.sub(r"[`'\"“”‘’]", " ", normalized)
    normalized = re.sub(r"[(){}\[\]<>:;,./\\|!?@%^&*=+-]+", " ", normalized)
    normalized = re.sub(r"\s+", " ", normalized)
    return normalized.strip()


def technology_literal_pattern(technology: str) -> str:
    escaped = re.escape(technology.strip())
    return rf"(?<![a-z0-9+#]){escaped}(?![a-z0-9+#])"


def split_supported_compound_technology(
    technology: str,
    supported_technologies: list[str],
) -> list[str]:
    tokens = [token for token in re.split(r"\s+", technology.strip()) if token]
    if len(tokens) < 2:
        return []
    supported_by_normalized = {
        normalize_technology_evidence_text(candidate): candidate for candidate in supported_technologies
    }
    split_candidates = []
    for token in tokens:
        candidate = supported_by_normalized.get(normalize_technology_evidence_text(token))
        if candidate is None:
            return []
        split_candidates.append(candidate)
    return list(dict.fromkeys(split_candidates))
