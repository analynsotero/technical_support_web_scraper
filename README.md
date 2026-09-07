# Technical Support Job Scraper

Scrapes entry-level Technical Support / IT Help Desk postings **directly
from each target company's own careers site** (not a generic multi-employer
job board), and doubles as an application tracker:

- `data/tracker.json` - the actual source of truth: every tracked job keyed by ID, with its status
- `data/jobs.csv` - the same data as a spreadsheet-friendly export
- `data/dashboard.html` - a browsable, filterable, sortable table with a status dropdown per job

## Target companies

Concentrix, Accenture, Sutherland, Teleperformance, TTEC, Foundever, Alorica,
TaskUs, VXI Global Solutions, and iQor are scraped **directly from their own
careers sites** - each one runs on a different platform (Workday, a custom
Elasticsearch API, Oracle Recruiting Cloud, SAP SuccessFactors, etc.), so
there's a dedicated scraper module per company in `scrapers/` rather than one
generic scraper. See "How it works" below for what each one does.

**TELUS Digital is the one exception.** Its careers site
(careers.telusdigital.com / jobs.telusdigital.com) blocks every plain HTTP
request behind a Cloudflare Managed Challenge (a JS puzzle), which can't be
solved without a headless browser - not used anywhere else in this project.
So `scrapers/telus_digital.py` falls back to searching LinkedIn, Indeed, and
JobStreet (the same scrapers `junior_data_engineer` uses) and keeping only
results whose company resolves to TELUS Digital via
`utils.matches_target_company()` - a company-filtered fallback for this one
company, not the broad multi-employer search this tracker otherwise avoids.

## Setup

From the `job-applications` folder:

```
pip install -r requirements.txt
```

Requires **Windows** with `curl.exe` available (built into Windows 10 1803+/Windows 11 -
this is what actually does the HTTP fetching; see "How it works" below).

## Usage

There are two scripts, run from inside this folder:

```
python run.py
```

Scrapes each of the 11 target companies (10 directly, TELUS Digital via the
job-board fallback) and merges what's found into the tracker (see "Tracking
applications" below). Takes 10-20 minutes - it deliberately waits ~2.5
seconds between requests to avoid being rate-limited or blocked, and the
TELUS Digital fallback alone runs the full job-title list against three
sites. Run it whenever you want a fresh look.

```
python serve.py
```

Opens the dashboard in your browser (http://127.0.0.1:8788) so you can
change a job's status. Leave it running while you use the tracker (Ctrl+C
to stop when done) - it only listens on `127.0.0.1`, so nothing outside
your machine can reach it. Opening `data/dashboard.html` directly by
double-clicking it also works for *viewing*, but status changes won't save
unless it's opened through `serve.py` (a plain file can't write back to
disk by itself).

Both scripts also work invoked from the parent `job-applications` folder as
`python technical_support/run.py` / `python technical_support/serve.py`.

## Tracking applications

Every job has a status - `To Apply`, `Applied`, `Initial Interview`,
`Technical Interview`, `Final Interview`, `Awaiting Decision`,
`Offer Received`, `Offer Accepted`, `Rejected`, `Withdrawn`, or
`No Response` - shown as a colored pill and changeable from the dropdown
in the dashboard's Status column. New listings always start at `To Apply`.

**Rerunning `python run.py` never resets or removes a status you've set.**
Specifically:
- A job still at `To Apply` that a site stops returning (it expired, got
  filled, or aged out) is dropped - there's no reason to keep something you
  never engaged with once it's gone.
- A job at any *other* status is kept on the list forever, even after the
  site stops returning it - it just gets tagged "no longer listed" in the
  dashboard so you know the original posting may no longer be live.
- A tracked job that's still being returned by a fresh scrape just gets
  its details (date posted, etc.) refreshed - its status is untouched
  either way.

## Configuration

Edit `config.py` to change:
- `SEARCH_TERMS` - the job titles used as search keywords against the
  companies whose career site supports server-side keyword search
  (Accenture, Teleperformance, TTEC, TaskUs, VXI, Alorica).
- `ROLE_KEYWORDS` - lowercase phrase fragments used to recognize a
  technical-support/helpdesk role by title (and for Teleperformance,
  description). Used by every scraper as the final relevance check, and as
  the *only* filter for the three companies with no server-side keyword
  search at all (Concentrix, Sutherland, iQor - see "How it works").
- `TARGET_COMPANIES` - only used by the TELUS Digital fallback, to
  recognize that company by name on a LinkedIn/Indeed/JobStreet result.
- `PAGES_PER_QUERY` - how many result pages to pull per query, for the
  companies/fallback sources that paginate.
