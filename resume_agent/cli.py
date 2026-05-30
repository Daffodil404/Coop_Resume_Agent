from __future__ import annotations

import sys
from pathlib import Path

from .ai_client import AIClient
from .jd import clean_jd_text
from .mock_ai import MockAIClient
from .storage import (
    create_application_dir,
    create_application_metadata,
    current_utc_time,
    save_application_artifacts,
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

    print(f"Created application draft: {application_dir}")
    print("Generated: jd_raw.txt, jd_clean.txt, jd_analysis.json, metadata.json")
    return 0
