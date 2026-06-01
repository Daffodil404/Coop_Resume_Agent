from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Callable

from .ai.model_router import ModelConfig, get_model_config
from .experience_bank.config import has_openai_api_key
from .experience_bank.openai_provider import OpenAIResponsesProvider


PROMPT_ROOT = Path(__file__).resolve().parent.parent / "prompts"


class OpenAIJdAnalysisClient:
    """Use OpenAI to extract structured JD analysis for downstream workflow steps."""

    name = "openai"

    def __init__(
        self,
        response_provider: Callable[[str, str], dict[str, object]] | None = None,
        model_config: ModelConfig | None = None,
        data_root: Path = Path("."),
    ) -> None:
        resolved_model_config = model_config or get_model_config("jd_analysis", data_root=data_root)
        provider = response_provider or OpenAIResponsesProvider(
            model=resolved_model_config.model,
            schema_name="jd_analysis",
            schema=JD_ANALYSIS_RESPONSE_SCHEMA,
            temperature=resolved_model_config.temperature,
            max_output_tokens=resolved_model_config.max_output_tokens,
            reasoning_effort=resolved_model_config.reasoning_effort,
        )
        self.response_provider = provider
        self.model_config = resolved_model_config
        self.model = getattr(provider, "model", None) or resolved_model_config.model

    def analyze_jd(self, clean_jd: str) -> dict[str, Any]:
        system_prompt = _load_prompt("jd_analysis.system.md")
        user_template = _load_prompt("jd_analysis.user.md")
        user_prompt = user_template.format(job_description=clean_jd)
        analysis = self.response_provider(system_prompt, user_prompt)
        analysis["analysis_source"] = self.name
        analysis["analysis_model"] = self.model
        analysis["analysis_task_key"] = self.model_config.task_key
        return analysis


def should_use_ai_jd_analysis() -> bool:
    return has_openai_api_key()


def _load_prompt(filename: str) -> str:
    return (PROMPT_ROOT / filename).read_text(encoding="utf-8")


NULLABLE_STRING = {"anyOf": [{"type": "string"}, {"type": "null"}]}
NULLABLE_BOOLEAN = {"anyOf": [{"type": "boolean"}, {"type": "null"}]}
STRING_LIST = {"type": "array", "items": {"type": "string"}}

JD_ANALYSIS_RESPONSE_SCHEMA = {
    "type": "object",
    "properties": {
        "company": NULLABLE_STRING,
        "role_title": NULLABLE_STRING,
        "location": NULLABLE_STRING,
        "work_term": NULLABLE_STRING,
        "start_date": NULLABLE_STRING,
        "role_type": NULLABLE_STRING,
        "core_responsibilities": STRING_LIST,
        "core_requirements": STRING_LIST,
        "nice_to_have": STRING_LIST,
        "tools_and_technologies": STRING_LIST,
        "domain": NULLABLE_STRING,
        "cover_letter_required": NULLABLE_BOOLEAN,
        "seniority_level": NULLABLE_STRING,
    },
    "required": [
        "company",
        "role_title",
        "location",
        "work_term",
        "start_date",
        "role_type",
        "core_responsibilities",
        "core_requirements",
        "nice_to_have",
        "tools_and_technologies",
        "domain",
        "cover_letter_required",
        "seniority_level",
    ],
    "additionalProperties": False,
}
