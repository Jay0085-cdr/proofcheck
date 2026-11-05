"""
timeline.py
Turns the candidate's commit dates into commits-per-week, for the bar chart
on each project card.
"""

from datetime import date, timedelta


def weekly_counts(dates):
    """["2026-01-06", "2026-01-07", "2026-01-20"] ->
    [{"week": "2026-01-05", "commits": 2}, {"week": "2026-01-12", "commits": 0},
     {"week": "2026-01-19", "commits": 1}]
    Each week starts on a Monday. Empty weeks in between are included,
    so the chart shows the gaps."""
    if not dates:
        return []

    def monday(text):
        day = date.fromisoformat(text)
        return day - timedelta(days=day.weekday())  # weekday(): Monday = 0

    counts = {}
    for text in dates:
        week = monday(text)
        counts[week] = counts.get(week, 0) + 1

    weeks = []
    week = min(counts)
    while week <= max(counts):
        weeks.append({"week": week.isoformat(), "commits": counts.get(week, 0)})
        week += timedelta(days=7)
    return weeks


def timeline_label(weeks, active_days):
    """A short summary such as "Built over 6 weeks"."""
    if not weeks:
        return "No commits by this user"
    if active_days == 1:
        return "All commits on 1 day"
    if len(weeks) == 1:
        return "Built within 1 week"
    return f"Built over {len(weeks)} weeks"
