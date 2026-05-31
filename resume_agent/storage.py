from __future__ import annotations

import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


MAX_FOLDER_NAME_LENGTH = 80


def create_application_dir(
    output_root: Path,
    company: str | None,
    role_title: str | None,
    created_at: datetime | None = None,
) -> Path:
    output_root.mkdir(parents=True, exist_ok=True)
    base_name = build_application_folder_name(
        company=company,
        role_title=role_title,
        created_at=created_at or current_utc_time(),
    )
    candidate = output_root / base_name
    index = 2
    while candidate.exists():
        candidate = output_root / f"{base_name}_{index}"
        index += 1
    candidate.mkdir()
    return candidate


def build_application_folder_name(
    company: str | None,
    role_title: str | None,
    created_at: datetime,
) -> str:
    company_part = slugify(company or "unknown company") or "unknown_company"
    role_part = slugify(role_title or "unknown role") or "unknown_role"
    folder_name = f"{created_at.date().isoformat()}_{company_part}_{role_part}"
    if len(folder_name) <= MAX_FOLDER_NAME_LENGTH:
        return folder_name
    return folder_name[:MAX_FOLDER_NAME_LENGTH].rstrip("_")


def create_application_metadata(
    application_dir: Path,
    analysis: dict[str, Any],
    created_at: datetime,
    source: str = "interactive_cli",
    status: str = "draft",
) -> dict[str, Any]:
    return {
        "application_id": application_dir.name,
        "company": analysis.get("company"),
        "role_title": analysis.get("role_title"),
        "created_at": format_timestamp(created_at),
        "source": source,
        "status": status,
    }


def save_application_artifacts(
    application_dir: Path,
    raw_jd: str,
    clean_jd: str,
    analysis: dict[str, Any],
    metadata: dict[str, Any],
) -> None:
    write_text(application_dir / "jd_raw.txt", raw_jd)
    write_text(application_dir / "jd_clean.txt", clean_jd)
    write_json(application_dir / "jd_analysis.json", analysis)
    write_json(application_dir / "metadata.json", metadata)


def save_resume_selection(application_dir: Path, selection: dict[str, Any]) -> None:
    write_json(application_dir / "resume_selection.json", selection)


def save_resume_strategy(application_dir: Path, strategy: dict[str, Any]) -> None:
    write_json(application_dir / "resume_strategy.json", strategy)


def write_text(path: Path, value: str) -> None:
    path.write_text(value, encoding="utf-8")


def write_json(path: Path, value: dict[str, Any]) -> None:
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def slugify(value: str) -> str:
    slug = value.lower()
    slug = re.sub(r"[^a-z0-9]+", "_", slug)
    slug = re.sub(r"_{2,}", "_", slug)
    slug = slug.strip("_")
    if len(slug) <= MAX_FOLDER_NAME_LENGTH:
        return slug
    return slug[:MAX_FOLDER_NAME_LENGTH].rstrip("_")


def current_utc_time() -> datetime:
    return datetime.now(timezone.utc)


def format_timestamp(value: datetime) -> str:
    return value.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")
