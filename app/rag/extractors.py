"""Document text extraction utilities.

This module handles extracting text from various document formats.
Each extractor function takes a file path and returns extracted text.

Supported formats:
- PDF (via pypdf with pdfplumber fallback)

Future formats can be added by implementing new extract_text_from_* functions.
"""

import logging
from pathlib import Path
from typing import Protocol

logger = logging.getLogger(__name__)


# =============================================================================
# EXTRACTOR PROTOCOL
# =============================================================================
# Define the interface for extractors to enable type checking and future
# polymorphism (e.g., factory pattern for different file types).


class TextExtractor(Protocol):
    """Protocol for text extraction functions."""

    def __call__(self, file_path: Path) -> str:
        """Extract text from a file.

        Args:
            file_path: Path to the file to extract text from.

        Returns:
            Extracted text as a single string.

        Raises:
            FileNotFoundError: If the file doesn't exist.
            ValueError: If the file format is unsupported or extraction fails.
        """
        ...


# =============================================================================
# PDF EXTRACTION
# =============================================================================


def extract_text_from_pdf(pdf_path: Path) -> str:
    """
    Extract text from a PDF file.

    Tries pypdf first (faster), falls back to pdfplumber (more robust)
    if pypdf fails due to font encoding or other issues.

    Args:
        pdf_path: Path to the PDF file.

    Returns:
        Extracted text as a single string with page markers.

    Raises:
        FileNotFoundError: If the PDF file doesn't exist.
        ValueError: If text extraction fails with both methods.
    """
    if not pdf_path.exists():
        raise FileNotFoundError(f"PDF file not found: {pdf_path}")

    # Try pypdf first - it's faster for simple PDFs
    try:
        text = _extract_with_pypdf(pdf_path)
        if text.strip():
            return text
        logger.warning(f"pypdf returned empty text for {pdf_path.name}, trying pdfplumber...")
    except Exception as e:
        logger.warning(f"pypdf failed for {pdf_path.name}: {e}, trying pdfplumber...")

    # Fall back to pdfplumber - handles complex fonts better
    try:
        text = _extract_with_pdfplumber(pdf_path)
        if text.strip():
            return text
        raise ValueError(f"No text could be extracted from {pdf_path.name}")
    except Exception as e:
        raise ValueError(f"Failed to extract text from {pdf_path.name}: {e}") from e


def _extract_with_pypdf(pdf_path: Path) -> str:
    """Extract text using pypdf.

    Args:
        pdf_path: Path to the PDF file.

    Returns:
        Extracted text with page markers.
    """
    from pypdf import PdfReader

    reader = PdfReader(pdf_path)
    text_parts = []

    for page_num, page in enumerate(reader.pages, start=1):
        page_text = page.extract_text()
        if page_text:
            text_parts.append(f"\n[Page {page_num}]\n{page_text}")

    return "\n".join(text_parts)


def _extract_with_pdfplumber(pdf_path: Path) -> str:
    """Extract text using pdfplumber (more robust for complex PDFs).

    Args:
        pdf_path: Path to the PDF file.

    Returns:
        Extracted text with page markers.
    """
    import pdfplumber

    text_parts = []

    with pdfplumber.open(pdf_path) as pdf:
        for page_num, page in enumerate(pdf.pages, start=1):
            page_text = page.extract_text()
            if page_text:
                text_parts.append(f"\n[Page {page_num}]\n{page_text}")

    return "\n".join(text_parts)


# =============================================================================
# EXTRACTOR REGISTRY
# =============================================================================
# Maps file extensions to their extractor functions.
# This enables automatic extractor selection based on file type.

EXTRACTORS: dict[str, TextExtractor] = {
    ".pdf": extract_text_from_pdf,
}


def get_extractor(file_path: Path) -> TextExtractor:
    """Get the appropriate extractor for a file based on its extension.

    Args:
        file_path: Path to the file.

    Returns:
        Extractor function for the file type.

    Raises:
        ValueError: If no extractor exists for the file type.
    """
    suffix = file_path.suffix.lower()
    if suffix not in EXTRACTORS:
        supported = ", ".join(EXTRACTORS.keys())
        raise ValueError(f"Unsupported file type: {suffix}. Supported types: {supported}")
    return EXTRACTORS[suffix]


def extract_text(file_path: Path) -> str:
    """Extract text from a file using the appropriate extractor.

    This is the main entry point for text extraction. It automatically
    selects the correct extractor based on file extension.

    Args:
        file_path: Path to the file.

    Returns:
        Extracted text as a string.

    Raises:
        FileNotFoundError: If the file doesn't exist.
        ValueError: If the file type is unsupported or extraction fails.
    """
    extractor = get_extractor(file_path)
    return extractor(file_path)
