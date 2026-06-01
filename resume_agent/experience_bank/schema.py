from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any


@dataclass
class DraftSource:
    type: str
    created_at: str
    structurer: str
    model: str | None = None


@dataclass
class DraftEvidence:
    action_lines: list[str] = field(default_factory=list)
    metric_lines: list[str] = field(default_factory=list)
    technology_lines: list[str] = field(default_factory=list)


@dataclass
class DraftConfidence:
    metrics: str = "low"
    tools: str = "low"
    ownership: str = "low"
    impact: str = "low"


@dataclass
class ExperienceDraft:
    id: str
    source: DraftSource
    status: str = "draft"
    title: str | None = None
    company: str | None = None
    time_period: str | None = None
    context: str | None = None
    problem: str | None = None
    role: str | None = None
    actions: list[str] = field(default_factory=list)
    technologies: list[str] = field(default_factory=list)
    impact: list[str] = field(default_factory=list)
    metrics: list[str] = field(default_factory=list)
    role_types: list[str] = field(default_factory=list)
    skills: list[str] = field(default_factory=list)
    domain_keywords: list[str] = field(default_factory=list)
    possible_resume_angles: list[str] = field(default_factory=list)
    evidence: DraftEvidence = field(default_factory=DraftEvidence)
    evidence_lines: list[str] = field(default_factory=list)
    draft_bullets: list[str] = field(default_factory=list)
    truth_constraints: list[str] = field(default_factory=list)
    uncertain_points: list[str] = field(default_factory=list)
    confidence: DraftConfidence = field(default_factory=DraftConfidence)
    usable_for: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)
