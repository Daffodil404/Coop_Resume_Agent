Draft ID: {draft_id}

Raw normalized note:
{clean_note}

Deterministic evidence:
{evidence}

Produce a structured draft with the Experience Bank draft schema.

Language policy:
- The raw note may be Chinese, English, or mixed Chinese-English.
- Write all generated fields in concise professional English.
- Apply this to `title`, `context`, `problem`, `role`, `actions`, `technologies`, `impact`, `metrics`, `role_types`, `skills`, `domain_keywords`, `possible_resume_angles`, `draft_bullets`, `truth_constraints`, `uncertain_points`, and `usable_for`.
- Preserve proper nouns, company names, product names, and technical terms in their conventional form when possible.
- Do not translate or rewrite raw evidence lines. They must remain traceable to the original input.
- Do not add facts during translation. Put any term that cannot be confidently translated in `uncertain_points`.

Field guidance:
- `title`: use an explicit title, or a conservative descriptive title for the single experience.
- `company`: extract only when explicitly named.
- `context`: summarize the factual project background.
- `problem`: summarize the factual requirement or problem being solved.
- `role`: state the contribution conservatively; do not claim sole ownership unless explicit.
- `actions`: list supported implementation or design actions as concise factual paraphrases.
- `technologies`: include only explicitly named technologies or tools.
- `technologies` may include programming languages, frameworks, libraries, developer tools, design tools, platforms, protocols, and AI-assisted workflow tools.
- If one phrase contains multiple reusable tools or capabilities, extract them separately when appropriate.
- For example, if the raw note says `Figma 的 MCP`, extract `Figma` and `MCP` separately, not `Figma MCP`.
- Do not add common but unmentioned frontend technologies such as React, TypeScript, Next.js, Tailwind, or CSS only because the note mentions frontend or landing page work.
- `impact`: include only supported outcomes.
- `impact`: include supported qualitative outcomes when the raw note clearly describes what the implementation enabled or supported. Do not invent quantitative metrics.
- `metrics`: include only explicitly stated metrics.
- `role_types`, `skills`, `domain_keywords`, `possible_resume_angles`, and `usable_for`: do not leave these empty when the raw note clearly supports conservative English labels.
- `uncertain_points`: list missing details that would improve future review.
- `draft_bullets`: keep empty.

Use null or empty lists where the note does not support a value. Do not leave semantically extractable fields empty merely because the deterministic evidence extractor missed a Chinese or conversational sentence.
