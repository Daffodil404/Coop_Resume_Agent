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
    """Return recursive category inventory and company-specific resume overrides."""
    categories: dict[str, dict[str, Any]] = {}
    company_overrides: dict[str, dict[str, Any]] = {}
    if not resume_root.is_dir():
        return {
            "resume_root": str(resume_root),
            "categories": categories,
            "company_overrides": company_overrides,
        }

    for category_dir in sorted(resume_root.iterdir(), key=lambda path: path.name.casefold()):
        if category_dir.name.startswith(".") or not category_dir.is_dir():
            continue
        if category_dir.name.casefold() == "company":
            company_overrides = _scan_company_overrides(category_dir)
            continue
        category_entry = _scan_category_tree(category_dir)
        if category_entry is None:
            continue
        categories[category_dir.name] = category_entry

    return {
        "resume_root": str(resume_root),
        "categories": categories,
        "company_overrides": company_overrides,
    }


def select_resume_pdf(resume_strategy: dict[str, Any], inventory: dict[str, Any]) -> dict[str, Any]:
    """Select the latest local PDF for the recommended resume base."""
    recommended_base = resume_strategy.get("recommended_resume_base")
    categories = inventory.get("categories", {})
    company_overrides = inventory.get("company_overrides", {})
    target_company = str(resume_strategy.get("target_company") or "").strip()
    available_categories = sorted(categories)
    matched_category = _find_preferred_category(recommended_base, available_categories)
    fallback_used = False
    selected_resume_pdf = None
    company_override_used = False

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

    if matched_category is not None:
        selected_resume_pdf = categories[matched_category]["latest_pdf"]
        company_override = _find_company_override(
            company_overrides=company_overrides,
            company_name=target_company,
            matched_category=matched_category,
        )
        if company_override is not None:
            selected_resume_pdf = company_override["latest_pdf"]
            company_override_used = True
            selection_reason = (
                f"Matched recommended resume base '{recommended_base}' to local category "
                f"'{matched_category}' and used a company-specific resume for '{target_company}'."
            )

    return {
        "resume_root": inventory.get("resume_root"),
        "recommended_resume_base": recommended_base,
        "target_company": target_company or None,
        "matched_category": matched_category,
        "selected_resume_pdf": selected_resume_pdf,
        "selection_reason": selection_reason,
        "fallback_used": fallback_used,
        "company_override_used": company_override_used,
        "available_categories": available_categories,
    }


def _scan_category_tree(category_dir: Path) -> dict[str, Any] | None:
    pdf_files = _collect_pdf_files(category_dir)
    if not pdf_files:
        return None
    latest_pdf = max(pdf_files, key=lambda path: (path.stat().st_mtime, path.name.casefold()))
    modified_at = datetime.fromtimestamp(latest_pdf.stat().st_mtime, tz=timezone.utc)
    return {
        "latest_pdf": str(latest_pdf),
        "modified_at": modified_at.isoformat().replace("+00:00", "Z"),
        "pdf_count": len(pdf_files),
    }


def _scan_company_overrides(company_root: Path) -> dict[str, dict[str, Any]]:
    overrides: dict[str, dict[str, Any]] = {}
    for company_dir in sorted(company_root.iterdir(), key=lambda path: path.name.casefold()):
        if company_dir.name.startswith(".") or not company_dir.is_dir():
            continue
        company_pdf_files = _collect_pdf_files(company_dir, recursive=False)
        category_overrides: dict[str, dict[str, Any]] = {}
        for category_dir in sorted(company_dir.iterdir(), key=lambda path: path.name.casefold()):
            if category_dir.name.startswith(".") or not category_dir.is_dir():
                continue
            category_entry = _scan_category_tree(category_dir)
            if category_entry is not None:
                category_overrides[category_dir.name] = category_entry
        if not category_overrides and not company_pdf_files:
            continue
        overrides[company_dir.name] = {
            "categories": category_overrides,
            "latest_pdf": str(max(company_pdf_files, key=lambda path: (path.stat().st_mtime, path.name.casefold())))
            if company_pdf_files
            else None,
        }
    return overrides


def _collect_pdf_files(root: Path, recursive: bool = True) -> list[Path]:
    if recursive:
        files = [path for path in root.rglob("*") if path.is_file() and path.suffix.casefold() == ".pdf"]
    else:
        files = [path for path in root.iterdir() if path.is_file() and path.suffix.casefold() == ".pdf"]
    return [path for path in files if all(not part.startswith(".") for part in path.relative_to(root).parts)]


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


def _find_company_override(
    company_overrides: dict[str, Any],
    company_name: str,
    matched_category: str,
) -> dict[str, Any] | None:
    if not company_name:
        return None
    company_entry = next(
        (
            value
            for key, value in company_overrides.items()
            if key.casefold() == company_name.casefold()
        ),
        None,
    )
    if not company_entry:
        return None
    categories = company_entry.get("categories", {})
    category_override = next(
        (
            value
            for key, value in categories.items()
            if key.casefold() == matched_category.casefold()
        ),
        None,
    )
    if category_override is not None:
        return category_override
    if company_entry.get("latest_pdf"):
        return {"latest_pdf": company_entry["latest_pdf"]}
    return None
