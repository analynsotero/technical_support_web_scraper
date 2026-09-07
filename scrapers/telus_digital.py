"""Scrapes TELUS Digital job postings - via LinkedIn/Indeed/JobStreet, not
TELUS Digital's own site.

TELUS Digital's own careers site (careers.telusdigital.com /
jobs.telusdigital.com) is fronted by Cloudflare's Managed Challenge on
every path, including any API routes - a plain HTTP request gets a 403
with a JS-only challenge page, which can't be solved without a headless
browser (not used anywhere else in this project, deliberately, so this
one company doesn't get a different dependency footprint than the other
ten). TELUS Digital's own public Ashby job board
(api.ashbyhq.com/posting-api/job-board/telus-digital) was also checked -
it's fully open, but only lists the AI Data Solutions/corporate arm
(US/Canada/LatAm/India/Bulgaria roles), not the Philippines BPO postings
this tracker is after.

So this is the one company still scraped the "generic job board" way: run
each of config.SEARCH_TERMS against LinkedIn, Indeed, and JobStreet (same
scrapers junior_data_engineer uses), then keep only results whose company
field resolves to "TELUS Digital" via utils.matches_target_company() - a
company-filtered fallback, not the broad multi-employer search this
tracker otherwise avoids.
"""

from . import linkedin, indeed, jobstreet
from .. import config, utils

COMPANY = "TELUS Digital"


def scrape():
    jobs = {}
    seen_jobstreet_terms = set()

    for term in config.SEARCH_TERMS:
        queries = [(term, config.PRIMARY_LOCATION)]
        if config.INCLUDE_REMOTE_SEARCH:
            queries.append((f"{term} remote", ""))

        for search_term, location in queries:
            for raw in linkedin.scrape(search_term, location, pages=config.PAGES_PER_QUERY):
                _keep_if_telus(jobs, raw)
            utils.polite_delay()

            for raw in indeed.scrape(search_term, location, pages=config.PAGES_PER_QUERY):
                _keep_if_telus(jobs, raw)
            utils.polite_delay()

            base_term = search_term.removesuffix(" remote")
            if base_term not in seen_jobstreet_terms:
                for raw in jobstreet.scrape(base_term, pages=config.PAGES_PER_QUERY):
                    _keep_if_telus(jobs, raw)
                seen_jobstreet_terms.add(base_term)
                utils.polite_delay()

    return list(jobs.values())


def _keep_if_telus(jobs, raw):
    if utils.matches_target_company(raw["company"]) != COMPANY:
        return
    raw["matched_company"] = COMPANY
    jobs[raw["id"]] = raw
