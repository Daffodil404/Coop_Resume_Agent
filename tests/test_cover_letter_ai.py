from __future__ import annotations

import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

import yaml

from resume_agent.ai.model_router import ModelConfig
from resume_agent.cover_letter_ai import (
    COVER_LETTER_RESPONSE_SCHEMA,
    CoverLetterGenerator,
    load_approved_experience_entries,
    select_relevant_experience_entries,
)


class CoverLetterAITests(unittest.TestCase):
    def test_selects_relevant_approved_experience_entries(self) -> None:
        with TemporaryDirectory() as temp_dir:
            data_root = Path(temp_dir)
            bank_path = data_root / "data/private/experience_bank.yaml"
            bank_path.parent.mkdir(parents=True)
            bank_path.write_text(
                yaml.safe_dump(
                    {
                        "version": 1,
                        "entries": [
                            {
                                "id": "experience_frontend",
                                "status": "approved",
                                "title": "I18N automation",
                                "skills": ["Internationalization", "Server-side rendering"],
                                "usable_for": ["Frontend engineering"],
                                "actions": ["Built a string extraction workflow."],
                            },
                            {
                                "id": "experience_data",
                                "status": "approved",
                                "title": "ETL pipeline",
                                "skills": ["ETL", "data processing"],
                                "usable_for": ["Data engineering"],
                                "actions": ["Built a production ETL pipeline."],
                            },
                        ],
                    },
                    sort_keys=False,
                    allow_unicode=True,
                ),
                encoding="utf-8",
            )

            selected = select_relevant_experience_entries(
                jd_analysis={"role_title": "Frontend Engineer", "tools_and_technologies": ["SSR"]},
                resume_strategy={"recommended_resume_base": "frontend"},
                resume_selection={},
                data_root=data_root,
                limit=1,
            )

        self.assertEqual(len(selected), 1)
        self.assertEqual(selected[0]["id"], "experience_frontend")

    def test_loads_only_approved_entries(self) -> None:
        with TemporaryDirectory() as temp_dir:
            data_root = Path(temp_dir)
            bank_path = data_root / "data/private/experience_bank.yaml"
            bank_path.parent.mkdir(parents=True)
            bank_path.write_text(
                yaml.safe_dump(
                    {
                        "version": 1,
                        "entries": [
                            {"id": "approved_one", "status": "approved"},
                            {"id": "draft_one", "status": "draft"},
                        ],
                    },
                    sort_keys=False,
                ),
                encoding="utf-8",
            )

            entries = load_approved_experience_entries(data_root=data_root)

        self.assertEqual([entry["id"] for entry in entries], ["approved_one"])

    def test_generates_cover_letter_prompt_payload_via_provider(self) -> None:
        captured: dict[str, object] = {}

        def fake_provider(system_prompt: str, user_prompt: str) -> dict[str, object]:
            captured["system_prompt"] = system_prompt
            captured["user_prompt"] = user_prompt
            return {
                "opening_paragraph": "Opening",
                "body_paragraphs": ["Body one", "Body two"],
                "closing_paragraph": "Closing",
                "evidence_entry_ids": ["experience_one"],
            }

        with TemporaryDirectory() as temp_dir:
            data_root = Path(temp_dir)
            bank_path = data_root / "data/private/experience_bank.yaml"
            bank_path.parent.mkdir(parents=True)
            bank_path.write_text(
                yaml.safe_dump(
                    {
                        "version": 1,
                        "entries": [{"id": "experience_one", "status": "approved", "skills": ["Python"]}],
                    },
                    sort_keys=False,
                ),
                encoding="utf-8",
            )
            generated = CoverLetterGenerator(
                response_provider=fake_provider,
                model_config=ModelConfig(task_key="cover_letter_writer", model="gpt-test"),
                data_root=data_root,
            ).generate(
                jd_analysis={"company": "Example", "role_title": "Software Engineer"},
                resume_strategy={"recommended_resume_base": "sde"},
                resume_selection={"selected_resume_pdf": "/tmp/example.pdf"},
                data_root=data_root,
            )

        self.assertEqual(generated["generation_source"]["model"], "gpt-test")
        self.assertIn("Software Engineer", str(captured["user_prompt"]))
        self.assertIn("experience_one", str(captured["user_prompt"]))

    def test_cover_letter_schema_requires_two_body_paragraphs(self) -> None:
        body_schema = COVER_LETTER_RESPONSE_SCHEMA["properties"]["body_paragraphs"]
        self.assertEqual(body_schema["minItems"], 2)
        self.assertEqual(body_schema["maxItems"], 2)


if __name__ == "__main__":
    unittest.main()
