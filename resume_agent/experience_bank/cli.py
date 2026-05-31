from __future__ import annotations

import sys
from pathlib import Path

import yaml

from .evidence import EvidenceExtractor, LOCAL_TECHNOLOGY_KEYWORDS_PATH
from .pipeline import ExperienceIngestionPipeline
from .storage import (
    approve_experience_draft,
    create_available_draft_id,
    load_experience_draft,
    load_raw_experience_note,
    save_experience_draft,
)
from .validator import validate_raw_experience_note


def run_experience_ingest(
    data_root: Path = Path("."),
    pipeline: ExperienceIngestionPipeline | None = None,
) -> int:
    selected_pipeline = pipeline or _build_pipeline(data_root)
    try:
        selected_pipeline.validate_configuration()
    except ValueError as error:
        print(str(error), file=sys.stderr)
        return 2

    print("Describe one project or experience at a time.")
    print("Paste a raw note or Typeless transcript. Include, when known:")
    print("- title or project name; company or organization; time period")
    print("- context; problem; your role; actions personally taken")
    print("- technologies or tools; impact or outcome; safe metrics")
    print("- truth constraints / what not to exaggerate")
    print("- target roles this experience may support")
    print("When you are done, press Ctrl-D on a new line to create a YAML draft.")
    print()
    try:
        raw_note = sys.stdin.read()
    except KeyboardInterrupt:
        print("\nExperience ingestion cancelled.", file=sys.stderr)
        return 130
    try:
        validate_raw_experience_note(raw_note)
    except ValueError as error:
        print(str(error), file=sys.stderr)
        return 1

    draft_id = create_available_draft_id(data_root=data_root)
    print("Processing experience note...", flush=True)
    try:
        structured_draft = selected_pipeline.structure(raw_note, draft_id=draft_id)
    except KeyboardInterrupt:
        print("\nExperience ingestion cancelled.", file=sys.stderr)
        return 130
    except (RuntimeError, ValueError) as error:
        print(str(error), file=sys.stderr)
        return 2
    saved_paths = save_experience_draft(
        raw_note=raw_note,
        structured_draft=structured_draft,
        data_root=data_root,
    )
    print(f"Saved raw experience note: {saved_paths['raw_note_path']}")
    print(f"Saved structured YAML draft: {saved_paths['draft_path']}")
    print(
        "Structuring complete: "
        f"{structured_draft['source']['structurer']}"
        f" ({structured_draft['source']['model'] or 'local'})"
    )
    print("Draft was not merged into an experience bank.")
    print_next_actions(draft_id)
    return offer_next_action_if_interactive(draft_id, data_root=data_root)


def run_experience_review(draft_id: str, data_root: Path = Path(".")) -> int:
    try:
        draft = load_experience_draft(draft_id, data_root=data_root)
    except ValueError as error:
        print(str(error), file=sys.stderr)
        return 1
    print(yaml.safe_dump(draft, sort_keys=False, allow_unicode=True))
    print_next_actions(draft_id)
    return offer_next_action_if_interactive(draft_id, data_root=data_root)


def run_experience_approve(draft_id: str, data_root: Path = Path(".")) -> int:
    try:
        draft = load_experience_draft(draft_id, data_root=data_root)
    except ValueError as error:
        print(str(error), file=sys.stderr)
        return 1
    print(f"Approve draft '{draft_id}' and merge it into the private local experience bank?")
    if draft.get("uncertain_points"):
        print("Warning: this draft still has uncertain_points.")
    try:
        response = input("Continue? [y/N] ").strip().lower()
    except (EOFError, KeyboardInterrupt):
        print("\nApproval cancelled.", file=sys.stderr)
        return 130
    if response not in {"y", "yes"}:
        print("Approval cancelled.")
        return 0
    allow_uncertain = False
    if draft.get("uncertain_points"):
        try:
            response = input("Approve despite uncertain_points? [y/N] ").strip().lower()
        except (EOFError, KeyboardInterrupt):
            print("\nApproval cancelled.", file=sys.stderr)
            return 130
        if response not in {"y", "yes"}:
            print("Approval cancelled. Supplement the draft before approval.")
            return 0
        allow_uncertain = True
    try:
        result = approve_experience_draft(
            draft_id,
            data_root=data_root,
            allow_uncertain=allow_uncertain,
        )
    except ValueError as error:
        print(str(error), file=sys.stderr)
        return 1
    print(f"Approved experience entry: {draft_id}")
    print(f"Updated private experience bank: {result['bank_path']}")
    print("Add another experience with: resume-agent experience ingest")
    if sys.stdin.isatty():
        try:
            response = input("Add another experience now? [y/N] ").strip().lower()
        except (EOFError, KeyboardInterrupt):
            print("\nFinished.", file=sys.stderr)
            return 0
        if response in {"y", "yes"}:
            return run_experience_ingest(data_root=data_root)
    return 0


