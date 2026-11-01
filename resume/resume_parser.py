"""
resume/resume_parser.py
Extracts plain text from a PDF resume.
"""

from pathlib import Path
from loguru import logger

try:
    import pdfplumber
    PDF_AVAILABLE = True
except ImportError:
    PDF_AVAILABLE = False

try:
    import PyPDF2
    PYPDF_AVAILABLE = True
except ImportError:
    PYPDF_AVAILABLE = False


def extract_resume_text(pdf_path: str = "resume/resume.pdf") -> str:
    """Extract text from PDF resume. Returns plain text string."""
    path = Path(pdf_path)
    if not path.exists():
        logger.warning("Resume not found at '{}'. Place your PDF in resume/resume.pdf", pdf_path)
        return ""

    text = ""

    # Try pdfplumber first (better quality)
    if PDF_AVAILABLE:
        try:
            with pdfplumber.open(path) as pdf:
                for page in pdf.pages:
                    text += (page.extract_text() or "") + "\n"
            if text.strip():
                logger.info("Resume parsed with pdfplumber ({} chars)", len(text))
                return text.strip()
        except Exception as e:
            logger.warning("pdfplumber failed: {}", e)

    # Fallback to PyPDF2
    if PYPDF_AVAILABLE:
        try:
            with open(path, "rb") as f:
                reader = PyPDF2.PdfReader(f)
                for page in reader.pages:
                    text += (page.extract_text() or "") + "\n"
            logger.info("Resume parsed with PyPDF2 ({} chars)", len(text))
            return text.strip()
        except Exception as e:
            logger.error("PyPDF2 failed: {}", e)

    logger.error("Could not parse resume. Install: pip install pdfplumber PyPDF2")
    return ""
