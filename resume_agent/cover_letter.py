from __future__ import annotations

from typing import Any


NARRATIVE_RESUME_BASES = {"ai_engineer", "research", "data_engineer"}
STANDARD_RESUME_BASES = {"sde", "frontend", "mobile", "qa_testing"}
SPECIALIZED_DOMAIN_KEYWORDS = (
    "healthcare",
    "robotics",
    "research",
    "education",
    "ai product",
    "scientific software",
    "public sector",
    "infrastructure",
    "government",
)


def decide_cover_letter(
    jd_analysis: dict[str, Any],
    resume_strategy: dict[str, Any],
    resume_selection: dict[str, Any],
) -> dict[str, Any]:
    """Return a deterministic recommendation without generating letter content."""
    recommended_base = resume_strategy.get("recommended_resume_base")
    domain = str(jd_analysis.get("domain") or "")
    role_title = str(jd_analysis.get("role_title") or "")
    searchable_text = f"{domain} {role_title}".casefold()

    if jd_analysis.get("cover_letter_required") is True:
        return _decision(
            recommendation="required",
            should_generate=True,
            estimated_value="high",
            reason="The job description explicitly requires a cover letter.",
            suggested_angle="Explain the most relevant experience for the stated role requirements.",
        )

    if resume_selection.get("fallback_used") is True:
        return _decision(
            recommendation="recommended",
            should_generate=True,
            estimated_value="high",
            reason="The selected resume used a fallback category, so a short cover letter may clarify the fit.",
            suggested_angle="Connect the selected resume's transferable experience to the target role.",
        )

    if recommended_base in NARRATIVE_RESUME_BASES:
        return _decision(
            recommendation="recommended",
            should_generate=True,
            estimated_value="medium",
            reason=f"The '{recommended_base}' resume base can benefit from a concise explanation of role fit.",
            suggested_angle="Highlight the specialized experience that aligns with the role's technical focus.",
        )

    if any(keyword in searchable_text for keyword in SPECIALIZED_DOMAIN_KEYWORDS):
        return _decision(
            recommendation="recommended",
            should_generate=True,
            estimated_value="medium",
            reason="The role appears specialized or mission-driven, so a concise narrative may add value.",
            suggested_angle="Explain how relevant experience connects to the role's specialized domain.",
        )

    if recommended_base in STANDARD_RESUME_BASES and _has_direct_resume_match(resume_selection):
        return _decision(
            recommendation="skip",
            should_generate=False,
            estimated_value="low",
            reason="The selected resume directly matches this standard role and the JD does not require a cover letter.",
            suggested_angle=None,
        )

    return _decision(
        recommendation="optional",
        should_generate=False,
        estimated_value="low",
        reason="The JD does not require a cover letter and there is no strong rule-based reason to generate one.",
        suggested_angle=None,
    )


def _has_direct_resume_match(resume_selection: dict[str, Any]) -> bool:
    return (
        resume_selection.get("fallback_used") is False
        and bool(resume_selection.get("matched_category"))
        and bool(resume_selection.get("selected_resume_pdf"))
    )


def _decision(
    recommendation: str,
    should_generate: bool,
    estimated_value: str,
    reason: str,
    suggested_angle: str | None,
) -> dict[str, Any]:
    return {
        "recommendation": recommendation,
        "should_generate": should_generate,
        "estimated_value": estimated_value,
        "reason": reason,
        "suggested_angle": suggested_angle,
    }
