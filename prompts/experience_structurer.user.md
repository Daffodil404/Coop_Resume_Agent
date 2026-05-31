Draft ID: {draft_id}

Raw normalized note:
{clean_note}

Deterministic evidence:
{evidence}

Produce a structured draft with the Experience Bank draft schema.

Field guidance:
- `title`: use an explicit title, or a conservative descriptive title for the single experience.
- `company`: extract only when explicitly named.
- `context`: summarize the factual project background.
- `problem`: summarize the factual requirement or problem being solved.
- `role`: state the contribution conservatively; do not claim sole ownership unless explicit.
- `actions`: list supported implementation or design actions as concise factual paraphrases.
- `technologies`: include only explicitly named technologies or tools.
- `impact`: include only supported outcomes.
- `metrics`: include only explicitly stated metrics.
- `uncertain_points`: list missing details that would improve future review.
- `draft_bullets`: keep empty.

Use null or empty lists where the note does not support a value. Do not leave semantically extractable fields empty merely because the deterministic evidence extractor missed a Chinese or conversational sentence.
