"""Redline - AI Resume Analyzer Application Factory and Web Server.

Built for the GDG BPPIMT AI/ML Team selection task.
Provides PDF ingestion, skill extraction, TF-IDF cosine matching, ATS readiness auditing,
weak-verb proofing, and Google Gemini AI recommendation endpoints.
"""

from __future__ import annotations

import datetime
import logging
import os
import re
from typing import Any, Dict, List, Optional, Tuple

from dotenv import load_dotenv
from flask import Flask, jsonify, render_template, request, Response
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address

from services.ai_client import generate_ai_suggestions
from services.ats import evaluate_ats_readiness
from services.improver import analyze_improvements
from services.matcher import analyze_match
from services.parser import parse_resume
from services.pdf_extractor import (
    extract_pdf_text,
    PDFExtractionError,
    validate_pdf_upload,
)
from services.skills import load_taxonomy

# Load environment variables from .env
load_dotenv()

# Logging configuration - never log resume plain text or PII
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("redline")


def create_app() -> Flask:
    """Application factory for Redline."""
    app = Flask(__name__)

    # Configuration
    max_mb = int(os.environ.get("MAX_CONTENT_LENGTH", 5 * 1024 * 1024))
    app.config["MAX_CONTENT_LENGTH"] = max_mb
    app.config["SECRET_KEY"] = os.environ.get("SECRET_KEY", "dev-secret-key-redline-2026")
    app.config["JSON_SORT_KEYS"] = False

    # Initialize rate limiter
    limiter = Limiter(
        get_remote_address,
        app=app,
        default_limits=["120 per minute"],
        storage_uri="memory://",
    )

    # Pre-warm skills taxonomy cache
    try:
        load_taxonomy()
        logger.info("Skills taxonomy loaded and cached successfully.")
    except Exception as exc:
        logger.error("Failed to load initial skills taxonomy: %s", exc)

    # ---------------------------------------------------------
    # Global Error Handlers (Consistent JSON errors)
    # ---------------------------------------------------------
    @app.errorhandler(413)
    def handle_request_entity_too_large(error: Any) -> Tuple[Response, int]:
        return jsonify({
            "error": "The uploaded PDF exceeds the 5 MB maximum size limit. Please upload a smaller file.",
            "code": "FILE_TOO_LARGE",
        }), 413

    @app.errorhandler(429)
    def handle_rate_limit_exceeded(error: Any) -> Tuple[Response, int]:
        return jsonify({
            "error": "Rate limit exceeded. Please wait a brief moment before submitting another analysis.",
            "code": "RATE_LIMIT_EXCEEDED",
        }), 429

    @app.errorhandler(404)
    def handle_not_found(error: Any) -> Tuple[Response, int]:
        if request.path.startswith("/api/"):
            return jsonify({
                "error": "The requested API endpoint was not found.",
                "code": "NOT_FOUND",
            }), 404
        return render_template("index.html"), 404

    @app.errorhandler(405)
    def handle_method_not_allowed(error: Any) -> Tuple[Response, int]:
        return jsonify({
            "error": f"Method {request.method} is not allowed for this route.",
            "code": "METHOD_NOT_ALLOWED",
        }), 405

    @app.errorhandler(500)
    def handle_internal_server_error(error: Any) -> Tuple[Response, int]:
        logger.error("Unhandled Internal Server Error: %s", str(error))
        return jsonify({
            "error": "An unexpected server error occurred while processing your request. Please try again.",
            "code": "INTERNAL_SERVER_ERROR",
        }), 500

    @app.errorhandler(PDFExtractionError)
    def handle_pdf_extraction_error(error: PDFExtractionError) -> Tuple[Response, int]:
        return jsonify({
            "error": error.message,
            "code": error.code,
        }), error.status_code

    # ---------------------------------------------------------
    # Web & API Routes
    # ---------------------------------------------------------
    @app.route("/")
    def index() -> str:
        """Render the Redline manuscript editor interface."""
        return render_template("index.html")

    @app.route("/api/health", methods=["GET"])
    def health_check() -> Tuple[Response, int]:
        """Health check endpoint for monitoring and Render liveness probes."""
        model_name = os.environ.get("GEMINI_MODEL", "gemini-2.5-flash")
        has_api_key = bool(os.environ.get("GEMINI_API_KEY"))

        return jsonify({
            "status": "healthy",
            "app": "Redline AI Resume Analyzer",
            "version": "1.0.0",
            "environment": os.environ.get("FLASK_ENV", "production"),
            "ai_configured": has_api_key,
            "ai_model": model_name,
            "timestamp": datetime.datetime.utcnow().isoformat() + "Z",
        }), 200

    @app.route("/api/analyze", methods=["POST"])
    @limiter.limit("20 per minute")
    def analyze_resume() -> Tuple[Response, int]:
        """Analyze a PDF resume against a target job description.

        Accepts multipart/form-data:
            - resume: PDF file
            - job_description: Plain text string
        """
        # 1. Validate Job Description presence and length
        jd_text = request.form.get("job_description", "").strip()
        if not jd_text:
            return jsonify({
                "error": "Job description is missing. Please paste the job description text.",
                "code": "EMPTY_JOB_DESCRIPTION",
            }), 400

        jd_words = jd_text.split()
        if len(jd_words) < 40:
            return jsonify({
                "error": (
                    f"Job description is too brief ({len(jd_words)} words provided). "
                    "Please provide at least 40 words to ensure accurate skill matching and TF-IDF analysis."
                ),
                "code": "JD_TOO_SHORT",
            }), 400

        # 2. Validate PDF file presence
        if "resume" not in request.files:
            return jsonify({
                "error": "No resume file was uploaded. Please attach a .pdf resume.",
                "code": "NO_FILE_UPLOADED",
            }), 400

        file = request.files["resume"]
        if not file or not file.filename or not file.filename.strip():
            return jsonify({
                "error": "Selected file has an invalid or empty filename.",
                "code": "INVALID_FILENAME",
            }), 400

        # Read binary content
        file_bytes = file.read()

        # 3. Server-side PDF validation (extension, MIME, size, magic bytes)
        validate_pdf_upload(
            file_bytes=file_bytes,
            filename=file.filename,
            content_type=file.content_type,
            max_size=app.config["MAX_CONTENT_LENGTH"],
        )

        # 4. Extract text via PyMuPDF
        extraction = extract_pdf_text(file_bytes)

        # Detect scanned or empty PDFs
        if extraction.get("is_scanned_or_empty"):
            warning = extraction.get("warning") or "This PDF appears to be a scanned image or contains no selectable text."
            return jsonify({
                "error": warning,
                "code": "SCANNED_OR_EMPTY_PDF",
                "details": {
                    "page_count": extraction.get("page_count", 0),
                    "char_count": extraction.get("char_count", 0),
                    "image_count": extraction.get("image_count", 0),
                },
            }), 422

        resume_text = extraction["text"]

        # 5. Extract structured resume information
        parsed_resume = parse_resume(resume_text)

        # 6. Run match analysis (TF-IDF + Skill Overlap)
        match_result = analyze_match(resume_text=resume_text, jd_text=jd_text)

        # 7. Run ATS readiness evaluation
        ats_result = evaluate_ats_readiness(
            full_text=resume_text,
            parsed_resume=parsed_resume,
        )

        # 8. Run weak verb and metrics improvement audit
        improvement_result = analyze_improvements(
            full_text=resume_text,
            experience_text=parsed_resume.get("raw_sections", {}).get("experience", ""),
        )

        # 9. Extract candidate bullet points for context
        candidate_bullets = [
            b for exp in parsed_resume.get("experience", []) for b in exp.get("bullets", [])
        ]
        if not candidate_bullets:
            candidate_bullets = [
                b for proj in parsed_resume.get("projects", []) for b in proj.get("bullets", [])
            ]

        # 10. Generate AI suggestions with guaranteed resilient fallback
        ai_result = generate_ai_suggestions(
            resume_text=resume_text,
            jd_text=jd_text,
            matched_skills=match_result["skills"]["matched"],
            missing_skills=match_result["skills"]["missing"],
            weak_verbs=improvement_result["weak_verbs_detected"],
            candidate_bullets=candidate_bullets,
            ats_checklist=ats_result["checklist"],
            score=match_result["overall_score"],
        )

        # 11. Build annotated resume payload (matched skills highlighted + margin notes)
        matched_terms_list = match_result["skills"]["matched"]
        annotations: List[Dict[str, Any]] = []
        for term in matched_terms_list:
            annotations.append({
                "term": term,
                "type": "matched_skill",
            })

        margin_notes: List[Dict[str, Any]] = []
        note_id = 1
        for wv in improvement_result["weak_verbs_detected"][:5]:
            margin_notes.append({
                "id": note_id,
                "type": "weak_verb",
                "target": wv["weak_phrase"],
                "note": f"Passive verb: replace with '{wv['suggested_alternatives'][0]}' to assert ownership.",
            })
            note_id += 1

        for mm in improvement_result["bullets_missing_metrics"][:3]:
            margin_notes.append({
                "id": note_id,
                "type": "missing_metric",
                "target": mm["bullet"][:40] + "...",
                "note": "Unquantified accomplishment: add a baseline, metric percentage, or throughput scale.",
            })
            note_id += 1

        # 12. Assemble complete JSON response
        response_payload = {
            "success": True,
            "timestamp": datetime.datetime.utcnow().isoformat() + "Z",
            "metadata": {
                "filename": file.filename,
                "file_size": len(file_bytes),
                "page_count": extraction["page_count"],
                "word_count": extraction["word_count"],
                "jd_word_count": len(jd_words),
            },
            "match": match_result,
            "profile": {
                "contacts": parsed_resume["contacts"],
                "sections_detected": parsed_resume["sections"],
                "summary": parsed_resume["summary"],
                "education": parsed_resume["education"],
                "experience": parsed_resume["experience"],
                "projects": parsed_resume["projects"],
                "certifications": parsed_resume["certifications"],
            },
            "ats_check": ats_result,
            "improvement_assistant": improvement_result,
            "ai_suggestions": ai_result,
            "annotated_resume": {
                "raw_text": resume_text,
                "pages": extraction["pages"],
                "annotations": annotations,
                "margin_notes": margin_notes,
            },
        }

        logger.info(
            "Successfully analyzed resume '%s' (%d words). Match score: %d%%, ATS score: %d%%.",
            file.filename,
            extraction["word_count"],
            match_result["overall_score"],
            ats_result["score"],
        )

        return jsonify(response_payload), 200

    return app


app = create_app()

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=False)
