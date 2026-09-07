import os

# Job titles used as search keywords against companies whose own career
# site supports server-side keyword search (Accenture, Teleperformance,
# TTEC, Foundever, Alorica, TaskUs, VXI). Covers the core "Technical
# Support" titling plus adjacent entry-level IT/helpdesk/NOC/support roles,
# since postings for this kind of work get listed under all of these.
SEARCH_TERMS = [
    "Technical Support Representative",
    "Technical Support Associate",
    "IT Support Associate",
    "IT Service Desk Analyst",
    "Service Desk Associate",
    "Help Desk Analyst",
    "IT Help Desk Support",
    "Desktop Support",
    "IT Support Specialist",
    "Application Support Analyst",
    "Technical Support Engineer Junior",
    "NOC Analyst Entry Level",
    "IT Operations Associate",
    "L1 Support",
    "Level 1 Technical Support",
    "Customer Technical Support",
    "Product Support Specialist",
    "SaaS Support Specialist",
]

# Lowercase phrase fragments used to recognize a technical-support/helpdesk
# role by its title (and sometimes description). Two things use this:
#   - Companies whose career site has no server-side keyword filter
#     (Concentrix, Sutherland, iQor) fetch their *entire* PH job list in one
#     request and this is the only filter applied.
#   - Companies that DO support a keyword param (see SEARCH_TERMS above)
#     still get their results re-checked against this, since a couple of
#     those search APIs turned out to rank loosely rather than strictly
#     filter (e.g. Foundever, Teleperformance return non-matching titles
#     alongside real matches).
# Deliberately phrase-based rather than single words like "technical" or
# "support" alone, which would also match unrelated roles like "Technical
# Architect" or "Sales Support".
ROLE_KEYWORDS = [
    "technical support", "tech support", "it support", "help desk",
    "helpdesk", "service desk", "desktop support", "desktop technician",
    "application support", "product support", "saas support",
    "noc analyst", "noc engineer", "level 1 support", "level 1 technical",
    "l1 support", "tier 1 support", "it operations", "it help desk",
    "customer technical support", "it service desk",
]

# The 11 companies this tracker follows, and the aliases used to recognize
# them from a raw "company" string on a third-party job board (job boards
# list the same employer under many legal-entity variants, e.g. "Concentrix
# Daksh Business Services", "TELUS International Philippines"). Only used
# by the TELUS Digital scraper, which falls back to searching LinkedIn/
# Indeed/JobStreet and filtering to this company - TELUS Digital's own
# careers site blocks plain HTTP requests with a Cloudflare JS challenge
# that can't be solved without a headless browser (not used in this
# project). Every other company is scraped directly from its own career
# site - see utils.matches_target_company() and scrapers/telus_digital.py.
TARGET_COMPANIES = {
    "Concentrix": ["concentrix"],
    "Accenture": ["accenture"],
    "Sutherland": ["sutherland"],
    "Teleperformance": ["teleperformance"],
    "TTEC": ["ttec"],
    "Foundever": ["foundever", "sitel"],  # Sitel rebranded to Foundever in 2022
    "TELUS Digital": ["telus digital", "telus international", "telus"],
    "Alorica": ["alorica"],
    "TaskUs": ["taskus"],
    "VXI Global Solutions": ["vxi global", "vxi"],
    "iQor": ["iqor"],
}

# Main location searched. JobStreet PH's results already include
# remote-tagged local jobs, so it only needs the one pass.
PRIMARY_LOCATION = "Philippines"

# For the TELUS Digital fallback (LinkedIn/Indeed), also run each term with
# "remote" appended and no location filter, to catch remote roles open to
# PH-based applicants.
INCLUDE_REMOTE_SEARCH = True

# How many result pages to pull per query, for the companies whose career
# site paginates results (TTEC, Foundever) and for the TELUS Digital
# fallback (LinkedIn/Indeed/JobStreet).
PAGES_PER_QUERY = 2

# Only keep postings listed within the last 24 hours - applied only to the
# TELUS Digital fallback (LinkedIn/Indeed/JobStreet), as a server-side
# filter on each site's search:
#   LinkedIn f_TPR=r86400, Indeed fromage=1, JobStreet daterange=1
# The other 10 companies are scraped directly from their own current
# listings, which don't offer this filter - freshness there is judged by
# whatever date field each site returns (some don't return one at all).
PAST_24_HOURS_ONLY = True

# Delay between HTTP requests. Keep this polite - these sites are being
# scraped without an official API, so avoid hammering them.
REQUEST_DELAY_SECONDS = 2.5

USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/124.0 Safari/537.36"
)

# Used to flag postings that look friendly to entry-level/junior applicants.
# This is a soft signal (added as a column), not a hard filter, since
# plenty of genuinely junior-friendly postings never use these exact words.
ENTRY_LEVEL_KEYWORDS = [
    "junior", "jr.", "entry level", "entry-level", "fresh grad",
    "fresh graduate", "graduate", "trainee", "associate",
    "no experience", "0-1 year", "l1", "level 1", "tier 1",
]

# Application-tracking statuses, in pipeline order. The dashboard shows
# these as a dropdown per job; jobs.csv/tracker.json store whichever one is
# currently selected. Every freshly scraped job starts at STATUSES[0].
STATUSES = [
    "To Apply",
    "Applied",
    "Initial Interview",
    "Technical Interview",
    "Final Interview",
    "Awaiting Decision",
    "Offer Received",
    "Offer Accepted",
    "Rejected",
    "Withdrawn",
    "No Response",
]
DEFAULT_STATUS = STATUSES[0]

# Local server used only so the dashboard can save status changes back to
# disk (a static HTML file opened directly can't write files itself). Binds
# to localhost only - see serve.py. Uses a different port than the
# junior_data_engineer tracker so both dashboards can run at once.
SERVER_HOST = "127.0.0.1"
SERVER_PORT = 8788

_PACKAGE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(_PACKAGE_DIR, "data")
JOBS_CSV = os.path.join(DATA_DIR, "jobs.csv")
TRACKER_FILE = os.path.join(DATA_DIR, "tracker.json")
DASHBOARD_FILE = os.path.join(DATA_DIR, "dashboard.html")
