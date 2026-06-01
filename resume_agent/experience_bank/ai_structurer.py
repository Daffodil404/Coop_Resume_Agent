from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Callable

from .evidence import ExtractedEvidence
from .openai_provider import OpenAIResponsesProvider


PROMPT_ROOT = Path(__file__).resolve().parent.parent.parent / "prompts"


class AIExperienceStructurer:
    """Prepared OpenAI adapter boundary. File writes remain outside this class."""

    name = "openai"

    def __init__(
        self,
        response_provider: Callable[[str, str], dict[str, object]] | None = None,
        model: str | None = None,
    ) -> None:
        provider = response_provider or OpenAIResponsesProvider(model=model)
        self.response_provider = provider
        self.model = model or getattr(provider, "model", None)

    def structure(
        self,
        clean_note: str,
        draft_id: str,
        evidence: ExtractedEvidence,
    ) -> dict[str, object]:
        system_prompt = _load_prompt("experience_structurer.system.md")
        user_template = _load_prompt("experience_structurer.user.md")
        user_prompt = user_template.format(
            draft_id=draft_id,
            clean_note=clean_note,
            evidence=evidence.to_dict(),
        )
        draft = self.response_provider(system_prompt, user_prompt)
        draft["id"] = draft_id
        draft["status"] = "draft"
        draft["source"] = {
            "type": "raw_experience_note",
            "created_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
            "structurer": self.name,
            "model": self.model,
        }
        draft["evidence"] = {
            "action_lines": evidence.action_lines,
            "metric_lines": evidence.metric_lines,
            "technology_lines": evidence.technology_lines,
        }
        draft["evidence_lines"] = evidence.evidence_lines
        draft["draft_bullets"] = []
        draft["truth_constraints"] = [
            "Use only claims explicitly supported by the raw note.",
            "Do not invent metrics, technologies, ownership, responsibilities, or outcomes.",
            "Review uncertain_points before merging this draft into an experience bank.",
        ]
        return draft


def _load_prompt(filename: str) -> str:
    return (PROMPT_ROOT / filename).read_text(encoding="utf-8")