def run_experience_supplement(
    draft_id: str,
    data_root: Path = Path("."),
    pipeline: ExperienceIngestionPipeline | None = None,
) -> int:
    try:
        original_note = load_raw_experience_note(draft_id, data_root=data_root)
    except ValueError as error:
        print(str(error), file=sys.stderr)
        return 1
    print(f"Add supplemental details for draft: {draft_id}")
    print("Paste additional facts only. Press Ctrl-D on a new line when finished.")
    print()
    try:
        supplement = sys.stdin.read()
    except KeyboardInterrupt:
        print("\nExperience supplement cancelled.", file=sys.stderr)
        return 130
    try:
        validate_raw_experience_note(supplement)
    except ValueError as error:
        print(str(error), file=sys.stderr)
        return 1

    combined_note = f"{original_note.rstrip()}\n\nSupplemental details:\n{supplement.strip()}\n"
    selected_pipeline = pipeline or _build_pipeline(data_root)
    new_draft_id = create_available_draft_id(data_root=data_root)
    print("Processing supplemented experience note...", flush=True)
    try:
        structured_draft = selected_pipeline.structure(combined_note, draft_id=new_draft_id)
    except KeyboardInterrupt:
        print("\nExperience supplement cancelled.", file=sys.stderr)
        return 130
    except (RuntimeError, ValueError) as error:
        print(str(error), file=sys.stderr)
        return 2
    structured_draft["source"]["supplements_draft_id"] = draft_id
    save_experience_draft(combined_note, structured_draft, data_root=data_root)
    print(f"Saved supplemented draft: {new_draft_id}")
    print_next_actions(new_draft_id)
    return offer_next_action_if_interactive(new_draft_id, data_root=data_root)


def print_next_actions(draft_id: str) -> None:
    print()
    print("Next actions:")
    print(f"- Review this draft: resume-agent experience review {draft_id}")
    print(f"- Supplement details: resume-agent experience supplement {draft_id}")
    print(f"- Approve and add to private bank: resume-agent experience approve {draft_id}")
    print("- Add another experience: resume-agent experience ingest")


def offer_next_action_if_interactive(draft_id: str, data_root: Path = Path(".")) -> int:
    if not sys.stdin.isatty():
        return 0
    print()
    print("Choose what to do next:")
    print("[r] Review draft  [s] Supplement details  [a] Approve  [n] Add another  [q] Quit")
    try:
        response = input("Next action: ").strip().lower()
    except (EOFError, KeyboardInterrupt):
        print("\nFinished.", file=sys.stderr)
        return 0
    if response in {"r", "review"}:
        return run_experience_review(draft_id, data_root=data_root)
    if response in {"s", "supplement"}:
        return run_experience_supplement(draft_id, data_root=data_root)
    if response in {"a", "approve"}:
        return run_experience_approve(draft_id, data_root=data_root)
    if response in {"n", "new", "add"}:
        return run_experience_ingest(data_root=data_root)
    if response not in {"", "q", "quit", "exit"}:
        print("Unknown action. Use the printed commands to continue later.", file=sys.stderr)
    return 0


def _build_pipeline(data_root: Path) -> ExperienceIngestionPipeline:
    return ExperienceIngestionPipeline(
        evidence_extractor=EvidenceExtractor(
            local_keywords_path=data_root / LOCAL_TECHNOLOGY_KEYWORDS_PATH,
        ),
        warning_handler=lambda message: print(f"Warning: {message}", file=sys.stderr, flush=True),
        progress_handler=lambda message: print(message, flush=True),
        new_technology_handler=_confirm_local_technology_keyword,
    )


def _confirm_local_technology_keyword(technology: str) -> bool:
    if not sys.stdin.isatty():
        return False
    try:
        response = input(
            f"Add '{technology}' to your local Experience Bank technology dictionary? [y/N] "
        ).strip().lower()
    except (EOFError, KeyboardInterrupt):
        print("\nSkipping local dictionary update.", file=sys.stderr)
        return False
    return response in {"y", "yes"}
