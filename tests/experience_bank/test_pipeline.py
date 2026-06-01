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

    def test_grounded_taxonomy_and_qualitative_impact_for_wechat_pay_flow(self) -> None:
        raw_note = (
            "Company: Cosnex\n"
            "This startup project needed to support domestic payments through WeChat Pay.\n"
            "I obtained WeChat merchant certification and configured certificates on the server.\n"
            "The backend prepared the payment amount and generated a payment link.\n"
            "The frontend rendered the link as a QR code.\n"
            "Users scanned the QR code with WeChat to invoke payment.\n"
            "The backend polled payment status and the frontend redirected after successful polling.\n"
            "The backend recorded transaction data into the database.\n"
            "Frontend stack: Next.js and TypeScript.\n"
            "Backend stack: Python.\n"
            "We also mentioned Dokploy for deployment.\n"
        )
        ai_draft = {
            "id": "experience_test",
            "status": "draft",
            "source": {
                "type": "raw_experience_note",
                "created_at": "2026-05-31T00:00:00Z",
                "structurer": "openai",
                "model": "fake-model",
            },
            "title": "WeChat Pay Integration",
            "company": "Cosnex",
            "time_period": None,
            "context": "Implemented a payment integration for a startup product.",
            "problem": "The product needed domestic payment support through WeChat Pay.",
            "role": "Full-stack engineer",
            "actions": [
                "Configured payment certificates and implemented the end-to-end QR-code payment workflow."
            ],
            "technologies": ["Python"],
            "impact": [],
            "metrics": [],
            "role_types": [],
            "skills": [],
            "domain_keywords": [],
            "possible_resume_angles": [],
            "evidence": {"action_lines": [], "metric_lines": [], "technology_lines": []},
            "evidence_lines": [],
            "draft_bullets": [],
            "truth_constraints": [],
            "uncertain_points": [],
            "confidence": {
                "metrics": "low",
                "tools": "low",
                "ownership": "medium",
                "impact": "low",
            },
            "usable_for": [],
        }
        with patch.dict(
            os.environ,
            {
                EXPERIENCE_MODE_ENV_VAR: "ai",
                OPENAI_API_KEY_ENV_VAR: "fake-key",
            },
            clear=True,
        ):
            draft = ExperienceIngestionPipeline(
                ai_structurer=_FakeAIStructurer(ai_draft)
            ).structure(raw_note, draft_id="experience_test")

        self.assertIn("Python", draft["technologies"])
        self.assertIn("Next.js", draft["technologies"])
        self.assertIn("TypeScript", draft["technologies"])
        self.assertIn("Dokploy", draft["technologies"])
        self.assertIn("WeChat Pay", draft["technologies"])
        self.assertNotIn("React", draft["technologies"])
        self.assertNotIn("Tailwind", draft["technologies"])
        self.assertIn("fullstack", draft["role_types"])
        self.assertIn("software_engineering", draft["role_types"])
        self.assertIn("frontend", draft["role_types"])
        self.assertIn("backend", draft["role_types"])
        self.assertIn("payment integration", draft["skills"])
        self.assertIn("third-party API integration", draft["skills"])
        self.assertIn("QR-code payment flow implementation", draft["skills"])
        self.assertIn("frontend-backend integration", draft["skills"])
        self.assertIn("backend polling", draft["skills"])
        self.assertIn("transaction data persistence", draft["skills"])
        self.assertIn("certificate configuration", draft["skills"])
        self.assertIn("full-stack feature implementation", draft["skills"])
        self.assertIn("payment integration", draft["domain_keywords"])
        self.assertIn("WeChat Pay", draft["domain_keywords"])
        self.assertIn("domestic payments", draft["domain_keywords"])
        self.assertIn("QR-code payment", draft["domain_keywords"])
        self.assertIn("transaction processing", draft["domain_keywords"])
        self.assertIn("Full-stack payment integration with WeChat Pay", draft["possible_resume_angles"])
        self.assertIn("QR-code payment flow implementation", draft["possible_resume_angles"])
        self.assertIn("Frontend-backend payment workflow integration", draft["possible_resume_angles"])
        self.assertIn("Backend polling and transaction persistence", draft["possible_resume_angles"])
        self.assertIn("Certificate-based payment service setup", draft["possible_resume_angles"])
        self.assertIn(
            "Enabled domestic users to complete payments through a WeChat Pay QR-code flow.",
            draft["impact"],
        )
        self.assertIn(
            "Supported payment status tracking and transaction data recording after successful polling.",
            draft["impact"],
        )
        self.assertEqual(draft["metrics"], [])
        self.assertEqual(
            draft["evidence"]["technology_lines"],
            [
                "This startup project needed to support domestic payments through WeChat Pay.",
                "Frontend stack: Next.js and TypeScript.",
                "Backend stack: Python.",
                "We also mentioned Dokploy for deployment.",
            ],
        )
        self.assertIn("fullstack", draft["usable_for"])
        self.assertIn("software_engineering", draft["usable_for"])
        self.assertIn("backend", draft["usable_for"])
        self.assertIn("frontend", draft["usable_for"])


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
