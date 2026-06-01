from __future__ import annotations

import unittest

from resume_agent.experience_bank.supplement import (
    analyze_experience_gaps,
    propose_supplement_merge,
)


class SupplementTests(unittest.TestCase):
    def test_analyzes_missing_and_weak_fields(self) -> None:
        draft = {
            "title": "API",
            "company": None,
            "time_period": None,
            "context": "Internal tool.",
            "problem": None,
            "role": None,
            "actions": ["Implemented the API."],
            "technologies": [],
            "impact": [],
            "metrics": [],
            "role_types": [],
            "skills": ["Collaboration"],
            "domain_keywords": [],
            "possible_resume_angles": [],
            "truth_constraints": [],
            "evidence": {
                "action_lines": [],
                "metric_lines": [],
                "technology_lines": [],
            },
        }

        gaps = analyze_experience_gaps(draft)

        self.assertIn("company", gaps["missing_fields"])
        self.assertIn("time_period", gaps["missing_fields"])
        self.assertIn("technologies", gaps["missing_fields"])
        self.assertIn("evidence.action_lines", gaps["missing_fields"])
        self.assertIn("title", gaps["weak_fields"])
        self.assertIn("skills", gaps["weak_fields"])
        self.assertIn(gaps["overall_status"], {"needs_more_detail", "not_ready"})

    def test_proposes_conservative_additive_merge(self) -> None:
        original = {
            "id": "experience_test",
            "title": None,
            "company": "Sample Lab",
            "time_period": None,
            "context": None,
            "problem": None,
            "role": None,
            "actions": ["Built an API."],
            "technologies": ["Python"],
            "impact": [],
            "metrics": [],
            "role_types": [],
            "skills": [],
            "domain_keywords": [],
            "possible_resume_angles": [],
            "usable_for": [],
            "evidence": {
                "action_lines": ["Built an API."],
                "metric_lines": [],
                "technology_lines": ["Built an API in Python."],
            },
            "evidence_lines": ["Built an API in Python."],
        }
        supplement = {
            "title": "Payments API",
            "company": "Sample Lab",
            "time_period": "January 2025 - April 2025",
            "context": "Built an internal service.",
            "problem": None,
            "role": "Backend developer",
            "actions": ["Added payment polling."],
            "technologies": ["HTTP APIs"],
            "impact": ["Supported payment status tracking."],
            "metrics": [],
            "role_types": ["backend"],
            "skills": ["backend polling"],
            "domain_keywords": ["payment integration"],
            "possible_resume_angles": ["Backend payment workflow integration"],
            "usable_for": ["backend"],
            "evidence": {
                "action_lines": ["Added payment polling."],
                "metric_lines": [],
                "technology_lines": ["Used HTTP 接口 for backend communication."],
            },
            "evidence_lines": ["Used HTTP 接口 for backend communication."],
        }

        proposal = propose_supplement_merge(original, supplement)

        self.assertEqual(proposal["merge_strategy"], "conservative_additive")
        self.assertEqual(proposal["proposed_draft"]["title"], "Payments API")
        self.assertIn("HTTP APIs", proposal["proposed_draft"]["technologies"])
        self.assertIn("backend", proposal["proposed_draft"]["usable_for"])
        self.assertIn("time_period", proposal["field_changes"])
        self.assertIn("evidence", proposal["field_changes"])


if __name__ == "__main__":
    unittest.main()
