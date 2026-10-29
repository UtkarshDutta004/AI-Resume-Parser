"""Syntactical analysis: identify conventional resume sections and patterns."""

from __future__ import annotations

import re

SECTION_ALIASES = {
    "summary": ("summary", "profile", "professional summary", "objective", "about me"),
    "skills": ("skills", "technical skills", "core competencies", "technologies"),
    "education": ("education", "academic background", "qualifications"),
    "experience": ("experience", "work experience", "employment history", "professional experience"),
    "projects": ("projects", "selected projects", "personal projects"),
    "certifications": ("certifications", "certificates", "licenses", "licenses & certifications"),
}
_HEADING_TO_SECTION = {
    re.sub(r"[^a-z ]", "", alias.lower()).strip(): section
    for section, aliases in SECTION_ALIASES.items()
    for alias in aliases
}


def _section_for_heading(line: str) -> str | None:
    heading = re.sub(r"[^a-z ]", "", line.lower()).strip()
    return _HEADING_TO_SECTION.get(heading)


def detect_sections(text: str) -> dict[str, list[str]]:
    """Group lines beneath recognized headings; unmatched lines go to ``other``."""
    sections: dict[str, list[str]] = {"other": []}
    current = "other"
    for raw_line in text.splitlines():
        line = raw_line.strip()
        if not line:
            continue
        section = _section_for_heading(line)
        if section:
            current = section
            sections.setdefault(section, [])
        else:
            sections.setdefault(current, []).append(line)
    return sections
