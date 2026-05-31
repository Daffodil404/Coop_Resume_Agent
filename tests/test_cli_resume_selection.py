from __future__ import annotations

import json
import os
import unittest
from contextlib import redirect_stdout
from io import StringIO
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

from resume_agent.cli import run_cover_letter_decision, run_resume_selection
from resume_agent.config import RESUME_ROOT_ENV_VAR


class CLIResumeSelectionTests(unittest.TestCase):
    def test_run_resume_selection_uses_configured_root_saves_json_and_prints_summary(self) -> None:
        with TemporaryDirectory() as temp_dir:
            temp_root = Path(temp_dir)
            resume_root = temp_root / "resumes"
            application_dir = temp_root / "application"
            ai_dir = resume_root / "AI"
            ai_dir.mkdir(parents=True)
            application_dir.mkdir()
            selected_pdf = ai_dir / "latest.pdf"
            selected_pdf.write_text("fake pdf")

            output = StringIO()
            with patch.dict(os.environ, {RESUME_ROOT_ENV_VAR: str(resume_root)}):
                with redirect_stdout(output):
                    selection = run_resume_selection(
                        application_dir,
                        {"recommended_resume_base": "ai_engineer"},
                    )

            saved_selection = json.loads(
                (application_dir / "resume_selection.json").read_text()
            )

        self.assertEqual(selection["selected_resume_pdf"], str(selected_pdf))
        self.assertEqual(saved_selection, selection)
        self.assertIn("Recommended resume base: ai_engineer", output.getvalue())
        self.assertIn("Matched local category: AI", output.getvalue())
        self.assertIn("Fallback used: No", output.getvalue())

    def test_run_cover_letter_decision_saves_json_and_prints_summary(self) -> None:
        with TemporaryDirectory() as temp_dir:
            application_dir = Path(temp_dir)
            output = StringIO()
            with redirect_stdout(output):
                decision = run_cover_letter_decision(
                    application_dir=application_dir,
                    jd_analysis={"cover_letter_required": True},
                    resume_strategy={"recommended_resume_base": "sde"},
                    resume_selection={
                        "matched_category": "SDE",
                        "selected_resume_pdf": "/tmp/resumes/SDE/latest.pdf",
                        "fallback_used": False,
                    },
                )

            saved_decision = json.loads(
                (application_dir / "cover_letter_decision.json").read_text()
            )

        self.assertEqual(saved_decision, decision)
        self.assertIn("Recommendation: required", output.getvalue())
        self.assertIn("Generate cover letter: Yes", output.getvalue())


if __name__ == "__main__":
    unittest.main()
