from __future__ import annotations

import os
from pathlib import Path


DEFAULT_RESUME_ROOT = Path("/Users/yanyuwoo/Desktop/resume/2026/coop")
RESUME_ROOT_ENV_VAR = "RESUME_AGENT_RESUME_ROOT"


def get_resume_root() -> Path:
    configured_root = os.environ.get(RESUME_ROOT_ENV_VAR)
    return Path(configured_root).expanduser() if configured_root else DEFAULT_RESUME_ROOT
