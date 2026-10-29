import json
from pathlib import Path

import pytest

from parser.extractor import extract_text
from parser.lexer import clean_text
from parser.semantic import analyze_candidate
from parser.syntax import detect_sections

ROOT = Path(__file__).resolve().parents[1]
SAMPLE_CASES = [
    ("sample_resume_1.pdf", "sample_resume_1.json", "pdf"),
    ("sample_resume_2.docx", "sample_resume_2.json", "docx"),
    ("sample_resume_3.txt", "sample_resume_3.json", "txt"),
]


@pytest.mark.parametrize(("filename", "expected_filename", "extension"), SAMPLE_CASES)
def test_samples_parse_to_expected_schema(filename, expected_filename, extension):
    sample_path = ROOT / "samples" / filename
    expected_path = ROOT / "samples" / "expected_output" / expected_filename
    assert sample_path.exists(), f"Run `python scripts/generate_samples.py` to create {filename}."

    text = clean_text(extract_text(sample_path.read_bytes(), extension))
    actual = analyze_candidate(text, detect_sections(text))
    expected = json.loads(expected_path.read_text(encoding="utf-8"))
    assert actual.keys() == expected.keys()
    for field in ("name", "email", "phone", "linkedin", "github", "skills", "education", "projects", "certifications"):
        assert actual[field] == expected[field]
    assert [entry["title"] for entry in actual["experience"]] == [
        entry["title"] for entry in expected["experience"]
    ]
