"""
matcher.py
Compares what the resume claims with what GitHub shows.
Plain if/else rules only, no AI, so every verdict can be explained.
"""

import difflib
import re

from timeline import timeline_label, weekly_counts

# A resume says "Node.js" but package.json says "express".
# These are the words that count as evidence for each tech.
ALIASES = {
    "node.js": ["node", "express"],
    "express": ["express"],
    "mongodb": ["mongodb", "mongoose"],
    "redis": ["redis", "ioredis"],
    "react": ["react"],
    "next.js": ["next"],
    "flask": ["flask"],
    "django": ["django"],
    "fastapi": ["fastapi"],
    "spring boot": ["spring"],
    "jwt": ["jwt", "jjwt", "jsonwebtoken"],
    "docker": ["docker", "dockerfile"],  # GitHub lists Dockerfiles as a "language"
    "postgresql": ["postgresql", "postgres", "pg", "plpgsql"],
    "mysql": ["mysql", "mysql2"],
    "sql": ["sql", "mysql", "mysql2", "postgresql", "postgres", "pg",
            "plpgsql", "sqlite", "sqlite3", "tsql"],
}


def normalize(text):
    """'Node.js' -> 'node', 'React JS' -> 'react', 'Chat-App' -> 'chatapp'."""
    text = re.sub(r"[^a-z0-9+#]", "", text.lower())  # keep letters, digits, + and #
    if text.endswith("js") and len(text) > 2:
        text = text[:-2]
    return text


def get_aliases(tech):
    """All words that count as evidence for `tech` (always includes itself)."""
    for name, words in ALIASES.items():
        if normalize(name) == normalize(tech):
            return words + [tech.lower()]
    return [tech.lower()]


def contains_word(text, word):
    """True if `word` appears in `text` as a whole word.
    So 'java' does NOT match inside 'javascript'."""
    pattern = r"(?<![a-z0-9])" + re.escape(word) + r"(?![a-z0-9])"
    return re.search(pattern, text) is not None


def similarity(a, b):
    """0.0 (totally different) to 1.0 (identical), after cleaning both names."""
    return difflib.SequenceMatcher(None, normalize(a), normalize(b)).ratio()


def short_name(project_name):
    """'Ghost Kitchen — Payment System' -> 'Ghost Kitchen'."""
    return re.split(r" [—–-] |:|\||\(", project_name)[0].strip()


def find_repo(project_name, repos):
    """Return the repo whose name is most similar to the project name,
    or None if nothing is at least 60% similar."""
    # Also try the short name, because a long subtitle
    # makes the full name look very different from the repo name
    short = short_name(project_name)

    best_repo = None
    best_score = 0.0
    for repo in repos:
        score = max(similarity(project_name, repo["name"]),
                    similarity(short, repo["name"]))
        if score > best_score:
            best_repo, best_score = repo, score
    return best_repo if best_score >= 0.6 else None


def tech_found(tech, repo):
    """True if the tech (or one of its aliases) is in the repo's
    languages or dependency files."""
    for word in get_aliases(tech):
        if word in repo["languages"] or contains_word(repo["deps"], word):
            return True
    return False


def red_flags(repo):
    """List of warnings about a repo. Empty list = nothing suspicious.
    Each flag has a "type" (for code to check) and "text" (for people to read)."""
    flags = []
    mine = repo["commit_count"]
    total = repo["total_commits"]

    if repo["fork"]:
        flags.append({"type": "fork", "text": "Repo is a fork (a copy of someone else's project)"})

    if mine == 0:
        flags.append({"type": "few_commits", "text": "No commits by the candidate"})
    elif mine < 5:
        flags.append({"type": "few_commits", "text": f"Only {mine} commit(s) by the candidate"})

    if mine > 0 and repo["active_days"] == 1:
        flags.append({"type": "one_day",
                      "text": f"All candidate commits were made on one day ({repo['first_commit']})"})

    others = total - mine
    if total > 0 and others > mine:
        names = ", ".join(repo["other_authors"]) or "unknown"
        flags.append({"type": "other_authors",
                      "text": f"Most commits ({others} of {total}) were made by other accounts: {names}"})

    copy = repo.get("copy")  # filled in by copy_detector.py (None = not a copy)
    if copy:
        flags.append({"type": "copied",
                      "text": f"{copy['identical']} of {copy['total']} source files are identical "
                              f"to {copy['source']} ({copy['stars']} stars)"})

    return flags


def check_project(project, repos):
    """Compare one resume project with the candidate's repos."""
    repo = find_repo(project["name"], repos)

    if repo is None:
        return {
            "project": project["name"],
            "status": "No evidence",
            "repo": None,
            "tech": {},
            "flags": [],
            "other_authors": [],
            "unlinked_authors": [],
            "copy": None,
            "timeline": [],
            "timeline_label": "",
            "claims": project.get("claims", []),
        }

    tech = {t: tech_found(t, repo) for t in project.get("tech", [])}
    weeks = weekly_counts(repo["commit_dates"])
    flags = red_flags(repo)

    # Verified only if every claimed tech was found AND there are no red flags
    if all(tech.values()) and not flags:
        status = "Verified"
    else:
        status = "Partial"

    return {
        "project": project["name"],
        "status": status,
        "repo": repo["name"],
        "tech": tech,
        "flags": flags,
        "other_authors": repo["other_authors"],
        "unlinked_authors": repo["unlinked_authors"],
        "copy": repo.get("copy"),
        "timeline": weeks,
        "timeline_label": timeline_label(weeks, repo["active_days"]),
        "claims": project.get("claims", []),
    }


def job_fit(resume_skills, required_skills):
    """Percentage of required skills that appear in the resume skills."""
    resume_set = {normalize(s) for s in resume_skills}

    matched = []
    for skill in required_skills:
        # The skill counts if the resume has it or one of its aliases
        options = {normalize(word) for word in get_aliases(skill)}
        if options & resume_set:  # & = items in both sets
            matched.append(skill)

    if not required_skills:
        return {"score": 0, "matched": [], "missing": []}

    return {
        "score": round(100 * len(matched) / len(required_skills)),
        "matched": matched,
        "missing": [s for s in required_skills if s not in matched],
    }
