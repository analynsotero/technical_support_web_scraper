"""Scrapes VXI Global Solutions's own careers site directly.

jobs.vxi.com/jobs is a Next.js app whose server-side API route
(POST /api/jobs) proxies to Google Cloud Talent Solution - it needs no
auth since VXI's own server holds the GCTS API key, not the browser.
Titles are re-checked against utils.matches_role() since the search
returns some unrelated roles alongside real matches (e.g. "Team Leader",
"Customer Experience Advisors" show up for a "technical support" query
too).

No canonical per-job detail URL was found (the site doesn't expose one in
its API response or its static HTML), so job_url links back to the search
page pre-filled with this posting's title as the query instead.
"""

import json
import urllib.parse

from .. import config, utils

URL = "https://jobs.vxi.com/api/jobs"
SEARCH_PAGE = "https://jobs.vxi.com/jobs"
COMPANY = "VXI Global Solutions"


def scrape():
    jobs = {}

    for term in config.SEARCH_TERMS:
        body = {"params": {"qu": term, "lo": "Philippines"}, "pageToken": None}
        try:
            raw = utils.fetch(URL, json_body=body)
        except Exception as exc:
            print(f"  [vxi] request failed for '{term}': {exc}")
            continue

        try:
            data = json.loads(raw)
        except json.JSONDecodeError:
            continue

        for m in data.get("jobData", {}).get("matchingJobs", []):
            j = m.get("job", {})
            title = j.get("title", "")
            req_id = j.get("requisitionId")
            if not req_id or not utils.matches_role(title):
                continue

            addresses = j.get("addresses") or []
            query = urllib.parse.urlencode({"qu": title, "lo": "Philippines"})

            jobs[req_id] = {
                "source": COMPANY,
                "id": f"vxi_{req_id}",
                "title": title,
                "company": COMPANY,
                "matched_company": COMPANY,
                "location": addresses[0] if addresses else "",
                "date_posted": j.get("postingPublishTime", ""),
                "job_url": f"{SEARCH_PAGE}?{query}",
                "search_term": term,
            }

        utils.polite_delay()

    return list(jobs.values())
