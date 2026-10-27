"""
resume_parser.py
Reads a resume (PDF or DOCX) and returns all of its text as one string.
"""

import docx
import pdfplumber


class ResumeError(Exception):
    """Raised when the resume can't be read (wrong type, no text, ...)."""


def read_pdf(file):
    pages_text = []
    with pdfplumber.open(file) as pdf:
        for page in pdf.pages:
            # extract_text() returns None for pages with no text (e.g. images)
            text = page.extract_text()
            if text:
                pages_text.append(text)
    return "\n".join(pages_text)


def read_docx(file):
    lines = []
    document = docx.Document(file)
    for paragraph in document.paragraphs:
        text = paragraph.text.strip()
        if not text:
            continue
        # Word stores bullet points as a "List" style, not as a "•" character.
        # Add "• " so bullet lines look the same as they do in a PDF.
        if "List" in paragraph.style.name:
            text = "• " + text
        lines.append(text)

    # Some resumes put text inside tables
    for table in document.tables:
        for row in table.rows:
            for cell in row.cells:
                if cell.text.strip():
                    lines.append(cell.text.strip())

    return "\n".join(lines)


def extract_text(file, filename=None):
    """
    Extract text from a resume.

    `file` can be a path like "resume.pdf", or a file object (from an upload).
    For file objects, pass `filename` so we know if it's a PDF or DOCX.
    """
    name = (filename or str(file)).lower()

    if name.endswith(".pdf"):
        text = read_pdf(file)
    elif name.endswith(".docx"):
        text = read_docx(file)
    else:
        raise ResumeError("Unsupported file type. Please upload a PDF or DOCX resume.")

    text = text.strip()

    # A scanned resume is just pictures, so we find no text
    if not text:
        raise ResumeError(
            "No text found in this resume. It may be a scanned image. "
            "Please use a text-based PDF or DOCX."
        )

    return text
