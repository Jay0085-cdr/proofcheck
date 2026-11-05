"""
pipeline.py
Runs every ProofCheck step in order. Used by api.py (the website)
and test_day4.py (the terminal report), so both always do the same thing.
"""

import copy_detector
import github_checker
from claims import extract_claims
from github_checker import check_user
from matcher import check_project, find_repo, job_fit
from questions import make_questions


def run_check(resume_text, username, required_skills):
    """Resume text + GitHub username -> the full report as a dict."""
    # Start each check fresh: empty tree cache and search counter
    github_checker.TREE_CACHE.clear()
    copy_detector.search_count = 0

    claims = extract_claims(resume_text)
    repos = check_user(username)

    results = []
    for project in claims["projects"]:
        # Copy check only for repos that match a resume project (saves API calls)
        repo = find_repo(project["name"], repos)
        if repo is not None and "copy" not in repo:
            repo["copy"] = copy_detector.find_copy(repo, project, username)
        results.append(check_project(project, repos))

    return {
        "mode": claims["mode"],
        "username": username,
        "skills": claims["skills"],
        "job_fit": job_fit(claims["skills"], required_skills),
        "projects": results,
        "questions": make_questions(results, claims["mode"]),
        "repo_count": len(repos),
    }
