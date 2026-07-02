"""PDF text extraction for resumes (PyMuPDF / `fitz`)."""

from __future__ import annotations

from typing import Literal

import fitz

ParseStatus = Literal["parsed", "no_text_found", "password_protected", "corrupt"]


def extract_resume_text(pdf_bytes: bytes) -> tuple[ParseStatus, str | None]:
    """Extract text from a PDF's raw bytes.

    Never raises — a malformed/corrupt PDF, a password-protected one, or a
    page-content error from the underlying MuPDF library are all reported
    as a status rather than propagated, so a bad file can never turn a
    parse attempt into a 500. A PDF that opens and decrypts fine but has no
    extractable text (e.g. a scanned image with no text layer) is
    ``no_text_found``, not an error — the file itself was valid.
    """

    try:
        doc = fitz.open(stream=pdf_bytes, filetype="pdf")
    except Exception:
        return "corrupt", None

    try:
        if doc.needs_pass and not doc.authenticate(""):
            return "password_protected", None

        try:
            text = "\n".join(page.get_text() for page in doc).strip()
        except Exception:
            return "corrupt", None
    finally:
        doc.close()

    if not text:
        return "no_text_found", None

    return "parsed", text
