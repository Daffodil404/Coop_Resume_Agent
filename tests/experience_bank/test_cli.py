from __future__ import annotations

import sys
import unittest
from contextlib import redirect_stdout
from io import StringIO
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

from resume_agent.experience_bank.cli import run_experience_ingest


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
            with patch.object(sys, "stdin", StringIO(raw_note)):
                with redirect_stdout(output):
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
        self.assertIn("Draft was not merged", terminal_output)


if __name__ == "__main__":
    unittest.main()
