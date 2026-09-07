"""Scrapes Technical Support / IT Help Desk job postings directly from each
target company's own careers site (config.TARGET_COMPANIES), and merges
them into technical_support/data/tracker.json - the persistent tracker
store - regenerating jobs.csv and dashboard.html from it.

Usage:
    python run.py

Each company is scraped through its own dedicated module in scrapers/
(concentrix.py, accenture.py, etc.), since every one of these career
sites runs on a different platform with its own request format - there's
no single generic "search this site" scraper like junior_data_engineer
uses. The one exception is TELUS Digital: its careers site blocks plain
HTTP requests behind a Cloudflare JS challenge, so scrapers/telus_digital.py
falls back to searching LinkedIn/Indeed/JobStreet and filtering to just
that company - see that module's docstring for why.

Jobs you've moved to any status other than "To Apply" (via the dashboard -
see serve.py) are kept on the list forever, even once a site stops
returning them. Only untouched "To Apply" jobs get dropped when a rerun no
longer finds them.

See README.md for setup and details on how each company is scraped.
"""

import os
import sys
from datetime import datetime, timezone

# Allow running this script directly (`python run.py` from inside this
# folder, or `python technical_support/run.py` from job-applications) by
# putting the folder that contains the technical_support package on
# sys.path, so the package's internal relative imports keep working.
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from technical_support import config, outputs, tracker
from technical_support.scrapers import (
    accenture,
    alorica,
    concentrix,
    foundever,
    iqor,
    sutherland,
    taskus,
    telus_digital,
    teleperformance,
    ttec,
    vxi,
)

# Company name -> its scraper module's scrape() function. Every one takes
# no arguments and returns a list of normalized job dicts already scoped
# to that company (and, except for the fetch-everything-then-filter ones,
# already scoped to Philippines/remote-for-PH roles too).
SCRAPERS = {
    "Concentrix": concentrix.scrape,
    "Accenture": accenture.scrape,
    "Sutherland": sutherland.scrape,
    "Teleperformance": teleperformance.scrape,
    "TTEC": ttec.scrape,
    "Foundever": foundever.scrape,
    "TELUS Digital": telus_digital.scrape,
    "Alorica": alorica.scrape,
    "TaskUs": taskus.scrape,
    "VXI Global Solutions": vxi.scrape,
    "iQor": iqor.scrape,
}


def scrape_all():
    all_jobs = []
    for i, (company, scrape_fn) in enumerate(SCRAPERS.items(), 1):
        print(f"[{i}/{len(SCRAPERS)}] {company}")
        try:
            company_jobs = scrape_fn()
        except Exception as exc:
            print(f"  failed: {exc}")
            continue
        print(f"  -> {len(company_jobs)} matching listings")
        all_jobs.extend(company_jobs)
    return all_jobs


def dedupe(jobs):
    seen = {}
    for j in jobs:
        seen[j["id"]] = j  # last write wins, keeps the list simple
    return list(seen.values())


def main():
    run_time = datetime.now(timezone.utc).isoformat()

    raw_jobs = scrape_all()
    jobs = dedupe(raw_jobs)
    print(f"\nScraped {len(raw_jobs)} listings, {len(jobs)} unique.")

    old_tracker = tracker.load()
    new_tracker, stats = tracker.merge_scrape(jobs, old_tracker, run_time)
    tracker.save(new_tracker)

    print(f"{stats['new']} new since last run.")
    print(f"{stats['carried_over']} carried over from a past run (status other than 'To Apply', no longer listed).")

    outputs.regenerate(new_tracker, generated_at=run_time)

    print(f"\nSaved {stats['total']} listings to {config.JOBS_CSV}")
    print(f"Dashboard: {config.DASHBOARD_FILE}")
    print("Run 'python serve.py' to open it and update statuses.")


if __name__ == "__main__":
    main()
