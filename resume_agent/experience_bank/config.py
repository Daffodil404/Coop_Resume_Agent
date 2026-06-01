from __future__ import annotations

import os


EXPERIENCE_MODE_ENV_VAR = "RESUME_AGENT_EXPERIENCE_MODE"
OPENAI_API_KEY_ENV_VAR = "OPENAI_API_KEY"
OPENAI_MODEL_ENV_VAR = "RESUME_AGENT_OPENAI_MODEL"
DEFAULT_OPENAI_MODEL = "gpt-4o-mini"
ALLOWED_EXPERIENCE_MODES = {"auto", "ai", "local"}


def get_experience_mode() -> str:
    mode = os.environ.get(EXPERIENCE_MODE_ENV_VAR, "auto").strip().lower()
    if mode not in ALLOWED_EXPERIENCE_MODES:
        raise ValueError(
            f"Invalid {EXPERIENCE_MODE_ENV_VAR}: {mode}. Expected one of: auto, ai, local."
        )
    return mode


def has_openai_api_key() -> bool:
    return bool(os.environ.get(OPENAI_API_KEY_ENV_VAR, "").strip())


def get_openai_api_key() -> str:
    api_key = os.environ.get(OPENAI_API_KEY_ENV_VAR, "").strip()
    if not api_key:
        raise ValueError("OPENAI_API_KEY is required for OpenAI Experience Bank structuring.")
    return api_key


def get_openai_model() -> str:
    return os.environ.get(OPENAI_MODEL_ENV_VAR, DEFAULT_OPENAI_MODEL).strip() or DEFAULT_OPENAI_MODEL
