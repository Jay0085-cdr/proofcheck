"""
questions.py
Suggests interview questions for projects that GitHub couldn't fully prove.

  - AI mode: Claude writes 3-5 specific technical questions.
  - Basic mode (or if the AI fails): fill-in-the-blank template questions.
"""

import json

import anthropic

from claims import ask_claude, has_api_key, strip_code_fences
from matcher import short_name

ALL_VERIFIED = "All projects were verified on GitHub. No extra questions needed."

PROMPT = """You are helping a recruiter prepare for a technical interview.
Below are resume projects that GitHub could NOT fully prove, with the evidence found.

Write 3 to 5 short, specific technical interview questions that would show whether
the candidate really built these projects. Focus on the missing tech and red flags.
Be neutral and fair; never accuse the candidate.

Return ONLY a JSON list of strings, like: ["Question 1?", "Question 2?"]

Projects:
{projects}
"""


def questions_for_project(r):
    """Template questions for one weak project, most important first."""
    project = short_name(r["project"])  # "Ghost Kitchen — ..." -> "Ghost Kitchen"
    repo = r["repo"]

    if repo is None:
        return [
            f"Can you walk me through how you built {project}? "
            "Is the code available anywhere?"
        ]

    questions = []
    flag_types = [f["type"] for f in r["flags"]]

    if "other_authors" in flag_types:
        authors = ", ".join(r["other_authors"]) or "other accounts"
        questions.append(
            f"Most commits in {repo} were made by {authors}. "
            "What was your part in this project?"
        )

    # One question for all missing tech, e.g. "Spring Boot, PostgreSQL and JWT"
    missing = [tech for tech, found in r["tech"].items() if not found]
    if missing:
        if len(missing) == 1:
            tech_list = missing[0]
        else:
            tech_list = ", ".join(missing[:-1]) + " and " + missing[-1]
        questions.append(
            f"Your resume says you used {tech_list} in {project}, but it isn't "
            "in the repo's code or dependencies. Where and how did you use it?"
        )

    if "one_day" in flag_types:
        questions.append(
            f"All commits in {repo} were made on one day. "
            "How did you develop it before uploading?"
        )

    return questions


def template_questions(weak_results):
    """Free questions made from simple templates.
    Takes turns between projects so every weak project gets asked about."""
    per_project = [questions_for_project(r) for r in weak_results]

    questions = []
    round_number = 0
    while len(questions) < 5 and any(len(q) > round_number for q in per_project):
        # Round 0 takes each project's 1st question, round 1 the 2nd, ...
        for project_questions in per_project:
            if round_number < len(project_questions):
                questions.append(project_questions[round_number])
        round_number += 1

    return questions[:5]  # keep the list short for the interviewer


def ai_questions(weak_results):
    """Ask Claude for questions. Raises an error if anything goes wrong."""
    # Send only what Claude needs, not the whole repo data
    summary = [
        {
            "project": r["project"],
            "status": r["status"],
            "repo": r["repo"],
            "tech_found": r["tech"],
            "red_flags": [f["text"] for f in r["flags"]],
            "claims": r["claims"],
        }
        for r in weak_results
    ]
    prompt = PROMPT.replace("{projects}", json.dumps(summary, indent=2))

    questions = json.loads(strip_code_fences(ask_claude(prompt)))
    if not isinstance(questions, list) or not questions:
        raise ValueError("Claude did not return a list of questions")
    return [str(q) for q in questions[:5]]


def make_questions(results, mode="basic"):
    """Return a list of interview questions for weak (not Verified) projects."""
    if not results:
        return ["No projects were found in the resume. "
                "Can you describe a project you built and the tech you used?"]

    weak = [r for r in results if r["status"] in ("Partial", "No evidence")]

    if not weak:
        return [ALL_VERIFIED]

    if mode == "ai" and has_api_key():
        try:
            return ai_questions(weak)
        except (anthropic.APIError, ValueError) as error:
            # json.JSONDecodeError is a kind of ValueError, so bad JSON lands here too
            print(f"AI questions failed, using templates instead: {error}")

    return template_questions(weak)
