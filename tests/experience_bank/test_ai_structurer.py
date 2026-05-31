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
        self.assertIn("partial guardrail hints", captured_prompts[0])
        self.assertIn("Do not leave semantically extractable fields empty", captured_prompts[1])
        self.assertIn("Built a Python API.", captured_prompts[1])


if __name__ == "__main__":
    unittest.main()
