"""
test_day4.py
Runs the full ProofCheck pipeline and prints a text report.

Usage:
    python test_day4.py path/to/resume.pdf_or_docx github_username "Python, React, SQL"
"""

import sys

from claims import extract_claims
from github_checker import check_user
from matcher import check_project, job_fit
from questions import make_questions
from resume_parser import extract_text


def main():
    if len(sys.argv) != 4:
        print('Usage: python test_day4.py resume.pdf|.docx github_username "Skill1, Skill2"')
        sys.exit(1)

    pdf_path, username, skills_text = sys.argv[1], sys.argv[2], sys.argv[3]
    required = [s.strip() for s in skills_text.split(",") if s.strip()]

    print("Reading resume...")
    claims = extract_claims(extract_text(pdf_path))

    print(f"Checking GitHub user '{username}'...")
    repos = check_user(username)

    results = [check_project(p, repos) for p in claims["projects"]]
    fit = job_fit(claims["skills"], required)

    # ---------- Report ----------
    print("\n" + "=" * 60)
    print(f"PROOFCHECK REPORT: {username}")
    print("=" * 60)
    print("Mode: " + ("AI" if claims["mode"] == "ai" else "Basic (no AI)"))

    print("\nSKILLS CLAIMED:")
    print("  " + (", ".join(claims["skills"]) or "(none found)"))

    print(f"\nJOB FIT: {fit['score']}% of required skills found in resume")
    print("  Matched: " + (", ".join(fit["matched"]) or "-"))
    print("  Missing: " + (", ".join(fit["missing"]) or "-"))

    print(f"\nPROJECTS ({len(results)}):")
    for r in results:
        print(f"\n  [{r['status']}] {r['project']}")
        print(f"    GitHub repo: {r['repo'] or 'no matching repo found'}")
        for tech, found in r["tech"].items():
            print(f"    {'yes' if found else 'NO ':<4} {tech}")
        for flag in r["flags"]:
            print(f"    ! {flag['text']}")
        for claim in r["claims"]:
            print(f"    claim: {claim}")

    print("\nINTERVIEW QUESTIONS:")
    for i, q in enumerate(make_questions(results, claims["mode"]), start=1):
        print(f"  {i}. {q}")

    print(f"\nGitHub has {len(repos)} public repos in total.")
    print("Note: ProofCheck never rejects anyone. It only shows evidence.")


if __name__ == "__main__":
    main()
