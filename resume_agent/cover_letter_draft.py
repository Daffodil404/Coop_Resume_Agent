from __future__ import annotations

from datetime import date
from pathlib import Path
from typing import Any

from jinja2 import Environment, FileSystemLoader, StrictUndefined


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
    cover_letter_decision: dict[str, Any],
    output_path: Path,
) -> dict[str, Any]:
    """Render an editable deterministic LaTeX draft when generation is recommended."""
    if cover_letter_decision.get("should_generate") is not True:
        return {
            "generated": False,
            "output_path": None,
            "generation_mode": "template_based_mock",
            "reason": "Cover letter generation was skipped by the decision step.",
        }

    company = str(jd_analysis.get("company") or "Company")
    role_title = str(jd_analysis.get("role_title") or "the advertised role")
    recommended_base = str(resume_strategy.get("recommended_resume_base") or "general")
    body_paragraph = BODY_TEMPLATES.get(recommended_base, DEFAULT_BODY)
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
        opening_paragraph=(
            f"I am writing to apply for the {escape_latex(role_title)} position at "
            f"{escape_latex(company)}."
        ),
        body_paragraph=escape_latex(body_paragraph),
        closing_paragraph=(
            "Thank you for considering my application. I would welcome the opportunity to "
            "discuss how my background may align with the role."
        ),
    )
    output_path.write_text(rendered, encoding="utf-8")
    return {
        "generated": True,
        "output_path": str(output_path),
        "generation_mode": "template_based_mock",
        "reason": "Generated an editable deterministic LaTeX cover letter draft.",
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
