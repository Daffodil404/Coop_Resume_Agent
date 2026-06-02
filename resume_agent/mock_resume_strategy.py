from __future__ import annotations

from typing import Any


class MockResumeStrategyClient:
    """Deterministic placeholder for future model-backed resume strategy."""

    def create_strategy(self, jd_analysis: dict[str, Any]) -> dict[str, str]:
        searchable_text = _build_searchable_text(jd_analysis)
        recommended_base, reason = _select_resume_base(searchable_text)
        return {
            "recommended_resume_base": recommended_base,
            "target_company": jd_analysis.get("company"),
            "selection_reason": reason,
            "strategy_source": "mock_rule_based",
        }


def _build_searchable_text(jd_analysis: dict[str, Any]) -> str:
    values = [
        jd_analysis.get("role_title"),
        jd_analysis.get("domain"),
        *jd_analysis.get("tools_and_technologies", []),
        *jd_analysis.get("core_responsibilities", []),
        *jd_analysis.get("core_requirements", []),
    ]
    return " ".join(str(value) for value in values if value).casefold()


def _select_resume_base(searchable_text: str) -> tuple[str, str]:
    rules = [
        ("mobile", ("android", "ios", "mobile"), "Matched mobile development keywords."),
        ("qa_testing", ("quality assurance", "qa", "testing", "test automation"), "Matched QA or testing keywords."),
        ("ai_engineer", ("machine learning", "artificial intelligence", " ai ", "llm", "nlp"), "Matched AI or machine-learning keywords."),
        ("data_engineer", ("data engineer", "etl", "data pipeline", "spark"), "Matched data-engineering keywords."),
        ("data_analyst", ("data analyst", "analytics", "dashboard", "reporting"), "Matched data-analysis keywords."),
        ("frontend", ("frontend", "front-end", "react", "javascript", "typescript"), "Matched frontend development keywords."),
    ]
    padded_text = f" {searchable_text} "
    for resume_base, keywords, reason in rules:
        if any(keyword in padded_text for keyword in keywords):
            return resume_base, reason
    return "sde", "No specialized resume category matched; using the general SDE resume."
