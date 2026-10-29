"""Semantic analysis: extract, validate, and normalize candidate information."""

from __future__ import annotations

import re
from datetime import date, datetime
from functools import lru_cache
from typing import Any

from parser.lexer import tokenize_lines

EMAIL_RE = re.compile(r"\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b", re.I)
PHONE_RE = re.compile(r"(?<!\w)(?:\+?\d{1,3}[\s().-]*)?(?:\(?\d{2,4}\)?[\s.-]*)?\d{3,4}[\s.-]?\d{4}(?!\w)")
URL_RE = re.compile(r"https?://[^\s,;<>]+|(?:www\.)?[A-Za-z0-9.-]+\.(?:com|org|net|io|dev)/[^\s,;<>]*", re.I)
DATE_RE = re.compile(
    r"\b(Jan(?:uary)?|Feb(?:ruary)?|Mar(?:ch)?|Apr(?:il)?|May|Jun(?:e)?|Jul(?:y)?|"
    r"Aug(?:ust)?|Sep(?:tember)?|Oct(?:ober)?|Nov(?:ember)?|Dec(?:ember)?|\d{1,2})"
    r"[ ,/-]+(19\d{2}|20\d{2})\b",
    re.I,
)
YEAR_RE = re.compile(r"\b(?:19|20)\d{2}\b")
DATE_TOKEN_RE = re.compile(
    r"\b(?:(?:Jan(?:uary)?|Feb(?:ruary)?|Mar(?:ch)?|Apr(?:il)?|May|Jun(?:e)?|"
    r"Jul(?:y)?|Aug(?:ust)?|Sep(?:tember)?|Oct(?:ober)?|Nov(?:ember)?|"
    r"Dec(?:ember)?)\.?\s+(?:19|20)\d{2}|(?:19|20)\d{2}|present|current)\b",
    re.I,
)
JOB_TITLE_RE = re.compile(
    r"\b(?:[A-Za-z][A-Za-z/&-]*\s+){0,3}"
    r"(?:engineer|developer|manager|analyst|designer|intern|consultant|lead|"
    r"architect|scientist|specialist|director|administrator|coordinator)\b",
    re.I,
)

SKILL_ALIASES = {
    "js": "JavaScript",
    "javascript": "JavaScript",
    "ts": "TypeScript",
    "typescript": "TypeScript",
    "py": "Python",
    "python": "Python",
    "node": "Node.js",
    "node.js": "Node.js",
    "react.js": "React",
    "react": "React",
    "postgres": "PostgreSQL",
    "postgresql": "PostgreSQL",
    "nlp": "Natural Language Processing",
    "natural language processing": "Natural Language Processing",
    "machine learning": "Machine Learning",
    "aws": "AWS",
    "docker": "Docker",
    "flask": "Flask",
    "sql": "SQL",
    "git": "Git",
    "html": "HTML",
    "css": "CSS",
}
KNOWN_SKILLS = sorted(SKILL_ALIASES, key=len, reverse=True)
DEGREE_ALIASES = {
    "bachelor of science": "Bachelor of Science",
    "b.s.": "Bachelor of Science",
    "bs": "Bachelor of Science",
    "bachelor of arts": "Bachelor of Arts",
    "b.a.": "Bachelor of Arts",
    "master of science": "Master of Science",
    "m.s.": "Master of Science",
    "ms": "Master of Science",
    "master of business administration": "Master of Business Administration",
    "mba": "Master of Business Administration",
    "ph.d.": "Doctor of Philosophy",
    "phd": "Doctor of Philosophy",
}


@lru_cache(maxsize=1)
def _load_nlp():
    """Load spaCy opportunistically; regex heuristics remain the supported fallback."""
    try:
        import spacy

        return spacy.load("en_core_web_sm")
    except (ImportError, OSError):
        return None


def extract_email(text: str) -> str | None:
    """Find the first syntactically plausible email address."""
    match = EMAIL_RE.search(text)
    return match.group(0).rstrip(".,;:") if match else None


def extract_phone(text: str) -> str | None:
    """Find and normalize a phone number candidate; reject implausible digit counts."""
    for match in PHONE_RE.finditer(text):
        digits = re.sub(r"\D", "", match.group(0))
        if 10 <= len(digits) <= 15:
            return match.group(0).strip()
    return None


def normalize_skills(text: str) -> list[str]:
    """Map recognized skill spellings and abbreviations to canonical names."""
    lowered = text.lower()
    found = set()
    for alias in KNOWN_SKILLS:
        if re.search(rf"(?<![a-z0-9]){re.escape(alias)}(?![a-z0-9])", lowered):
            found.add(SKILL_ALIASES[alias])
    return sorted(found, key=str.casefold)


def _extract_name(text: str) -> str | None:
    lines = tokenize_lines(text)[:8]
    if not lines:
        return None
    nlp = _load_nlp()
    if nlp:
        doc = nlp("\n".join(lines[:4]))
        for entity in doc.ents:
            candidate = " ".join(entity.text.split())
            if (
                entity.label_ == "PERSON"
                and "@" not in candidate
                and not re.search(r"\d|https?://", candidate, re.I)
                and 2 <= len(candidate.split()) <= 4
            ):
                return candidate
    for line in lines:
        if "@" in line or "http" in line.lower() or re.search(r"\d", line):
            continue
        words = re.findall(r"[A-Za-z][A-Za-z'-]*", line)
        if 2 <= len(words) <= 4 and len(line) < 60:
            return " ".join(words)
    return None


