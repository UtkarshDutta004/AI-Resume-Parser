"""Flask entry point for the AI Resume Parser."""

from __future__ import annotations

import os
from pathlib import Path

from flask import Flask, jsonify, render_template, request
from werkzeug.exceptions import RequestEntityTooLarge
from werkzeug.utils import secure_filename

from parser.extractor import ExtractionError, extract_text
from parser.lexer import clean_text
from parser.semantic import analyze_candidate
from parser.syntax import detect_sections

ALLOWED_EXTENSIONS = {"pdf", "docx", "txt"}
MAX_FILE_SIZE = 5 * 1024 * 1024


def create_app(test_config: dict | None = None) -> Flask:
    app = Flask(__name__)
    app.config.from_mapping(
        MAX_UPLOAD_SIZE=MAX_FILE_SIZE,
        MAX_CONTENT_LENGTH=MAX_FILE_SIZE + 64 * 1024,
        JSON_SORT_KEYS=False,
    )
    if test_config:
        app.config.update(test_config)

    @app.get("/")
    def index():
        return render_template("index.html")

    @app.post("/api/parse")
    def parse_resume():
        uploaded = request.files.get("file")
        if uploaded is None or not uploaded.filename:
            return jsonify({"error": "Choose a resume file to upload."}), 400

        filename = secure_filename(uploaded.filename)
        if not filename:
            return jsonify({"error": "The uploaded filename is invalid."}), 400
        extension = Path(filename).suffix.lower().lstrip(".")
        if extension not in ALLOWED_EXTENSIONS:
            return jsonify({"error": "Unsupported file type. Upload a PDF, DOCX, or TXT file."}), 415

        try:
            file_bytes = uploaded.read()
            if not file_bytes:
                return jsonify({"error": "The uploaded file is empty."}), 400
            if len(file_bytes) > app.config["MAX_UPLOAD_SIZE"]:
                return jsonify({"error": "File exceeds the 5 MB upload limit."}), 413
            text = clean_text(extract_text(file_bytes, extension))
            if not text.strip():
                return jsonify({"error": "No readable text was found in the uploaded resume."}), 422
            sections = detect_sections(text)
            candidate = analyze_candidate(text, sections)
        except ExtractionError as exc:
            return jsonify({"error": str(exc)}), 422
        except Exception:
            app.logger.exception("Resume parsing failed")
            return jsonify({"error": "The resume could not be parsed. Check the file and try again."}), 500

        return jsonify({"success": True, "filename": filename, "candidate": candidate})

    @app.errorhandler(RequestEntityTooLarge)
    def file_too_large(_error):
        return jsonify({"error": "File exceeds the 5 MB upload limit."}), 413

    return app


app = create_app()

@app.get("/health")
def health():
    return {"status": "ok"}, 200

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", "5000")), debug=False)
