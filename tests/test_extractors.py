"""Tests for the extractors module.

Unit tests use mocked PDF libraries to test extraction logic without real files.
"""

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from app.rag.extractors import (
    EXTRACTORS,
    _extract_with_pdfplumber,
    _extract_with_pypdf,
    _is_section_heading,
    extract_text,
    extract_text_from_pdf,
    get_extractor,
    preprocess_text_with_sections,
)

# =============================================================================
# TEST FIXTURES
# =============================================================================


def create_mock_pypdf_reader(pages: list[str | None]) -> MagicMock:
    """Create a mock PdfReader with the given page texts."""
    mock_reader = MagicMock()
    mock_pages = []
    for text in pages:
        mock_page = MagicMock()
        mock_page.extract_text.return_value = text
        mock_pages.append(mock_page)
    mock_reader.pages = mock_pages
    return mock_reader


def create_mock_pdfplumber_pdf(pages: list[str]) -> MagicMock:
    """Create a mock pdfplumber PDF with the given page texts."""
    mock_pdf = MagicMock()
    mock_pages = []
    for text in pages:
        mock_page = MagicMock()
        mock_page.extract_text.return_value = text
        mock_pages.append(mock_page)
    mock_pdf.pages = mock_pages
    mock_pdf.__enter__ = MagicMock(return_value=mock_pdf)
    mock_pdf.__exit__ = MagicMock(return_value=False)
    return mock_pdf


# =============================================================================
# UNIT TESTS - Extractor Registry
# =============================================================================


class TestExtractorRegistry:
    """Tests for the extractor registry and get_extractor function."""

    def test_pdf_extractor_registered(self) -> None:
        """PDF extractor should be registered in EXTRACTORS."""
        assert ".pdf" in EXTRACTORS
        assert EXTRACTORS[".pdf"] == extract_text_from_pdf

    def test_get_extractor_returns_pdf_extractor(self) -> None:
        """get_extractor should return PDF extractor for .pdf files."""
        extractor = get_extractor(Path("document.pdf"))
        assert extractor == extract_text_from_pdf

    def test_get_extractor_case_insensitive(self) -> None:
        """get_extractor should handle uppercase extensions."""
        extractor = get_extractor(Path("document.PDF"))
        assert extractor == extract_text_from_pdf

    def test_get_extractor_raises_for_unsupported_type(self) -> None:
        """get_extractor should raise ValueError for unsupported file types."""
        with pytest.raises(ValueError, match="Unsupported file type: .docx"):
            get_extractor(Path("document.docx"))

    def test_get_extractor_error_lists_supported_types(self) -> None:
        """Error message should list supported file types."""
        with pytest.raises(ValueError, match=r"\.pdf"):
            get_extractor(Path("document.txt"))


# =============================================================================
# UNIT TESTS - extract_text (Main Entry Point)
# =============================================================================


class TestExtractText:
    """Tests for the extract_text main entry point."""

    def test_extract_text_delegates_to_correct_extractor(self) -> None:
        """extract_text should use the appropriate extractor for file type."""
        with patch("app.rag.extractors.extract_text_from_pdf") as mock_extract:
            mock_extract.return_value = "extracted text"

            # Need to patch the registry to use our mock
            with patch.dict(EXTRACTORS, {".pdf": mock_extract}):
                result = extract_text(Path("test.pdf"))

            mock_extract.assert_called_once_with(Path("test.pdf"))
            assert result == "extracted text"

    def test_extract_text_raises_for_unsupported_type(self) -> None:
        """extract_text should raise ValueError for unsupported types."""
        with pytest.raises(ValueError, match="Unsupported file type"):
            extract_text(Path("document.xyz"))


# =============================================================================
# UNIT TESTS - PDF Extraction with pypdf
# =============================================================================


