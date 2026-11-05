"""
test_day3.py
Quick manual test for Day 3.

Usage:
    python test_day3.py github_username
"""

import sys

from github_checker import check_user, parse_username


def yes_no(value):
    return "yes" if value else "no"


def main():
    if len(sys.argv) != 2:
        print("Usage: python test_day3.py github_username")
        sys.exit(1)

    username = parse_username(sys.argv[1])  # also accepts a github.com link
    print(f"Checking GitHub user '{username}'... (this can take a few seconds)\n")

    repos = check_user(username)

    if not repos:
        print("This user has no public repos.")
        return

    # Print the table header
    header = (
        f"{'REPO':<28} {'FORK':<5} {'LANGUAGES':<28} {'COMMITS':>7} "
        f"{'DAYS':>5}  {'FIRST':<10}  {'LAST':<10}  {'PKG.JSON':<8} {'REQS.TXT':<8}"
    )
    print(header)
    print("-" * len(header))

    # One row per repo
    for r in repos:
        langs = ", ".join(r["languages"]) or "-"
        print(
            f"{r['name'][:28]:<28} {yes_no(r['fork']):<5} {langs[:28]:<28} "
            f"{r['commit_count']:>7} {r['active_days']:>5}  "
            f"{r['first_commit'] or '-':<10}  {r['last_commit'] or '-':<10}  "
            f"{yes_no(r['has_package_json']):<8} {yes_no(r['has_requirements']):<8}"
        )

    print(f"\nTotal repos: {len(repos)}")


if __name__ == "__main__":
    main()
