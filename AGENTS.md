# resume-agent Project Guidance

## Project Scope

This repository contains `resume-agent`, a local Python interactive CLI tool for generating tailored resume and cover letter drafts from pasted job descriptions.

The MVP workflow is:

1. Launch the CLI with `python -m resume_agent` or `resume-agent`.
2. Prompt the user to paste a Job Description directly into the terminal.
3. Read multiline input until Ctrl-D.
4. Clean the pasted JD.
5. Use a mock AI client to extract structured JD information.
6. Create an application folder under `applications/`.
7. Save workflow artifacts such as `jd_raw.txt`, `jd_clean.txt`, `jd_analysis.json`, `metadata.json`, and later resume/cover-letter outputs.
8. Use local YAML data and Jinja2 LaTeX templates for resume generation.

## MVP Boundaries

Do not implement the following unless explicitly requested:

* Web crawling
* LinkedIn, Workday, or OscarPlus scraping
* Web UI
* Database
* PDF compilation
* Real AI API calls
* Automatic job application submission

## Project Directory Rules

* Source code should stay under `resume_agent/`.
* Tests should stay under `tests/`.
* Reusable examples should stay under `examples/`.
* LaTeX templates should stay under `templates/`.
* Prompt templates should stay under `prompts/`, if used.
* Reusable fake/sample data should stay under `data/samples/`.
* Real local user data should stay under `data/private/`.
* Generated application workflow outputs should stay under `applications/`.

## Privacy Rules for This Project

* `applications/` contains generated job application artifacts and should be ignored by Git except for `applications/.gitkeep`.
* `data/private/` contains real user profile or experience-bank data and should be ignored by Git.
* `data/samples/` may be committed only if it contains fake or clearly sanitized sample data.
* Do not hard-code real candidate background, real job descriptions, or real generated application materials into source code or tests.

## Implementation Style

* Keep the CLI interactive and simple.
* Use deterministic mock AI behavior until real API integration is explicitly requested.
* Keep AI client logic behind an abstraction.
* Prefer JSON/YAML outputs for intermediate artifacts.
* Keep persistence logic separate from CLI logic where practical.
* Add minimal tests for core utilities, JD cleaning, mock analysis, folder creation, and collision handling.
