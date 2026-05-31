from __future__ import annotations

import sys
from pathlib import Path

from .ai_client import AIClient
from .config import get_resume_root
from .jd import clean_jd_text
from .mock_ai import MockAIClient
from .mock_resume_strategy import MockResumeStrategyClient
from .resume_inventory import scan_resume_inventory, select_resume_pdf
from .storage import (
    create_application_dir,
    create_application_metadata,
    current_utc_time,
    save_application_artifacts,
    save_resume_strategy,
    save_resume_selection,
)


def read_jd_from_stdin() -> str:
    print("Paste the full Job Description below.")
    print("When you are done, press Ctrl-D on a new line to start analysis.")
    print()
    return sys.stdin.read()


def print_analysis_summary(analysis: dict[str, object]) -> None:
    print()
    print("Analysis summary")
    print(f"Company: {analysis.get('company') or 'Unknown'}")
    print(f"Role: {analysis.get('role_title') or 'Unknown'}")
    print(f"Location: {analysis.get('location') or 'Unknown'}")
    print(f"Work term: {analysis.get('work_term') or 'Unknown'}")
    print(f"Role type: {analysis.get('role_type') or 'Unknown'}")
    print()


def confirm_analysis() -> bool:
    try:
        response = input("Continue with this analysis? [Y/n] ").strip().lower()
    except EOFError:
        response = ""
    return response in {"", "y", "yes"}


def create_resume_selection(resume_strategy: dict[str, object]) -> dict[str, object]:
    inventory = scan_resume_inventory(get_resume_root())
    return select_resume_pdf(resume_strategy, inventory)


def run_resume_selection(
    application_dir: Path,
    resume_strategy: dict[str, object],
) -> dict[str, object]:
    selection = create_resume_selection(resume_strategy)
    save_resume_selection(application_dir, selection)
    print_resume_selection_summary(selection)
    return selection


def print_resume_selection_summary(selection: dict[str, object]) -> None:
    print()
    print("Resume selection summary")
    print(f"Recommended resume base: {selection.get('recommended_resume_base') or 'Unknown'}")
    print(f"Matched local category: {selection.get('matched_category') or 'None'}")
    print(f"Selected latest PDF: {selection.get('selected_resume_pdf') or 'None'}")
    print(f"Fallback used: {'Yes' if selection.get('fallback_used') else 'No'}")
    print()


def main() -> int:
    raw_jd = read_jd_from_stdin()
    if not raw_jd.strip():
        print("No Job Description received. Nothing was generated.", file=sys.stderr)
        return 1

    clean_jd = clean_jd_text(raw_jd)
    ai_client: AIClient = MockAIClient()
    analysis = ai_client.analyze_jd(clean_jd)
    print_analysis_summary(analysis)

    if not confirm_analysis():
        print("Analysis discarded. Nothing was saved.")
        return 0

    output_root = Path.cwd() / "applications"
    created_at = current_utc_time()
    application_dir = create_application_dir(
        output_root=output_root,
        company=analysis["company"],
        role_title=analysis["role_title"],
        created_at=created_at,
    )
    metadata = create_application_metadata(
        application_dir=application_dir,
        analysis=analysis,
        created_at=created_at,
    )
    save_application_artifacts(
        application_dir=application_dir,
        raw_jd=raw_jd,
        clean_jd=clean_jd,
        analysis=analysis,
        metadata=metadata,
    )
    resume_strategy = MockResumeStrategyClient().create_strategy(analysis)
    save_resume_strategy(application_dir, resume_strategy)
    run_resume_selection(application_dir, resume_strategy)

    print(f"Created application draft: {application_dir}")
    print(
        "Generated: jd_raw.txt, jd_clean.txt, jd_analysis.json, metadata.json, "
        "resume_strategy.json, resume_selection.json"
    )
    return 0
