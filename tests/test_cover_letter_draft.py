from __future__ import annotations

import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

from resume_agent.cover_letter_draft import escape_latex, render_cover_letter_draft


class CoverLetterDraftTests(unittest.TestCase):
    def test_renders_ai_generated_latex_cover_letter_when_available(self) -> None:
        with TemporaryDirectory() as temp_dir:
            output_path = Path(temp_dir) / "cover_letter.tex"
            with patch(
                "resume_agent.cover_letter_draft.should_use_ai_cover_letter_generation",
                return_value=True,
            ):
                with patch(
                    "resume_agent.cover_letter_draft.CoverLetterGenerator.generate",
                    return_value={
                        "opening_paragraph": "I am applying for the AI Engineer role at Test Company.",
                        "body_paragraphs": [
                            "My I18N automation work improved developer experience and multilingual support.",
                            "My ETL pipeline experience aligns with production data workflows and monitoring.",
                        ],
                        "closing_paragraph": "I would welcome the opportunity to discuss my fit.",
                        "evidence_entry_ids": ["experience_one", "experience_two"],
                    },
                ):
                    generation = render_cover_letter_draft(
                        jd_analysis={"company": "Test Company", "role_title": "AI Engineer"},
                        resume_strategy={"recommended_resume_base": "ai_engineer"},
                        resume_selection={"selected_resume_pdf": "/tmp/resume.pdf"},
                        cover_letter_decision={"should_generate": True},
                        output_path=output_path,
                    )
                rendered = output_path.read_text()

        self.assertTrue(generation["generated"])
        self.assertEqual(generation["generation_mode"], "openai_grounded")
        self.assertEqual(generation["evidence_entry_ids"], ["experience_one", "experience_two"])
        self.assertIn(r"\documentclass[11pt]{letter}", rendered)
        self.assertIn(r"\opening{Dear Hiring Team,}", rendered)
        self.assertIn(r"\closing{Sincerely,\\Yanyu Wu}", rendered)
        self.assertIn("I18N automation work improved developer experience", rendered)

    def test_skips_rendering_when_generation_is_not_requested(self) -> None:
        with TemporaryDirectory() as temp_dir:
            output_path = Path(temp_dir) / "cover_letter.tex"
            generation = render_cover_letter_draft(
                jd_analysis={},
                resume_strategy={},
                resume_selection={},
                cover_letter_decision={"should_generate": False},
                output_path=output_path,
            )

            self.assertFalse(output_path.exists())

        self.assertFalse(generation["generated"])
        self.assertIsNone(generation["output_path"])

    def test_escapes_latex_special_characters(self) -> None:
        self.assertEqual(
            escape_latex(r"A&B%$#_{}~^\\"),
            r"A\&B\%\$\#\_\{\}\textasciitilde{}\textasciicircum{}\textbackslash{}\textbackslash{}",
        )

    def test_uses_different_body_templates_for_resume_bases(self) -> None:
        with TemporaryDirectory() as temp_dir:
            temp_root = Path(temp_dir)
            ai_path = temp_root / "ai.tex"
            mobile_path = temp_root / "mobile.tex"
            with patch(
                "resume_agent.cover_letter_draft.should_use_ai_cover_letter_generation",
                return_value=False,
            ):
                render_cover_letter_draft(
                    jd_analysis={},
                    resume_strategy={"recommended_resume_base": "ai_engineer"},
                    resume_selection={},
                    cover_letter_decision={"should_generate": True},
                    output_path=ai_path,
                )
                render_cover_letter_draft(
                    jd_analysis={},
                    resume_strategy={"recommended_resume_base": "mobile"},
                    resume_selection={},
                    cover_letter_decision={"should_generate": True},
                    output_path=mobile_path,
                )

            ai_rendered = ai_path.read_text()
            mobile_rendered = mobile_path.read_text()

        self.assertIn("AI and machine-learning focus", ai_rendered)
        self.assertIn("mobile focus", mobile_rendered)
        self.assertNotEqual(ai_rendered, mobile_rendered)

    def test_escapes_company_and_role_in_rendered_latex(self) -> None:
        with TemporaryDirectory() as temp_dir:
            output_path = Path(temp_dir) / "cover_letter.tex"
            with patch(
                "resume_agent.cover_letter_draft.should_use_ai_cover_letter_generation",
                return_value=False,
            ):
                render_cover_letter_draft(
                    jd_analysis={"company": "A&B", "role_title": "R&D_Engineer"},
                    resume_strategy={"recommended_resume_base": "sde"},
                    resume_selection={},
                    cover_letter_decision={"should_generate": True},
                    output_path=output_path,
                )
            rendered = output_path.read_text()

        self.assertIn(r"A\&B", rendered)
        self.assertIn(r"R\&D\_Engineer", rendered)

    def test_falls_back_to_template_when_ai_generation_fails(self) -> None:
        with TemporaryDirectory() as temp_dir:
            output_path = Path(temp_dir) / "cover_letter.tex"
            with patch(
                "resume_agent.cover_letter_draft.should_use_ai_cover_letter_generation",
                return_value=True,
            ):
                with patch(
                    "resume_agent.cover_letter_draft.CoverLetterGenerator.generate",
                    side_effect=RuntimeError("provider failure"),
                ):
                    with self.assertRaisesRegex(RuntimeError, "provider failure"):
                        render_cover_letter_draft(
                            jd_analysis={"company": "Test Company", "role_title": "Software Developer"},
                            resume_strategy={"recommended_resume_base": "sde"},
                            resume_selection={},
                            cover_letter_decision={"should_generate": True},
                            output_path=output_path,
                        )


if __name__ == "__main__":
    unittest.main()
