from __future__ import annotations

import sys
from pathlib import Path

from .ingestion import structure_experience_note
from .storage import create_draft_id, save_experience_draft
from .validator import validate_raw_experience_note


def run_experience_ingest(data_root: Path = Path(".")) -> int:
    print("Describe one project or experience at a time.")
    print("Paste a raw note or Typeless transcript. Include, when known:")
    print("- title or project name; company or organization; time period")
    print("- context; problem; your role; actions personally taken")
    print("- technologies or tools; impact or outcome; safe metrics")
    print("- truth constraints / what not to exaggerate")
    print("- target roles this experience may support")
    print("When you are done, press Ctrl-D on a new line to create a YAML draft.")
    print()
    raw_note = sys.stdin.read()
    try:
        validate_raw_experience_note(raw_note)
    except ValueError as error:
        print(str(error), file=sys.stderr)
        return 1

    draft_id = create_draft_id()
    structured_draft = structure_experience_note(raw_note, draft_id=draft_id)
    saved_paths = save_experience_draft(
        raw_note=raw_note,
        structured_draft=structured_draft,
        data_root=data_root,
    )
    print(f"Saved raw experience note: {saved_paths['raw_note_path']}")
    print(f"Saved structured YAML draft: {saved_paths['draft_path']}")
    print("Draft was not merged into an experience bank.")
    return 0
