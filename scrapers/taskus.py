"""Scrapes TaskUs's own careers site directly.

jobs.taskus.com is a marketing wrapper around a Workday career site
(taskus.wd1.myworkdayjobs.com); Workday exposes a public JSON search API
(POST /wday/cxs/taskus/Careers/jobs) that needs no auth. Philippines is
selected via a `locationCountry` facet ID rather than a text param -
`e56f1daf83e04bacae794ba5c5593560` is TaskUs's fixed facet value for
Philippines (found via an unfiltered facets query; stable, hardcoded
here). The full-text search is reasonably literal, but titles are still
re-checked against utils.matches_role() to drop the occasional unrelated
match (e.g. "Technical Writer").
"""

import json

from .. import config, utils

URL = "https://taskus.wd1.myworkdayjobs.com/wday/cxs/taskus/Careers/jobs"
CAREERS_BASE = "https://taskus.wd1.myworkdayjobs.com/Careers"
COMPANY = "TaskUs"
PHILIPPINES_FACET_ID = "e56f1daf83e04bacae794ba5c5593560"
RESULTS_PER_QUERY = 20


def scrape():
    jobs = {}

    for term in config.SEARCH_TERMS:
        body = {
            "appliedFacets": {"locationCountry": [PHILIPPINES_FACET_ID]},
            "limit": RESULTS_PER_QUERY,
            "offset": 0,
            "searchText": term,
        }
        try:
            raw = utils.fetch(URL, json_body=body)
        except Exception as exc:
            print(f"  [taskus] request failed for '{term}': {exc}")
            continue

        try:
            data = json.loads(raw)
        except json.JSONDecodeError:
            continue

        for j in data.get("jobPostings", []):
            title = j.get("title", "")
            external_path = j.get("externalPath", "")
            if not external_path or not utils.matches_role(title):
                continue

            bullet_fields = j.get("bulletFields") or [""]
            job_id = bullet_fields[0] or external_path

            jobs[job_id] = {
                "source": COMPANY,
                "id": f"tu_{job_id}",
                "title": title,
                "company": COMPANY,
                "matched_company": COMPANY,
                "location": j.get("locationsText", ""),
                "date_posted": j.get("postedOn", ""),
                "job_url": f"{CAREERS_BASE}{external_path}",
                "search_term": term,
            }

        utils.polite_delay()

    return list(jobs.values())
