"""Scrapes Concentrix's own careers site directly.

https://jobs.concentrix.com/philippines/ is a WordPress/Elementor page
that embeds its entire Philippines job list as JSON in a
<script id="jobsData"> element on first load (real requisitions live in
Workday and get synced into this feed) - no JS execution or pagination
needed, one GET returns everything. There's no server-side keyword filter,
so relevance filtering (utils.matches_role) happens client-side here.
"""

import json
import re

from .. import utils

URL = "https://jobs.concentrix.com/philippines/"
COMPANY = "Concentrix"
_PATTERN = re.compile(
    r'<script[^>]+id="jobsData"[^>]*>(.*?)</script>', re.S
)


def scrape():
    try:
        html = utils.fetch(URL)
    except Exception as exc:
        print(f"  [concentrix] request failed: {exc}")
        return []

    match = _PATTERN.search(html)
    if not match:
        return []

    try:
        payload = json.loads(match.group(1))
    except json.JSONDecodeError:
        return []

    jobs = []
    for j in payload.get("data", []):
        job_id = j.get("id")
        title = j.get("job_title", "")
        if not job_id or not utils.matches_role(title):
            continue

        location = ", ".join(
            part for part in (j.get("city"), j.get("state"), j.get("country")) if part
        )

        jobs.append({
            "source": COMPANY,
            "id": f"cnx_{job_id}",
            "title": title,
            "company": COMPANY,
            "matched_company": COMPANY,
            "location": location,
            "date_posted": j.get("created_at", ""),
            "job_url": j.get("apply_url") or j.get("landing_page_url", ""),
            "search_term": "",
        })

    return jobs
