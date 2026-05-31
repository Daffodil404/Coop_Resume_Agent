from __future__ import annotations

import os
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from resume_agent.resume_inventory import scan_resume_inventory, select_resume_pdf
from resume_agent.storage import save_resume_selection


class ResumeInventoryTests(unittest.TestCase):
    def test_scan_inventory_selects_latest_pdf_and_ignores_non_pdf_files(self) -> None:
        with TemporaryDirectory() as temp_dir:
            resume_root = Path(temp_dir)
            ai_dir = resume_root / "AI"
            ai_dir.mkdir()
            older_pdf = ai_dir / "older.pdf"
            latest_pdf = ai_dir / "latest.PDF"
            ignored_file = ai_dir / "notes.txt"
            older_pdf.write_text("older")
            latest_pdf.write_text("latest")
            ignored_file.write_text("ignore")
            os.utime(older_pdf, (100, 100))
            os.utime(latest_pdf, (200, 200))

            inventory = scan_resume_inventory(resume_root)

        self.assertEqual(inventory["categories"]["AI"]["latest_pdf"], str(latest_pdf))
        self.assertEqual(inventory["categories"]["AI"]["pdf_count"], 2)

    def test_select_resume_pdf_maps_ai_engineer_to_ai(self) -> None:
        inventory = {
            "resume_root": "/tmp/resumes",
            "categories": {
                "AI": {"latest_pdf": "/tmp/resumes/AI/latest.pdf"},
                "SDE": {"latest_pdf": "/tmp/resumes/SDE/latest.pdf"},
            },
        }

        selection = select_resume_pdf({"recommended_resume_base": "ai_engineer"}, inventory)

        self.assertEqual(selection["matched_category"], "AI")
        self.assertEqual(selection["selected_resume_pdf"], "/tmp/resumes/AI/latest.pdf")
        self.assertFalse(selection["fallback_used"])

    def test_select_resume_pdf_falls_back_when_preferred_folder_is_missing(self) -> None:
        inventory = {
            "resume_root": "/tmp/resumes",
            "categories": {
                "Mobile": {"latest_pdf": "/tmp/resumes/Mobile/latest.pdf"},
                "SDE": {"latest_pdf": "/tmp/resumes/SDE/latest.pdf"},
            },
        }

        selection = select_resume_pdf({"recommended_resume_base": "ai_engineer"}, inventory)

        self.assertEqual(selection["matched_category"], "SDE")
        self.assertEqual(selection["selected_resume_pdf"], "/tmp/resumes/SDE/latest.pdf")
        self.assertTrue(selection["fallback_used"])
        self.assertIn("Fell back", selection["selection_reason"])

    def test_save_resume_selection_writes_json_artifact(self) -> None:
        with TemporaryDirectory() as temp_dir:
            application_dir = Path(temp_dir)
            save_resume_selection(
                application_dir,
                {
                    "resume_root": "/tmp/resumes",
                    "recommended_resume_base": "sde",
                    "matched_category": "SDE",
                    "selected_resume_pdf": "/tmp/resumes/SDE/latest.pdf",
                    "selection_reason": "Matched recommended resume base.",
                    "fallback_used": False,
                    "available_categories": ["SDE"],
                },
            )

            artifact = application_dir / "resume_selection.json"
            self.assertTrue(artifact.is_file())
            self.assertIn('"matched_category": "SDE"', artifact.read_text())


if __name__ == "__main__":
    unittest.main()
