from __future__ import annotations

import re
from datetime import datetime

from .schema import ExperienceDraft
from .validator import validate_raw_experience_note


TECHNOLOGY_KEYWORDS = [
    "Python",
    "Java",
    "JavaScript",
    "TypeScript",
    "React",
    "Node",
    "SQL",
    "PostgreSQL",
    "MySQL",
    "AWS",
    "Azure",
    "GCP",
    "Docker",
    "Kubernetes",
    "Git",
    "Linux",
    "C++",
    "C#",
    "HTML",
    "CSS",
    "REST",
    "GraphQL",
    "Terraform",
    "Jenkins",
]

ROLE_TYPE_RULES = {
    "ai_engineer": ("machine learning", "artificial intelligence", "llm", "nlp"),
    "data_engineer": ("data pipeline", "etl", "data engineer", "spark"),
    "data_analyst": ("analytics", "dashboard", "reporting", "data analyst"),
    "frontend": ("frontend", "front-end", "react", "css", "html"),
    "mobile": ("mobile", "android", "ios"),
    "qa_testing": ("quality assurance", "testing", "test automation", "qa"),
    "sde": ("software", "developer", "api", "backend", "full stack"),
}

SKILL_RULES = {
    "collaboration": ("collaborated", "worked with", "stakeholder", "team"),
    "problem solving": ("debugged", "resolved", "improved", "optimized"),
    "development": ("built", "developed", "implemented", "created"),
    "testing": ("tested", "testing", "unit test", "integration test"),
    "deployment": ("deployed", "deployment", "ci/cd"),
}

DOMAIN_RULES = {
    "healthcare": ("healthcare", "clinical", "patient"),
    "finance": ("bank", "banking", "finance", "financial"),
    "education": ("education", "learning platform", "course platform"),
    "research": ("research", "experiment", "scientific"),
    "e-commerce": ("e-commerce", "retail", "checkout"),
}


def structure_experience_note(raw_note: str, draft_id: str) -> dict[str, object]:
    """Build a conservative structured draft from explicit note content."""
    validate_raw_experience_note(raw_note)
    lines = [line.strip() for line in raw_note.splitlines() if line.strip()]
    searchable_text = " ".join(lines)
    title = _extract_labeled_value(lines, ("title", "project", "experience"))
    company = _extract_labeled_value(lines, ("company", "employer", "organization"))
    time_period = _extract_time_period(searchable_text)
    actions = _extract_matching_lines(
        lines,
        r"\b(built|created|developed|implemented|designed|improved|optimized|deployed|tested|collaborated|automated|analyzed)\b",
    )
    impact = _extract_matching_lines(
        lines,
        r"\b(improved|reduced|increased|saved|enabled|supported|impact|result|outcome)\b",
    )
    metrics = _extract_metrics(lines)
    technologies = _extract_keywords(searchable_text, TECHNOLOGY_KEYWORDS)
    role_types = _infer_categories(searchable_text, ROLE_TYPE_RULES)
    skills = _infer_categories(searchable_text, SKILL_RULES)
    domain_keywords = _infer_categories(searchable_text, DOMAIN_RULES)
    uncertain_points = _build_uncertain_points(title, company, time_period, actions, impact)
    confidence = _calculate_confidence(title, company, actions, technologies)

    draft = ExperienceDraft(
        id=draft_id,
        title=title,
        company=company,
        time_period=time_period,
        context=_extract_labeled_value(lines, ("context", "background")),
        problem=_extract_labeled_value(lines, ("problem", "challenge")),
        role=_extract_labeled_value(lines, ("role", "position")),
        actions=actions,
        technologies=technologies,
        impact=impact,
        metrics=metrics,
        role_types=role_types,
        skills=skills,
        domain_keywords=domain_keywords,
        possible_resume_angles=_build_resume_angles(role_types, skills),
        raw_bullets=lines,
        truth_constraints=[
            "Use only claims explicitly supported by the raw note.",
            "Do not invent metrics, technologies, responsibilities, or outcomes.",
            "Review uncertain_points before merging this draft into an experience bank.",
        ],
        uncertain_points=uncertain_points,
        confidence=confidence,
        usable_for=role_types,
    )
    return draft.to_dict()


def _extract_labeled_value(lines: list[str], labels: tuple[str, ...]) -> str | None:
    pattern = rf"^(?:{'|'.join(re.escape(label) for label in labels)})\s*:\s*(.+)$"
    for line in lines:
        match = re.match(pattern, line, re.IGNORECASE)
        if match:
            return match.group(1).strip()
    return None


def _extract_time_period(text: str) -> str | None:
    match = re.search(
        r"\b(?:Jan(?:uary)?|Feb(?:ruary)?|Mar(?:ch)?|Apr(?:il)?|May|Jun(?:e)?|"
        r"Jul(?:y)?|Aug(?:ust)?|Sep(?:tember)?|Oct(?:ober)?|Nov(?:ember)?|"
        r"Dec(?:ember)?)?\s*\d{4}\s*(?:-|to)\s*(?:present|"
        r"(?:Jan(?:uary)?|Feb(?:ruary)?|Mar(?:ch)?|Apr(?:il)?|May|Jun(?:e)?|"
        r"Jul(?:y)?|Aug(?:ust)?|Sep(?:tember)?|Oct(?:ober)?|Nov(?:ember)?|"
        r"Dec(?:ember)?)?\s*\d{4})\b",
        text,
        re.IGNORECASE,
    )
    return match.group(0) if match else None


def _extract_matching_lines(lines: list[str], pattern: str) -> list[str]:
    return [line for line in lines if re.search(pattern, line, re.IGNORECASE)]


def _extract_metrics(lines: list[str]) -> list[str]:
    metric_pattern = r"(?:\b\d+(?:\.\d+)?%|\$\d+|\b\d+(?:\.\d+)?\s*(?:users?|records?|hours?|minutes?|seconds?|requests?|items?)\b)"
    return [line for line in lines if re.search(metric_pattern, line, re.IGNORECASE)]


def _extract_keywords(text: str, keywords: list[str]) -> list[str]:
    return [
        keyword
        for keyword in keywords
        if re.search(rf"(?<![A-Za-z0-9+#]){re.escape(keyword)}(?![A-Za-z0-9+#])", text, re.IGNORECASE)
    ]


def _infer_categories(text: str, rules: dict[str, tuple[str, ...]]) -> list[str]:
    lowered_text = text.casefold()
    return [
        category
        for category, keywords in rules.items()
        if any(keyword in lowered_text for keyword in keywords)
    ]


def _build_resume_angles(role_types: list[str], skills: list[str]) -> list[str]:
    return [f"Highlight verified {value} evidence." for value in [*role_types, *skills]]


def _build_uncertain_points(
    title: str | None,
    company: str | None,
    time_period: str | None,
    actions: list[str],
    impact: list[str],
) -> list[str]:
    uncertain_points = []
    if title is None:
        uncertain_points.append("Confirm the experience or project title.")
    if company is None:
        uncertain_points.append("Confirm whether this experience is associated with a company or organization.")
    if time_period is None:
        uncertain_points.append("Confirm the time period.")
    if not actions:
        uncertain_points.append("Add explicit actions taken.")
    if not impact:
        uncertain_points.append("Confirm any supported impact or outcomes.")
    return uncertain_points


def _calculate_confidence(
    title: str | None,
    company: str | None,
    actions: list[str],
    technologies: list[str],
) -> str:
    explicit_field_count = sum([title is not None, company is not None, bool(actions), bool(technologies)])
    if explicit_field_count >= 4:
        return "high"
    if explicit_field_count >= 2:
        return "medium"
    return "low"
