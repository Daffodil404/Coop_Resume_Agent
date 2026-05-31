from __future__ import annotations

from .evidence import ExtractedEvidence

MINIMUM_NOTE_LENGTH = 40
ALLOWED_STATUSES = {"draft", "reviewed", "approved", "archived"}
ALLOWED_CONFIDENCE_LEVELS = {"low", "medium", "high"}
REQUIRED_FIELDS = {
    "id",
    "status",
    "source",
    "evidence",
    "confidence",
    "draft_bullets",
    "evidence_lines",
}
LIST_FIELDS = {
    "actions",
    "technologies",
    "impact",
    "metrics",
    "role_types",
    "skills",
    "domain_keywords",
    "possible_resume_angles",
    "draft_bullets",
    "evidence_lines",
    "truth_constraints",
    "uncertain_points",
    "usable_for",
}
EVIDENCE_LIST_FIELDS = {"action_lines", "metric_lines", "technology_lines"}


def validate_raw_experience_note(raw_note: str) -> None:
    """Reject notes that do not contain enough text for a conservative draft."""
    normalized = raw_note.strip()
    if not normalized:
        raise ValueError("Experience note cannot be empty.")
    if len(normalized) < MINIMUM_NOTE_LENGTH:
        raise ValueError(
            f"Experience note is too short. Please provide at least {MINIMUM_NOTE_LENGTH} characters."
        )


def validate_experience_draft(draft: dict[str, object]) -> None:
    """Validate an unmerged experience draft before saving it."""
    missing_fields = sorted(REQUIRED_FIELDS - draft.keys())
    if missing_fields:
        raise ValueError(f"Experience draft is missing required fields: {', '.join(missing_fields)}")

    status = draft["status"]
    if status not in ALLOWED_STATUSES:
        raise ValueError(f"Invalid experience draft status: {status}")

    source = draft["source"]
    if not isinstance(source, dict):
        raise ValueError("Experience draft source must be a mapping.")
    for field_name in ("type", "created_at", "structurer", "model"):
        if field_name not in source:
            raise ValueError(f"Experience draft source is missing required field: {field_name}")

    confidence = draft["confidence"]
    if not isinstance(confidence, dict):
        raise ValueError("Experience draft confidence must be a mapping.")
    for field_name in ("metrics", "tools", "ownership", "impact"):
        level = confidence.get(field_name)
        if level not in ALLOWED_CONFIDENCE_LEVELS:
            raise ValueError(f"Invalid confidence value for {field_name}: {level}")

    evidence = draft["evidence"]
    if not isinstance(evidence, dict):
        raise ValueError("Experience draft evidence must be a mapping.")
    for field_name in EVIDENCE_LIST_FIELDS:
        if not isinstance(evidence.get(field_name), list):
            raise ValueError(f"Experience draft evidence field '{field_name}' must be a list.")

    for field_name in LIST_FIELDS:
        if not isinstance(draft.get(field_name), list):
            raise ValueError(f"Experience draft field '{field_name}' must be a list.")

    if status == "approved":
        raise ValueError("Approved drafts cannot be saved through ingestion; manual review is required.")


def validate_experience_draft_against_evidence(
    draft: dict[str, object],
    evidence: ExtractedEvidence,
) -> None:
    """Reject obvious unsupported AI or fallback claims before persistence."""
    unsupported_technologies = sorted(set(draft["technologies"]) - set(evidence.technologies))
    if unsupported_technologies:
        raise ValueError(
            f"Experience draft contains unsupported technologies: {', '.join(unsupported_technologies)}"
        )

    unsupported_metrics = sorted(set(draft["metrics"]) - set(evidence.metric_lines))
    if unsupported_metrics:
        raise ValueError(
            f"Experience draft contains unsupported metrics: {', '.join(unsupported_metrics)}"
        )
