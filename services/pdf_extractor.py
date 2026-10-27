"""PDF extraction and validation service using PyMuPDF (fitz).

Implements strict validation:
- Extension verification (.pdf)
- MIME type check
- Magic bytes (%PDF-) validation
- Size validation (<= 5MB)
- Corruption and encryption protection
- Scanned / image-only resume detection with friendly guidance
"""

from __future__ import annotations

import io
from typing import Any, Dict, List, Optional, Tuple

try:
    import fitz  # PyMuPDF
except ImportError:
    fitz = None  # Handled gracefully if not yet loaded in active process


MAX_FILE_SIZE = 5 * 1024 * 1024  # 5 MB
PDF_MAGIC_BYTES = b"%PDF-"
MIN_READABLE_CHARS = 50
MIN_READABLE_WORDS = 15


class PDFExtractionError(Exception):
    """Base exception for PDF extraction failures."""
    def __init__(self, message: str, code: str = "PDF_ERROR", status_code: int = 400):
        super().__init__(message)
        self.message = message
        self.code = code
        self.status_code = status_code


def validate_pdf_upload(
    file_bytes: bytes,
    filename: Optional[str] = None,
    content_type: Optional[str] = None,
    max_size: int = MAX_FILE_SIZE,
) -> None:
    """Validate uploaded PDF file on extension, MIME type, size, and magic bytes.

    Raises:
        PDFExtractionError: If any validation rule fails.
    """
    if not file_bytes or len(file_bytes) == 0:
        raise PDFExtractionError("No file content was provided.", code="EMPTY_FILE", status_code=400)

    # 1. Size check
    if len(file_bytes) > max_size:
        max_mb = max_size / (1024 * 1024)
        actual_mb = len(file_bytes) / (1024 * 1024)
        raise PDFExtractionError(
            f"File size exceeds the 5 MB limit (received {actual_mb:.2f} MB, maximum allowed is {max_mb:.0f} MB).",
            code="FILE_TOO_LARGE",
            status_code=413,
        )

    # 2. Filename extension check
    if filename:
        clean_name = filename.strip().lower()
        if not clean_name.endswith(".pdf"):
            raise PDFExtractionError(
                f"Invalid file extension for '{filename}'. Only .pdf files are accepted.",
                code="INVALID_EXTENSION",
                status_code=400,
            )

    # 3. MIME type check (when provided by client or request)
    if content_type:
        allowed_mimes = {"application/pdf", "application/x-pdf", "application/acrobat", "applications/vnd.pdf", "text/pdf"}
        clean_mime = content_type.split(";")[0].strip().lower()
        if clean_mime and clean_mime not in allowed_mimes and clean_mime != "application/octet-stream":
            raise PDFExtractionError(
                f"Invalid MIME type '{clean_mime}'. Expected 'application/pdf'.",
                code="INVALID_MIME_TYPE",
                status_code=400,
            )

    # 4. Real PDF magic bytes check (%PDF- in preamble)
    # The PDF specification allows up to 1024 bytes of preamble before %PDF-
    preamble = file_bytes[:1024]
    if PDF_MAGIC_BYTES not in preamble:
        raise PDFExtractionError(
            "The uploaded file is not a valid PDF document (missing %PDF- signature).",
            code="INVALID_PDF_HEADER",
            status_code=400,
        )


def extract_pdf_text(file_bytes: bytes) -> Dict[str, Any]:
    """Extract full text, page breakdown, and metadata from PDF bytes using PyMuPDF.

    Args:
        file_bytes: Raw binary content of the PDF.

    Returns:
        Dict with keys:
            - text: concatenated text string
            - pages: list of per-page text strings
            - page_count: int
            - word_count: int
            - char_count: int
            - is_scanned_or_empty: bool
            - message: Optional warning message if scanned or low text

    Raises:
        PDFExtractionError: For encrypted, corrupted, or unreadable PDFs.
    """
    global fitz
    if fitz is None:
        try:
            import fitz as pymupdf
            fitz = pymupdf
        except ImportError as exc:
            raise PDFExtractionError(
                "PyMuPDF library is not installed on the server.",
                code="SERVER_DEPENDENCY_ERROR",
                status_code=500,
            ) from exc

    try:
        doc = fitz.open(stream=file_bytes, filetype="pdf")
    except Exception as exc:
        raise PDFExtractionError(
            f"Unable to read PDF file. The file may be corrupted or malformed ({str(exc)}).",
            code="CORRUPTED_PDF",
            status_code=400,
        ) from exc

    try:
        # Check for encryption
        if doc.is_encrypted:
            # Try authenticating with empty password
            if not doc.authenticate(""):
                raise PDFExtractionError(
                    "This PDF is password-protected or encrypted. Please remove password protection before uploading.",
                    code="ENCRYPTED_PDF",
                    status_code=400,
                )

        page_count = len(doc)
        if page_count == 0:
            raise PDFExtractionError(
                "The PDF document contains no pages.",
                code="EMPTY_PDF_PAGES",
                status_code=400,
            )

        pages_text: List[str] = []
        total_images = 0

        for page_idx in range(page_count):
            page = doc.load_page(page_idx)
            text = page.get_text("text") or ""
            pages_text.append(text)
            total_images += len(page.get_images())

        full_text = "\n\n".join(pages_text).strip()
        words = full_text.split()
        word_count = len(words)
        char_count = len(full_text)

        # Scanned PDF or empty text detection
        is_scanned_or_empty = (char_count < MIN_READABLE_CHARS or word_count < MIN_READABLE_WORDS)
        warning_msg: Optional[str] = None

        if is_scanned_or_empty:
            if total_images > 0:
                warning_msg = (
                    "This PDF appears to be a scanned image or photograph without selectable text. "
                    "AI Resume Analyzer requires selectable text to analyze your resume accurately. "
                    "Please upload a PDF exported directly from Word, Google Docs, Canva, or LaTeX."
                )
            else:
                warning_msg = (
                    "Almost no readable text could be extracted from this PDF. "
                    "Please ensure your resume contains selectable text and try again."
                )

        return {
            "text": full_text,
            "pages": pages_text,
            "page_count": page_count,
            "word_count": word_count,
            "char_count": char_count,
            "image_count": total_images,
            "is_scanned_or_empty": is_scanned_or_empty,
            "warning": warning_msg,
        }

    except PDFExtractionError:
        raise
    except Exception as exc:
        raise PDFExtractionError(
            f"An unexpected error occurred while parsing the PDF: {str(exc)}",
            code="PARSING_FAILED",
            status_code=500,
        ) from exc
    finally:
        try:
            doc.close()
        except Exception:
            pass