class TestExtractWithPypdf:
    """Tests for _extract_with_pypdf function."""

    def test_extracts_single_page(self) -> None:
        """Should extract text from a single page PDF."""
        mock_reader = create_mock_pypdf_reader(["Page one content"])

        with patch("pypdf.PdfReader", return_value=mock_reader):
            result = _extract_with_pypdf(Path("test.pdf"))

        assert "[Page 1]" in result
        assert "Page one content" in result

    def test_extracts_multiple_pages(self) -> None:
        """Should extract text from multiple pages with page markers."""
        mock_reader = create_mock_pypdf_reader(
            [
                "First page content",
                "Second page content",
                "Third page content",
            ]
        )

        with patch("pypdf.PdfReader", return_value=mock_reader):
            result = _extract_with_pypdf(Path("test.pdf"))

        assert "[Page 1]" in result
        assert "[Page 2]" in result
        assert "[Page 3]" in result
        assert "First page content" in result
        assert "Second page content" in result
        assert "Third page content" in result

    def test_skips_empty_pages(self) -> None:
        """Should skip pages with no text."""
        mock_reader = create_mock_pypdf_reader(
            [
                "First page",
                "",  # Empty page
                None,  # None return
                "Fourth page",
            ]
        )

        with patch("pypdf.PdfReader", return_value=mock_reader):
            result = _extract_with_pypdf(Path("test.pdf"))

        assert "[Page 1]" in result
        assert "[Page 2]" not in result
        assert "[Page 3]" not in result
        assert "[Page 4]" in result

    def test_returns_empty_string_for_empty_pdf(self) -> None:
        """Should return empty string for PDF with no extractable text."""
        mock_reader = create_mock_pypdf_reader([])

        with patch("pypdf.PdfReader", return_value=mock_reader):
            result = _extract_with_pypdf(Path("test.pdf"))

        assert result == ""


# =============================================================================
# UNIT TESTS - PDF Extraction with pdfplumber
# =============================================================================


class TestExtractWithPdfplumber:
    """Tests for _extract_with_pdfplumber function."""

    def test_extracts_single_page(self) -> None:
        """Should extract text from a single page PDF."""
        mock_pdf = create_mock_pdfplumber_pdf(["Page one content"])

        with patch("pdfplumber.open", return_value=mock_pdf):
            result = _extract_with_pdfplumber(Path("test.pdf"))

        assert "[Page 1]" in result
        assert "Page one content" in result

    def test_extracts_multiple_pages(self) -> None:
        """Should extract text from multiple pages with page markers."""
        mock_pdf = create_mock_pdfplumber_pdf(
            [
                "First page content",
                "Second page content",
            ]
        )

        with patch("pdfplumber.open", return_value=mock_pdf):
            result = _extract_with_pdfplumber(Path("test.pdf"))

        assert "[Page 1]" in result
        assert "[Page 2]" in result
        assert "First page content" in result
        assert "Second page content" in result

    def test_skips_empty_pages(self) -> None:
        """Should skip pages with no text."""
        mock_pdf = create_mock_pdfplumber_pdf(
            [
                "Content",
                "",  # Empty
                "More content",
            ]
        )

        with patch("pdfplumber.open", return_value=mock_pdf):
            result = _extract_with_pdfplumber(Path("test.pdf"))

        assert "[Page 1]" in result
        assert "[Page 2]" not in result
        assert "[Page 3]" in result


# =============================================================================
# UNIT TESTS - extract_text_from_pdf (Fallback Logic)
# =============================================================================


class TestExtractTextFromPdf:
    """Tests for extract_text_from_pdf with fallback logic."""

    def test_raises_file_not_found_for_missing_file(self) -> None:
        """Should raise FileNotFoundError for non-existent files."""
        with pytest.raises(FileNotFoundError, match="PDF file not found"):
            extract_text_from_pdf(Path("/nonexistent/file.pdf"))

    def test_uses_pypdf_when_successful(self) -> None:
        """Should use pypdf result when extraction succeeds."""
        with (
            patch("app.rag.extractors._extract_with_pypdf") as mock_pypdf,
            patch("app.rag.extractors._extract_with_pdfplumber") as mock_plumber,
            patch.object(Path, "exists", return_value=True),
        ):
            mock_pypdf.return_value = "pypdf extracted text"

            result = extract_text_from_pdf(Path("test.pdf"))

            mock_pypdf.assert_called_once()
            mock_plumber.assert_not_called()
            assert result == "pypdf extracted text"

    def test_falls_back_to_pdfplumber_on_pypdf_failure(self) -> None:
        """Should fall back to pdfplumber when pypdf fails."""
        with (
            patch("app.rag.extractors._extract_with_pypdf") as mock_pypdf,
            patch("app.rag.extractors._extract_with_pdfplumber") as mock_plumber,
            patch.object(Path, "exists", return_value=True),
        ):
            mock_pypdf.side_effect = Exception("pypdf encoding error")
            mock_plumber.return_value = "pdfplumber extracted text"

            result = extract_text_from_pdf(Path("test.pdf"))

            mock_pypdf.assert_called_once()
            mock_plumber.assert_called_once()
            assert result == "pdfplumber extracted text"

    def test_falls_back_to_pdfplumber_on_empty_pypdf_result(self) -> None:
        """Should fall back to pdfplumber when pypdf returns empty text."""
        with (
            patch("app.rag.extractors._extract_with_pypdf") as mock_pypdf,
            patch("app.rag.extractors._extract_with_pdfplumber") as mock_plumber,
            patch.object(Path, "exists", return_value=True),
        ):
            mock_pypdf.return_value = ""  # Empty result
            mock_plumber.return_value = "pdfplumber extracted text"

            result = extract_text_from_pdf(Path("test.pdf"))

            mock_pypdf.assert_called_once()
            mock_plumber.assert_called_once()
            assert result == "pdfplumber extracted text"

    def test_raises_value_error_when_both_fail(self) -> None:
        """Should raise ValueError when both extraction methods fail."""
        with (
            patch("app.rag.extractors._extract_with_pypdf") as mock_pypdf,
            patch("app.rag.extractors._extract_with_pdfplumber") as mock_plumber,
            patch.object(Path, "exists", return_value=True),
        ):
            mock_pypdf.side_effect = Exception("pypdf failed")
            mock_plumber.side_effect = Exception("pdfplumber failed")

            with pytest.raises(ValueError, match="Failed to extract text"):
                extract_text_from_pdf(Path("test.pdf"))

    def test_raises_value_error_when_both_return_empty(self) -> None:
        """Should raise ValueError when both methods return empty text."""
        with (
            patch("app.rag.extractors._extract_with_pypdf") as mock_pypdf,
            patch("app.rag.extractors._extract_with_pdfplumber") as mock_plumber,
            patch.object(Path, "exists", return_value=True),
        ):
            mock_pypdf.return_value = ""
            mock_plumber.return_value = "   "  # Whitespace only

            with pytest.raises(ValueError, match="No text could be extracted"):
                extract_text_from_pdf(Path("test.pdf"))


