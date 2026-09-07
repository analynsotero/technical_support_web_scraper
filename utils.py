import json
import os
import re
import subprocess
import tempfile
import time
import urllib.parse

from . import config


class FetchError(Exception):
    pass


def fetch(url, params=None, json_body=None, form_fields=None, headers=None):
    """Fetches a URL via the system's curl.exe rather than the `requests`
    library. Several of the sites this project talks to (Indeed, JobStreet,
    and some of the companies' own career sites) block Python's
    requests/urllib3 based on its TLS fingerprint even with a spoofed
    User-Agent header, but Windows' built-in curl.exe (which uses the OS's
    own Schannel TLS stack) gets through - verified directly against these
    sites before writing this.

    Plain GET by default. Pass `json_body` (a dict) to POST it as
    application/json, or `form_fields` (a dict) to POST it as
    multipart/form-data (some career-site APIs, e.g. Accenture's, expect a
    browser-style FormData submission rather than raw JSON). `headers` adds
    extra request headers (e.g. Referer, required by a couple of the widget
    APIs to resolve which tenant's jobs to return).

    The response body is written to a temp file with -o rather than
    captured from stdout: piping curl's stdout through Windows corrupts
    multi-byte UTF-8 sequences (verified - accented characters came back
    as replacement characters), but writing straight to a file preserves
    the bytes correctly.
    """
    if params:
        query = urllib.parse.urlencode({k: v for k, v in params.items() if v is not None})
        url = f"{url}?{query}"

    cmd = ["curl.exe", "-s", "-L", "-A", config.USER_AGENT, "--max-time", "20"]

    for key, value in (headers or {}).items():
        cmd += ["-H", f"{key}: {value}"]

    if json_body is not None:
        cmd += ["-X", "POST", "-H", "Content-Type: application/json", "--data-raw", json.dumps(json_body)]
    elif form_fields is not None:
        cmd += ["-X", "POST"]
        for key, value in form_fields.items():
            cmd += ["-F", f"{key}={value}"]

    fd, tmp_path = tempfile.mkstemp(suffix=".html")
    os.close(fd)
    cmd += ["-o", tmp_path, "-w", "%{http_code}", url]
    try:
        try:
            result = subprocess.run(cmd, capture_output=True, timeout=25)
        except (FileNotFoundError, subprocess.TimeoutExpired) as exc:
            raise FetchError(f"curl invocation failed: {exc}") from exc

        if result.returncode != 0:
            raise FetchError(f"curl exited {result.returncode}: {result.stderr.decode(errors='replace').strip()}")

        status = result.stdout.decode("ascii", errors="replace").strip()
        if not status.startswith("2"):
            raise FetchError(f"HTTP {status} for {url}")

        with open(tmp_path, "r", encoding="utf-8", errors="replace") as f:
            return f.read()
    finally:
        try:
            os.remove(tmp_path)
        except OSError:
            pass


def polite_delay():
    time.sleep(config.REQUEST_DELAY_SECONDS)


def looks_entry_level(*texts):
    combined = " ".join(t for t in texts if t).lower()
    return any(kw in combined for kw in config.ENTRY_LEVEL_KEYWORDS)


_ROLE_KEYWORD_PATTERNS = [
    re.compile(r"\b" + re.escape(kw) + r"\b") for kw in config.ROLE_KEYWORDS
]


def matches_role(*texts):
    """Used by scrapers that can't filter by keyword server-side (they fetch
    a company's full/broad job list and need to narrow it down themselves):
    True if any of the given texts (title, description, category, ...) look
    like one of the technical-support/IT-helpdesk roles in
    config.ROLE_KEYWORDS.

    Matches on whole-word boundaries rather than a plain substring check -
    short keywords like "it support" would otherwise false-positive inside
    unrelated text (e.g. "...process mapping, aud[it support]..." from
    "audit support").
    """
    combined = " ".join(t for t in texts if t).lower()
    return any(pattern.search(combined) for pattern in _ROLE_KEYWORD_PATTERNS)


def _normalize_company(name):
    return re.sub(r"[^a-z0-9]+", " ", (name or "").lower()).strip()


def matches_target_company(company_name):
    """Returns the canonical company label (a key of config.TARGET_COMPANIES)
    if company_name looks like one of the target companies, else None.
    Matching is done on a normalized name against each company's alias list,
    since job boards list the same employer under many legal-entity variants
    ("Concentrix Daksh Business Services", "TELUS International Philippines
    Inc.", etc.).
    """
    normalized = _normalize_company(company_name)
    if not normalized:
        return None
    for canonical, aliases in config.TARGET_COMPANIES.items():
        for alias in aliases:
            if _normalize_company(alias) in normalized:
                return canonical
    return None
