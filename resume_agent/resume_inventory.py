from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Any


STRATEGY_CATEGORY_CANDIDATES = {
    "ai_engineer": ["AI", "AI+SDE"],
    "data_engineer": ["Data Analyst", "DA:DE"],
    "data_analyst": ["Data Analyst", "DA:DE"],
    "sde": ["SDE"],
    "frontend": ["Frontend", "SDE"],
    "mobile": ["Mobile"],
    "qa_testing": ["QA", "SDE"],
}

FALLBACK_CATEGORY_PRIORITY = ["SDE", "AI", "AI+SDE", "Data Analyst", "DA:DE", "Mobile", "Frontend", "QA"]


def scan_resume_inventory(resume_root: Path) -> dict[str, Any]:
    """Return the latest PDF from each visible immediate category folder."""
    categories: dict[str, dict[str, Any]] = {}
    if not resume_root.is_dir():
        return {"resume_root": str(resume_root), "categories": categories}

    for category_dir in sorted(resume_root.iterdir(), key=lambda path: path.name.casefold()):
        if category_dir.name.startswith(".") or not category_dir.is_dir():
            continue
        pdf_files = [
            path
            for path in category_dir.iterdir()
            if path.is_file() and path.suffix.casefold() == ".pdf"
        ]
        if not pdf_files:
            continue
        latest_pdf = max(pdf_files, key=lambda path: (path.stat().st_mtime, path.name.casefold()))
        modified_at = datetime.fromtimestamp(latest_pdf.stat().st_mtime, tz=timezone.utc)
        categories[category_dir.name] = {
            "latest_pdf": str(latest_pdf),
            "modified_at": modified_at.isoformat().replace("+00:00", "Z"),
            "pdf_count": len(pdf_files),
        }

    return {"resume_root": str(resume_root), "categories": categories}


def select_resume_pdf(resume_strategy: dict[str, Any], inventory: dict[str, Any]) -> dict[str, Any]:
    """Select the latest local PDF for the recommended resume base."""
    recommended_base = resume_strategy.get("recommended_resume_base")
    categories = inventory.get("categories", {})
    available_categories = sorted(categories)
    matched_category = _find_preferred_category(recommended_base, available_categories)
    fallback_used = False

    if matched_category:
        selection_reason = (
            f"Matched recommended resume base '{recommended_base}' "
            f"to local category '{matched_category}'."
        )
    else:
        matched_category = _find_fallback_category(available_categories)
        fallback_used = matched_category is not None
        if matched_category:
            selection_reason = (
                f"No preferred local category was available for '{recommended_base}'. "
                f"Fell back to '{matched_category}'."
            )
        else:
            selection_reason = "No local resume PDF categories were available."

    selected_resume_pdf = (
        categories[matched_category]["latest_pdf"] if matched_category is not None else None
    )
    return {
        "resume_root": inventory.get("resume_root"),
        "recommended_resume_base": recommended_base,
        "matched_category": matched_category,
        "selected_resume_pdf": selected_resume_pdf,
        "selection_reason": selection_reason,
        "fallback_used": fallback_used,
        "available_categories": available_categories,
    }


def _find_preferred_category(
    recommended_base: str | None,
    available_categories: list[str],
) -> str | None:
    category_lookup = {category.casefold(): category for category in available_categories}
    for candidate in STRATEGY_CATEGORY_CANDIDATES.get(recommended_base or "", []):
        matched_category = category_lookup.get(candidate.casefold())
        if matched_category:
            return matched_category
    return None


def _find_fallback_category(available_categories: list[str]) -> str | None:
    category_lookup = {category.casefold(): category for category in available_categories}
    for candidate in FALLBACK_CATEGORY_PRIORITY:
        matched_category = category_lookup.get(candidate.casefold())
        if matched_category:
            return matched_category
    return available_categories[0] if available_categories else None
