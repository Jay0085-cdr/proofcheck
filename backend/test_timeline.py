"""
test_timeline.py
Tests for the commit timeline (Feature 3).

Usage:
    python test_timeline.py
"""

from github_checker import get_commit_facts
from timeline import timeline_label, weekly_counts


def test_weekly_counts():
    # Tue + Wed of one week, nothing the next week, Monday of the week after
    weeks = weekly_counts(["2026-01-06", "2026-01-07", "2026-01-19"])
    assert weeks == [
        {"week": "2026-01-05", "commits": 2},
        {"week": "2026-01-12", "commits": 0},
        {"week": "2026-01-19", "commits": 1},
    ]
    assert weekly_counts([]) == []
    print("PASS weekly counts")


def test_labels():
    assert timeline_label([], 0) == "No commits by this user"
    assert timeline_label([{"week": "2026-01-05", "commits": 4}], 1) == "All commits on 1 day"
    assert timeline_label([{"week": "2026-01-05", "commits": 4}], 3) == "Built within 1 week"
    assert timeline_label(weekly_counts(["2026-01-06", "2026-02-10"]), 2) == "Built over 6 weeks"
    print("PASS labels")


def test_real_repo():
    facts = get_commit_facts("1Marc/modern-todomvc-vanillajs", "1Marc")
    weeks = weekly_counts(facts["commit_dates"])
    print(f"\n1Marc/modern-todomvc-vanillajs: {timeline_label(weeks, facts['active_days'])}")
    print("  commits per week:", [w["commits"] for w in weeks])
    assert len(weeks) > 1
    assert sum(w["commits"] for w in weeks) == facts["commit_count"]
    print("PASS real repo")


if __name__ == "__main__":
    test_weekly_counts()
    test_labels()
    test_real_repo()
