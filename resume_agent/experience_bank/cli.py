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
    save_experience_draft,
    save_experience_supplement_proposal,
    save_updated_experience_draft_version,
)
from .supplement import (
    analyze_experience_gaps,
    create_supplement_proposal,
    propose_supplement_merge,
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
    if sys.stdin.isatty():
        follow_up_exit_code = offer_immediate_supplement(
            draft_id=draft_id,
            original_draft=structured_draft,
            data_root=data_root,
            pipeline=selected_pipeline,
        )
        if follow_up_exit_code != 0:
            return follow_up_exit_code
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
        original_draft = load_experience_draft(draft_id, data_root=data_root)
    except ValueError as error:
        print(str(error), file=sys.stderr)
        return 1
    return run_supplement_workflow(
        draft_id=draft_id,
        original_draft=original_draft,
        data_root=data_root,
        pipeline=pipeline,
    )


def run_supplement_workflow(
    draft_id: str,
    original_draft: dict[str, object],
    data_root: Path = Path("."),
    pipeline: ExperienceIngestionPipeline | None = None,
) -> int:
    gap_analysis = analyze_experience_gaps(original_draft)
    print_gap_analysis(draft_id, gap_analysis)
    print("Paste supplemental details only. Press Ctrl-D on a new line when finished.")
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

    selected_pipeline = pipeline or _build_pipeline(data_root)
    supplement_draft_id = create_available_draft_id(data_root=data_root)
    print("Processing supplemented experience note...", flush=True)
    try:
        structured_draft = selected_pipeline.structure(supplement, draft_id=supplement_draft_id)
    except KeyboardInterrupt:
        print("\nExperience supplement cancelled.", file=sys.stderr)
        return 130
    except (RuntimeError, ValueError) as error:
        print(str(error), file=sys.stderr)
        return 2
    structured_draft["source"]["supplements_draft_id"] = draft_id
    proposed_changes = propose_supplement_merge(original_draft, structured_draft)
    proposal = create_supplement_proposal(
        original_draft=original_draft,
        gap_analysis=gap_analysis,
        raw_supplement_note=supplement,
        structured_supplement=structured_draft,
        proposed_changes=proposed_changes,
    )
    saved_paths = save_experience_supplement_proposal(proposal, data_root=data_root)
    print(f"Saved supplement proposal: {saved_paths['proposal_path']}")
    print("Original draft was not overwritten.")
    print_proposed_changes_summary(proposed_changes)
    if _confirm_create_updated_draft():
        updated_paths = save_updated_experience_draft_version(
            original_draft_id=draft_id,
            raw_supplement_note=supplement,
            structured_draft=proposed_changes["proposed_draft"],
            data_root=data_root,
        )
        print(f"Saved updated draft version: {updated_paths['draft_path']}")
    print_next_actions(draft_id)
    return offer_next_action_if_interactive(draft_id, data_root=data_root)


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


def print_gap_analysis(draft_id: str, gap_analysis: dict[str, object]) -> None:
    print(f"Supplement analysis for draft: {draft_id}")
    print(f"Overall status: {gap_analysis['overall_status']}")
    print(f"Reason: {gap_analysis['reason']}")
    if gap_analysis["missing_fields"]:
        print(f"Missing fields: {', '.join(gap_analysis['missing_fields'])}")
    if gap_analysis["weak_fields"]:
        print(f"Weak fields: {', '.join(gap_analysis['weak_fields'])}")
    if gap_analysis["unsupported_fields"]:
        print(f"Unsupported fields: {', '.join(gap_analysis['unsupported_fields'])}")
    if gap_analysis["priority_questions"]:
        print("Priority questions:")
        for question in gap_analysis["priority_questions"]:
            print(f"- {question}")


def print_proposed_changes_summary(proposed_changes: dict[str, object]) -> None:
    field_changes = proposed_changes["field_changes"]
    if field_changes:
        print("Supplement proposal includes changes for:")
        for field_name in field_changes:
            print(f"- {field_name}")
    if proposed_changes["warnings"]:
        for warning in proposed_changes["warnings"]:
            print(f"Warning: {warning}")


def offer_immediate_supplement(
    draft_id: str,
    original_draft: dict[str, object],
    data_root: Path,
    pipeline: ExperienceIngestionPipeline,
) -> int:
    gap_analysis = analyze_experience_gaps(original_draft)
    print()
    print("Immediate follow-up questions")
    print_gap_analysis(draft_id, gap_analysis)
    try:
        response = input("Add supplemental details now? [Y/n] ").strip().lower()
    except (EOFError, KeyboardInterrupt):
        print("\nSkipping supplemental follow-up.", file=sys.stderr)
        return 0
    if response not in {"", "y", "yes"}:
        return 0
    return run_supplement_workflow(
        draft_id=draft_id,
        original_draft=original_draft,
        data_root=data_root,
        pipeline=pipeline,
    )


def _confirm_create_updated_draft() -> bool:
    if not sys.stdin.isatty():
        return False
    try:
        response = input(
            "Create a new updated draft version from this supplement proposal? [y/N] "
        ).strip().lower()
    except (EOFError, KeyboardInterrupt):
        print("\nSkipping updated draft creation.", file=sys.stderr)
        return False
    return response in {"y", "yes"}


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
