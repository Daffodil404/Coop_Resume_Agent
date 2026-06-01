from __future__ import annotations

import re
from datetime import datetime, timezone

from .evidence import EvidenceExtractor, ExtractedEvidence
from .preprocessor import RawNotePreprocessor
from .schema import DraftConfidence, DraftEvidence, DraftSource, ExperienceDraft
from .validator import validate_raw_experience_note


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


class RuleBasedExperienceStructurer:
    """Conservative local fallback for explicit raw-note extraction."""

    name = "rule_based"
    model = None

    def structure(
        self,
        raw_note: str,
        draft_id: str,
        evidence: ExtractedEvidence | None = None,
    ) -> dict[str, object]:
        validate_raw_experience_note(raw_note)
        clean_note = RawNotePreprocessor().preprocess(raw_note)
        extracted_evidence = evidence or EvidenceExtractor().extract(clean_note)
        lines = extracted_evidence.evidence_lines
        searchable_text = " ".join(lines)
        title = _english_safe_value(_extract_labeled_value(lines, ("title", "project", "experience")))
        company = _english_safe_value(_extract_labeled_value(lines, ("company", "employer", "organization")))
        time_period = _extract_time_period(searchable_text)
        actions = _english_safe_lines(extracted_evidence.action_lines)
        impact = _english_safe_lines(extracted_evidence.impact_lines)
        metrics = _english_safe_lines(extracted_evidence.metric_lines)
        technologies = extracted_evidence.technologies
        role_types = _infer_categories(searchable_text, ROLE_TYPE_RULES)
        skills = _infer_categories(searchable_text, SKILL_RULES)
        domain_keywords = _infer_categories(searchable_text, DOMAIN_RULES)
        uncertain_points = _build_uncertain_points(title, company, time_period, actions, impact)
        if any(not _is_english_safe(line) for line in extracted_evidence.evidence_lines):
            uncertain_points.append(
                "Review the original non-English evidence lines with the AI structurer or translate them manually."
            )

        draft = ExperienceDraft(
            id=draft_id,
            status="draft",
            source=DraftSource(
                type="raw_experience_note",
                created_at=_current_timestamp(),
                structurer=self.name,
                model=self.model,
            ),
            title=title,
            company=company,
            time_period=time_period,
            context=_english_safe_value(_extract_labeled_value(lines, ("context", "background"))),
            problem=_english_safe_value(_extract_labeled_value(lines, ("problem", "challenge"))),
            role=_english_safe_value(_extract_labeled_value(lines, ("role", "position"))),
            actions=actions,
            technologies=technologies,
            impact=impact,
            metrics=metrics,
            role_types=role_types,
            skills=skills,
            domain_keywords=domain_keywords,
            possible_resume_angles=_build_resume_angles(role_types, skills),
            evidence=DraftEvidence(
                action_lines=extracted_evidence.action_lines,
                metric_lines=extracted_evidence.metric_lines,
                technology_lines=extracted_evidence.technology_lines,
            ),
            evidence_lines=lines,
            draft_bullets=[],
            truth_constraints=[
                "Use only claims explicitly supported by the raw note.",
                "Do not invent metrics, technologies, ownership, responsibilities, or outcomes.",
                "Review uncertain_points before merging this draft into an experience bank.",
            ],
            uncertain_points=uncertain_points,
            confidence=DraftConfidence(
                metrics=_confidence_for_presence(metrics),
                tools=_confidence_for_presence(technologies),
                ownership=_confidence_for_presence(actions),
                impact=_confidence_for_presence(impact),
            ),
            usable_for=role_types,
        )
        return draft.to_dict()


def structure_experience_note(raw_note: str, draft_id: str) -> dict[str, object]:
    """Backwards-compatible wrapper for the default local structurer."""
    clean_note = RawNotePreprocessor().preprocess(raw_note)
    evidence = EvidenceExtractor().extract(clean_note)
    return RuleBasedExperienceStructurer().structure(clean_note, draft_id, evidence)


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


def _english_safe_value(value: str | None) -> str | None:
    return value if value is not None and _is_english_safe(value) else None


def _english_safe_lines(lines: list[str]) -> list[str]:
    return [line for line in lines if _is_english_safe(line)]


def _is_english_safe(value: str) -> bool:
    return value.isascii()


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


def _confidence_for_presence(values: list[str]) -> str:
    return "high" if values else "low"


def _current_timestamp() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