# =============================================================================
# UNIT TESTS - Section Preprocessing (Week 4)
# =============================================================================


class TestIsSectionHeading:
    """Tests for _is_section_heading function."""

    def test_detects_uppercase_headings(self) -> None:
        """Should detect ALL CAPS section headings."""
        assert _is_section_heading("SAFETY CONSIDERATIONS") is True
        assert _is_section_heading("BEFORE STARTING YOUR FURNACE") is True
        assert _is_section_heading("MAINTENANCE CHECKLIST") is True

    def test_rejects_short_lines(self) -> None:
        """Should reject lines shorter than minimum length."""
        assert _is_section_heading("WARNING") is False
        assert _is_section_heading("NOTE") is False
        assert _is_section_heading("A B C") is False

    def test_rejects_long_lines(self) -> None:
        """Should reject lines longer than maximum length (likely paragraphs)."""
        long_line = "THIS IS A VERY LONG LINE THAT EXCEEDS THE MAXIMUM LENGTH FOR A HEADING AND IS PROBABLY A PARAGRAPH"
        assert _is_section_heading(long_line) is False

    def test_rejects_hazard_warnings(self) -> None:
        """Should reject safety warning labels."""
        assert _is_section_heading("FIRE OR EXPLOSION HAZARD") is False
        assert _is_section_heading("CARBON MONOXIDE POISONING HAZARD") is False

    def test_rejects_page_headers(self) -> None:
        """Should reject common page headers/footers."""
        assert _is_section_heading("CONDENSING GAS FURNACE: OWNER'S MANUAL") is False

    def test_rejects_table_of_contents_lines(self) -> None:
        """Should reject lines with many dots (ToC entries)."""
        assert _is_section_heading("TABLE OF CONTENTS . . . . . . . 2") is False

    def test_rejects_page_markers(self) -> None:
        """Should reject page markers."""
        assert _is_section_heading("[Page 1]") is False
        assert _is_section_heading("[Page 12]") is False


class TestPreprocessTextWithSections:
    """Tests for preprocess_text_with_sections function."""

    def test_adds_markdown_headings(self) -> None:
        """Should add ## prefix to section headings."""
        text = """Some intro text

SAFETY CONSIDERATIONS
Here is some safety info.

MAINTENANCE CHECKLIST
Here is the checklist."""

        result = preprocess_text_with_sections(text)

        assert "## SAFETY CONSIDERATIONS" in result
        assert "## MAINTENANCE CHECKLIST" in result

    def test_preserves_non_heading_lines(self) -> None:
        """Should preserve lines that aren't headings."""
        text = """FILTERING OUT TROUBLE
Check your filter every month.
Replace if dirty."""

        result = preprocess_text_with_sections(text)

        assert "Check your filter every month." in result
        assert "Replace if dirty." in result

    def test_handles_empty_text(self) -> None:
        """Should handle empty text gracefully."""
        result = preprocess_text_with_sections("")
        assert result == ""
