from __future__ import annotations

import unittest

from resume_agent.experience_bank.validator import validate_raw_experience_note


class ValidatorTests(unittest.TestCase):
    def test_rejects_empty_note(self) -> None:
        with self.assertRaisesRegex(ValueError, "cannot be empty"):
            validate_raw_experience_note("  \n")

    def test_rejects_short_note(self) -> None:
        with self.assertRaisesRegex(ValueError, "too short"):
            validate_raw_experience_note("Built API.")

    def test_accepts_note_with_enough_detail(self) -> None:
        validate_raw_experience_note(
            "Built a Python API and documented the workflow for a student project."
        )


if __name__ == "__main__":
    unittest.main()
