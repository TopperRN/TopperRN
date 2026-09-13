"""Scrape the public contribution calendar (no token) into data/contributions.json.

Usage:
    GH_USER=TopperRN python scripts/fetch_contributions.py
"""
import datetime as dt
import json
import os
import re
import sys
from collections import defaultdict
from pathlib import Path

import requests
from bs4 import BeautifulSoup

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "data" / "contributions.json"
USER = os.environ.get("GH_USER") or "TopperRN"


def fetch(user):
    r = requests.get(
        f"https://github.com/users/{user}/contributions",
        headers={"User-Agent": "Mozilla/5.0 (profile README heatmap)"},
        timeout=30,
    )
    r.raise_for_status()
    return r.text


def parse(html):
    soup = BeautifulSoup(html, "html.parser")
    tips = {t.get("for"): t.get_text(strip=True) for t in soup.find_all("tool-tip")}
    days = []
    for td in soup.select("td.ContributionCalendar-day[data-date]"):
        m = re.match(r"([\d,]+) contributions?", tips.get(td.get("id"), ""))
        days.append({
            "date": td["data-date"],
            "count": int(m.group(1).replace(",", "")) if m else 0,
            "level": int(td.get("data-level", 0)),
        })
    if not days:
        sys.exit("no contribution cells found; GitHub's markup may have changed")
    days.sort(key=lambda d: d["date"])

    total = sum(d["count"] for d in days)
    heading = soup.find(id="js-contribution-activity-description")
    if heading:
        m = re.search(r"([\d,]+)\s+contributions?", heading.get_text(" ", strip=True))
        if m:
            total = int(m.group(1).replace(",", ""))
    return days, total


def streaks(days):
    counts = [d["count"] for d in days]
    # today may simply not have commits yet, so don't let it break the streak
    end = len(counts) - 1
    if counts and counts[end] == 0:
        end -= 1
    current = 0
    while end >= 0 and counts[end] > 0:
        current += 1
        end -= 1

    longest, run, run_start, best_range = 0, 0, 0, None
    for i, c in enumerate(counts):
        if c > 0:
            if run == 0:
                run_start = i
            run += 1
            if run > longest:
                longest, best_range = run, (days[run_start]["date"], days[i]["date"])
        else:
            run = 0
    return current, longest, best_range


def main():
    days, total = parse(fetch(USER))
    current, longest, longest_range = streaks(days)
    best = max(days, key=lambda d: d["count"])
    months = defaultdict(int)
    for d in days:
        months[d["date"][:7]] += d["count"]

    data = {
        "user": USER,
        "fetched_at": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"),
        "total": total,
        "stats": {
            "current_streak": current,
            "longest_streak": longest,
            "longest_streak_range": longest_range,
            "best_day": {"date": best["date"], "count": best["count"]},
            "active_days": sum(1 for d in days if d["count"] > 0),
        },
        "months": dict(months),
        "days": days,
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(data, indent=1) + "\n", encoding="utf-8")
    print(f"{USER}: {total} contributions, {len(days)} days, current streak {current}, longest {longest}")


if __name__ == "__main__":
    main()
