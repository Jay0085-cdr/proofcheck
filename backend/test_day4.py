"""
test_day4.py
Runs the full ProofCheck pipeline and prints a text report.

Usage:
    python test_day4.py path/to/resume.pdf_or_docx github_username "Python, React, SQL"
    python test_day4.py path/to/resume.pdf_or_docx github_username "Python, React, SQL" self
"""

import sys

from pipeline import run_check
from resume_parser import extract_text


def main():
    if len(sys.argv) not in (4, 5):
        print('Usage: python test_day4.py resume.pdf|.docx github_username "Skill1, Skill2" [self]')
        sys.exit(1)

    pdf_path, username, skills_text = sys.argv[1], sys.argv[2], sys.argv[3]
    view = sys.argv[4] if len(sys.argv) == 5 else "recruiter"
    required = [s.strip() for s in skills_text.split(",") if s.strip()]

    print(f"Reading resume and checking GitHub user '{username}'...")
    report = run_check(extract_text(pdf_path), username, required, view)
    results = report["projects"]
    fit = report["job_fit"]

    # ---------- Report ----------
    print("\n" + "=" * 60)
    print(f"PROOFCHECK REPORT: {username}")
    print("=" * 60)
    print("Mode: " + ("AI" if report["mode"] == "ai" else "Basic (no AI)"))

    print("\nSKILLS CLAIMED:")
    print("  " + (", ".join(report["skills"]) or "(none found)"))

    print(f"\nJOB FIT: {fit['score']}% of required skills found in resume")
    print("  Matched: " + (", ".join(fit["matched"]) or "-"))
    print("  Missing: " + (", ".join(fit["missing"]) or "-"))

    print(f"\nPROJECTS ({len(results)}):")
    for r in results:
        print(f"\n  [{r['status']}] {r['project']}")
        print(f"    GitHub repo: {r['repo'] or 'no matching repo found'}")
        for tech, found in r["tech"].items():
            print(f"    {'yes' if found else 'NO ':<4} {tech}")
        if r["repo"]:
            bars = " ".join(str(w["commits"]) for w in r["timeline"])
            print(f"    timeline: {r['timeline_label']}" + (f"  [{bars}]" if bars else ""))
        for flag in r["flags"]:
            print(f"    ! {flag['text']}")
        for claim in r["claims"]:
            print(f"    claim: {claim}")

    if view == "self":
        print("\nFIX-IT LIST:")
        lines = report["fixes"]
    else:
        print("\nINTERVIEW QUESTIONS:")
        lines = report["questions"]
    for i, line in enumerate(lines, start=1):
        print(f"  {i}. {line}")

    print(f"\nGitHub has {report['repo_count']} public repos in total.")
    print("Note: ProofCheck never rejects anyone. It only shows evidence.")


if __name__ == "__main__":
    main()
