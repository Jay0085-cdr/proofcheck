"""
test_self_check.py
Tests for "Check myself" mode (Feature 2). No internet needed.

Usage:
    python test_self_check.py
"""

from fixes import NOTHING_TO_FIX, find_typos, is_real_email, make_fixes


def project(**changes):
    """A Verified project; pass keyword arguments to change parts of it."""
    r = {"project": "Chat App — Realtime Messenger", "status": "Verified", "repo": "chat-app",
         "tech": {"React": True}, "flags": [], "other_authors": [], "unlinked_authors": [],
         "copy": None, "claims": []}
    r.update(changes)
    return r


def test_typos():
    resume = "SKILLS\nJava, Python, React.js,Node.js\nDatabases: MySQL, MongoD\nEDUCATION\nMongoD"
    assert find_typos(resume) == [("MongoD", "MongoDB")]
    assert find_typos("SKILLS\nPostgress, Dockr, React, JavaScript") == [
        ("Postgress", "PostgreSQL"), ("Dockr", "Docker")]
    print("PASS typo detection")


def test_emails():
    assert is_real_email("jay@gmail.com")
    assert not is_real_email("dev@ghostkitchen.local")
    assert not is_real_email("me@localhost")
    print("PASS real vs fake email")


def test_fix_templates():
    results = [
        project(status="No evidence", repo=None, tech={}),
        project(status="Partial", tech={"React": True, "Redis": False}),
        project(status="Partial", unlinked_authors=[{"name": "Jay", "email": "jay@gmail.com"}]),
        project(status="Partial", flags=[{"type": "fork", "text": "fork"}]),
        project(status="Partial", copy={"source": "a/b", "stars": 5, "identical": 9, "total": 10},
                flags=[{"type": "copied", "text": "copied"}]),
    ]
    tips = make_fixes(results, "SKILLS\nMongoD")
    assert "no public GitHub repo" in tips[0]
    assert "Redis isn't visible in chat-app" in tips[1]
    assert "Settings → Emails" in tips[2]
    assert "is a fork" in tips[3]
    assert "9 of 10 source files are identical to a/b" in tips[4]
    assert "MongoDB" in tips[5]
    print("PASS fix-it templates")


def test_nothing_to_fix():
    assert make_fixes([project()], "SKILLS\nReact") == [NOTHING_TO_FIX]
    print("PASS nothing to fix")


if __name__ == "__main__":
    test_typos()
    test_emails()
    test_fix_templates()
    test_nothing_to_fix()
