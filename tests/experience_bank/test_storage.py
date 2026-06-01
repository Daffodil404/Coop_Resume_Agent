from __future__ import annotations

import unittest
from datetime import datetime, timezone
from pathlib import Path
from tempfile import TemporaryDirectory

import yaml

from resume_agent.experience_bank.ingestion import RuleBasedExperienceStructurer
from resume_agent.experience_bank.storage import (
    approve_experience_draft,
    create_available_draft_id,
    load_experience_draft,
    save_experience_draft,
)


class StorageTests(unittest.TestCase):
    def test_saves_raw_note_and_yaml_draft_under_private_data(self) -> None:
        with TemporaryDirectory() as temp_dir:
            data_root = Path(temp_dir)
            raw_note = (
                "Title: Sample\n"
                "Company: Sample Lab\n"
                "Built a Python REST API and tested the workflow with a team.\n"
            )
            paths = save_experience_draft(
                raw_note=raw_note,
                structured_draft=RuleBasedExperienceStructurer().structure(
                    raw_note,
                    draft_id="experience_test",
                ),
                data_root=data_root,
            )
            raw_path = Path(paths["raw_note_path"])
            draft_path = Path(paths["draft_path"])
            loaded_draft = yaml.safe_load(draft_path.read_text())

        self.assertEqual(
            raw_path.relative_to(data_root),
            Path("data/private/raw_experience_notes/experience_test.txt"),
        )
        self.assertEqual(
            draft_path.relative_to(data_root),
            Path("data/private/experience_drafts/experience_test.yaml"),
        )
        self.assertEqual(loaded_draft["title"], "Sample")

    def test_approves_reviewed_draft_into_private_bank(self) -> None:
        with TemporaryDirectory() as temp_dir:
            data_root = Path(temp_dir)
            raw_note = (
                "Title: Sample\n"
                "Company: Sample Lab\n"
                "Time period: January 2025 - April 2025\n"
                "Built a Python REST API and improved response time by 20%.\n"
            )
            draft = RuleBasedExperienceStructurer().structure(
                raw_note,
                draft_id="experience_test",
            )
            draft["uncertain_points"] = []
            save_experience_draft(raw_note, draft, data_root=data_root)

            result = approve_experience_draft("experience_test", data_root=data_root)
            bank = yaml.safe_load(Path(result["bank_path"]).read_text())

        self.assertEqual(bank["entries"][0]["id"], "experience_test")
        self.assertEqual(bank["entries"][0]["status"], "approved")

    def test_approval_requires_explicit_override_for_uncertain_points(self) -> None:
        with TemporaryDirectory() as temp_dir:
            data_root = Path(temp_dir)
            raw_note = (
                "Title: Sample\n"
                "Company: Sample Lab\n"
                "Built a Python REST API and tested the workflow with a team.\n"
            )
            save_experience_draft(
                raw_note,
                RuleBasedExperienceStructurer().structure(raw_note, draft_id="experience_test"),
                data_root=data_root,
            )

            with self.assertRaisesRegex(ValueError, "uncertain_points"):
                approve_experience_draft("experience_test", data_root=data_root)

    def test_loads_saved_experience_draft(self) -> None:
        with TemporaryDirectory() as temp_dir:
            data_root = Path(temp_dir)
            raw_note = (
                "Title: Sample\n"
                "Company: Sample Lab\n"
                "Built a Python REST API and tested the workflow with a team.\n"
            )
            save_experience_draft(
                raw_note,
                RuleBasedExperienceStructurer().structure(raw_note, draft_id="experience_test"),
                data_root=data_root,
            )

            loaded = load_experience_draft("experience_test", data_root=data_root)

        self.assertEqual(loaded["id"], "experience_test")

    def test_creates_available_draft_id_when_timestamp_id_already_exists(self) -> None:
        with TemporaryDirectory() as temp_dir:
            data_root = Path(temp_dir)
            created_at = datetime(2026, 5, 31, 20, 0, tzinfo=timezone.utc)
            draft_id = create_available_draft_id(data_root=data_root, created_at=created_at)
            draft_dir = data_root / "data/private/experience_drafts"
            draft_dir.mkdir(parents=True)
            (draft_dir / f"{draft_id}.yaml").write_text("id: existing\n")

            next_draft_id = create_available_draft_id(data_root=data_root, created_at=created_at)

        self.assertEqual(next_draft_id, f"{draft_id}_2")


if __name__ == "__main__":
    unittest.main()
