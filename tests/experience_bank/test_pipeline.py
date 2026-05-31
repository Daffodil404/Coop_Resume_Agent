from __future__ import annotations

import os
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

from resume_agent.experience_bank.config import EXPERIENCE_MODE_ENV_VAR, OPENAI_API_KEY_ENV_VAR
from resume_agent.experience_bank.evidence import EvidenceExtractor, ExtractedEvidence
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

    def test_guardrail_removes_ai_technology_not_found_in_raw_note(self) -> None:
        local_draft = RuleBasedExperienceStructurer().structure(
            RAW_NOTE,
            draft_id="experience_test",
        )
        local_draft["source"]["structurer"] = "openai"
        local_draft["source"]["model"] = "fake-model"
        local_draft["technologies"].append("Kubernetes")
        warnings = []
        with patch.dict(
            os.environ,
            {
                EXPERIENCE_MODE_ENV_VAR: "ai",
                OPENAI_API_KEY_ENV_VAR: "fake-key",
            },
            clear=True,
        ):
            draft = ExperienceIngestionPipeline(
                ai_structurer=_FakeAIStructurer(local_draft),
                warning_handler=warnings.append,
            ).structure(RAW_NOTE, draft_id="experience_test")

        self.assertNotIn("Kubernetes", draft["technologies"])
        self.assertIn("not found in the raw note", draft["uncertain_points"][-1])
        self.assertIn("Removed AI-extracted technologies", warnings[-1])

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
            with self.assertRaisesRegex(ValueError, "metrics not found in deterministic evidence"):
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

    def test_new_raw_note_technology_can_be_added_to_local_dictionary(self) -> None:
        raw_note = (
            "Title: Landing Page\n"
            "Company: Sample Lab\n"
            "Used CustomTool to implement and refine the frontend landing page.\n"
        )
        local_draft = RuleBasedExperienceStructurer().structure(
            raw_note,
            draft_id="experience_test",
        )
        local_draft["source"]["structurer"] = "openai"
        local_draft["source"]["model"] = "fake-model"
        local_draft["technologies"].append("CustomTool")
        with TemporaryDirectory() as temp_dir:
            local_keywords_path = Path(temp_dir) / "technologies.local.json"
            with patch.dict(
                os.environ,
                {
                    EXPERIENCE_MODE_ENV_VAR: "ai",
                    OPENAI_API_KEY_ENV_VAR: "fake-key",
                },
                clear=True,
            ):
                draft = ExperienceIngestionPipeline(
                    ai_structurer=_FakeAIStructurer(local_draft),
                    evidence_extractor=EvidenceExtractor(local_keywords_path=local_keywords_path),
                    new_technology_handler=lambda technology: True,
                ).structure(raw_note, draft_id="experience_test")

            saved_keywords = local_keywords_path.read_text(encoding="utf-8")

        self.assertEqual(draft["technologies"], ["CustomTool"])
        self.assertIn("CustomTool", saved_keywords)
        self.assertEqual(
            draft["evidence"]["technology_lines"],
            ["Used CustomTool to implement and refine the frontend landing page."],
        )

    def test_new_raw_note_technology_continues_when_dictionary_update_is_declined(self) -> None:
        raw_note = (
            "Title: Landing Page\n"
            "Company: Sample Lab\n"
            "Used CustomTool to implement and refine the frontend landing page.\n"
        )
        local_draft = RuleBasedExperienceStructurer().structure(
            raw_note,
            draft_id="experience_test",
        )
        local_draft["source"]["structurer"] = "openai"
        local_draft["source"]["model"] = "fake-model"
        local_draft["technologies"].append("CustomTool")
        with patch.dict(
            os.environ,
            {
                EXPERIENCE_MODE_ENV_VAR: "ai",
                OPENAI_API_KEY_ENV_VAR: "fake-key",
            },
            clear=True,
        ):
            draft = ExperienceIngestionPipeline(
                ai_structurer=_FakeAIStructurer(local_draft),
                new_technology_handler=lambda technology: False,
            ).structure(raw_note, draft_id="experience_test")

        self.assertEqual(draft["technologies"], ["CustomTool"])

    def test_mixed_language_evidence_supports_figma_and_mcp_separately(self) -> None:
        raw_note = (
            "Company: Cosnex\n"
            "This startup project focused on a frontend landing page.\n"
            "使用了 Figma 的 MCP 来快速完成样式实现。\n"
            "Implemented the landing page frontend, refined the layout, and optimized the code structure.\n"
        )
        local_draft = RuleBasedExperienceStructurer().structure(
            raw_note,
            draft_id="experience_test",
        )
        local_draft["source"]["structurer"] = "openai"
        local_draft["source"]["model"] = "fake-model"
        local_draft["technologies"].append("Figma MCP")
        warnings = []
        with patch.dict(
            os.environ,
            {
                EXPERIENCE_MODE_ENV_VAR: "ai",
                OPENAI_API_KEY_ENV_VAR: "fake-key",
            },
            clear=True,
        ):
            draft = ExperienceIngestionPipeline(
                ai_structurer=_FakeAIStructurer(local_draft),
                warning_handler=warnings.append,
                new_technology_handler=lambda technology: False,
            ).structure(raw_note, draft_id="experience_test")

        self.assertIn("Figma", draft["technologies"])
        self.assertIn("MCP", draft["technologies"])
        self.assertNotIn("Figma MCP", draft["technologies"])
        self.assertNotIn("React", draft["technologies"])
        self.assertNotIn("TypeScript", draft["technologies"])
        self.assertNotIn("Next.js", draft["technologies"])
        self.assertNotIn("Tailwind", draft["technologies"])
        self.assertNotIn("CSS", draft["technologies"])
        self.assertNotIn(
            "Removed AI-extracted technologies that were not found in the raw note: MCP",
            draft["uncertain_points"],
        )
        self.assertIn("使用了 Figma 的 MCP 来快速完成样式实现。", draft["evidence"]["technology_lines"])
        self.assertNotIn("Removed AI-extracted technologies", " ".join(warnings))


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
