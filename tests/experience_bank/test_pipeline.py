from __future__ import annotations

import os
import unittest
from unittest.mock import patch

from resume_agent.experience_bank.config import EXPERIENCE_MODE_ENV_VAR, OPENAI_API_KEY_ENV_VAR
from resume_agent.experience_bank.evidence import ExtractedEvidence
from resume_agent.experience_bank.ingestion import RuleBasedExperienceStructurer
from resume_agent.experience_bank.openai_provider import OpenAIProviderError
from resume_agent.experience_bank.pipeline import ExperienceIngestionPipeline


RAW_NOTE = (
    "Title: API Project\n"
    "Company: Sample Lab\n"
    "Built a Python REST API and tested the workflow with a team.\n"
)


class PipelineTests(unittest.TestCase):
    def test_auto_without_key_warns_and_uses_local_fallback(self) -> None:
        warnings = []
        with patch.dict(os.environ, {}, clear=True):
            draft = ExperienceIngestionPipeline(warning_handler=warnings.append).structure(
                RAW_NOTE,
                draft_id="experience_test",
            )

        self.assertEqual(draft["source"]["structurer"], "rule_based")
        self.assertIn("Using local Experience Bank fallback", warnings[0])

    def test_ai_mode_requires_api_key(self) -> None:
        with patch.dict(os.environ, {EXPERIENCE_MODE_ENV_VAR: "ai"}, clear=True):
            with self.assertRaisesRegex(ValueError, "OPENAI_API_KEY is required"):
                ExperienceIngestionPipeline().structure(RAW_NOTE, draft_id="experience_test")

    def test_rejects_invalid_internal_mode(self) -> None:
        with self.assertRaisesRegex(ValueError, "Invalid Experience Bank ingestion mode"):
            ExperienceIngestionPipeline(mode="invalid").structure(
                RAW_NOTE,
                draft_id="experience_test",
            )

    def test_local_mode_ignores_api_key_and_uses_fallback(self) -> None:
        with patch.dict(
            os.environ,
            {
                EXPERIENCE_MODE_ENV_VAR: "local",
                OPENAI_API_KEY_ENV_VAR: "fake-key",
            },
            clear=True,
        ):
            draft = ExperienceIngestionPipeline().structure(RAW_NOTE, draft_id="experience_test")

        self.assertEqual(draft["source"]["structurer"], "rule_based")

    def test_auto_with_key_falls_back_when_openai_request_fails(self) -> None:
        warnings = []
        with patch.dict(os.environ, {OPENAI_API_KEY_ENV_VAR: "fake-key"}, clear=True):
            draft = ExperienceIngestionPipeline(
                ai_structurer=_FailingAIStructurer(),
                warning_handler=warnings.append,
            ).structure(
                RAW_NOTE,
                draft_id="experience_test",
            )

        self.assertEqual(draft["source"]["structurer"], "rule_based")
        self.assertIn("simulated API failure", warnings[0])

    def test_guardrail_rejects_unsupported_ai_technology(self) -> None:
        local_draft = RuleBasedExperienceStructurer().structure(
            RAW_NOTE,
            draft_id="experience_test",
        )
        local_draft["source"]["structurer"] = "openai"
        local_draft["source"]["model"] = "fake-model"
        local_draft["technologies"].append("Kubernetes")
        with patch.dict(
            os.environ,
            {
                EXPERIENCE_MODE_ENV_VAR: "ai",
                OPENAI_API_KEY_ENV_VAR: "fake-key",
            },
            clear=True,
        ):
            with self.assertRaisesRegex(ValueError, "unsupported technologies"):
                ExperienceIngestionPipeline(
                    ai_structurer=_FakeAIStructurer(local_draft)
                ).structure(RAW_NOTE, draft_id="experience_test")

    def test_guardrail_rejects_unsupported_ai_metric(self) -> None:
        local_draft = RuleBasedExperienceStructurer().structure(
            RAW_NOTE,
            draft_id="experience_test",
        )
        local_draft["source"]["structurer"] = "openai"
        local_draft["source"]["model"] = "fake-model"
        local_draft["metrics"].append("Reduced latency by 90%.")
        with patch.dict(
            os.environ,
            {
                EXPERIENCE_MODE_ENV_VAR: "ai",
                OPENAI_API_KEY_ENV_VAR: "fake-key",
            },
            clear=True,
        ):
            with self.assertRaisesRegex(ValueError, "unsupported metrics"):
                ExperienceIngestionPipeline(
                    ai_structurer=_FakeAIStructurer(local_draft)
                ).structure(RAW_NOTE, draft_id="experience_test")

    def test_guardrail_accepts_vite_when_raw_note_explicitly_mentions_it(self) -> None:
        raw_note = (
            "Title: Frontend Component\n"
            "Company: Sample Lab\n"
            "Built a Vue and Vite component and tested the workflow with a team.\n"
        )
        local_draft = RuleBasedExperienceStructurer().structure(
            raw_note,
            draft_id="experience_test",
        )
        local_draft["source"]["structurer"] = "openai"
        local_draft["source"]["model"] = "fake-model"
        with patch.dict(
            os.environ,
            {
                EXPERIENCE_MODE_ENV_VAR: "ai",
                OPENAI_API_KEY_ENV_VAR: "fake-key",
            },
            clear=True,
        ):
            draft = ExperienceIngestionPipeline(
                ai_structurer=_FakeAIStructurer(local_draft)
            ).structure(raw_note, draft_id="experience_test")

        self.assertEqual(draft["technologies"], ["Vue", "Vite"])


class _FakeAIStructurer:
    name = "openai"
    model = "fake-model"

    def __init__(self, draft: dict[str, object]) -> None:
        self.draft = draft

    def structure(
        self,
        clean_note: str,
        draft_id: str,
        evidence: ExtractedEvidence,
    ) -> dict[str, object]:
        return self.draft


class _FailingAIStructurer:
    name = "openai"
    model = "fake-model"

    def structure(
        self,
        clean_note: str,
        draft_id: str,
        evidence: ExtractedEvidence,
    ) -> dict[str, object]:
        raise OpenAIProviderError("simulated API failure")


if __name__ == "__main__":
    unittest.main()
