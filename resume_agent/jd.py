from __future__ import annotations

import re


def clean_jd_text(text: str) -> str:
    """Normalize pasted JD text while preserving paragraph boundaries."""
    normalized = text.replace("\r\n", "\n").replace("\r", "\n")
    normalized = re.sub(r"[ \t]+", " ", normalized)
    normalized = re.sub(r"\n{3,}", "\n\n", normalized)
    lines = [line.strip() for line in normalized.split("\n")]
    return "\n".join(lines).strip() + "\n"
