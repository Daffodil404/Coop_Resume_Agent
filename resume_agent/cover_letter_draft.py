from __future__ import annotations

from datetime import date
from pathlib import Path
from typing import Any

from jinja2 import Environment, FileSystemLoader, StrictUndefined

from .cover_letter_ai import CoverLetterGenerator, should_use_ai_cover_letter_generation
from .experience_bank.openai_provider import OpenAIProviderError


TEMPLATE_ROOT = Path(__file__).resolve().parent.parent / "templates"
TEMPLATE_NAME = "cover_letter.tex.j2"

BODY_TEMPLATES = {
    "ai_engineer": (
        "The role's AI and machine-learning focus makes it useful to provide context alongside "
        "the selected resume. This draft is intended to highlight relevant technical work and "
        "should be edited to add only verified examples."
    ),
    "data_engineer": (
        "The role's data-engineering focus makes it useful to clarify how the selected resume "
        "relates to data workflows, systems, and tools. This draft should be edited to add only "
        "verified examples."
    ),
    "sde": (
        "The selected software-development resume provides the primary application context. "
        "This draft can be edited to identify the most relevant verified technical examples for "
        "the role."
    ),
    "frontend": (
        "The role's frontend focus makes it useful to identify the most relevant verified "
        "interface and web-development examples from the selected resume."
    ),
    "mobile": (
        "The role's mobile focus makes it useful to identify the most relevant verified mobile "
        "development examples from the selected resume."
    ),
    "qa_testing": (
        "The role's quality and testing focus makes it useful to identify the most relevant "
        "verified testing examples from the selected resume."
    ),
}

DEFAULT_BODY = (
    "The selected resume provides the primary application context. This draft should be edited "
    "to add only verified examples that are relevant to the role."
)


def render_cover_letter_draft(
    jd_analysis: dict[str, Any],
    resume_strategy: dict[str, Any],
    resume_selection: dict[str, Any],
    cover_letter_decision: dict[str, Any],
    output_path: Path,
    data_root: Path = Path("."),
) -> dict[str, Any]:
    """Render a cover letter draft with AI generation when available."""
    if cover_letter_decision.get("should_generate") is not True:
        return {
            "generated": False,
            "output_path": None,
            "generation_mode": "template_based_mock",
            "reason": "Cover letter generation was skipped by the decision step.",
        }

    company = str(jd_analysis.get("company") or "Company")
    role_title = str(jd_analysis.get("role_title") or "the advertised role")
    draft_content, generation_mode, generation_reason = _build_cover_letter_content(
        jd_analysis=jd_analysis,
        resume_strategy=resume_strategy,
        resume_selection=resume_selection,
        data_root=data_root,
    )
    environment = Environment(
        loader=FileSystemLoader(TEMPLATE_ROOT),
        undefined=StrictUndefined,
        autoescape=False,
        keep_trailing_newline=True,
    )
    template = environment.get_template(TEMPLATE_NAME)
    rendered = template.render(
        current_date=escape_latex(date.today().strftime("%B %d, %Y")),
        recipient_block=f"Hiring Team\\\\{escape_latex(company)}",
        opening_paragraph=escape_latex(draft_content["opening_paragraph"]),
        body_paragraphs=[escape_latex(paragraph) for paragraph in draft_content["body_paragraphs"]],
        closing_paragraph=escape_latex(draft_content["closing_paragraph"]),
    )
    output_path.write_text(rendered, encoding="utf-8")
    return {
        "generated": True,
        "output_path": str(output_path),
        "generation_mode": generation_mode,
        "reason": generation_reason,
        "evidence_entry_ids": draft_content.get("evidence_entry_ids", []),
        "role_title": role_title,
        "company": company,
    }


def escape_latex(text: str) -> str:
    """Escape common LaTeX special characters without double-escaping replacements."""
    replacements = {
        "\\": r"\textbackslash{}",
        "&": r"\&",
        "%": r"\%",
        "$": r"\$",
        "#": r"\#",
        "_": r"\_",
        "{": r"\{",
        "}": r"\}",
        "~": r"\textasciitilde{}",
        "^": r"\textasciicircum{}",
    }
    return "".join(replacements.get(character, character) for character in text)


def _build_cover_letter_content(
    jd_analysis: dict[str, Any],
    resume_strategy: dict[str, Any],
    resume_selection: dict[str, Any],
    data_root: Path,
) -> tuple[dict[str, Any], str, str]:
    if should_use_ai_cover_letter_generation():
        try:
            generated = CoverLetterGenerator().generate(
                jd_analysis=jd_analysis,
                resume_strategy=resume_strategy,
                resume_selection=resume_selection,
                data_root=data_root,
            )
            return (
                generated,
                "openai_grounded",
                "Generated a grounded cover letter draft with approved Experience Bank entries.",
            )
        except OpenAIProviderError as error:
            fallback_content = _build_fallback_cover_letter_content(jd_analysis, resume_strategy)
            return (
                fallback_content,
                "template_based_fallback",
                f"{error} Falling back to deterministic template content.",
            )
    fallback_content = _build_fallback_cover_letter_content(jd_analysis, resume_strategy)
    return (
        fallback_content,
        "template_based_mock",
        "OPENAI_API_KEY is not configured. Generated a deterministic cover letter draft.",
    )


def _build_fallback_cover_letter_content(
    jd_analysis: dict[str, Any],
    resume_strategy: dict[str, Any],
) -> dict[str, Any]:
    company = str(jd_analysis.get("company") or "the company")
    role_title = str(jd_analysis.get("role_title") or "the advertised role")
    recommended_base = str(resume_strategy.get("recommended_resume_base") or "general")
    body_paragraph = BODY_TEMPLATES.get(recommended_base, DEFAULT_BODY)
    return {
        "opening_paragraph": f"I am writing to apply for the {role_title} position at {company}.",
        "body_paragraphs": [body_paragraph, DEFAULT_BODY],
        "closing_paragraph": (
            "Thank you for considering my application. I would welcome the opportunity to "
            "discuss how my background may align with the role."
        ),
        "evidence_entry_ids": [],
    }
