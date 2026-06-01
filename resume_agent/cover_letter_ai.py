from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Callable

import yaml

from .experience_bank.config import get_openai_model, has_openai_api_key
from .experience_bank.openai_provider import OpenAIProviderError, OpenAIResponsesProvider


PROMPT_ROOT = Path(__file__).resolve().parent.parent / "prompts"
EXPERIENCE_BANK_PATH = Path("data/private/experience_bank.yaml")


class CoverLetterGenerator:
    """Generate grounded cover-letter paragraphs from JD context and approved experiences."""

    name = "openai"

    def __init__(
        self,
        response_provider: Callable[[str, str], dict[str, object]] | None = None,
        model: str | None = None,
    ) -> None:
        provider = response_provider or OpenAIResponsesProvider(
            model=model,
            schema_name="cover_letter_draft",
            schema=COVER_LETTER_RESPONSE_SCHEMA,
        )
        self.response_provider = provider
        self.model = model or getattr(provider, "model", None)

    def generate(
        self,
        jd_analysis: dict[str, Any],
        resume_strategy: dict[str, Any],
        resume_selection: dict[str, Any],
        data_root: Path = Path("."),
    ) -> dict[str, Any]:
        approved_entries = select_relevant_experience_entries(
            jd_analysis=jd_analysis,
            resume_strategy=resume_strategy,
            resume_selection=resume_selection,
            data_root=data_root,
        )
        system_prompt = _load_prompt("cover_letter_writer.system.md")
        user_template = _load_prompt("cover_letter_writer.user.md")
        user_prompt = user_template.format(
            jd_analysis=json.dumps(jd_analysis, ensure_ascii=False, indent=2, sort_keys=True),
            resume_strategy=json.dumps(resume_strategy, ensure_ascii=False, indent=2, sort_keys=True),
            resume_selection=json.dumps(resume_selection, ensure_ascii=False, indent=2, sort_keys=True),
            approved_experience_entries=json.dumps(
                approved_entries,
                ensure_ascii=False,
                indent=2,
                sort_keys=True,
            ),
        )
        generated = self.response_provider(system_prompt, user_prompt)
        generated["generation_source"] = {
            "type": self.name,
            "model": self.model,
        }
        return generated


def should_use_ai_cover_letter_generation() -> bool:
    return has_openai_api_key()


def select_relevant_experience_entries(
    jd_analysis: dict[str, Any],
    resume_strategy: dict[str, Any],
    resume_selection: dict[str, Any],
    data_root: Path = Path("."),
    limit: int = 4,
) -> list[dict[str, Any]]:
    approved_entries = load_approved_experience_entries(data_root=data_root)
    if not approved_entries:
        return []
    query_tokens = _build_query_tokens(jd_analysis, resume_strategy, resume_selection)
    ranked_entries = sorted(
        approved_entries,
        key=lambda entry: (_score_entry(entry, query_tokens), entry.get("id", "")),
        reverse=True,
    )
    selected_entries = [entry for entry in ranked_entries if _score_entry(entry, query_tokens) > 0]
    if not selected_entries:
        selected_entries = ranked_entries
    return selected_entries[:limit]


def load_approved_experience_entries(data_root: Path = Path(".")) -> list[dict[str, Any]]:
    bank_path = data_root / EXPERIENCE_BANK_PATH
    if not bank_path.is_file():
        return []
    bank = yaml.safe_load(bank_path.read_text(encoding="utf-8"))
    if not isinstance(bank, dict):
        return []
    entries = bank.get("entries", [])
    if not isinstance(entries, list):
        return []
    return [
        entry
        for entry in entries
        if isinstance(entry, dict) and str(entry.get("status") or "").casefold() == "approved"
    ]


def _build_query_tokens(
    jd_analysis: dict[str, Any],
    resume_strategy: dict[str, Any],
    resume_selection: dict[str, Any],
) -> set[str]:
    tokens: set[str] = set()
    values: list[Any] = [
        jd_analysis.get("company"),
        jd_analysis.get("role_title"),
        jd_analysis.get("domain"),
        jd_analysis.get("role_type"),
        jd_analysis.get("work_term"),
        resume_strategy.get("recommended_resume_base"),
        resume_selection.get("matched_category"),
    ]
    values.extend(jd_analysis.get("tools_and_technologies", []))
    values.extend(jd_analysis.get("core_requirements", []))
    values.extend(jd_analysis.get("core_responsibilities", []))
    for value in values:
        for token in _tokenize(value):
            tokens.add(token)
    return tokens


def _score_entry(entry: dict[str, Any], query_tokens: set[str]) -> int:
    searchable_parts: list[Any] = [
        entry.get("title"),
        entry.get("company"),
        entry.get("context"),
        entry.get("problem"),
        entry.get("role"),
    ]
    searchable_parts.extend(entry.get("actions", []))
    searchable_parts.extend(entry.get("technologies", []))
    searchable_parts.extend(entry.get("impact", []))
    searchable_parts.extend(entry.get("skills", []))
    searchable_parts.extend(entry.get("domain_keywords", []))
    searchable_parts.extend(entry.get("possible_resume_angles", []))
    searchable_parts.extend(entry.get("usable_for", []))
    entry_tokens: set[str] = set()
    for part in searchable_parts:
        entry_tokens.update(_tokenize(part))
    if not query_tokens:
        return 1 if entry_tokens else 0
    overlap = entry_tokens & query_tokens
    return len(overlap)


def _tokenize(value: Any) -> set[str]:
    if not value:
        return set()
    text = str(value).casefold()
    normalized = []
    for character in text:
        normalized.append(character if character.isalnum() else " ")
    return {token for token in "".join(normalized).split() if len(token) >= 2}


def _load_prompt(filename: str) -> str:
    return (PROMPT_ROOT / filename).read_text(encoding="utf-8")


COVER_LETTER_RESPONSE_SCHEMA = {
    "type": "object",
    "properties": {
        "opening_paragraph": {"type": "string"},
        "body_paragraphs": {
            "type": "array",
            "items": {"type": "string"},
            "minItems": 2,
            "maxItems": 2,
        },
        "closing_paragraph": {"type": "string"},
        "evidence_entry_ids": {
            "type": "array",
            "items": {"type": "string"},
        },
    },
    "required": [
        "opening_paragraph",
        "body_paragraphs",
        "closing_paragraph",
        "evidence_entry_ids",
    ],
    "additionalProperties": False,
}
