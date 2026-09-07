"""Scrapes Alorica's own careers site directly.

alorica.com/careers is just a WordPress marketing page with no real job
search - the actual requisitions live in Oracle Recruiting Cloud (Fusion
HCM), which exposes a public JSON REST API needing no auth. The API's
`location` filter is unreliable (returns some non-PH noise even when
asked for "Philippines"), so this filters on the returned
`PrimaryLocationCountry == "PH"` field instead, and titles are still
re-checked against utils.matches_role() since the keyword search itself
also returns some unrelated roles for a matching country.
"""

import json

from .. import config, utils

URL = "https://fa-euxw-saasfaprod1.fa.ocs.oraclecloud.com/hcmRestApi/resources/latest/recruitingCEJobRequisitions"
COMPANY = "Alorica"
RESULTS_PER_QUERY = 50


def scrape():
    jobs = {}

    for term in config.SEARCH_TERMS:
        finder = (
            "findReqs;siteNumber=CX_1,"
            "facetsList=LOCATIONS;TITLES;CATEGORIES;POSTING_DATES,"
            f"limit={RESULTS_PER_QUERY},keyword=\"{term}\""
        )
        params = {
            "onlyData": "true",
            "expand": "requisitionList.secondaryLocations",
            "finder": finder,
        }
        try:
            raw = utils.fetch(URL, params=params)
        except Exception as exc:
            print(f"  [alorica] request failed for '{term}': {exc}")
            continue

        try:
            data = json.loads(raw)
        except json.JSONDecodeError:
            continue

        items = data.get("items", [])
        reqs = items[0].get("requisitionList", []) if items else []

        for j in reqs:
            if j.get("PrimaryLocationCountry") != "PH":
                continue
            title = j.get("Title", "")
            job_id = j.get("Id")
            if not job_id or not utils.matches_role(title):
                continue

            jobs[job_id] = {
                "source": COMPANY,
                "id": f"alo_{job_id}",
                "title": title,
                "company": COMPANY,
                "matched_company": COMPANY,
                "location": j.get("PrimaryLocation", ""),
                "date_posted": j.get("PostedDate", ""),
                "job_url": f"https://fa-euxw-saasfaprod1.fa.ocs.oraclecloud.com/hcmUI/CandidateExperience/en/sites/CX_1/job/{job_id}",
                "search_term": term,
            }

        utils.polite_delay()

    return list(jobs.values())
