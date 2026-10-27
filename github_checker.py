"""
github_checker.py
Collects facts about a candidate's public GitHub repos:
languages, how many commits they made, when, and their dependency files.
"""

import os

import requests
from dotenv import load_dotenv

# Load GITHUB_TOKEN from the .env file
load_dotenv()

API = "https://api.github.com"
RAW = "https://raw.githubusercontent.com"


def make_headers():
    """Add the token if we have one (5000 requests/hour instead of 60)."""
    headers = {"Accept": "application/vnd.github+json"}
    token = os.getenv("GITHUB_TOKEN")
    if token:
        headers["Authorization"] = f"Bearer {token}"
    return headers


def check_rate_limit(response):
    """Stop with a clear message for token problems or rate limits."""
    if response.status_code == 401:
        raise RuntimeError(
            "GitHub rejected the token (401). Your GITHUB_TOKEN in .env is "
            "wrong or revoked. Fix it, or leave it empty to run without one."
        )
    if response.status_code in (403, 429) and "rate limit" in response.text.lower():
        raise RuntimeError(
            "GitHub rate limit reached. Check that GITHUB_TOKEN is set "
            "correctly in your .env file, or wait an hour and try again."
        )


def get_json(url, params=None):
    """GET a GitHub API url. Returns the JSON, or None if status isn't 200."""
    response = requests.get(url, headers=make_headers(), params=params, timeout=15)
    check_rate_limit(response)
    if response.status_code != 200:
        return None
    return response.json()


def get_text(url):
    """GET any url and return its text, or "" if status isn't 200."""
    response = requests.get(url, headers=make_headers(), timeout=15)
    check_rate_limit(response)
    if response.status_code != 200:
        return ""
    return response.text


def get_all_repos(username):
    """Return every public repo of the user (GitHub gives max 100 per page)."""
    repos = []
    page = 1
    while True:
        batch = get_json(
            f"{API}/users/{username}/repos",
            params={"per_page": 100, "page": page},
        )
        if not batch:  # None or empty list -> no more pages
            break
        repos.extend(batch)
        page += 1
    return repos


def get_commit_facts(full_name, username):
    """Count the user's commits in one repo and find which dates they were on."""
    # Note: only the latest 100 commits are fetched, which is enough for our red flags.
    # Empty repos return 409, so get_json gives None and we treat it as 0 commits.
    commits = get_json(
        f"{API}/repos/{full_name}/commits",
        params={"author": username, "per_page": 100},
    ) or []

    # Each commit date looks like "2024-03-15T10:22:01Z"; keep just "2024-03-15"
    dates = [c["commit"]["author"]["date"][:10] for c in commits]

    # Also fetch ALL commits (anyone's) to see who else worked on the repo
    all_commits = get_json(
        f"{API}/repos/{full_name}/commits",
        params={"per_page": 100},
    ) or []

    other_authors = []
    for c in all_commits:
        # "author" is the GitHub account; it's None if the commit email isn't
        # linked to any account, so fall back to the name saved in git
        if c["author"]:
            who = c["author"]["login"]
        else:
            who = c["commit"]["author"]["name"] + " (no GitHub account)"
        if who.lower() != username.lower() and who not in other_authors:
            other_authors.append(who)

    return {
        "commit_count": len(commits),
        "active_days": len(set(dates)),  # set() removes duplicate dates
        "first_commit": min(dates) if dates else None,
        "last_commit": max(dates) if dates else None,
        "total_commits": len(all_commits),
        "other_authors": other_authors,
    }


# Folders full of downloaded/generated code that the candidate didn't write
SKIP_FOLDERS = {"node_modules", "venv", ".venv", "env", "site-packages",
                "vendor", "dist", "build", "__pycache__", ".next"}

DEP_FILES = ("package.json", "requirements.txt")


def get_deps(full_name, branch):
    """Find every package.json / requirements.txt in the repo and read them."""
    # The Trees API lists every file path in the repo in one call.
    # Empty repos return 409, so we get None and find no files.
    tree = get_json(
        f"{API}/repos/{full_name}/git/trees/{branch}",
        params={"recursive": 1},
    ) or {}

    dep_paths = []
    for item in tree.get("tree", []):
        parts = item["path"].split("/")  # "frontend/package.json" -> ["frontend", "package.json"]
        if item["type"] != "blob" or parts[-1] not in DEP_FILES:
            continue
        if any(folder in SKIP_FOLDERS for folder in parts[:-1]):
            continue
        dep_paths.append(item["path"])

    # Download each file and glue the contents together
    contents = [get_text(f"{RAW}/{full_name}/{branch}/{path}") for path in dep_paths]

    return {
        "dep_files": dep_paths,
        "has_package_json": any(p.endswith("package.json") for p in dep_paths),
        "has_requirements": any(p.endswith("requirements.txt") for p in dep_paths),
        "deps": "\n".join(contents).strip().lower(),
    }


def check_user(username):
    """Return one dict of facts for each public repo of `username`."""
    # Make sure the user exists first
    if get_json(f"{API}/users/{username}") is None:
        raise ValueError(f"GitHub user not found: {username}")

    results = []
    for repo in get_all_repos(username):
        full_name = repo["full_name"]  # e.g. "octocat/Hello-World"

        languages = get_json(f"{API}/repos/{full_name}/languages") or {}

        info = {
            "name": repo["name"],
            "fork": repo["fork"],
            "languages": [lang.lower() for lang in languages],
        }
        info.update(get_commit_facts(full_name, username))
        info.update(get_deps(full_name, repo["default_branch"]))
        results.append(info)

    return results
