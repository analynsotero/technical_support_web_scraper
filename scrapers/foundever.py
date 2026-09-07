"""Scrapes Foundever's own careers site directly.

https://jobs.foundever.com/ runs on SAP SuccessFactors Recruiting
Marketing (Jobs2Web) - server-rendered HTML, no JS needed. Verified in
testing that the `q` (keyword) param has no effect at all (identical
top-of-list results for every keyword tried, sorted by something else
entirely) - so this doesn't bother sending it, and instead pages through
every Philippines-tagged posting via SuccessFactors' real pagination
param, `startrow` (10 results per page - found in the page's own "Page 2"
link, `?locationsearch=Philippines&startrow=10`), filtering the results
to role-relevant titles with utils.matches_role() same as the other
fetch-all-then-filter scrapers (concentrix/sutherland/iqor).
"""

from bs4 import BeautifulSoup

from .. import config, utils

BASE_URL = "https://jobs.foundever.com/search/"
COMPANY = "Foundever"
RESULTS_PER_PAGE = 10


def scrape():
    jobs = {}

    for page in range(config.PAGES_PER_QUERY * 3):  # smaller page size than other sites, so pull a few more
        params = {"locationsearch": "Philippines", "startrow": page * RESULTS_PER_PAGE}
        try:
            html = utils.fetch(BASE_URL, params=params)
        except Exception as exc:
            print(f"  [foundever] request failed for page {page + 1}: {exc}")
            break

        soup = BeautifulSoup(html, "html.parser")
        rows = soup.select("tr.data-row")
        if not rows:
            break

        for row in rows:
            link = row.select_one("a.jobTitle-link")
            if not link:
                continue
            title = link.get_text(strip=True)
            if not utils.matches_role(title):
                continue

            href = link.get("href", "")
            job_id = href.strip("/").split("/")[-1] if href else title
            location_el = row.select_one("span.jobLocation")
            date_el = row.select_one("span.jobDate")

            jobs[job_id] = {
                "source": COMPANY,
                "id": f"fdv_{job_id}",
                "title": title,
                "company": COMPANY,
                "matched_company": COMPANY,
                "location": location_el.get_text(strip=True) if location_el else "",
                "date_posted": date_el.get_text(strip=True) if date_el else "",
                "job_url": f"https://jobs.foundever.com{href}" if href else "",
                "search_term": "",
            }

        utils.polite_delay()

    return list(jobs.values())
