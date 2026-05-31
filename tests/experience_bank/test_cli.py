from __future__ import annotations

import sys
import unittest
from contextlib import redirect_stderr, redirect_stdout
from io import StringIO
import os
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

from resume_agent.experience_bank.cli import (
    _confirm_local_technology_keyword,
    run_experience_ingest,
)
from resume_agent.experience_bank.pipeline import ExperienceIngestionPipeline


class ExperienceIngestCLITests(unittest.TestCase):
    def test_ingest_saves_private_draft_without_merging_final_bank(self) -> None:
        raw_note = (
            "Title: Sample API Project\n"
            "Company: Sample Lab\n"
            "Built a Python REST API and tested the workflow with a student team.\n"
        )
        with TemporaryDirectory() as temp_dir:
            data_root = Path(temp_dir)
            output = StringIO()
            stderr = StringIO()
            with patch.dict(os.environ, {}, clear=True):
                with patch.object(sys, "stdin", StringIO(raw_note)):
                    with redirect_stdout(output):
                        with redirect_stderr(stderr):
                            exit_code = run_experience_ingest(data_root=data_root)

            raw_notes = list((data_root / "data/private/raw_experience_notes").glob("*.txt"))
            drafts = list((data_root / "data/private/experience_drafts").glob("*.yaml"))

        self.assertEqual(exit_code, 0)
        self.assertEqual(len(raw_notes), 1)
        self.assertEqual(len(drafts), 1)
        self.assertFalse((data_root / "data/private/experience_bank.yaml").exists())
        terminal_output = output.getvalue()
        self.assertIn("Describe one project or experience at a time.", terminal_output)
        self.assertIn("actions personally taken", terminal_output)
        self.assertIn("truth constraints / what not to exaggerate", terminal_output)
        self.assertIn("target roles this experience may support", terminal_output)
        self.assertIn("Processing experience note...", terminal_output)
        self.assertIn("Structuring complete: rule_based (local)", terminal_output)
        self.assertIn("Draft was not merged", terminal_output)
        self.assertIn("Next actions:", terminal_output)
        self.assertIn("experience review", terminal_output)
        self.assertIn("experience supplement", terminal_output)
        self.assertIn("experience approve", terminal_output)
        self.assertIn("Using local Experience Bank fallback", stderr.getvalue())

    def test_ctrl_c_cancels_without_traceback_or_files(self) -> None:
        with TemporaryDirectory() as temp_dir:
            data_root = Path(temp_dir)
            stdout = StringIO()
            stderr = StringIO()
            interrupted_stdin = StringIO()
            with patch.object(interrupted_stdin, "read", side_effect=KeyboardInterrupt):
                with patch.object(sys, "stdin", interrupted_stdin):
                    with redirect_stdout(stdout):
                        with redirect_stderr(stderr):
                            exit_code = run_experience_ingest(data_root=data_root)

            private_data_dir = data_root / "data/private"

        self.assertEqual(exit_code, 130)
        self.assertFalse(private_data_dir.exists())
        self.assertIn("Experience ingestion cancelled.", stderr.getvalue())
        self.assertNotIn("Traceback", stderr.getvalue())

    def test_ctrl_c_during_structuring_cancels_without_files(self) -> None:
        raw_note = (
            "Title: Sample API Project\n"
            "Company: Sample Lab\n"
            "Built a Python REST API and tested the workflow with a team.\n"
        )
        with TemporaryDirectory() as temp_dir:
            data_root = Path(temp_dir)
            stdout = StringIO()
            stderr = StringIO()
            pipeline = ExperienceIngestionPipeline(mode="local")
            with patch.object(pipeline, "structure", side_effect=KeyboardInterrupt):
                with patch.object(sys, "stdin", StringIO(raw_note)):
                    with redirect_stdout(stdout):
                        with redirect_stderr(stderr):
                            exit_code = run_experience_ingest(
                                data_root=data_root,
                                pipeline=pipeline,
                            )

            private_data_dir = data_root / "data/private"

        self.assertEqual(exit_code, 130)
        self.assertFalse(private_data_dir.exists())
        self.assertIn("Processing experience note...", stdout.getvalue())
        self.assertIn("Experience ingestion cancelled.", stderr.getvalue())

    def test_can_confirm_new_local_technology_keyword_interactively(self) -> None:
        with patch.object(sys, "stdin", _InteractiveStringIO("y\n")):
            should_add = _confirm_local_technology_keyword("Figma")

        self.assertTrue(should_add)


class _InteractiveStringIO(StringIO):
    def isatty(self) -> bool:
        return True


if __name__ == "__main__":
    unittest.main()
