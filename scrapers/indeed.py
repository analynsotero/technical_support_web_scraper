"""Scrapes Indeed Philippines search results.

Indeed server-renders each page's job cards into a JSON blob embedded in
the HTML (window.mosaic.providerData["mosaic-provider-jobcards"]), so we
parse that directly instead of scraping visible text - it's both more
reliable and gives us structured fields (company rating, exact job key
for the URL, etc.) that aren't reliably present in the rendered markup.
"""

import json
import re

from .. import config, utils

DOMAIN = "ph.indeed.com"
RESULTS_PER_PAGE = 10
_PATTERN = re.compile(
    r'window\.mosaic\.providerData\["mosaic-provider-jobcards"\]\s*=\s*(\{.*?\});',
    re.S,
)


def scrape(search_term, location, pages=2):
    jobs = []

    for page in range(pages):
        params = {"q": search_term, "start": page * RESULTS_PER_PAGE}
        if location:
            params["l"] = location
        if config.PAST_24_HOURS_ONLY:
            params["fromage"] = 1  # Indeed's "last 24 hours" date-posted filter

        try:
            html = utils.fetch(f"https://{DOMAIN}/jobs", params=params)
        except Exception as exc:
            print(f"  [indeed] request failed: {exc}")
            break

        match = _PATTERN.search(html)
        if not match:
            break

        try:
            data = json.loads(match.group(1))
        except json.JSONDecodeError:
            break

        results = (
            data.get("metaData", {})
                .get("mosaicProviderJobCardsModel", {})
                .get("results", [])
        )
        if not results:
            break

        for r in results:
            job_key = r.get("jobkey")
            if not job_key:
                continue

            jobs.append({
                "source": "Indeed",
                "id": f"in_{job_key}",
                "title": r.get("displayTitle") or r.get("title", ""),
                "company": r.get("company", ""),
                "location": r.get("formattedLocation", ""),
                "date_posted": r.get("formattedRelativeTime", ""),
                "job_url": f"https://{DOMAIN}/viewjob?jk={job_key}",
                "search_term": search_term,
            })

        utils.polite_delay()

    return jobs
