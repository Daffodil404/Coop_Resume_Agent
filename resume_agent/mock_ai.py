from __future__ import annotations

import re
from typing import Any


TOOLS_AND_TECHNOLOGIES = [
    "Python",
    "Java",
    "JavaScript",
    "TypeScript",
    "React",
    "Node",
    "SQL",
    "PostgreSQL",
    "MySQL",
    "AWS",
    "Azure",
    "GCP",
    "Docker",
    "Kubernetes",
    "Git",
    "Linux",
    "C++",
    "C#",
    "HTML",
    "CSS",
    "REST",
    "GraphQL",
    "Terraform",
    "Jenkins",
    "CI/CD",
]


KNOWN_COMPANIES = [
    "Scotiabank",
    "Shopify",
    "RBC",
    "TD",
    "BMO",
    "CIBC",
    "Manulife",
    "Sun Life",
    "Geotab",
]


class MockAIClient:
    """Deterministic placeholder for future model-backed JD analysis."""

    def analyze_jd(self, clean_jd: str) -> dict[str, Any]:
        lines = [line.strip() for line in clean_jd.splitlines() if line.strip()]
        return {
            "company": _extract_company(lines),
            "role_title": _extract_role_title(lines),
            "location": _extract_location(clean_jd),
            "work_term": _extract_work_term(clean_jd),
            "start_date": _extract_start_date(clean_jd),
            "role_type": _extract_role_type(clean_jd),
            "core_responsibilities": _extract_responsibilities(lines),
            "core_requirements": _extract_requirements(lines),
            "nice_to_have": _extract_nice_to_have(lines),
            "tools_and_technologies": _extract_tools_and_technologies(clean_jd),
            "domain": _extract_domain(clean_jd),
            "cover_letter_required": _extract_cover_letter_required(clean_jd),
            "seniority_level": _extract_seniority_level(clean_jd),
            "analysis_source": "mock",
        }


def _extract_company(lines: list[str]) -> str | None:
    patterns = [
        r"^Company\s*:\s*(.+)$",
        r"^Employer\s*:\s*(.+)$",
        r"^Organization\s*:\s*(.+)$",
    ]
    for line in lines[:12]:
        for pattern in patterns:
            match = re.search(pattern, line, re.IGNORECASE)
            if match:
                return _clean_value(match.group(1))
    text = "\n".join(lines[:40])
    for company in KNOWN_COMPANIES:
        if re.search(rf"\b{re.escape(company)}\b", text, re.IGNORECASE):
            return company
    return None


def _extract_role_title(lines: list[str]) -> str | None:
    patterns = [
        r"^(?:Job\s*)?Title\s*:\s*(.+)$",
        r"^Position\s*:\s*(.+)$",
        r"^Role\s*:\s*(.+)$",
    ]
    for line in lines[:12]:
        for pattern in patterns:
            match = re.search(pattern, line, re.IGNORECASE)
            if match:
                return _clean_value(match.group(1))

    text = "\n".join(lines[:40])
    role_patterns = [
        r"\bFull[- ]Stack Developer\b",
        r"\bSoftware Developer\b",
        r"\bSoftware Engineer\b",
        r"\bBackend Developer\b",
        r"\bFrontend Developer\b",
        r"\bData Analyst\b",
        r"\bData Engineer\b",
        r"\bBusiness Analyst\b",
        r"\bProduct Manager\b",
        r"\bUX Designer\b",
    ]
    for pattern in role_patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            return _title_case_role(match.group(0))
    return None


def _extract_location(text: str) -> str | None:
    match = re.search(r"Location(?:\(s\))?\s*:\s*(.+)", text, re.IGNORECASE)
    if match:
        return _format_location(_clean_value(match.group(1)))

    known_locations = [
        "Toronto",
        "Waterloo",
        "Vancouver",
        "Montreal",
        "Ottawa",
        "Calgary",
        "Remote",
        "Hybrid",
    ]
    for location in known_locations:
        if re.search(rf"\b{re.escape(location)}\b", text, re.IGNORECASE):
            return location
    return None


def _extract_work_term(text: str) -> str | None:
    match = re.search(r"\b(?:4|8|12|16)\s*(?:month|months)\b", text, re.IGNORECASE)
    return match.group(0) if match else None


def _extract_start_date(text: str) -> str | None:
    match = re.search(
        r"\b(?:January|February|March|April|May|June|July|August|September|October|November|December)\s+\d{4}\b",
        text,
        re.IGNORECASE,
    )
    if match:
        return match.group(0)
    term_match = re.search(r"\b(?:Winter|Spring|Summer|Fall|Autumn)\s+\d{4}\b", text, re.IGNORECASE)
    return term_match.group(0) if term_match else None


