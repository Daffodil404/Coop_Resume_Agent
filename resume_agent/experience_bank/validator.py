from __future__ import annotations


MINIMUM_NOTE_LENGTH = 40


def validate_raw_experience_note(raw_note: str) -> None:
    """Reject notes that do not contain enough text for a conservative draft."""
    normalized = raw_note.strip()
    if not normalized:
        raise ValueError("Experience note cannot be empty.")
    if len(normalized) < MINIMUM_NOTE_LENGTH:
        raise ValueError(
            f"Experience note is too short. Please provide at least {MINIMUM_NOTE_LENGTH} characters."
        )