- `ENTRY_LEVEL_KEYWORDS` - words used to flag postings as entry-level-friendly.
- `PAST_24_HOURS_ONLY` - only applies to the TELUS Digital fallback
  (LinkedIn/Indeed/JobStreet); the other 10 companies don't offer that
  filter, so freshness there depends on whatever date field each site
  itself returns (a couple don't return one at all - see "Known limitations").

## How it works

No headless browser is used anywhere - each company's career site is fetched
directly via `curl.exe` (see `utils.fetch`) and parsed from whatever
structured data it returns. The mechanics are different for every company:

| Company | Mechanism |
|---|---|
| Concentrix | One GET; entire PH job list is embedded as JSON in a `<script id="jobsData">` tag. No server-side keyword filter - `ROLE_KEYWORDS` does all the filtering. |
| Accenture | `POST /api/accenture/elastic/findjobs` (multipart form, like a browser FormData submit) against an in-house Elasticsearch API. The search is semantic/"vector", not literal, so it returns plenty of unrelated jobs too - titles are always re-checked. |
| Sutherland | One GET to the Shazamme widget backend (`shazamme.io`, needs a `Referer` header) that returns Sutherland's *entire global* job list in one response, no filter params at all - filtered entirely client-side. |
| Teleperformance | `GET /Umbraco/Api/Careers/GetCareersBase` - TP's own wrapper API around its iCIMS requisitions (iCIMS itself is CAPTCHA-blocked via AWS WAF if hit directly). TP Philippines posts almost everything under generic recruiting-funnel titles, so relevance is checked against the job **description**, not the title. |
| TTEC | Server-rendered HTML search (`?k=&l=&p=`). The location param doesn't actually filter server-side (verified: `l=Philippines` still returns Mexico/Colombia/India jobs), so PH is filtered client-side on each result's own location text. No date is available without fetching each job's detail page, which isn't done (too many extra requests) - `date_posted` is blank. |
| Foundever | Server-rendered HTML. Both the keyword (`q`) and page (`p`) params turned out to have no effect at all in testing, so this instead pages through SuccessFactors' real pagination param (`startrow`) and filters entirely client-side. |
| TELUS Digital | Not scraped directly - see "Target companies" above. |
| Alorica | Public Oracle Recruiting Cloud (Fusion HCM) JSON REST API, no auth. Its `location` filter is unreliable, so PH is filtered on the returned `PrimaryLocationCountry == "PH"` field. |
| TaskUs | `POST /wday/cxs/taskus/Careers/jobs` - Workday's standard public JSON search API, filtered to PH via a `locationCountry` facet ID. |
| VXI Global Solutions | `POST /api/jobs` - VXI's own Next.js server route, which proxies to Google Cloud Talent Solution using a key VXI holds server-side (not exposed to the browser). No canonical per-job URL was found, so `job_url` links back to the search page pre-filled with that job's title instead of a direct link. |
| iQor | One GET; entire *global* job list (not just PH) is embedded as JSON in a `<script id="__NEXT_DATA__">` tag - the `?country=` query param looks like a filter but does nothing, so PH is filtered client-side on `jobPostingCountryName`. Relevance is checked against title + category only, not description - iQor's postings share a boilerplate qualifications blurb that mentions "technical support" as one of several acceptable prior-experience types, which would otherwise match nearly every call-center role regardless of what the job actually is. |

The TELUS Digital fallback (`scrapers/telus_digital.py`) reuses
`scrapers/linkedin.py`, `scrapers/indeed.py`, and `scrapers/jobstreet.py` -
the same generic per-site scrapers `junior_data_engineer` uses (LinkedIn's
public guest search API, Indeed's embedded JSON, JobStreet's embedded
`window.SEEK_REDUX_DATA`) - and filters results down to that one company.

## Important: please read

Every one of these companies' Terms of Service technically prohibits
automated scraping of their site. This script is meant for **personal,
low-volume job searching only** - checking it a few times a day, not
running it continuously or at scale. Even so:

- No login/account is used anywhere, so there's no risk of an *account* ban.
- A site could still temporarily rate-limit or block requests coming from
  your IP if run too frequently - the built-in delay is there to minimize
  that, don't reduce it much further.
- Don't redistribute the scraped data or use this for anything beyond your
  own job search.

## Known limitations

- Several companies' server-side search/location filters turned out to be
  unreliable or entirely non-functional when tested (Accenture's search is
  semantic rather than literal; TTEC and Foundever's location/keyword params
  don't filter at all; Alorica's location filter is loose). Every scraper
  compensates with its own client-side filtering - see "How it works" for
  which fields it checks per company - but this means the underlying sites
  could change behavior without warning and silently make a scraper less
  accurate rather than obviously broken.
- `ROLE_KEYWORDS` filtering is phrase-based and reasonably precise, but it's
  still a heuristic - a genuinely relevant posting with unusual phrasing
  could be missed, and for the fetch-all-then-filter companies (Concentrix,
  Sutherland, iQor) it's the *only* filter, so it directly determines what
  shows up.
- TTEC's `date_posted` is always blank (no date on TTEC's list page, and
  fetching a detail page per result to get one wasn't worth the extra
  request volume).
- VXI's `job_url` isn't a direct link to the specific posting (none was
  found) - it links to VXI's search page pre-filled with that job's title.
- The "entry-level match" flag is a keyword heuristic, not a guarantee -
  use it as a hint, not a filter you should fully trust.
- Site layouts/APIs change over time; if a company suddenly returns 0
  results, that scraper likely needs a small update to match a markup/API
  change - `run.py` prints a per-company result count on every run, which
  is the easiest way to notice this happening.
- `serve.py` has to be running for status changes to save - if you edit a
  status while it's not running (or after closing it), the dashboard will
  show an error banner and revert the dropdown.
