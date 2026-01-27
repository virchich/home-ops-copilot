"""Document text extraction utilities.

This module handles extracting text from various document formats.
Each extractor function takes a file path and returns extracted text.

Supported formats:
- PDF (via pypdf with pdfplumber fallback)

Week 4 Enhancement: Section-aware preprocessing
- Detects ALL CAPS section headings from PDF text
- Converts to markdown-style headings for better chunking

Future formats can be added by implementing new extract_text_from_* functions.
"""

import logging
from collections.abc import Callable
from pathlib import Path

logger = logging.getLogger(__name__)


# =============================================================================
# TYPE ALIAS
# =============================================================================
# Define the type for extractor functions.
# Each extractor takes a Path and returns extracted text as a string.

TextExtractor = Callable[[Path], str]


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


# =============================================================================
# SECTION-AWARE PREPROCESSING (Week 4)
# =============================================================================


# Minimum length for a line to be considered a section heading
MIN_HEADING_LENGTH = 12

# Maximum length for a heading (longer lines are probably paragraphs)
MAX_HEADING_LENGTH = 60

# Minimum number of words for a heading
MIN_HEADING_WORDS = 2

# Patterns to exclude from being treated as headings (exact matches)
HEADING_EXCLUSIONS = {
    # Single words that aren't real headings
    "WARNING",
    "CAUTION",
    "NOTE",
    "IMPORTANT",
}

# Substrings that indicate non-section headings
HEADING_EXCLUSION_PATTERNS = [
    # Safety warnings
    "HAZARD",
    "WARNING!",
    "CAUTION!",
    # Page headers/footers
    "OWNER'S MANUAL",
    ": OWNER'S MANUAL",
    "CONDENSING GAS",  # Common page title
    # Figure and diagram labels
    "GAS CONTROL",
    "SHOWN IN",
    "LIMIT SWITCH",
    "GAS BURNER",
    "HOT SURFACE",
    "BEHIND GAS",
    "FILTER CABINET",
    "MANUAL RESET",  # Figure label
    # Table headers
    "HEIGHT -",
    "FILTER SIZE",
    "FILTER TYPE",
    "INSPECTION INTERVAL",
    # Notes and forms
    "NOTE TO",
    "INFORMATION:",
    "CONTACT INFORMATION",
    # Partial lines (usually figure captions or continuation)
    "(",
    ")",
    '"',
    "SETTING FOR YOUR",  # Continuation line
    "SERVICE CALL",  # Usually quoted
]


def _is_section_heading(line: str) -> bool:
    """
    Determine if a line is likely a section heading.

    Criteria for a heading:
    1. Mostly uppercase letters (>80%)
    2. Length within reasonable bounds (12-60 chars)
    3. At least 2 words
    4. Not in the exclusion list or matching exclusion patterns
    5. Doesn't look like table of contents (with dots)
    6. Has at least some alphabetic characters

    Args:
        line: A single line of text.

    Returns:
        True if the line appears to be a section heading.
    """
    stripped = line.strip()

    # Skip empty or very short lines
    if len(stripped) < MIN_HEADING_LENGTH:
        return False

    # Skip very long lines (likely paragraphs)
    if len(stripped) > MAX_HEADING_LENGTH:
        return False

    # Skip if in exclusion list
    if stripped in HEADING_EXCLUSIONS:
        return False

    # Skip if matches any exclusion pattern
    stripped_upper = stripped.upper()
    for pattern in HEADING_EXCLUSION_PATTERNS:
        if pattern in stripped_upper:
            return False

    # Skip if looks like table of contents (lots of dots)
    if stripped.count(".") > 2:
        return False

    # Skip if it's a page marker
    if stripped.startswith("[Page"):
        return False

    # Require minimum number of words
    words = stripped.split()
    if len(words) < MIN_HEADING_WORDS:
        return False

    # Get only alphabetic characters
    alpha_chars = [c for c in stripped if c.isalpha()]
    if len(alpha_chars) < 8:
        return False

    # Check if mostly uppercase
    upper_count = sum(1 for c in alpha_chars if c.isupper())
    upper_ratio = upper_count / len(alpha_chars) if alpha_chars else 0

    # Consider it a heading if >80% uppercase
    return upper_ratio > 0.8


def preprocess_text_with_sections(text: str) -> str:
    """
    Preprocess text to add markdown-style section headings.

    This function detects ALL CAPS section headings in PDF-extracted text
    and converts them to markdown format (## HEADING). This enables
    structure-aware chunking using MarkdownNodeParser.

    Args:
        text: Raw extracted text from a document.

    Returns:
        Text with markdown-style headings inserted before sections.

    Example:
        Input:
            "SAFETY CONSIDERATIONS
            Installing and servicing..."

        Output:
            "## SAFETY CONSIDERATIONS
            Installing and servicing..."
    """
    lines = text.split("\n")
    processed_lines = []

    for line in lines:
        if _is_section_heading(line):
            # Convert to markdown heading
            heading = line.strip()
            # Use ## for main sections (h2 level)
            processed_lines.append(f"\n## {heading}\n")
        else:
            processed_lines.append(line)

    return "\n".join(processed_lines)
