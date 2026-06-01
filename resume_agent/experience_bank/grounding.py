from __future__ import annotations

from .evidence import ExtractedEvidence


def apply_grounded_enrichment(
    draft: dict[str, object],
    clean_note: str,
    evidence: ExtractedEvidence,
) -> None:
    _merge_explicit_technologies(draft, evidence)
    draft["evidence"]["technology_lines"] = evidence.technology_lines
    _enrich_taxonomy_fields(draft, clean_note)


def _merge_explicit_technologies(draft: dict[str, object], evidence: ExtractedEvidence) -> None:
    merged = [*draft["technologies"]]
    for technology in evidence.technologies:
        if technology not in merged:
            merged.append(technology)
    draft["technologies"] = merged


def _enrich_taxonomy_fields(draft: dict[str, object], clean_note: str) -> None:
    normalized_text = clean_note.casefold()
    technologies = {technology.casefold(): technology for technology in draft["technologies"]}

    has_frontend = any(keyword in normalized_text for keyword in ("frontend", "landing page", "qr code"))
    has_backend = any(
        keyword in normalized_text
        for keyword in ("backend", "server", "database", "poll", "polling")
    )
    has_payment = any(
        keyword in normalized_text
        for keyword in ("payment", "wechat pay", "wechat payment", "merchant certification")
    )
    has_qr_payment = "qr code" in normalized_text or "qr-code" in normalized_text
    has_polling = "poll" in normalized_text or "polling" in normalized_text
    has_transaction_persistence = "transaction" in normalized_text and "database" in normalized_text
    has_certificate_setup = "certificate" in normalized_text or "certification" in normalized_text

    role_types = list(draft["role_types"])
    if has_frontend and has_backend:
        _append_unique(role_types, "fullstack")
    if has_frontend:
        _append_unique(role_types, "frontend")
    if has_backend:
        _append_unique(role_types, "backend")
    if has_frontend or has_backend or has_payment:
        _append_unique(role_types, "software_engineering")
    draft["role_types"] = role_types

    skills = list(draft["skills"])
    if has_payment:
        _append_unique(skills, "payment integration")
        _append_unique(skills, "third-party API integration")
    if has_qr_payment:
        _append_unique(skills, "QR-code payment flow implementation")
    if has_frontend and has_backend:
        _append_unique(skills, "frontend-backend integration")
        _append_unique(skills, "full-stack feature implementation")
    if has_polling:
        _append_unique(skills, "backend polling")
    if has_transaction_persistence:
        _append_unique(skills, "transaction data persistence")
    if has_certificate_setup:
        _append_unique(skills, "certificate configuration")
    draft["skills"] = skills

    domain_keywords = list(draft["domain_keywords"])
    if has_payment:
        _append_unique(domain_keywords, "payment integration")
    if "wechat pay" in normalized_text or "wechat payment" in normalized_text:
        _append_unique(domain_keywords, "WeChat Pay")
    if "domestic payment" in normalized_text or "domestic payments" in normalized_text:
        _append_unique(domain_keywords, "domestic payments")
    if has_qr_payment:
        _append_unique(domain_keywords, "QR-code payment")
    if has_transaction_persistence or "transaction" in normalized_text:
        _append_unique(domain_keywords, "transaction processing")
    draft["domain_keywords"] = domain_keywords

    angles = list(draft["possible_resume_angles"])
    if "WeChat Pay" in domain_keywords:
        _append_unique(angles, "Full-stack payment integration with WeChat Pay")
    if has_qr_payment:
        _append_unique(angles, "QR-code payment flow implementation")
    if has_frontend and has_backend and has_payment:
        _append_unique(angles, "Frontend-backend payment workflow integration")
    if has_polling and has_transaction_persistence:
        _append_unique(angles, "Backend polling and transaction persistence")
    if has_certificate_setup:
        _append_unique(angles, "Certificate-based payment service setup")
    draft["possible_resume_angles"] = angles

    impact = list(draft["impact"])
    if has_payment and has_qr_payment:
        _append_unique(
            impact,
            "Enabled domestic users to complete payments through a WeChat Pay QR-code flow.",
        )
    if has_polling and has_transaction_persistence:
        _append_unique(
            impact,
            "Supported payment status tracking and transaction data recording after successful polling.",
        )
    draft["impact"] = impact

    if not draft["metrics"]:
        draft["metrics"] = []

    usable_for = list(draft["usable_for"])
    for label in ("fullstack", "software_engineering", "backend", "frontend"):
        if label in role_types:
            _append_unique(usable_for, label)
    draft["usable_for"] = usable_for


def _append_unique(items: list[str], value: str) -> None:
    if value not in items:
        items.append(value)
