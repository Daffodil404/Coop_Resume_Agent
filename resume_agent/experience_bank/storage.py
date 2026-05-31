from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import yaml


RAW_NOTES_DIR = Path("data/private/raw_experience_notes")
EXPERIENCE_DRAFTS_DIR = Path("data/private/experience_drafts")


def create_draft_id(created_at: datetime | None = None) -> str:
    timestamp = created_at or datetime.now(timezone.utc)
    return timestamp.astimezone(timezone.utc).strftime("experience_%Y%m%dT%H%M%SZ")


def save_experience_draft(
    raw_note: str,
    structured_draft: dict[str, Any],
    data_root: Path = Path("."),
) -> dict[str, str]:
    """Save raw and YAML draft files without merging into a final bank."""
    raw_notes_dir = data_root / RAW_NOTES_DIR
    drafts_dir = data_root / EXPERIENCE_DRAFTS_DIR
    raw_notes_dir.mkdir(parents=True, exist_ok=True)
    drafts_dir.mkdir(parents=True, exist_ok=True)
    draft_id = str(structured_draft["id"])
    raw_path = _available_path(raw_notes_dir / f"{draft_id}.txt")
    draft_path = _available_path(drafts_dir / f"{draft_id}.yaml")
    raw_path.write_text(raw_note, encoding="utf-8")
    draft_path.write_text(
        yaml.safe_dump(structured_draft, sort_keys=False, allow_unicode=True),
        encoding="utf-8",
    )
    return {
        "raw_note_path": str(raw_path),
        "draft_path": str(draft_path),
    }


def _available_path(path: Path) -> Path:
    candidate = path
    index = 2
    while candidate.exists():
        candidate = path.with_name(f"{path.stem}_{index}{path.suffix}")
        index += 1
    return candidate
