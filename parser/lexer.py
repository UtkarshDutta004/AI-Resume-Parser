"""Lexical analysis: normalize resume text and split it into tokens."""

from __future__ import annotations

import re
import unicodedata


def clean_text(text: str) -> str:
    """Remove extraction noise while preserving meaningful line boundaries."""
    normalized = unicodedata.normalize("NFKC", text).replace("\x00", "")
    normalized = normalized.replace("\r\n", "\n").replace("\r", "\n")
    lines = []
    for line in normalized.split("\n"):
        line = re.sub(r"[ \t\f\v]+", " ", line).strip()
        if line:
            lines.append(line)
    return "\n".join(lines)


def tokenize_words(text: str) -> list[str]:
    """Return word-like tokens, including common technical skill punctuation."""
    return re.findall(r"[A-Za-z0-9]+(?:[+#./'-][A-Za-z0-9+#./'-]*)*", clean_text(text))


def tokenize_lines(text: str) -> list[str]:
    """Return non-empty, normalized source lines."""
    return [line for line in clean_text(text).splitlines() if line]
