from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any


@dataclass
class ExperienceDraft:
    id: str
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
    raw_bullets: list[str] = field(default_factory=list)
    truth_constraints: list[str] = field(default_factory=list)
    uncertain_points: list[str] = field(default_factory=list)
    confidence: str = "low"
    usable_for: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)
