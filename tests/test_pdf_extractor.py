"""Tests for PDF extraction and validation service."""

from pathlib import Path
import pytest
from services.pdf_extractor import (
    extract_pdf_text,
    PDFExtractionError,
    validate_pdf_upload,
)

SAMPLES_DIR = Path(__file__).resolve().parent.parent / "samples"


def test_validate_pdf_upload_valid():
    valid_pdf_bytes = b"%PDF-1.4\n1 0 obj\n<<\n>>\nendobj\ntrailer\n<<\n>>\n%%EOF"
    # Should not raise exception
    validate_pdf_upload(valid_pdf_bytes, filename="resume.pdf", content_type="application/pdf")


def test_validate_pdf_upload_wrong_extension():
    data = b"%PDF-1.4 mock data"
    with pytest.raises(PDFExtractionError) as exc_info:
        validate_pdf_upload(data, filename="resume.docx", content_type="application/pdf")
    assert exc_info.value.code == "INVALID_EXTENSION"
    assert exc_info.value.status_code == 400


def test_validate_pdf_upload_file_too_large():
    huge_data = b"%PDF-" + b"0" * (6 * 1024 * 1024)  # 6 MB
    with pytest.raises(PDFExtractionError) as exc_info:
        validate_pdf_upload(huge_data, filename="resume.pdf", max_size=5 * 1024 * 1024)
    assert exc_info.value.code == "FILE_TOO_LARGE"
    assert exc_info.value.status_code == 413


def test_validate_pdf_upload_invalid_magic_bytes():
    bad_data = b"NOT_A_PDF_DOCUMENT_CONTENT"
    with pytest.raises(PDFExtractionError) as exc_info:
        validate_pdf_upload(bad_data, filename="resume.pdf", content_type="application/pdf")
    assert exc_info.value.code == "INVALID_PDF_HEADER"
    assert exc_info.value.status_code == 400


def test_extract_pdf_text_valid_sample():
    sample_path = SAMPLES_DIR / "valid_sample_resume.pdf"
    if not sample_path.exists():
        pytest.skip("valid_sample_resume.pdf not found")

    with open(sample_path, "rb") as f:
        content = f.read()

    result = extract_pdf_text(content)
    assert result["page_count"] >= 1
    assert result["word_count"] > 100
    assert not result["is_scanned_or_empty"]
    assert "Alex Chen" in result["text"] or "ALEX CHEN" in result["text"]


def test_extract_pdf_text_scanned_image_detection():
    sample_path = SAMPLES_DIR / "scanned_image_resume.pdf"
    if not sample_path.exists():
        pytest.skip("scanned_image_resume.pdf not found")

    with open(sample_path, "rb") as f:
        content = f.read()

    result = extract_pdf_text(content)
    assert result["is_scanned_or_empty"] is True
    assert result["warning"] is not None
