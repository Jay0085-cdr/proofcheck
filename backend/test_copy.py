"""
test_copy.py
Tests for the copied project detector (Feature 1).

Usage:
    python test_copy.py

Part 1 checks the ignore rules without the internet.
Part 2 runs two real cases on GitHub:
  - a re-upload of a popular public repo (should be flagged)
  - an original project (should NOT be flagged)
"""

import copy_detector
from copy_detector import find_copy, is_source_file
from github_checker import API, get_json
from matcher import red_flags
from questions import questions_for_project


def file(path, size=100):
    return {"path": path, "type": "blob", "size": size, "sha": "x"}


def test_ignore_rules():
    assert is_source_file(file("src/App.jsx"))
    assert is_source_file(file("backend/app/main.py"))
    assert not is_source_file(file("README.md"))
    assert not is_source_file(file("LICENSE"))
    assert not is_source_file(file("package-lock.json"))
    assert not is_source_file(file("vite.config.js"))
    assert not is_source_file(file("src/index.css"))
    assert not is_source_file(file("node_modules/react/index.js"))
    assert not is_source_file(file("frontend/dist/assets/index.js"))
    assert not is_source_file(file("src/empty.py", size=0))
    assert not is_source_file(file("public/logo.png"))   # not source code
    print("PASS ignore rules")


def test_flag_and_question():
    copy = {"source": "someone/popular-app", "stars": 900, "identical": 30, "total": 40}
    repo = {"fork": False, "commit_count": 10, "total_commits": 10, "active_days": 5,
            "first_commit": "2026-01-01", "other_authors": [], "copy": copy}
    flags = red_flags(repo)
    assert flags == [{"type": "copied", "text": "30 of 40 source files are identical "
                                                 "to someone/popular-app (900 stars)"}]
    result = {"project": "Chat App", "repo": "chat-app", "flags": flags, "tech": {},
              "other_authors": [], "copy": copy}
    assert "someone/popular-app" in questions_for_project(result)[0]
    print("PASS flag text and interview question")


def repo_facts(full_name):
    """The few repo facts find_copy needs, straight from the GitHub API."""
    data = get_json(f"{API}/repos/{full_name}")
    parent = data.get("parent")
    return {
        "name": data["name"],
        "full_name": data["full_name"],
        "default_branch": data["default_branch"],
        "parent": parent and {"full_name": parent["full_name"],
                              "default_branch": parent["default_branch"],
                              "stars": parent["stargazers_count"]},
    }


def run_case(full_name, project):
    copy_detector.search_count = 0
    owner = full_name.split("/")[0]
    result = find_copy(repo_facts(full_name), project, owner)
    print(f"\n{full_name}")
    if result:
        print(f"  FLAG: {result['identical']} of {result['total']} source files are "
              f"identical to {result['source']} ({result['stars']} stars)")
    else:
        print("  No copy found")
    return result


def test_copied_repo():
    # Not a GitHub fork: someone uploaded the files of the popular
    # gothinkster/react-redux-realworld-example-app as their own new repo
    result = run_case("technexxa/react-redux-realworld-example-app",
                      {"name": "React Redux RealWorld App", "tech": ["React"]})
    assert result is not None, "expected a copy flag"
    assert result["source"] == "gothinkster/react-redux-realworld-example-app"
    print("PASS copied repo is flagged")


def test_original_repo():
    result = run_case("Jay0085-cdr/ghost-kitchen-payment",
                      {"name": "Ghost Kitchen — Payment Reconciliation", "tech": ["Spring Boot"]})
    assert result is None, "original project should not be flagged"
    print("PASS original repo is not flagged")


if __name__ == "__main__":
    test_ignore_rules()
    test_flag_and_question()
    test_copied_repo()
    test_original_repo()
