"""Scrapes TTEC's own careers site directly.

https://www.ttecjobs.com/en/search-jobs is a TalentBrew (Radancy) career
site - fully server-rendered HTML, no JS needed. Keyword (k) + location
(l) + page (p) are plain query params; TalentBrew's keyword search is a
literal text match (unlike Accenture's semantic search), so results are
already relevant to the keyword, though titles are still re-checked
against utils.matches_role() as a cheap safety net. The `l` (location)
param, on the other hand, turned out NOT to filter server-side at all
(verified: `l=Philippines` still returns jobs in Mexico, Colombia, India,
etc.), so this filters on each result's own location text instead.

TalentBrew doesn't put a date on the search-results list page - it's only
on each job's own detail page (in a JobPosting JSON-LD block) - and
fetching a detail page per result would multiply the request count many
times over, so date_posted is left blank here rather than doing that.
"""

from bs4 import BeautifulSoup

from .. import config, utils

BASE_URL = "https://www.ttecjobs.com/en/search-jobs"
SITE_ROOT = "https://www.ttecjobs.com"
COMPANY = "TTEC"


def scrape():
    jobs = {}

    for term in config.SEARCH_TERMS:
        for page in range(1, config.PAGES_PER_QUERY + 1):
            params = {"k": term, "l": "Philippines", "p": page}
            try:
                html = utils.fetch(BASE_URL, params=params)
            except Exception as exc:
                print(f"  [ttec] request failed for '{term}' page {page}: {exc}")
                break

            soup = BeautifulSoup(html, "html.parser")
            cards = soup.select("a[data-job-id]")
            if not cards:
                break

            for card in cards:
                job_id = card.get("data-job-id")
                title_el = card.select_one("h2.job-title-logo-spacing")
                location_el = card.select_one("span.job-location")
                title = title_el.get_text(strip=True) if title_el else ""
                location = location_el.get_text(strip=True) if location_el else ""
                if not job_id or "philippines" not in location.lower() or not utils.matches_role(title):
                    continue

                jobs[job_id] = {
                    "source": COMPANY,
                    "id": f"ttec_{job_id}",
                    "title": title,
                    "company": COMPANY,
                    "matched_company": COMPANY,
                    "location": location,
                    "date_posted": "",
                    "job_url": f"{SITE_ROOT}{card['href']}" if card.get("href") else "",
                    "search_term": term,
                }

            utils.polite_delay()

    return list(jobs.values())
