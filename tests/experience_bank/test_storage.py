from __future__ import annotations

import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

import yaml

from resume_agent.experience_bank.storage import save_experience_draft


class StorageTests(unittest.TestCase):
    def test_saves_raw_note_and_yaml_draft_under_private_data(self) -> None:
        with TemporaryDirectory() as temp_dir:
            data_root = Path(temp_dir)
            paths = save_experience_draft(
                raw_note="A sufficiently detailed fake raw experience note.",
                structured_draft={"id": "experience_test", "title": "Sample"},
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


if __name__ == "__main__":
    unittest.main()
