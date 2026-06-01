from __future__ import annotations

import unittest

from resume_agent.experience_bank.ai_structurer import AIExperienceStructurer
from resume_agent.experience_bank.evidence import ExtractedEvidence


class AIExperienceStructurerTests(unittest.TestCase):
    def test_loads_prompts_and_forces_draft_source_metadata(self) -> None:
        captured_prompts = []

        def response_provider(system_prompt: str, user_prompt: str) -> dict[str, object]:
            captured_prompts.extend([system_prompt, user_prompt])
            return {
                "id": "invented_id",
                "status": "approved",
                "source": {},
                "evidence": {"action_lines": ["invented"], "metric_lines": [], "technology_lines": []},
                "evidence_lines": ["invented"],
                "draft_bullets": ["invented"],
                "truth_constraints": [],
            }

        evidence = ExtractedEvidence(
            action_lines=["Built a Python API."],
            technology_lines=["Built a Python API."],
            technologies=["Python"],
            evidence_lines=["Built a Python API."],
        )
        draft = AIExperienceStructurer(
            response_provider=response_provider,
            model="fake-model",
        ).structure(
            clean_note="Built a Python API.",
            draft_id="experience_test",
            evidence=evidence,
        )

        self.assertEqual(draft["id"], "experience_test")
        self.assertEqual(draft["status"], "draft")
        self.assertEqual(draft["source"]["structurer"], "openai")
        self.assertEqual(draft["source"]["model"], "fake-model")
        self.assertEqual(draft["evidence"]["action_lines"], ["Built a Python API."])
        self.assertEqual(draft["evidence_lines"], ["Built a Python API."])
        self.assertEqual(draft["draft_bullets"], [])
        self.assertIn("Do not invent metrics", draft["truth_constraints"][1])
        self.assertIn("Never invent technologies", captured_prompts[0])
        self.assertIn("mixed Chinese-English", captured_prompts[0])
        self.assertIn("concise professional English", captured_prompts[0])
        self.assertIn("Do not translate or rewrite `evidence_lines`", captured_prompts[0])
        self.assertIn("partial guardrail hints", captured_prompts[0])
        self.assertIn("Write all generated fields in concise professional English", captured_prompts[1])
        self.assertIn("Do not leave semantically extractable fields empty", captured_prompts[1])
        self.assertIn("Built a Python API.", captured_prompts[1])

    def test_preserves_mixed_language_evidence_while_structured_fields_are_english(self) -> None:
        raw_line = "使用 Vue 实现了 landing page，并优化了组件结构。"

        def response_provider(system_prompt: str, user_prompt: str) -> dict[str, object]:
            return {
                "id": "experience_test",
                "title": "Landing Page Frontend Implementation",
                "company": "Cosnex",
                "time_period": "August 2025 - Present",
                "context": "Implemented a startup landing page frontend.",
                "problem": "The initial generated implementation required layout refinement.",
                "role": "Frontend developer",
                "actions": ["Refined the layout and modularized the component structure."],
                "technologies": ["Vue"],
                "impact": [],
                "metrics": [],
                "role_types": ["frontend"],
                "skills": ["frontend development", "code modularization"],
                "domain_keywords": ["startup"],
                "possible_resume_angles": ["Frontend implementation and code quality"],
                "evidence": {"action_lines": [], "metric_lines": [], "technology_lines": []},
                "evidence_lines": [],
                "draft_bullets": [],
                "truth_constraints": [],
                "uncertain_points": ["Confirm the deployment outcome."],
                "confidence": {
                    "metrics": "low",
                    "tools": "high",
                    "ownership": "medium",
                    "impact": "low",
                },
                "usable_for": ["frontend"],
            }

        evidence = ExtractedEvidence(
            technology_lines=[raw_line],
            technologies=["Vue"],
            evidence_lines=[raw_line],
        )
        draft = AIExperienceStructurer(
            response_provider=response_provider,
            model="fake-model",
        ).structure(
            clean_note=raw_line,
            draft_id="experience_test",
            evidence=evidence,
        )

        self.assertEqual(draft["actions"], ["Refined the layout and modularized the component structure."])
        self.assertEqual(draft["skills"], ["frontend development", "code modularization"])
        self.assertEqual(draft["role_types"], ["frontend"])
        self.assertEqual(draft["technologies"], ["Vue"])
        self.assertEqual(draft["evidence_lines"], [raw_line])
        self.assertNotIn("React", draft["technologies"])


if __name__ == "__main__":
    unittest.main()
