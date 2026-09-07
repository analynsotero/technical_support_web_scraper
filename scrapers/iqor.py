"""Scrapes iQor's own careers site directly.

https://apply.iqor.com/jobs is a Next.js app that server-renders its
entire GLOBAL job list into a <script id="__NEXT_DATA__"> JSON blob on
first load - one GET returns everything, no pagination needed. The
`?country=Philippines` query param looks like a filter but doesn't
actually do anything server-side (verified: the response is identical
with or without it, and includes US/India/Colombia/Mexico postings too),
so this filters on each job's own `jobPostingCountryName` field instead.

iQor's titles are usually specific enough on their own ("Desktop
Technician II", "IT Security Analyst"), so relevance filtering checks
title + category rather than the full description - the description turned
out to be a bad signal here: most iQor postings share a boilerplate
qualifications blurb ("...experience in collections/sales/customer
service/technical support...") that would match nearly every call-center
role regardless of what the job actually is.
"""

import json
import re

from .. import utils

URL = "https://apply.iqor.com/jobs"
COMPANY = "iQor"
_PATTERN = re.compile(
    r'<script id="__NEXT_DATA__"[^>]*>(.*?)</script>', re.S
)


def scrape():
    try:
        html = utils.fetch(URL)
    except Exception as exc:
        print(f"  [iqor] request failed: {exc}")
        return []

    match = _PATTERN.search(html)
    if not match:
        return []

    try:
        data = json.loads(match.group(1))
    except json.JSONDecodeError:
        return []

    listing = data.get("props", {}).get("pageProps", {}).get("listData", [])

    jobs = []
    for j in listing:
        job_id = j.get("jobPostingID")
        title = j.get("jobTitleName", "")
        if not job_id or j.get("jobPostingCountryName") != "Philippines":
            continue
        if not utils.matches_role(title, j.get("jobCategory", ""), j.get("laborCategory", "")):
            continue

        location = ", ".join(
            part for part in (j.get("jobPostingCity"), j.get("jobPostingStateName"), j.get("jobPostingCountryName"))
            if part
        )

        jobs.append({
            "source": COMPANY,
            "id": f"iqr_{job_id}",
            "title": title,
            "company": COMPANY,
            "matched_company": COMPANY,
            "location": location,
            "date_posted": j.get("startDt", ""),
            "job_url": f"https://apply.iqor.com/jobs/{job_id}",
            "search_term": "",
        })

    return jobs