def _normalize_date(value: str) -> str:
    if value.strip().lower() in {"present", "current"}:
        return date.today().strftime("%Y-%m")
    match = DATE_RE.search(value)
    if match:
        month = match.group(1)
        year = int(match.group(2))
        if month.isdigit():
            return f"{year:04d}-{int(month):02d}"
        try:
            month_number = datetime.strptime(month[:3].title(), "%b").month
        except ValueError:
            month_number = 1
        return f"{year:04d}-{month_number:02d}"
    year = YEAR_RE.search(value)
    return year.group(0) if year else value.strip()


def _normalize_degree(line: str) -> str | None:
    lowered = line.lower()
    for alias in sorted(DEGREE_ALIASES, key=len, reverse=True):
        if re.search(rf"(?<!\w){re.escape(alias)}(?!\w)", lowered):
            return DEGREE_ALIASES[alias]
    return None


def _education_entries(lines: list[str]) -> list[dict[str, Any]]:
    entries = []
    for line in lines:
        degree = _normalize_degree(line)
        if degree or re.search(r"\b(university|college|institute)\b", line, re.I):
            dates = [match.group(0) for match in DATE_TOKEN_RE.finditer(line)]
            entries.append({
                "degree": degree,
                "institution": line if not degree else _institution_from_line(line, degree),
                "dates": [_normalize_date(value) for value in dates],
            })
    return entries


def _institution_from_line(line: str, degree: str) -> str | None:
    cleaned = re.sub(re.escape(degree), "", line, flags=re.I)
    cleaned = DATE_TOKEN_RE.sub("", cleaned)
    cleaned = re.sub(r"^[\s,|–—-]+|[\s,|–—-]+$", "", cleaned)
    return cleaned or None


def _experience_entries(lines: list[str]) -> tuple[list[dict[str, Any]], int]:
    entries = []
    intervals: list[tuple[int, int]] = []
    for line in lines:
        date_values = [match.group(0) for match in DATE_TOKEN_RE.finditer(line)]
        if date_values or re.search(r"\b(engineer|developer|manager|analyst|designer|intern|consultant|lead)\b", line, re.I):
            title_match = JOB_TITLE_RE.search(line)
            title = _normalize_job_title(title_match.group(0)) if title_match else line
            organization = _extract_organization(line, title_match)
            entries.append({
                "title": title,
                "organization": organization,
                "dates": [_normalize_date(value) for value in date_values],
            })
            if len(date_values) >= 2:
                start = _date_to_month(_normalize_date(date_values[0]))
                end = _date_to_month(_normalize_date(date_values[-1]))
                if end > start:
                    intervals.append((start, end))
    merged: list[list[int]] = []
    for start, end in sorted(intervals):
        if merged and start <= merged[-1][1]:
            merged[-1][1] = max(merged[-1][1], end)
        else:
            merged.append([start, end])
    total_months = sum(end - start for start, end in merged)
    return entries, total_months // 12


def _normalize_job_title(value: str) -> str:
    """Canonicalize title casing while preserving common all-caps abbreviations."""
    abbreviations = {"hr": "HR", "it": "IT", "ui": "UI", "ux": "UX"}
    return " ".join(
        abbreviations.get(word.lower(), word.lower() if word.lower() in {"and", "of"} else word.capitalize())
        for word in value.split()
    )


def _extract_organization(line: str, title_match: re.Match[str] | None) -> str | None:
    if title_match is None:
        return None
    organization = line[title_match.end():].split("|", 1)[0]
    organization = DATE_TOKEN_RE.sub("", organization)
    organization = re.sub(r"^[\s,;:|–—-]+|[\s,;:|–—-]+$", "", organization)
    return organization or None


def _date_to_month(value: str) -> int:
    match = re.fullmatch(r"(\d{4})(?:-(\d{2}))?", value)
    if not match:
        return 0
    return int(match.group(1)) * 12 + int(match.group(2) or 1) - 1


def analyze_candidate(text: str, sections: dict[str, list[str]] | None = None) -> dict[str, Any]:
    """Semantically interpret lexical text and syntactical section groups."""
    sections = sections or {}
    links = URL_RE.findall(text)
    linkedin = next((url.rstrip(".,)") for url in links if "linkedin.com" in url.lower()), None)
    github = next((url.rstrip(".,)") for url in links if "github.com" in url.lower()), None)
    skill_text = "\n".join(sections.get("skills", [])) or text
    education = _education_entries(sections.get("education", []))
    experience, total_years = _experience_entries(sections.get("experience", []))
    projects = sections.get("projects", [])
    certifications = sections.get("certifications", [])
    return {
        "name": _extract_name(text),
        "email": extract_email(text),
        "phone": extract_phone(text),
        "linkedin": linkedin,
        "github": github,
        "skills": normalize_skills(skill_text),
        "education": education,
        "experience": experience,
        "total_years_experience": total_years,
        "projects": projects,
        "certifications": certifications,
    }
