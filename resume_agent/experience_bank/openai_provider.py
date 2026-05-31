from __future__ import annotations

import json
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from .config import get_openai_api_key, get_openai_model


OPENAI_RESPONSES_URL = "https://api.openai.com/v1/responses"


class OpenAIProviderError(RuntimeError):
    """Raised when the OpenAI Responses API cannot produce a usable draft."""


class OpenAIResponsesProvider:
    """Call OpenAI Responses API with strict structured output."""

    def __init__(self, model: str | None = None, timeout_seconds: int = 60) -> None:
        self.model = model or get_openai_model()
        self.timeout_seconds = timeout_seconds

    def __call__(self, system_prompt: str, user_prompt: str) -> dict[str, object]:
        payload = {
            "model": self.model,
            "instructions": system_prompt,
            "input": user_prompt,
            "text": {
                "format": {
                    "type": "json_schema",
                    "name": "experience_bank_draft",
                    "strict": True,
                    "schema": EXPERIENCE_DRAFT_RESPONSE_SCHEMA,
                }
            },
        }
        request = Request(
            OPENAI_RESPONSES_URL,
            data=json.dumps(payload).encode("utf-8"),
            headers={
                "Authorization": f"Bearer {get_openai_api_key()}",
                "Content-Type": "application/json",
            },
            method="POST",
        )
        try:
            with urlopen(request, timeout=self.timeout_seconds) as response:
                response_payload = json.load(response)
        except HTTPError as error:
            raise OpenAIProviderError(_format_http_error(error)) from error
        except URLError as error:
            raise OpenAIProviderError(f"OpenAI API request failed: {error.reason}") from error

        output_text = _extract_output_text(response_payload)
        try:
            parsed = json.loads(output_text)
        except json.JSONDecodeError as error:
            raise OpenAIProviderError("OpenAI API returned invalid structured JSON.") from error
        if not isinstance(parsed, dict):
            raise OpenAIProviderError("OpenAI API returned a non-object structured response.")
        return parsed


def _extract_output_text(response_payload: dict[str, Any]) -> str:
    for output_item in response_payload.get("output", []):
        for content_item in output_item.get("content", []):
            if content_item.get("type") == "refusal":
                raise OpenAIProviderError(f"OpenAI API refused the request: {content_item.get('refusal')}")
            if content_item.get("type") == "output_text":
                return str(content_item.get("text", ""))
    raise OpenAIProviderError("OpenAI API response did not contain structured output text.")


def _format_http_error(error: HTTPError) -> str:
    try:
        payload = json.loads(error.read().decode("utf-8"))
        message = payload.get("error", {}).get("message")
    except (UnicodeDecodeError, json.JSONDecodeError):
        message = None
    return f"OpenAI API request failed with HTTP {error.code}: {message or error.reason}"


NULLABLE_STRING = {"anyOf": [{"type": "string"}, {"type": "null"}]}
STRING_LIST = {"type": "array", "items": {"type": "string"}}

EXPERIENCE_DRAFT_RESPONSE_SCHEMA = {
    "type": "object",
    "properties": {
        "id": {"type": "string"},
        "title": NULLABLE_STRING,
        "company": NULLABLE_STRING,
        "time_period": NULLABLE_STRING,
        "context": NULLABLE_STRING,
        "problem": NULLABLE_STRING,
        "role": NULLABLE_STRING,
        "actions": STRING_LIST,
        "technologies": STRING_LIST,
        "impact": STRING_LIST,
        "metrics": STRING_LIST,
        "role_types": STRING_LIST,
        "skills": STRING_LIST,
        "domain_keywords": STRING_LIST,
        "possible_resume_angles": STRING_LIST,
        "evidence": {
            "type": "object",
            "properties": {
                "action_lines": STRING_LIST,
                "metric_lines": STRING_LIST,
                "technology_lines": STRING_LIST,
            },
            "required": ["action_lines", "metric_lines", "technology_lines"],
            "additionalProperties": False,
        },
        "evidence_lines": STRING_LIST,
        "draft_bullets": STRING_LIST,
        "truth_constraints": STRING_LIST,
        "uncertain_points": STRING_LIST,
        "confidence": {
            "type": "object",
            "properties": {
                "metrics": {"type": "string", "enum": ["low", "medium", "high"]},
                "tools": {"type": "string", "enum": ["low", "medium", "high"]},
                "ownership": {"type": "string", "enum": ["low", "medium", "high"]},
                "impact": {"type": "string", "enum": ["low", "medium", "high"]},
            },
            "required": ["metrics", "tools", "ownership", "impact"],
            "additionalProperties": False,
        },
        "usable_for": STRING_LIST,
    },
    "required": [
        "id",
        "title",
        "company",
        "time_period",
        "context",
        "problem",
        "role",
        "actions",
        "technologies",
        "impact",
        "metrics",
        "role_types",
        "skills",
        "domain_keywords",
        "possible_resume_angles",
        "evidence",
        "evidence_lines",
        "draft_bullets",
        "truth_constraints",
        "uncertain_points",
        "confidence",
        "usable_for",
    ],
    "additionalProperties": False,
}
