"""Scrapes Sutherland's own careers site directly.

The public-facing page (jobs.sutherlandglobal.com/job-results) is a Duda
site embedding a Shazamme job-search widget; the widget's backend
(shazamme.io) has no documented keyword/country filter and just returns
every job Sutherland has open worldwide in one response - a Referer header
matching the Duda site is required to resolve which tenant's jobs to
return. So this fetches everything once and filters to Philippines +
role-relevant titles client-side.
"""

import json

from .. import utils

URL = "https://shazamme.io/Job-Listing/src/php/actions"
COMPANY = "Sutherland"
_REFERER = "https://www.jobs.sutherlandglobal.com/job-results"


def scrape():
    try:
        raw = utils.fetch(
            URL,
            params={"dudaSiteID": "76755cce", "action": "Get Jobs"},
            headers={"Referer": _REFERER},
        )
    except Exception as exc:
        print(f"  [sutherland] request failed: {exc}")
        return []

    try:
        entries = json.loads(raw.strip())
    except json.JSONDecodeError:
        return []

    jobs = []
    for entry in entries:
        j = entry.get("data", {})
        if j.get("country") != "Philippines":
            continue

        title = j.get("jobName", "")
        job_id = j.get("jobID")
        if not job_id or not utils.matches_role(title, j.get("category", ""), j.get("subCategory") or ""):
            continue

        location = ", ".join(part for part in (j.get("city"), j.get("state")) if part) or "Philippines"

        jobs.append({
            "source": COMPANY,
            "id": f"sthd_{job_id}",
            "title": title,
            "company": COMPANY,
            "matched_company": COMPANY,
            "location": location,
            "date_posted": j.get("postedDate", ""),
            "job_url": j.get("applicationURL") or j.get("jobURL", ""),
            "search_term": "",
        })

    return jobs
