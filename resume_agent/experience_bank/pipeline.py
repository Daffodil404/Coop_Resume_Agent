from __future__ import annotations

from dataclasses import dataclass
from typing import Callable

from .ai_structurer import AIExperienceStructurer
from .config import ALLOWED_EXPERIENCE_MODES, get_experience_mode, has_openai_api_key
from .evidence import (
    EvidenceExtractor,
    ExtractedEvidence,
    include_explicit_technologies,
    split_supported_compound_technology,
    technology_is_explicitly_mentioned,
)
from .grounding import apply_grounded_enrichment
from .ingestion import RuleBasedExperienceStructurer
from .preprocessor import RawNotePreprocessor
from .openai_provider import OpenAIProviderError
from .structurer import ExperienceStructurer
from .validator import validate_experience_draft, validate_experience_draft_against_evidence


@dataclass
class ExperienceIngestionPipeline:
    """Coordinate preprocessing, structuring, guardrails, and local fallback."""

    mode: str | None = None
    preprocessor: RawNotePreprocessor | None = None
    evidence_extractor: EvidenceExtractor | None = None
    local_structurer: ExperienceStructurer | None = None
    ai_structurer: ExperienceStructurer | None = None
    warning_handler: Callable[[str], None] | None = None
    progress_handler: Callable[[str], None] | None = None
    new_technology_handler: Callable[[str], bool] | None = None

    def validate_configuration(self) -> None:
        selected_mode = self.mode or get_experience_mode()
        if selected_mode not in ALLOWED_EXPERIENCE_MODES:
            raise ValueError(
                f"Invalid Experience Bank ingestion mode: {selected_mode}. Expected one of: auto, ai, local."
            )
        if selected_mode == "ai" and not has_openai_api_key():
            raise ValueError("OPENAI_API_KEY is required when RESUME_AGENT_EXPERIENCE_MODE=ai.")

    def structure(self, raw_note: str, draft_id: str) -> dict[str, object]:
        selected_mode = self.mode or get_experience_mode()
        self.validate_configuration()
        preprocessor = self.preprocessor or RawNotePreprocessor()
        evidence_extractor = self.evidence_extractor or EvidenceExtractor()
        local_structurer = self.local_structurer or RuleBasedExperienceStructurer()
        clean_note = preprocessor.preprocess(raw_note)
        evidence = evidence_extractor.extract(clean_note)

        if selected_mode == "local":
            self._progress("Using local Experience Bank structurer.")
            draft = local_structurer.structure(clean_note, draft_id, evidence)
        elif selected_mode == "ai":
            self._progress("Calling OpenAI to structure the experience draft. This may take a few seconds.")
            draft = self._structure_with_ai(clean_note, draft_id, evidence)
        elif selected_mode == "auto":
            draft = self._structure_auto(clean_note, draft_id, evidence, local_structurer)
        else:
            raise ValueError(f"Unknown Experience Bank ingestion mode: {selected_mode}")

        apply_grounded_enrichment(draft, clean_note, evidence)
        evidence = self._review_new_technologies(draft, clean_note, evidence, evidence_extractor)
        validate_experience_draft(draft)
        validate_experience_draft_against_evidence(draft, evidence)
        return draft

    def _structure_auto(
        self,
        clean_note: str,
        draft_id: str,
        evidence: ExtractedEvidence,
        local_structurer: ExperienceStructurer,
    ) -> dict[str, object]:
        if not has_openai_api_key():
            self._warn("OPENAI_API_KEY is not configured. Using local Experience Bank fallback.")
            self._progress("Using local Experience Bank structurer.")
            return local_structurer.structure(clean_note, draft_id, evidence)
        try:
            self._progress("Calling OpenAI to structure the experience draft. This may take a few seconds.")
            return self._structure_with_ai(clean_note, draft_id, evidence)
        except OpenAIProviderError as error:
            self._warn(f"{error} Using local Experience Bank fallback.")
            self._progress("Using local Experience Bank structurer.")
            return local_structurer.structure(clean_note, draft_id, evidence)

    def _structure_with_ai(
        self,
        clean_note: str,
        draft_id: str,
        evidence: ExtractedEvidence,
    ) -> dict[str, object]:
        ai_structurer = self.ai_structurer or AIExperienceStructurer()
        return ai_structurer.structure(clean_note, draft_id, evidence)

    def _review_new_technologies(
        self,
        draft: dict[str, object],
        clean_note: str,
        evidence: ExtractedEvidence,
        evidence_extractor: EvidenceExtractor,
    ) -> ExtractedEvidence:
        self._split_supported_compound_technologies(draft, evidence)
        new_technologies = sorted(set(draft["technologies"]) - set(evidence.technologies))
        if not new_technologies:
            return evidence
        missing_from_note = [
            technology
            for technology in new_technologies
            if not technology_is_explicitly_mentioned(technology, clean_note)
        ]
        if missing_from_note:
            draft["technologies"] = [
                technology
                for technology in draft["technologies"]
                if technology not in missing_from_note
            ]
            draft["uncertain_points"].append(
                "Removed AI-extracted technologies that were not found in the raw note: "
                f"{', '.join(missing_from_note)}"
            )
            self._warn(
                "Removed AI-extracted technologies not found in the raw note: "
                f"{', '.join(missing_from_note)}"
            )
            new_technologies = [
                technology for technology in new_technologies if technology not in missing_from_note
            ]
        for technology in new_technologies:
            self._warn(
                f"AI extracted a technology not yet included in the local keyword dictionary: "
                f"{technology}"
            )
            if self.new_technology_handler and self.new_technology_handler(technology):
                evidence_extractor.add_local_keyword(technology)
                self._progress(f"Added local technology keyword: {technology}")
            else:
                self._progress(f"Continuing without adding local technology keyword: {technology}")
        evidence = include_explicit_technologies(evidence, clean_note, new_technologies)
        draft["evidence"]["technology_lines"] = evidence.technology_lines
        return evidence

    def _split_supported_compound_technologies(
        self,
        draft: dict[str, object],
        evidence: ExtractedEvidence,
    ) -> None:
        normalized_technologies = []
        for technology in draft["technologies"]:
            split_technologies = split_supported_compound_technology(technology, evidence.technologies)
            if split_technologies:
                normalized_technologies.extend(split_technologies)
                continue
            normalized_technologies.append(technology)
        draft["technologies"] = list(dict.fromkeys(normalized_technologies))

    def _warn(self, message: str) -> None:
        if self.warning_handler:
            self.warning_handler(message)

    def _progress(self, message: str) -> None:
        if self.progress_handler:
            self.progress_handler(message)
