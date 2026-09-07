"""Regenerates jobs.csv and dashboard.html from the tracker store.

Both run.py (after a fresh scrape) and serve.py (after a status edit from
the dashboard) call regenerate() so the CSV and HTML never fall out of
sync with tracker.json, which is the actual source of truth.
"""

import csv
import os

from . import config, dashboard

_CSV_FIELDNAMES = [
    "source", "title", "company", "matched_company", "location",
    "date_posted", "status", "is_entry_level", "is_new", "still_listed",
    "first_seen", "last_seen", "search_term", "job_url",
]


def to_job_list(tracker):
    jobs = []
    for job_id, record in tracker.items():
        job = dict(record)
        job["id"] = job_id
        jobs.append(job)
    jobs.sort(key=lambda j: j["first_seen"], reverse=True)
    return jobs


def write_csv(jobs, path):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=_CSV_FIELDNAMES, extrasaction="ignore")
        writer.writeheader()
        for j in jobs:
            writer.writerow(j)


def regenerate(tracker, generated_at):
    jobs = to_job_list(tracker)
    write_csv(jobs, config.JOBS_CSV)
    dashboard.generate(jobs, config.DASHBOARD_FILE, generated_at=generated_at)
    return jobs
