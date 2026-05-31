from __future__ import annotations

from copy import deepcopy
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import yaml

from .validator import validate_experience_draft

RAW_NOTES_DIR = Path("data/private/raw_experience_notes")
EXPERIENCE_DRAFTS_DIR = Path("data/private/experience_drafts")
EXPERIENCE_BANK_PATH = Path("data/private/experience_bank.yaml")


def create_draft_id(created_at: datetime | None = None) -> str:
    timestamp = created_at or datetime.now(timezone.utc)
    return timestamp.astimezone(timezone.utc).strftime("experience_%Y%m%dT%H%M%SZ")


def create_available_draft_id(
    data_root: Path = Path("."),
    created_at: datetime | None = None,
) -> str:
    base_id = create_draft_id(created_at)
    candidate = base_id
    index = 2
    while (
        (data_root / RAW_NOTES_DIR / f"{candidate}.txt").exists()
        or (data_root / EXPERIENCE_DRAFTS_DIR / f"{candidate}.yaml").exists()
    ):
        candidate = f"{base_id}_{index}"
        index += 1
    return candidate


def save_experience_draft(
    raw_note: str,
    structured_draft: dict[str, Any],
    data_root: Path = Path("."),
) -> dict[str, str]:
    """Save raw and YAML draft files without merging into a final bank."""
    validate_experience_draft(structured_draft)
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


def load_experience_draft(draft_id: str, data_root: Path = Path(".")) -> dict[str, Any]:
    draft_path = data_root / EXPERIENCE_DRAFTS_DIR / f"{draft_id}.yaml"
    if not draft_path.is_file():
        raise ValueError(f"Experience draft not found: {draft_id}")
    draft = yaml.safe_load(draft_path.read_text(encoding="utf-8"))
    if not isinstance(draft, dict):
        raise ValueError(f"Experience draft is not a YAML mapping: {draft_id}")
    return draft


def load_raw_experience_note(draft_id: str, data_root: Path = Path(".")) -> str:
    raw_path = data_root / RAW_NOTES_DIR / f"{draft_id}.txt"
    if not raw_path.is_file():
        raise ValueError(f"Raw experience note not found: {draft_id}")
    return raw_path.read_text(encoding="utf-8")


def approve_experience_draft(
    draft_id: str,
    data_root: Path = Path("."),
    allow_uncertain: bool = False,
) -> dict[str, Any]:
    """Approve a reviewed draft and merge it into the private local bank."""
    draft = load_experience_draft(draft_id, data_root=data_root)
    validate_experience_draft(draft)
    uncertain_points = draft.get("uncertain_points", [])
    if uncertain_points and not allow_uncertain:
        raise ValueError(
            "Draft still has uncertain_points. Supplement the draft or approve with explicit override."
        )

    approved_entry = deepcopy(draft)
    approved_entry["status"] = "approved"
    bank_path = data_root / EXPERIENCE_BANK_PATH
    bank_path.parent.mkdir(parents=True, exist_ok=True)
    bank = _load_experience_bank(bank_path)
    entries = bank["entries"]
    replacement_index = next(
        (index for index, entry in enumerate(entries) if entry.get("id") == draft_id),
        None,
    )
    if replacement_index is None:
        entries.append(approved_entry)
    else:
        entries[replacement_index] = approved_entry
    bank_path.write_text(
        yaml.safe_dump(bank, sort_keys=False, allow_unicode=True),
        encoding="utf-8",
    )
    return {
        "bank_path": str(bank_path),
        "entry": approved_entry,
    }


def _load_experience_bank(bank_path: Path) -> dict[str, Any]:
    if not bank_path.is_file():
        return {"version": 1, "entries": []}
    bank = yaml.safe_load(bank_path.read_text(encoding="utf-8"))
    if not isinstance(bank, dict) or not isinstance(bank.get("entries"), list):
        raise ValueError(f"Experience bank is not a valid YAML mapping: {bank_path}")
    return bank


def _available_path(path: Path) -> Path:
    candidate = path
    index = 2
    while candidate.exists():
        candidate = path.with_name(f"{path.stem}_{index}{path.suffix}")
        index += 1
    return candidate
