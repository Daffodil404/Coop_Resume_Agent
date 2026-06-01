from __future__ import annotations

from copy import deepcopy
from datetime import datetime, timezone
from typing import Any


FIELD_QUESTIONS = {
    "title": "What is the clearest project or experience title for this work?",
    "company": "Which company, organization, or team was this work for?",
    "time_period": "What was the time period for this experience?",
    "context": "What product, system, or business context was this work part of?",
    "problem": "What exact requirement or problem was this work solving?",
    "role": "What was your exact responsibility or ownership?",
    "actions": "Which part did you personally implement or design?",
    "technologies": "What technologies, frameworks, tools, or platforms did you actually use?",
    "impact": "What measurable or qualitative result can be safely claimed?",
    "metrics": "Are there any explicit numbers or metrics you can safely state?",
    "role_types": "Which job categories does this experience support most clearly?",
    "skills": "What specific reusable skills does this experience demonstrate?",
    "domain_keywords": "What domain or business keywords best describe this work?",
    "possible_resume_angles": "What are the strongest conservative resume angles for this experience?",
    "evidence.action_lines": "Which raw lines best support the actions you took?",
    "evidence.technology_lines": "Which raw lines explicitly mention your tools or technologies?",
    "truth_constraints": "Is there anything this experience should NOT be exaggerated into?",
}

GENERIC_LIST_VALUES = {
    "skills": {"collaboration", "development", "testing", "problem solving"},
    "usable_for": {"resume building", "job applications"},
}


def analyze_experience_gaps(draft: dict[str, Any]) -> dict[str, Any]:
    missing_fields: list[str] = []
    weak_fields: list[str] = []
    unsupported_fields: list[str] = []

    for field_name in (
        "title",
        "company",
        "time_period",
        "context",
        "problem",
        "role",
        "actions",
        "technologies",
        "impact",
        "metrics",
        "role_types",
        "skills",
        "domain_keywords",
        "possible_resume_angles",
        "truth_constraints",
    ):
        value = draft.get(field_name)
        if _is_missing(value):
            missing_fields.append(field_name)
        elif _is_weak(field_name, value):
            weak_fields.append(field_name)

    evidence = draft.get("evidence", {})
    for field_name in ("action_lines", "technology_lines"):
        field_key = f"evidence.{field_name}"
        value = evidence.get(field_name, [])
        if _is_missing(value):
            missing_fields.append(field_key)
        elif _is_weak(field_key, value, draft=draft):
            weak_fields.append(field_key)
    if draft.get("actions") and not evidence.get("action_lines"):
        unsupported_fields.append("actions")
    if draft.get("technologies") and not evidence.get("technology_lines"):
        unsupported_fields.append("technologies")

    ordered_fields = [*missing_fields, *weak_fields, *unsupported_fields]
    field_questions = {field_name: FIELD_QUESTIONS[field_name] for field_name in ordered_fields}
    priority_questions = [field_questions[field_name] for field_name in ordered_fields[:5]]

    overall_status = "complete_enough"
    if unsupported_fields or missing_fields:
        overall_status = "not_ready" if len(missing_fields) >= 5 else "needs_more_detail"
    elif weak_fields:
        overall_status = "needs_more_detail"

    reason = _build_gap_reason(missing_fields, weak_fields, unsupported_fields)
    return {
        "overall_status": overall_status,
        "missing_fields": missing_fields,
        "weak_fields": weak_fields,
        "unsupported_fields": unsupported_fields,
        "field_questions": field_questions,
        "priority_questions": priority_questions,
        "reason": reason,
    }


