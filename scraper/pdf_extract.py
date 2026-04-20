"""
PDF text extraction using pdfplumber.
"""

import logging
from pathlib import Path

import pdfplumber

logger = logging.getLogger(__name__)


def extract_text_from_pdf(pdf_path: str | Path) -> str:
    """
    Extract all text from a PDF file.

    Returns the full text content, or empty string on failure.
    """
    pdf_path = Path(pdf_path)
    if not pdf_path.exists():
        logger.warning(f"PDF not found: {pdf_path}")
        return ""

    try:
        text_parts: list[str] = []
        with pdfplumber.open(pdf_path) as pdf:
            for page in pdf.pages:
                page_text = page.extract_text()
                if page_text:
                    text_parts.append(page_text)

        full_text = "\n\n".join(text_parts)
        logger.info(f"Extracted {len(full_text)} chars from {pdf_path.name}")
        return full_text

    except Exception as e:
        logger.error(f"Failed to extract text from {pdf_path}: {e}")
        return ""


def extract_tables_from_pdf(pdf_path: str | Path) -> list[list[list[str]]]:
    """
    Extract tables from a PDF. Returns a list of tables,
    where each table is a list of rows, each row a list of cell strings.
    """
    pdf_path = Path(pdf_path)
    if not pdf_path.exists():
        return []

    try:
        all_tables: list[list[list[str]]] = []
        with pdfplumber.open(pdf_path) as pdf:
            for page in pdf.pages:
                tables = page.extract_tables()
                for table in tables:
                    cleaned = [
                        [cell or "" for cell in row]
                        for row in table
                    ]
                    all_tables.append(cleaned)
        return all_tables
    except Exception as e:
        logger.error(f"Failed to extract tables from {pdf_path}: {e}")
        return []
