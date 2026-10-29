import pytest

from parser.extractor import ExtractionError, extract_text
from parser.lexer import clean_text, tokenize_lines, tokenize_words
from parser.semantic import analyze_candidate, extract_email, extract_phone, normalize_skills
from parser.syntax import detect_sections


def test_lexer_cleans_noise_and_tokenizes():
    source = "  Ada   Lovelace \r\n\r\nC++\x00 NLP  "
    assert clean_text(source) == "Ada Lovelace\nC++ NLP"
    assert tokenize_lines(source) == ["Ada Lovelace", "C++ NLP"]
    assert tokenize_words(source) == ["Ada", "Lovelace", "C++", "NLP"]


def test_section_detection_groups_resume_content():
    sections = detect_sections(
        "Ada Lovelace\nSKILLS\nPython, SQL\nWork Experience\nEngineer at Acme\nEducation\nState University"
    )
    assert sections["other"] == ["Ada Lovelace"]
    assert sections["skills"] == ["Python, SQL"]
    assert sections["experience"] == ["Engineer at Acme"]
    assert sections["education"] == ["State University"]


def test_contact_extraction_validates_email_and_phone():
    assert extract_email("Contact: ADA@example.org.") == "ADA@example.org"
    assert extract_email("not an email") is None
    assert extract_phone("Call +1 (415) 555-0132 today") == "+1 (415) 555-0132"
    assert extract_phone("Only 123") is None


def test_skill_normalization_deduplicates_aliases():
    assert normalize_skills("JS, JavaScript, py, Python, React.js, PostgreSQL") == [
        "JavaScript", "PostgreSQL", "Python", "React"
    ]


def test_semantic_analysis_normalizes_dates_degrees_and_experience_duration():
    text = (
        "Morgan Gray\nmorgan@example.com\n"
        "EDUCATION\nBachelor of Science, North University | May 2018\n"
        "EXPERIENCE\nSoftware Engineer, Example Co. | Jan 2020 - Dec 2022\n"
        "PROJECTS\nSearch Tool\nCERTIFICATIONS\nCloud Fundamentals"
    )
    sections = detect_sections(text)
    candidate = analyze_candidate(text, sections)
    assert candidate["education"] == [{
        "degree": "Bachelor of Science",
        "institution": "North University",
        "dates": ["2018-05"],
    }]
    assert candidate["experience"][0] == {
        "title": "Software Engineer",
        "organization": "Example Co.",
        "dates": ["2020-01", "2022-12"],
    }
    assert candidate["total_years_experience"] == 2
    assert candidate["projects"] == ["Search Tool"]
    assert candidate["certifications"] == ["Cloud Fundamentals"]
    assert candidate["name"] == "Morgan Gray"


def test_text_extractor_rejects_invalid_encodings_and_formats():
    with pytest.raises(ExtractionError, match="UTF-8"):
        extract_text(b"\xff", "txt")
    with pytest.raises(ExtractionError, match="PDF"):
        extract_text(b"not a PDF", "pdf")
    with pytest.raises(ExtractionError, match="DOCX"):
        extract_text(b"not a DOCX", "docx")
    with pytest.raises(ExtractionError, match="Unsupported"):
        extract_text(b"text", "rtf")
