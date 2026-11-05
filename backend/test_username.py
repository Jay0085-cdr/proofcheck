"""
test_username.py
The username box accepts a plain username or a full GitHub link. No internet needed.

Usage:
    python test_username.py
"""

from github_checker import parse_username

CASES = {
    "Jay0085-cdr": "Jay0085-cdr",
    "  @Jay0085-cdr ": "Jay0085-cdr",
    "https://github.com/Jay0085-cdr": "Jay0085-cdr",
    "https://github.com/Jay0085-cdr/": "Jay0085-cdr",
    "github.com/Jay0085-cdr/ghost-kitchen-payment": "Jay0085-cdr",
    "http://www.GitHub.com/Jay0085-cdr?tab=repositories": "Jay0085-cdr",
    "https://github.com/Jay0085-cdr#readme": "Jay0085-cdr",
}

if __name__ == "__main__":
    for text, expected in CASES.items():
        got = parse_username(text)
        assert got == expected, f"{text!r} -> {got!r}, expected {expected!r}"
    print(f"PASS {len(CASES)} username formats")
