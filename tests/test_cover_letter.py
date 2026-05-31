from __future__ import annotations

import unittest

from resume_agent.cover_letter import decide_cover_letter


class CoverLetterDecisionTests(unittest.TestCase):
    def test_required_when_jd_explicitly_requires_cover_letter(self) -> None:
        decision = decide_cover_letter(
            {"cover_letter_required": True},
            {"recommended_resume_base": "sde"},
            _direct_selection("SDE"),
        )

        self.assertEqual(decision["recommendation"], "required")
        self.assertTrue(decision["should_generate"])
        self.assertEqual(decision["estimated_value"], "high")

    def test_recommended_for_ai_role(self) -> None:
        decision = decide_cover_letter(
            {"role_title": "AI Product Engineer"},
            {"recommended_resume_base": "ai_engineer"},
            _direct_selection("AI"),
        )

        self.assertEqual(decision["recommendation"], "recommended")
        self.assertTrue(decision["should_generate"])

    def test_recommended_for_mission_driven_role(self) -> None:
        decision = decide_cover_letter(
            {"domain": "Healthcare"},
            {"recommended_resume_base": "sde"},
            _direct_selection("SDE"),
        )

        self.assertEqual(decision["recommendation"], "recommended")
        self.assertTrue(decision["should_generate"])

    def test_skip_for_standard_sde_role_with_direct_resume_fit(self) -> None:
        decision = decide_cover_letter(
            {"role_title": "Software Developer"},
            {"recommended_resume_base": "sde"},
            _direct_selection("SDE"),
        )

        self.assertEqual(decision["recommendation"], "skip")
        self.assertFalse(decision["should_generate"])

    def test_recommended_when_resume_selection_used_fallback(self) -> None:
        selection = _direct_selection("SDE")
        selection["fallback_used"] = True
        decision = decide_cover_letter(
            {"role_title": "Software Developer"},
            {"recommended_resume_base": "ai_engineer"},
            selection,
        )

        self.assertEqual(decision["recommendation"], "recommended")
        self.assertTrue(decision["should_generate"])


def _direct_selection(category: str) -> dict[str, object]:
    return {
        "matched_category": category,
        "selected_resume_pdf": f"/tmp/resumes/{category}/latest.pdf",
        "fallback_used": False,
    }


if __name__ == "__main__":
    unittest.main()
