"""Scrapes Teleperformance's own careers site directly.

https://www.tp.com/en-ph/locations/philippines/careers/ is a custom
Umbraco/.NET site with its own wrapper API
(GET /Umbraco/Api/Careers/GetCareersBase) that aggregates the underlying
iCIMS requisitions - going to iCIMS directly
(careersph-teleperformance.icims.com) gets AWS-WAF CAPTCHA-blocked
regardless of headers used, but this wrapper endpoint isn't protected.

Teleperformance Philippines posts almost everything under generic
recruiting-funnel titles ("Teleperformance Philippines - Luzon - Customer
Expert") rather than per-specialty titles, so unlike the other scrapers
here, relevance is checked against the job DESCRIPTION (which does
mention "Technical Support Representatives" for the postings that route
into that queue) rather than the title, which would never match anything.
"""

import json

from .. import config, utils

URL = "https://www.tp.com/Umbraco/Api/Careers/GetCareersBase"
COMPANY = "Teleperformance"
NODE_ID = 1780  # fixed Umbraco content-node ID for the PH careers page
PAGE_SIZE = 20


def scrape():
    jobs = {}

    for term in config.SEARCH_TERMS:
        params = {
            "node": NODE_ID,
            "search": term,
            "country": "Philippines",
            "culture": "en-ph",
            "pageSize": PAGE_SIZE,
            "page": 0,
        }
        try:
            raw = utils.fetch(URL, params=params)
        except Exception as exc:
            print(f"  [teleperformance] request failed for '{term}': {exc}")
            continue

        try:
            data = json.loads(raw)
        except json.JSONDecodeError:
            continue

        for j in data.get("resultado", []):
            job_id = j.get("externalId")
            title = j.get("title", "")
            if not job_id or not utils.matches_role(j.get("description", "")):
                continue

            jobs[job_id] = {
                "source": COMPANY,
                "id": f"tp_{job_id}",
                "title": title,
                "company": COMPANY,
                "matched_company": COMPANY,
                "location": ", ".join(part for part in (j.get("location"), j.get("country")) if part),
                "date_posted": j.get("date", ""),
                "job_url": j.get("url", ""),
                "search_term": term,
            }

        utils.polite_delay()

    return list(jobs.values())
