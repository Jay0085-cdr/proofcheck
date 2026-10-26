"""
resume_parser.py
Reads a resume PDF and returns all of its text as one string.
"""

import pdfplumber


def extract_text(file):
    """
    Extract text from a PDF.

    `file` can be either:
      - a path like "my_resume.pdf", or
      - an uploaded file object (for example, from Streamlit's file_uploader)
    """
    pages_text = []

    with pdfplumber.open(file) as pdf:
        for page in pdf.pages:
            # extract_text() returns None for pages with no text (e.g. images)
            text = page.extract_text()
            if text:
                pages_text.append(text)

    full_text = "\n".join(pages_text).strip()

    # A scanned resume is just pictures, so pdfplumber finds no text
    if not full_text:
        raise ValueError(
            "No text found in this PDF. It may be a scanned image. "
            "Please use a text-based PDF."
        )

    return full_text
