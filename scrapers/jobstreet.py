"""Scrapes JobStreet Philippines search results.

JobStreet (SEEK) server-renders the full result set into a JSON blob
embedded in the page (window.SEEK_REDUX_DATA), so no headless browser is
needed despite the site being a JS-heavy React app. We hit the generic
`/jobs?keywords=...` search endpoint and let JobStreet redirect to its
canonical, human-readable URL rather than trying to guess their slug
rules ourselves.
"""

import json
import re

from .. import config, utils

BASE_URL = "https://ph.jobstreet.com/jobs"
RESULTS_PER_PAGE = 30
_PATTERN = re.compile(
    r"window\.SEEK_REDUX_DATA\s*=\s*(\{.*?\})\s*;\s*window", re.S
)


def scrape(search_term, pages=2):
    jobs = []

    for page in range(1, pages + 1):
        params = {"keywords": search_term, "page": page}
        if config.PAST_24_HOURS_ONLY:
            params["daterange"] = 1  # JobStreet's "last 24 hours" date-listed filter
        try:
            html = utils.fetch(BASE_URL, params=params)
        except Exception as exc:
            print(f"  [jobstreet] request failed: {exc}")
            break

        match = _PATTERN.search(html)
        if not match:
            break

        try:
            data = json.loads(match.group(1))
        except json.JSONDecodeError:
            break

        job_list = (
            data.get("results", {})
                .get("results", {})
                .get("jobs", [])
        )
        if not job_list:
            break

        for j in job_list:
            job_id = j.get("id")
            if not job_id:
                continue

            locations = j.get("locations") or []
            location_label = locations[0].get("label", "") if locations else ""

            jobs.append({
                "source": "JobStreet",
                "id": f"js_{job_id}",
                "title": j.get("title", ""),
                "company": j.get("companyName", ""),
                "location": location_label,
                "date_posted": j.get("listingDateDisplay", ""),
                "job_url": f"https://ph.jobstreet.com/job/{job_id}",
                "search_term": search_term,
            })

        utils.polite_delay()

    return jobs