def propose_supplement_merge(
    original_draft: dict[str, Any],
    structured_supplement: dict[str, Any],
) -> dict[str, Any]:
    proposed_draft = deepcopy(original_draft)
    field_changes: dict[str, Any] = {}
    warnings: list[str] = []

    for field_name in ("title", "company", "time_period", "context", "problem", "role"):
        original_value = proposed_draft.get(field_name)
        supplement_value = structured_supplement.get(field_name)
        if _is_missing(original_value) and not _is_missing(supplement_value):
            proposed_draft[field_name] = supplement_value
            field_changes[field_name] = {
                "action": "fill_missing",
                "value": supplement_value,
            }

    for field_name in (
        "actions",
        "technologies",
        "impact",
        "metrics",
        "role_types",
        "skills",
        "domain_keywords",
        "possible_resume_angles",
        "usable_for",
    ):
        additions = _list_additions(proposed_draft.get(field_name, []), structured_supplement.get(field_name, []))
        if additions:
            proposed_draft[field_name] = [*proposed_draft.get(field_name, []), *additions]
            field_changes[field_name] = {
                "action": "add_items",
                "items": additions,
            }

    evidence_changes = {}
    for field_name in ("action_lines", "metric_lines", "technology_lines"):
        additions = _list_additions(
            proposed_draft.get("evidence", {}).get(field_name, []),
            structured_supplement.get("evidence", {}).get(field_name, []),
        )
        if additions:
            proposed_draft["evidence"][field_name] = [*proposed_draft["evidence"].get(field_name, []), *additions]
            evidence_changes[field_name] = additions
    evidence_line_additions = _list_additions(
        proposed_draft.get("evidence_lines", []),
        structured_supplement.get("evidence_lines", []),
    )
    if evidence_line_additions:
        proposed_draft["evidence_lines"] = [*proposed_draft.get("evidence_lines", []), *evidence_line_additions]
        evidence_changes["evidence_lines"] = evidence_line_additions
    if evidence_changes:
        field_changes["evidence"] = {
            "action": "add_evidence",
            "items": evidence_changes,
        }

    if not field_changes:
        warnings.append("Supplement note did not produce any additive field-level changes.")

    return {
        "merge_strategy": "conservative_additive",
        "field_changes": field_changes,
        "warnings": warnings,
        "proposed_draft": proposed_draft,
    }


def create_supplement_proposal(
    original_draft: dict[str, Any],
    gap_analysis: dict[str, Any],
    raw_supplement_note: str,
    structured_supplement: dict[str, Any],
    proposed_changes: dict[str, Any],
) -> dict[str, Any]:
    return {
        "proposal_id": _current_supplement_id(original_draft["id"]),
        "supplement_for": original_draft["id"],
        "created_at": _current_timestamp(),
        "status": "supplement_proposal",
        "gap_analysis": gap_analysis,
        "raw_supplement_note": raw_supplement_note,
        "structured_supplement": structured_supplement,
        "proposed_changes": proposed_changes,
    }


def _is_missing(value: Any) -> bool:
    return value is None or value == "" or value == []


def _is_weak(field_name: str, value: Any, draft: dict[str, Any] | None = None) -> bool:
    if field_name == "title" and isinstance(value, str):
        return len(value.strip()) < 6
    if field_name in {"context", "problem", "role"} and isinstance(value, str):
        return len(value.strip()) < 20
    if field_name == "metrics" and value == []:
        return True
    if field_name == "impact" and isinstance(value, list):
        return all(len(item.strip()) < 20 for item in value)
    if field_name == "evidence.action_lines" and draft is not None:
        return bool(draft.get("actions")) and value == []
    if field_name in GENERIC_LIST_VALUES and isinstance(value, list):
        lowered = {item.strip().lower() for item in value}
        return bool(lowered) and lowered <= GENERIC_LIST_VALUES[field_name]
    return False


def _build_gap_reason(
    missing_fields: list[str],
    weak_fields: list[str],
    unsupported_fields: list[str],
) -> str:
    if unsupported_fields:
        return (
            "The draft contains claims that need better grounding before reuse: "
            f"{', '.join(unsupported_fields)}."
        )
    if missing_fields:
        return (
            "The draft is missing reusable information needed for resume and interview reuse: "
            f"{', '.join(missing_fields)}."
        )
    if weak_fields:
        return (
            "The draft has fields that are present but still too weak or generic for strong reuse: "
            f"{', '.join(weak_fields)}."
        )
    return "The draft is complete enough for manual review."


def _list_additions(existing: list[str], incoming: list[str]) -> list[str]:
    existing_set = set(existing)
    return [item for item in incoming if item not in existing_set]


def _current_timestamp() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _current_supplement_id(experience_id: str) -> str:
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    return f"{experience_id}_supplement_{timestamp}"
