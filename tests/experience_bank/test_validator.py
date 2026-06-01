from __future__ import annotations

import unittest

from resume_agent.experience_bank.ingestion import RuleBasedExperienceStructurer
from resume_agent.experience_bank.validator import (
    validate_experience_draft,
    validate_raw_experience_note,
)


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

    def test_rejects_invalid_status(self) -> None:
        draft = _valid_draft()
        draft["status"] = "merged"

        with self.assertRaisesRegex(ValueError, "Invalid experience draft status"):
            validate_experience_draft(draft)

    def test_rejects_invalid_confidence_value(self) -> None:
        draft = _valid_draft()
        draft["confidence"]["metrics"] = "certain"

        with self.assertRaisesRegex(ValueError, "Invalid confidence value"):
            validate_experience_draft(draft)

    def test_rejects_approved_draft_during_ingestion(self) -> None:
        draft = _valid_draft()
        draft["status"] = "approved"

        with self.assertRaisesRegex(ValueError, "manual review"):
            validate_experience_draft(draft)


def _valid_draft() -> dict[str, object]:
    return RuleBasedExperienceStructurer().structure(
        raw_note=(
            "Title: API Project\n"
            "Company: Sample Lab\n"
            "Built a Python REST API and tested the workflow with a team.\n"
        ),
        draft_id="experience_test",
    )


if __name__ == "__main__":
    unittest.main()
