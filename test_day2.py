"""
test_day2.py
Quick manual test for Day 1 + Day 2.

Usage:
    python test_day2.py path/to/resume.pdf
"""

import json
import sys

from claims import extract_claims
from resume_parser import extract_text


def main():
    if len(sys.argv) != 2:
        print("Usage: python test_day2.py path/to/resume.pdf")
        sys.exit(1)

    pdf_path = sys.argv[1]

    # Step 1: PDF -> text
    text = extract_text(pdf_path)
    print("=" * 60)
    print("EXTRACTED TEXT")
    print("=" * 60)
    print(text)

    # Step 2: text -> claims JSON
    print()
    print("=" * 60)
    print("CLAIMS (from Claude)")
    print("=" * 60)
    claims = extract_claims(text)
    print(json.dumps(claims, indent=2))


if __name__ == "__main__":
    main()
