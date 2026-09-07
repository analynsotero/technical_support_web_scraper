"""Persistent job-tracking store (technical_support/data/tracker.json).

This is the single source of truth for both "what jobs are currently in
the list" and "what status has the user set for each one" - jobs.csv and
dashboard.html are just regenerated views of it. Keeping one JSON file
keyed by job ID (rather than treating jobs.csv itself as the store) is
what lets both run.py (a fresh scrape) and serve.py (a status edit from
the dashboard) update the same data safely.
"""

import json
import os

from . import config, utils


def load():
    if not os.path.exists(config.TRACKER_FILE):
        return {}
    with open(config.TRACKER_FILE, "r", encoding="utf-8") as f:
        return json.load(f)


def save(tracker):
    os.makedirs(config.DATA_DIR, exist_ok=True)
    with open(config.TRACKER_FILE, "w", encoding="utf-8") as f:
        json.dump(tracker, f, indent=2, ensure_ascii=False)


def merge_scrape(fresh_jobs, tracker, run_time):
    """Folds a fresh scrape into the existing tracker.

    - A job seen for the first time is added with status "To Apply".
    - A job that's already tracked keeps its existing status untouched,
      no matter what status that is - only its scraped fields (title,
      location, date_posted, etc.) get refreshed.
    - A previously tracked job that ISN'T in this scrape (it aged out of
      the site's own results) is dropped only if it's still "To Apply".
      Anything the user has moved to any other status is carried forward
      indefinitely, since that's the whole point of a tracker - applying
      to a job shouldn't make it vanish from the list.

    Returns (new_tracker, stats) where stats has counts for the run summary.
    """
    new_tracker = {}
    fresh_ids = set()
    new_count = 0
    carried_over_count = 0

    for j in fresh_jobs:
        job_id = j["id"]
        fresh_ids.add(job_id)
        existing = tracker.get(job_id)

        record = {
            "source": j["source"],
            "title": j["title"],
            "company": j["company"],
            "matched_company": j.get("matched_company", ""),
            "location": j["location"],
            "date_posted": j["date_posted"],
            "search_term": j.get("search_term", ""),
            "job_url": j["job_url"],
            "is_entry_level": utils.looks_entry_level(j["title"], j.get("search_term", "")),
            "still_listed": True,
            "last_seen": run_time,
        }

        if existing:
            record["status"] = existing["status"]
            record["first_seen"] = existing["first_seen"]
            record["is_new"] = False
        else:
            record["status"] = config.DEFAULT_STATUS
            record["first_seen"] = run_time
            record["is_new"] = True
            new_count += 1

        new_tracker[job_id] = record

    for job_id, existing in tracker.items():
        if job_id in fresh_ids:
            continue
        if existing["status"] == config.DEFAULT_STATUS:
            continue  # never applied to it and it's no longer listed - drop it
        carried = dict(existing)
        carried["still_listed"] = False
        carried["is_new"] = False
        new_tracker[job_id] = carried
        carried_over_count += 1

    stats = {
        "new": new_count,
        "carried_over": carried_over_count,
        "total": len(new_tracker),
    }
    return new_tracker, stats


def update_status(job_id, new_status):
    """Used by serve.py when the dashboard changes a status dropdown."""
    if new_status not in config.STATUSES:
        raise ValueError(f"unknown status: {new_status!r}")

    tracker = load()
    if job_id not in tracker:
        raise KeyError(f"unknown job id: {job_id!r}")

    tracker[job_id]["status"] = new_status
    save(tracker)
    return tracker
