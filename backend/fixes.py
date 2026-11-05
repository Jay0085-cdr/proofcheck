"""
fixes.py
"Check myself" mode: instead of interview questions, tell the candidate
what to fix so their GitHub backs up their resume.

  - Basic mode: fill-in-the-blank templates.
  - AI mode: Claude rephrases the same tips (falls back to templates if it fails).
"""

import difflib
import json
import re

import anthropic

from claims import TECH_KEYWORDS, ask_claude, has_api_key, is_section_heading, strip_code_fences
from matcher import short_name

NOTHING_TO_FIX = "Nothing to fix: every project is backed by GitHub evidence."

PROMPT = """Rewrite these tips for a job seeker so they are friendly, clear and short.
Keep every fact (repo names, emails, tech names) exactly the same.
Return ONLY a JSON list of strings, one per tip, in the same order.

Tips:
{tips}
"""

# One-word spellings from the keyword list, e.g. "mongodb" -> "MongoDB"
SPELLINGS = {word: name for name, words in TECH_KEYWORDS.items()
             for word in words if " " not in word}


def join_words(items):
    """["A", "B", "C"] -> "A, B and C"."""
    return items[0] if len(items) == 1 else ", ".join(items[:-1]) + " and " + items[-1]


def skills_lines(resume_text):
    """The lines of the Skills section (or the whole resume if there isn't one)."""
    lines = []
    in_skills = False
    for line in resume_text.split("\n"):
        if is_section_heading(line):
            in_skills = "skill" in line.lower()
        elif in_skills:
            lines.append(line)
    return lines or resume_text.split("\n")


def find_typos(resume_text):
    """Words that are almost, but not exactly, a known tech name.
    Returns pairs like ("MongoD", "MongoDB")."""
    typos = []
    for line in skills_lines(resume_text):
        for word in re.split(r"[,;:/|()•\s]+", line):
            word = word.strip(".")
            lower = word.lower()
            if len(lower) < 4 or lower in SPELLINGS:
                continue
            # cutoff=0.85 means "at least 85% the same letters"
            close = difflib.get_close_matches(lower, SPELLINGS, n=1, cutoff=0.85)
            if close and (word, SPELLINGS[close[0]]) not in typos:
                typos.append((word, SPELLINGS[close[0]]))
    return typos


def is_real_email(email):
    """False for made-up addresses like "dev@myapp.local" that GitHub can't verify."""
    domain = email.lower().rpartition("@")[2]
    return "." in domain and not domain.endswith((".local", ".localdomain", ".lan",
                                                   ".internal", "localhost"))


def fixes_for_project(r):
    """Template tips for one project."""
    project = short_name(r["project"])
    repo = r["repo"]

    if repo is None:
        return [f"{project}: no public GitHub repo found. Push the code to a public repo "
                "with a similar name, or add a live demo link to your resume."]

    tips = []
    for person in r["unlinked_authors"]:
        who = f"\"{person['name']}\" <{person['email']}>"
        if is_real_email(person["email"]):
            tips.append(f"{repo}: commits were made as {who}, an email that isn't linked to "
                        "your GitHub account. Add it in GitHub → Settings → Emails so these "
                        "commits count as yours.")
        else:
            # GitHub only links emails you can verify, and "dev@x.local" has no inbox
            tips.append(f"{repo}: commits were made as {who}. GitHub can't link that email "
                        "because it isn't a real inbox. Run git config user.email with the "
                        "email on your GitHub account so new commits count as yours. Old "
                        "commits only change if you rewrite history (git rebase) and force-push.")

    missing = [tech for tech, found in r["tech"].items() if not found]
    if missing:
        tips.append(f"{project}: {join_words(missing)} isn't visible in {repo}'s code or "
                    "dependency files. Add the code that shows it, or remove it from this "
                    "project on your resume.")

    flag_types = [f["type"] for f in r["flags"]]
    copy = r.get("copy")
    if copy:
        tips.append(f"{repo}: {copy['identical']} of {copy['total']} source files are "
                    f"identical to {copy['source']}. Explain in the README what you built "
                    "on top of it, or remove it from your resume.")
    elif "fork" in flag_types:
        tips.append(f"{repo} is a fork. Explain in the README what you built on top of "
                    "the original, or remove it from your resume.")

    if "one_day" in flag_types:
        tips.append(f"{repo}: all your commits are from one day. If you built it somewhere "
                    "else first, mention that in the README.")
    return tips


def template_fixes(results, resume_text):
    tips = []
    for r in results:
        if r["status"] != "Verified":
            tips.extend(fixes_for_project(r))
    for typo, correct in find_typos(resume_text):
        tips.append(f"\"{typo}\" looks like a typo for \"{correct}\". Fix the spelling so "
                    "recruiters and keyword searches find it.")
    return tips


def make_fixes(results, resume_text, mode="basic"):
    """Return the fix-it list for "Check myself" mode."""
    tips = template_fixes(results, resume_text)
    if not tips:
        return [NOTHING_TO_FIX]

    if mode == "ai" and has_api_key():
        try:
            reply = ask_claude(PROMPT.replace("{tips}", json.dumps(tips, indent=2)))
            rewritten = json.loads(strip_code_fences(reply))
            if isinstance(rewritten, list) and len(rewritten) == len(tips):
                return [str(t) for t in rewritten]
        except (anthropic.APIError, ValueError) as error:
            print(f"AI rephrasing failed, using templates instead: {error}")

    return tips
