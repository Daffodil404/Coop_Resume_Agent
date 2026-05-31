from __future__ import annotations

import unittest

from resume_agent.mock_resume_strategy import MockResumeStrategyClient


class MockResumeStrategyTests(unittest.TestCase):
    def setUp(self) -> None:
        self.client = MockResumeStrategyClient()

    def test_recommends_ai_resume_for_machine_learning_role(self) -> None:
        strategy = self.client.create_strategy(
            {
                "role_title": "Machine Learning Engineer Co-op",
                "tools_and_technologies": ["Python"],
                "core_requirements": ["Experience with machine learning models."],
            }
        )

        self.assertEqual(strategy["recommended_resume_base"], "ai_engineer")

    def test_recommends_sde_resume_when_no_specialized_category_matches(self) -> None:
        strategy = self.client.create_strategy(
            {
                "role_title": "Software Developer Co-op",
                "tools_and_technologies": ["Java"],
            }
        )

        self.assertEqual(strategy["recommended_resume_base"], "sde")


if __name__ == "__main__":
    unittest.main()
