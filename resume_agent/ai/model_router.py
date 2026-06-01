from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml


PRIVATE_CONFIG_PATH = Path("data/private/config.yaml")

TASK_KEYS = (
    "jd_analysis",
    "resume_strategy",
    "resume_selection",
    "cover_letter_decision",
    "cover_letter_evidence_selection",
    "cover_letter_outline",
    "cover_letter_writer",
    "cover_letter_review",
)

DEFAULT_MODEL_ALIASES = {
    "cheap": "gpt-4.1-nano",
    "balanced": "gpt-4.1-mini",
    "strong_mini": "gpt-5.4-mini",
    "strong": "gpt-5.4",
    "premium": "gpt-5.5",
}

DEFAULT_TASK_CONFIGS = {
    "jd_analysis": {
        "model": "balanced",
        "temperature": 0.1,
        "max_output_tokens": 1500,
    },
    "resume_strategy": {
        "model": "balanced",
        "temperature": 0.1,
        "max_output_tokens": 1000,
    },
    "resume_selection": {
        "model": "balanced",
        "temperature": 0.1,
        "max_output_tokens": 1000,
    },
    "cover_letter_decision": {
        "model": "balanced",
        "temperature": 0.1,
        "max_output_tokens": 800,
    },
    "cover_letter_evidence_selection": {
        "model": "strong_mini",
        "temperature": 0.1,
        "max_output_tokens": 1200,
    },
    "cover_letter_outline": {
        "model": "strong_mini",
        "temperature": 0.2,
        "max_output_tokens": 1200,
    },
    "cover_letter_writer": {
        "model": "strong",
        "temperature": 0.35,
        "max_output_tokens": 1800,
    },
    "cover_letter_review": {
        "model": "strong_mini",
        "temperature": 0.1,
        "max_output_tokens": 1200,
    },
}

TASK_ENV_PREFIXES = {
    "jd_analysis": "OPENAI_JD_ANALYSIS",
    "resume_strategy": "OPENAI_RESUME_STRATEGY",
    "resume_selection": "OPENAI_RESUME_SELECTION",
    "cover_letter_decision": "OPENAI_COVER_LETTER_DECISION",
    "cover_letter_evidence_selection": "OPENAI_COVER_LETTER_EVIDENCE_SELECTION",
    "cover_letter_outline": "OPENAI_COVER_LETTER_OUTLINE",
    "cover_letter_writer": "OPENAI_COVER_LETTER_WRITER",
    "cover_letter_review": "OPENAI_COVER_LETTER_REVIEW",
}


class ModelRouterError(ValueError):
    """Raised when task-level model routing cannot resolve a valid config."""


@dataclass(frozen=True)
class ModelConfig:
    task_key: str
    model: str
    temperature: float | None = None
    max_output_tokens: int | None = None
    reasoning_effort: str | None = None


def get_model_config(task_key: str, data_root: Path = Path(".")) -> ModelConfig:
    if task_key not in TASK_KEYS:
        known_tasks = ", ".join(TASK_KEYS)
        raise ModelRouterError(f"Unknown model-routing task key: {task_key}. Expected one of: {known_tasks}.")

    config_data = _load_private_config(data_root)
    model_aliases = dict(DEFAULT_MODEL_ALIASES)
    model_aliases.update(_read_mapping(config_data, "ai", "models"))

    task_config = dict(DEFAULT_TASK_CONFIGS[task_key])
    task_config.update(_read_task_config(config_data, task_key))
    task_config = _apply_env_overrides(task_key, task_config)

    model_value = str(task_config.get("model") or "").strip()
    if not model_value:
        raise ModelRouterError(f"Configured model for task '{task_key}' is empty.")
    resolved_model = str(model_aliases.get(model_value, model_value)).strip()
    if not resolved_model:
        raise ModelRouterError(f"Resolved model for task '{task_key}' is empty.")

    temperature = _coerce_optional_float(task_config.get("temperature"), field_name=f"{task_key}.temperature")
    max_output_tokens = _coerce_optional_int(
        task_config.get("max_output_tokens"),
        field_name=f"{task_key}.max_output_tokens",
    )
    reasoning_effort = _coerce_optional_reasoning_effort(task_config.get("reasoning_effort"), task_key)

    return ModelConfig(
        task_key=task_key,
        model=resolved_model,
        temperature=temperature,
        max_output_tokens=max_output_tokens,
        reasoning_effort=reasoning_effort,
    )


def _load_private_config(data_root: Path) -> dict[str, Any]:
    config_path = data_root / PRIVATE_CONFIG_PATH
    if not config_path.is_file():
        return {}
    loaded = yaml.safe_load(config_path.read_text(encoding="utf-8"))
    if loaded is None:
        return {}
    if not isinstance(loaded, dict):
        raise ModelRouterError(f"Private config must be a YAML mapping: {config_path}")
    return loaded


def _read_mapping(config_data: dict[str, Any], *path: str) -> dict[str, Any]:
    node: Any = config_data
    for key in path:
        if not isinstance(node, dict):
            return {}
        node = node.get(key)
    if node is None:
        return {}
    if not isinstance(node, dict):
        dotted_path = ".".join(path)
        raise ModelRouterError(f"Expected '{dotted_path}' to be a YAML mapping.")
    return node


def _read_task_config(config_data: dict[str, Any], task_key: str) -> dict[str, Any]:
    tasks = _read_mapping(config_data, "ai", "tasks")
    task_config = tasks.get(task_key)
    if task_config is None:
        return {}
    if not isinstance(task_config, dict):
        raise ModelRouterError(f"Expected ai.tasks.{task_key} to be a YAML mapping.")
    return task_config


def _apply_env_overrides(task_key: str, task_config: dict[str, Any]) -> dict[str, Any]:
    prefix = TASK_ENV_PREFIXES[task_key]
    overridden = dict(task_config)

    model_override = os.environ.get(f"{prefix}_MODEL")
    if model_override is not None:
        overridden["model"] = model_override.strip()

    temperature_override = os.environ.get(f"{prefix}_TEMPERATURE")
    if temperature_override is not None:
        overridden["temperature"] = temperature_override.strip()

    max_tokens_override = os.environ.get(f"{prefix}_MAX_OUTPUT_TOKENS")
    if max_tokens_override is not None:
        overridden["max_output_tokens"] = max_tokens_override.strip()

    reasoning_override = os.environ.get(f"{prefix}_REASONING_EFFORT")
    if reasoning_override is not None:
        overridden["reasoning_effort"] = reasoning_override.strip()

    return overridden


def _coerce_optional_float(value: Any, field_name: str) -> float | None:
    if value is None or value == "":
        return None
    try:
        return float(value)
    except (TypeError, ValueError) as error:
        raise ModelRouterError(f"Invalid float value for {field_name}: {value!r}") from error


def _coerce_optional_int(value: Any, field_name: str) -> int | None:
    if value is None or value == "":
        return None
    try:
        return int(value)
    except (TypeError, ValueError) as error:
        raise ModelRouterError(f"Invalid integer value for {field_name}: {value!r}") from error


def _coerce_optional_reasoning_effort(value: Any, task_key: str) -> str | None:
    if value is None or value == "":
        return None
    effort = str(value).strip().lower()
    allowed = {"none", "minimal", "low", "medium", "high", "xhigh"}
    if effort not in allowed:
        allowed_text = ", ".join(sorted(allowed))
        raise ModelRouterError(
            f"Invalid reasoning_effort for task '{task_key}': {value!r}. Expected one of: {allowed_text}."
        )
    return effort
