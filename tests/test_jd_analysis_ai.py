from __future__ import annotations

import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

from resume_agent.ai.model_router import ModelConfig
from resume_agent.cli import analyze_job_description
from resume_agent.experience_bank.openai_provider import OpenAIProviderError
from resume_agent.openai_jd_analysis import JD_ANALYSIS_RESPONSE_SCHEMA, OpenAIJdAnalysisClient


class JdAnalysisAITests(unittest.TestCase):
    def test_openai_jd_analysis_client_returns_structured_analysis(self) -> None:
        captured: dict[str, object] = {}

        def fake_provider(system_prompt: str, user_prompt: str) -> dict[str, object]:
            captured["system_prompt"] = system_prompt
            captured["user_prompt"] = user_prompt
            return {
                "company": "Mondelez International",
                "role_title": "Digitization Data Analyst",
                "location": "Hybrid",
                "work_term": "4-month",
                "start_date": "Fall 2026",
                "role_type": "Co-op",
                "core_responsibilities": ["Develop Power BI dashboards."],
                "core_requirements": ["Proven experience as a Power BI Developer."],
                "nice_to_have": ["Relevant certifications are a plus."],
                "tools_and_technologies": ["Power BI", "SQL", "Excel"],
                "domain": "Data / Analytics",
                "cover_letter_required": True,
                "seniority_level": "Student / Intern",
            }

        client = OpenAIJdAnalysisClient(
            response_provider=fake_provider,
            model_config=ModelConfig(task_key="jd_analysis", model="gpt-test"),
        )
        analysis = client.analyze_jd(
            "Application Documents Required: Cover Letter, Resume, Unofficial Transcript"
        )

        self.assertEqual(analysis["company"], "Mondelez International")
        self.assertTrue(analysis["cover_letter_required"])
        self.assertEqual(analysis["analysis_source"], "openai")
        self.assertEqual(analysis["analysis_model"], "gpt-test")
        self.assertIn("Application Documents Required", str(captured["user_prompt"]))

    def test_cli_uses_openai_jd_analysis_when_available(self) -> None:
        fake_client = type(
            "FakeClient",
            (),
            {
                "model": "gpt-test",
                "analyze_jd": lambda self, _clean_jd: {
                    "company": "Mondelez International",
                    "role_title": "Digitization Data Analyst",
                    "location": "Hybrid",
                    "work_term": "4-month",
                    "start_date": "Fall 2026",
                    "role_type": "Co-op",
                    "core_responsibilities": [],
                    "core_requirements": [],
                    "nice_to_have": [],
                    "tools_and_technologies": [],
                    "domain": "Data / Analytics",
                    "cover_letter_required": True,
                    "seniority_level": "Student / Intern",
                    "analysis_source": "openai",
                },
            },
        )()
        with patch("resume_agent.cli.should_use_ai_jd_analysis", return_value=True):
            with patch("resume_agent.cli.OpenAIJdAnalysisClient", return_value=fake_client) as client_class:
                analysis = analyze_job_description(
                    "Application Documents Required: Cover Letter",
                    data_root=Path("."),
                )

        self.assertTrue(analysis["cover_letter_required"])
        client_class.assert_called_once()

    def test_cli_falls_back_to_local_jd_analysis_when_openai_fails(self) -> None:
        with patch("resume_agent.cli.should_use_ai_jd_analysis", return_value=True):
            with patch(
                "resume_agent.cli.OpenAIJdAnalysisClient.analyze_jd",
                side_effect=OpenAIProviderError("simulated API failure"),
            ):
                analysis = analyze_job_description(
                    "Position Title: Data Analyst\nLocation: Hybrid",
                    data_root=Path("."),
                )

        self.assertEqual(analysis["analysis_source"], "mock")

    def test_jd_analysis_schema_supports_nullable_cover_letter_required(self) -> None:
        schema = JD_ANALYSIS_RESPONSE_SCHEMA["properties"]["cover_letter_required"]
        self.assertEqual(schema["anyOf"][0]["type"], "boolean")
        self.assertEqual(schema["anyOf"][1]["type"], "null")


if __name__ == "__main__":
    unittest.main()
