"""Scrapes LinkedIn's public "guest" job search endpoint (no login required).

This is the same endpoint the site itself uses to lazy-load more results
as you scroll, so it returns lightweight HTML fragments instead of a full
page. No account credentials are used, which avoids any risk of an
account ban - the worst case is the request gets rate-limited.
"""

from bs4 import BeautifulSoup

from .. import config, utils

BASE_URL = "https://www.linkedin.com/jobs-guest/jobs/api/seeMoreJobPostings/search"
RESULTS_PER_PAGE = 25


def scrape(search_term, location, pages=2):
    jobs = []

    for page in range(pages):
        start = page * RESULTS_PER_PAGE
        params = {"keywords": search_term, "location": location, "start": start}
        if config.PAST_24_HOURS_ONLY:
            params["f_TPR"] = "r86400"  # LinkedIn's "past 24 hours" filter
        try:
            html = utils.fetch(BASE_URL, params=params)
        except Exception as exc:
            print(f"  [linkedin] request failed: {exc}")
            break

        soup = BeautifulSoup(html, "html.parser")
        cards = soup.find_all("div", class_="base-card")
        if not cards:
            break

        for card in cards:
            title_el = card.find("h3", class_="base-search-card__title")
            link_el = card.find("a", class_="base-card__full-link")
            if not title_el or not link_el:
                continue

            company_el = card.find("h4", class_="base-search-card__subtitle")
            location_el = card.find("span", class_="job-search-card__location")
            # LinkedIn swaps in a "--new" class variant for recently-posted
            # jobs (job-search-card__listdate--new), so match by tag alone
            # rather than the base class - there's only one <time> per card.
            date_el = card.find("time")

            urn = card.get("data-entity-urn", "")
            job_id = urn.split(":")[-1] if urn else link_el["href"]

            jobs.append({
                "source": "LinkedIn",
                "id": f"li_{job_id}",
                "title": title_el.get_text(strip=True),
                "company": company_el.get_text(strip=True) if company_el else "",
                "location": location_el.get_text(strip=True) if location_el else "",
                "date_posted": date_el["datetime"] if date_el and date_el.has_attr("datetime") else "",
                "job_url": link_el["href"].split("?")[0],
                "search_term": search_term,
            })

        utils.polite_delay()

    return jobs
