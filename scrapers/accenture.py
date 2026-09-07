"""Scrapes Accenture's own careers site directly.

https://www.accenture.com/ph-en/careers/jobsearch is a custom search app
backed by an in-house Elasticsearch API
(POST /api/accenture/elastic/findjobs, submitted as multipart/form-data
like a browser FormData post - no auth needed). The search is a "vector"
(semantic) search rather than a strict keyword match, so a query for
"technical support" also returns plenty of unrelated roles (sorting by
relevancy rather than newest gets the real matches close to the front, but
titles are still re-checked against utils.matches_role() before being
kept).
"""

import json

from .. import config, utils

URL = "https://www.accenture.com/api/accenture/elastic/findjobs"
COMPANY = "Accenture"
RESULTS_PER_QUERY = 50


def scrape():
    jobs = {}

    for term in config.SEARCH_TERMS:
        fields = {
            "startIndex": "0",
            "maxResultSize": str(RESULTS_PER_QUERY),
            "jobKeyword": term,
            "jobCountry": "Philippines",
            "jobLanguage": "en",
            "countrySite": "ph-en",
            "sortBy": "0",  # relevancy - the semantic search ranks literal matches higher this way than "newest"
            "searchType": "vectorSearch",
            "jobFilters": "[]",
            "totalHits": "true",
        }
        try:
            raw = utils.fetch(URL, form_fields=fields)
        except Exception as exc:
            print(f"  [accenture] request failed for '{term}': {exc}")
            continue

        try:
            data = json.loads(raw)
        except json.JSONDecodeError:
            continue

        for j in data.get("data", []):
            title = j.get("title", "")
            req_id = j.get("requisitionId")
            if not req_id or not utils.matches_role(title):
                continue

            job_url = (j.get("jobDetailUrl") or "").replace("{0}", "ph-en")
            city = j.get("location")
            city = ", ".join(city) if isinstance(city, list) else city
            location = ", ".join(part for part in (city, j.get("country")) if part)

            jobs[req_id] = {
                "source": COMPANY,
                "id": f"acn_{req_id}",
                "title": title,
                "company": COMPANY,
                "matched_company": COMPANY,
                "location": location,
                "date_posted": j.get("updateDate", ""),
                "job_url": job_url,
                "search_term": term,
            }

        utils.polite_delay()

    return list(jobs.values())
