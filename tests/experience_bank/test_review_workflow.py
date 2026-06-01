from __future__ import annotations

import sys
import unittest
from contextlib import redirect_stdout
from io import StringIO
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

import yaml

from resume_agent.experience_bank.cli import (
    offer_next_action_if_interactive,
    run_experience_approve,
    run_experience_review,
    run_experience_supplement,
)
from resume_agent.experience_bank.ingestion import RuleBasedExperienceStructurer
from resume_agent.experience_bank.pipeline import ExperienceIngestionPipeline
from resume_agent.experience_bank.storage import save_experience_draft


class ReviewWorkflowTests(unittest.TestCase):
    def test_review_prints_yaml_and_next_actions(self) -> None:
        with TemporaryDirectory() as temp_dir:
            data_root = Path(temp_dir)
            _save_draft(data_root)
            output = StringIO()
            with redirect_stdout(output):
                exit_code = run_experience_review("experience_test", data_root=data_root)

        self.assertEqual(exit_code, 0)
        self.assertIn("title: Sample API Project", output.getvalue())
        self.assertIn("Next actions:", output.getvalue())

    def test_approve_merges_into_private_bank_after_confirmation(self) -> None:
        with TemporaryDirectory() as temp_dir:
            data_root = Path(temp_dir)
            _save_draft(data_root, clear_uncertain_points=True)
            with patch("builtins.input", return_value="y"):
                exit_code = run_experience_approve("experience_test", data_root=data_root)
            bank = yaml.safe_load((data_root / "data/private/experience_bank.yaml").read_text())

        self.assertEqual(exit_code, 0)
        self.assertEqual(bank["entries"][0]["status"], "approved")

    def test_approve_requires_second_confirmation_for_uncertain_points(self) -> None:
        with TemporaryDirectory() as temp_dir:
            data_root = Path(temp_dir)
            _save_draft(data_root)
            with patch("builtins.input", side_effect=["y", "n"]):
                exit_code = run_experience_approve("experience_test", data_root=data_root)

            bank_path = data_root / "data/private/experience_bank.yaml"

        self.assertEqual(exit_code, 0)
        self.assertFalse(bank_path.exists())

    def test_supplement_creates_new_draft_and_preserves_old_draft(self) -> None:
        with TemporaryDirectory() as temp_dir:
            data_root = Path(temp_dir)
            _save_draft(data_root)
            pipeline = ExperienceIngestionPipeline(mode="local")
            supplement = "Additional impact: the component remained in the project layout after launch."
            with patch.object(sys, "stdin", StringIO(supplement)):
                exit_code = run_experience_supplement(
                    "experience_test",
                    data_root=data_root,
                    pipeline=pipeline,
                )
            drafts = list((data_root / "data/private/experience_drafts").glob("*.yaml"))
            proposals = list((data_root / "data/private/experience_supplements").glob("*.yaml"))

        self.assertEqual(exit_code, 0)
        self.assertEqual(len(drafts), 1)
        self.assertEqual(len(proposals), 1)

    def test_supplement_can_save_updated_draft_version_without_overwriting_original(self) -> None:
        with TemporaryDirectory() as temp_dir:
            data_root = Path(temp_dir)
            _save_draft(data_root)
            pipeline = ExperienceIngestionPipeline(mode="local")
            supplement = "Time period: January 2025 - April 2025\nImpact: Supported internal API adoption."
            with (
                patch.object(sys, "stdin", _InteractiveStringIO(supplement)),
                patch("builtins.input", return_value="y"),
            ):
                exit_code = run_experience_supplement(
                    "experience_test",
                    data_root=data_root,
                    pipeline=pipeline,
                )
            drafts = list((data_root / "data/private/experience_drafts").glob("*.yaml"))
            proposals = list((data_root / "data/private/experience_supplements").glob("*.yaml"))
            updated_draft_path = next(path for path in drafts if path.stem != "experience_test")
            updated_raw_note = (
                data_root / "data/private/raw_experience_notes" / f"{updated_draft_path.stem}.txt"
            ).read_text(encoding="utf-8")

        self.assertEqual(exit_code, 0)
        self.assertEqual(len(drafts), 2)
        self.assertEqual(len(proposals), 1)
        self.assertEqual(updated_raw_note, supplement)

    def test_interactive_next_action_dispatches_review(self) -> None:
        with TemporaryDirectory() as temp_dir:
            data_root = Path(temp_dir)
            with (
                patch.object(sys, "stdin", _InteractiveStringIO("r\n")),
                patch(
                    "resume_agent.experience_bank.cli.run_experience_review",
                    return_value=0,
                ) as review,
            ):
                exit_code = offer_next_action_if_interactive(
                    "experience_test",
                    data_root=data_root,
                )

        self.assertEqual(exit_code, 0)
        review.assert_called_once_with("experience_test", data_root=data_root)


def _save_draft(data_root: Path, clear_uncertain_points: bool = False) -> None:
    raw_note = (
        "Title: Sample API Project\n"
        "Company: Sample Lab\n"
        "Built a Python REST API and tested the workflow with a team.\n"
    )
    draft = RuleBasedExperienceStructurer().structure(raw_note, draft_id="experience_test")
    if clear_uncertain_points:
        draft["uncertain_points"] = []
    save_experience_draft(raw_note, draft, data_root=data_root)


class _InteractiveStringIO(StringIO):
    def isatty(self) -> bool:
        return True


if __name__ == "__main__":
    unittest.main()
