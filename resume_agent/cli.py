from __future__ import annotations

import sys
from pathlib import Path

from .ai_client import AIClient
from .config import get_resume_root
from .cover_letter import decide_cover_letter
from .cover_letter_draft import render_cover_letter_draft
from .experience_bank.cli import (
    run_experience_approve,
    run_experience_ingest,
    run_experience_review,
    run_experience_supplement,
)
from .jd import clean_jd_text
from .mock_ai import MockAIClient
from .mock_resume_strategy import MockResumeStrategyClient
from .openai_jd_analysis import OpenAIJdAnalysisClient, should_use_ai_jd_analysis
from .resume_inventory import scan_resume_inventory, select_resume_pdf
from .storage import (
    create_application_dir,
    create_application_metadata,
    current_utc_time,
    save_application_artifacts,
    save_cover_letter_decision,
    save_cover_letter_generation,
    save_resume_strategy,
    save_resume_selection,
)
from .experience_bank.openai_provider import OpenAIProviderError


def read_jd_from_stdin() -> str | None:
    print("Paste the full Job Description below.")
    print("When you are done, press Ctrl-D on a new line to start analysis.")
    print()
    try:
        return sys.stdin.read()
    except KeyboardInterrupt:
        print("\nJob description ingestion cancelled.", file=sys.stderr)
        return None


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


def run_cover_letter_decision(
    application_dir: Path,
    jd_analysis: dict[str, object],
    resume_strategy: dict[str, object],
    resume_selection: dict[str, object],
) -> dict[str, object]:
    decision = decide_cover_letter(jd_analysis, resume_strategy, resume_selection)
    save_cover_letter_decision(application_dir, decision)
    print_cover_letter_decision_summary(decision)
    return decision


def print_cover_letter_decision_summary(decision: dict[str, object]) -> None:
    print()
    print("Cover letter decision")
    print(f"Recommendation: {decision['recommendation']}")
    print(f"Generate cover letter: {'Yes' if decision['should_generate'] else 'No'}")
    print(f"Reason: {decision['reason']}")
    if decision.get("suggested_angle"):
        print(f"Suggested angle: {decision['suggested_angle']}")
    print()


def run_cover_letter_draft_generation(
    application_dir: Path,
    jd_analysis: dict[str, object],
    resume_strategy: dict[str, object],
    resume_selection: dict[str, object],
    cover_letter_decision: dict[str, object],
) -> dict[str, object]:
    generation = render_cover_letter_draft(
        jd_analysis=jd_analysis,
        resume_strategy=resume_strategy,
        resume_selection=resume_selection,
        cover_letter_decision=cover_letter_decision,
        output_path=application_dir / "cover_letter.tex",
        data_root=Path.cwd(),
    )
    save_cover_letter_generation(application_dir, generation)
    if generation["generated"]:
        print(f"Generated editable cover letter draft: {generation['output_path']}")
        print(f"Cover letter generation mode: {generation['generation_mode']}")
    else:
        print("Cover letter generation skipped.")
    print()
    return generation


def main() -> int:
    if sys.argv[1:] == ["experience", "ingest"]:
        return run_experience_ingest()
    if len(sys.argv) == 4 and sys.argv[1:3] == ["experience", "review"]:
        return run_experience_review(sys.argv[3])
    if len(sys.argv) == 4 and sys.argv[1:3] == ["experience", "approve"]:
        return run_experience_approve(sys.argv[3])
    if len(sys.argv) == 4 and sys.argv[1:3] == ["experience", "supplement"]:
        return run_experience_supplement(sys.argv[3])
    if sys.argv[1:]:
        print(
            "Usage: resume-agent [experience ingest|review <draft-id>|"
            "supplement <draft-id>|approve <draft-id>]",
            file=sys.stderr,
        )
        return 2

    raw_jd = read_jd_from_stdin()
    if raw_jd is None:
        return 130
    if not raw_jd.strip():
        print("No Job Description received. Nothing was generated.", file=sys.stderr)
        return 1

    clean_jd = clean_jd_text(raw_jd)
    analysis = analyze_job_description(clean_jd, data_root=Path.cwd())
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
    resume_selection = run_resume_selection(application_dir, resume_strategy)
    cover_letter_decision = run_cover_letter_decision(
        application_dir,
        analysis,
        resume_strategy,
        resume_selection,
    )
    run_cover_letter_draft_generation(
        application_dir,
        analysis,
        resume_strategy,
        resume_selection,
        cover_letter_decision,
    )

    print(f"Created application draft: {application_dir}")
    print(
        "Generated: jd_raw.txt, jd_clean.txt, jd_analysis.json, metadata.json, "
        "resume_strategy.json, resume_selection.json, cover_letter_decision.json, "
        "cover_letter_generation.json"
    )
    return 0


def analyze_job_description(clean_jd: str, data_root: Path) -> dict[str, object]:
    if should_use_ai_jd_analysis():
        try:
            ai_client = OpenAIJdAnalysisClient(data_root=data_root)
            print(f"Using model {ai_client.model} for jd_analysis")
            return ai_client.analyze_jd(clean_jd)
        except OpenAIProviderError as error:
            print(f"{error} Using local JD analysis fallback.", file=sys.stderr)
    ai_client: AIClient = MockAIClient()
    return ai_client.analyze_jd(clean_jd)
