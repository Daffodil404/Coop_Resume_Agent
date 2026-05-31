from __future__ import annotations

import unittest

from resume_agent.experience_bank.ingestion import RuleBasedExperienceStructurer, structure_experience_note


class IngestionTests(unittest.TestCase):
    def test_structures_explicit_fields_and_obvious_technologies(self) -> None:
        draft = structure_experience_note(
            raw_note=(
                "Title: Inventory Dashboard\n"
                "Company: Sample Lab\n"
                "Role: Student Developer\n"
                "Time period: January 2025 - April 2025\n"
                "Built a React and Python dashboard backed by SQL.\n"
                "Improved processing time by 25% after testing the workflow.\n"
            ),
            draft_id="experience_test",
        )

        self.assertEqual(draft["id"], "experience_test")
        self.assertEqual(draft["title"], "Inventory Dashboard")
        self.assertEqual(draft["company"], "Sample Lab")
        self.assertEqual(draft["role"], "Student Developer")
        self.assertEqual(draft["time_period"], "January 2025 - April 2025")
        self.assertEqual(draft["technologies"], ["Python", "React", "SQL"])
        self.assertEqual(
            draft["metrics"],
            ["Improved processing time by 25% after testing the workflow."],
        )
        self.assertEqual(draft["domain_keywords"], [])
        self.assertEqual(draft["status"], "draft")
        self.assertEqual(draft["source"]["structurer"], "rule_based")
        self.assertIsNone(draft["source"]["model"])
        self.assertEqual(draft["evidence"]["action_lines"], draft["actions"])
        self.assertEqual(draft["evidence"]["metric_lines"], draft["metrics"])
        self.assertEqual(draft["draft_bullets"], [])
        self.assertEqual(draft["evidence_lines"][0], "Title: Inventory Dashboard")
        self.assertEqual(draft["confidence"]["metrics"], "high")
        self.assertIn("Use only claims explicitly supported by the raw note.", draft["truth_constraints"])

    def test_does_not_treat_years_as_metrics_or_invent_company(self) -> None:
        draft = structure_experience_note(
            raw_note=(
                "Worked on a student software project from January 2025 - April 2025.\n"
                "Implemented a Java API and documented open questions for review.\n"
            ),
            draft_id="experience_test",
        )

        self.assertIsNone(draft["company"])
        self.assertEqual(draft["metrics"], [])
        self.assertIn(
            "Confirm whether this experience is associated with a company or organization.",
            draft["uncertain_points"],
        )

    def test_rule_based_structurer_class_still_works(self) -> None:
        draft = RuleBasedExperienceStructurer().structure(
            raw_note=(
                "Title: API Project\n"
                "Company: Sample Lab\n"
                "Built a Python REST API and tested the workflow with a team.\n"
            ),
            draft_id="experience_test",
        )

        self.assertEqual(draft["source"]["structurer"], "rule_based")
        self.assertEqual(draft["technologies"], ["Python", "REST"])


if __name__ == "__main__":
    unittest.main()