def _extract_role_type(text: str) -> str | None:
    if re.search(r"\bco-?op\b", text, re.IGNORECASE):
        return "Co-op"
    if re.search(r"\bintern(?:ship)?\b", text, re.IGNORECASE):
        return "Internship"
    if re.search(r"\bpart[- ]time\b", text, re.IGNORECASE):
        return "Part-time"
    if re.search(r"\bfull[- ]time\b", text, re.IGNORECASE):
        return "Full-time"
    return None


def _extract_responsibilities(lines: list[str]) -> list[str]:
    responsibility_lines: list[str] = []
    for line in lines:
        cleaned = _clean_bullet(line)
        if re.search(
            r"\b(build|develop|design|implement|deliver|maintain|collaborate|work closely|support|create|improve|deploy)\b",
            cleaned,
            re.IGNORECASE,
        ):
            responsibility_lines.append(cleaned)
        if len(responsibility_lines) == 8:
            break
    return responsibility_lines


def _extract_requirements(lines: list[str]) -> list[str]:
    requirement_lines: list[str] = []
    for line in lines:
        cleaned = _clean_bullet(line)
        if re.search(r"\b(required|requirement|experience|proficient|familiar|knowledge|ability|skills?)\b", cleaned, re.IGNORECASE):
            requirement_lines.append(cleaned)
        if len(requirement_lines) == 8:
            break
    return requirement_lines


def _extract_nice_to_have(lines: list[str]) -> list[str]:
    nice_to_have: list[str] = []
    for line in lines:
        cleaned = _clean_bullet(line)
        if re.search(r"\b(nice to have|asset|preferred|bonus|plus)\b", cleaned, re.IGNORECASE):
            nice_to_have.append(cleaned)
        if len(nice_to_have) == 8:
            break
    return nice_to_have


def _extract_tools_and_technologies(text: str) -> list[str]:
    found = []
    for keyword in TOOLS_AND_TECHNOLOGIES:
        if re.search(rf"(?<![A-Za-z0-9+#]){re.escape(keyword)}(?![A-Za-z0-9+#])", text, re.IGNORECASE):
            found.append(keyword)
    return found


def _extract_domain(text: str) -> str | None:
    domain_rules = [
        ("Banking / Finance", r"\b(bank|banking|financial|finance|capital markets|wealth management)\b"),
        ("E-commerce", r"\b(e-?commerce|retail|merchant|checkout|payments?)\b"),
        ("Cloud / Infrastructure", r"\b(cloud|infrastructure|platform|devops|kubernetes)\b"),
        ("Data / Analytics", r"\b(data|analytics|machine learning|reporting|dashboard)\b"),
        ("Healthcare", r"\b(healthcare|clinical|patient|medical)\b"),
    ]
    for domain, pattern in domain_rules:
        if re.search(pattern, text, re.IGNORECASE):
            return domain
    return None


def _extract_cover_letter_required(text: str) -> bool | None:
    if not re.search(r"\bcover letter\b", text, re.IGNORECASE):
        return None
    if re.search(r"\bcover letter\b.{0,40}\b(required|must|mandatory)\b", text, re.IGNORECASE):
        return True
    if re.search(r"\bcover letter\b.{0,40}\b(optional)\b", text, re.IGNORECASE):
        return False
    return None


def _extract_seniority_level(text: str) -> str | None:
    if re.search(r"\b(new grad|entry[- ]level|junior)\b", text, re.IGNORECASE):
        return "Entry-level"
    if re.search(r"\b(co-?op|intern(?:ship)?)\b", text, re.IGNORECASE):
        return "Student / Intern"
    if re.search(r"\bsenior\b", text, re.IGNORECASE):
        return "Senior"
    if re.search(r"\b(intermediate|mid[- ]level)\b", text, re.IGNORECASE):
        return "Intermediate"
    return None


def _clean_value(value: str) -> str:
    return value.strip(" -\t")


def _clean_bullet(value: str) -> str:
    return re.sub(r"^[-*•]\s*", "", value).strip()


def _format_location(value: str) -> str:
    parts = [_clean_value(part) for part in value.split(":") if _clean_value(part)]
    if len(parts) >= 3:
        return ", ".join(reversed(parts))
    return value


def _title_case_role(value: str) -> str:
    words = value.replace("-", " ").split()
    keep_upper = {"UX", "UI", "QA"}
    return " ".join(word.upper() if word.upper() in keep_upper else word.capitalize() for word in words)
