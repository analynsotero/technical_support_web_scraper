"""Generates the local HTML dashboard from the current tracker state.

Viewing it is fine by just opening the file, but changing a job's status
only saves if it's opened through serve.py (http://127.0.0.1:8788) -
that's what's actually listening for the save request. Opened as a bare
file (file://), status changes will show an error telling you to run
serve.py.
"""

import json

from . import config

_TEMPLATE = """<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<title>Technical Support Job Search</title>
<style>
  body {{ font-family: Segoe UI, Arial, sans-serif; margin: 0; padding: 24px; background: #f7f7f9; color: #1a1a1a; }}
  h1 {{ font-size: 20px; margin: 0 0 4px; }}
  .meta {{ color: #666; font-size: 13px; margin-bottom: 16px; }}
  .controls {{ display: flex; gap: 12px; flex-wrap: wrap; margin-bottom: 16px; align-items: center; }}
  .controls input, .controls select {{ padding: 6px 10px; font-size: 14px; border: 1px solid #ccc; border-radius: 6px; }}
  .controls input[type=text] {{ flex: 1; min-width: 200px; }}
  table {{ width: 100%; border-collapse: collapse; background: #fff; border-radius: 8px; overflow: hidden; box-shadow: 0 1px 3px rgba(0,0,0,0.08); }}
  th, td {{ text-align: left; padding: 10px 12px; border-bottom: 1px solid #eee; font-size: 13px; vertical-align: top; }}
  th {{ background: #fafafa; cursor: pointer; user-select: none; position: sticky; top: 0; }}
  tr:hover {{ background: #f6f9ff; }}
  tr.delisted {{ opacity: 0.6; }}
  a {{ color: #1a56db; text-decoration: none; }}
  a:hover {{ text-decoration: underline; }}
  .badge {{ display: inline-block; font-size: 11px; padding: 2px 7px; border-radius: 10px; font-weight: 600; }}
  .badge.new {{ background: #e6f4ea; color: #1e7e34; }}
  .badge.entry {{ background: #fff4e0; color: #9a6700; }}
  .badge.delisted {{ background: #eee; color: #777; }}
  #count {{ font-size: 13px; color: #666; margin-bottom: 8px; }}
  #saveError {{ display: none; background: #fdecea; color: #a4262c; padding: 8px 12px; border-radius: 6px; font-size: 13px; margin-bottom: 12px; }}
  select.status {{
    padding: 4px 10px; font-size: 12px; font-weight: 600; border-radius: 999px;
    border: 1px solid; cursor: pointer;
  }}
</style>
</head>
<body>
  <h1>Technical Support Job Search</h1>
  <div class="meta">Generated {generated_at} &middot; {total} listings scraped directly from each company's own careers site (Concentrix, Accenture, Sutherland, Teleperformance, TTEC, Foundever, Alorica, TaskUs, VXI Global Solutions, iQor) &middot; TELUS Digital via LinkedIn/Indeed/JobStreet, company-filtered - its own site blocks direct scraping</div>
  <div id="saveError"></div>

  <div class="controls">
    <input type="text" id="search" placeholder="Filter by title, company, or location...">
    <select id="companyFilter">
      <option value="">All companies</option>
      {company_options}
    </select>
    <select id="sourceFilter">
      <option value="">All sources</option>
    </select>
    <select id="statusFilter">
      <option value="">All statuses</option>
      {status_options}
    </select>
    <label><input type="checkbox" id="entryOnly"> Entry-level match only</label>
    <label><input type="checkbox" id="newOnly"> New since last run only</label>
  </div>

  <div id="count"></div>
  <table id="jobsTable">
    <thead>
      <tr>
        <th data-key="title">Title</th>
        <th data-key="company">Company</th>
        <th data-key="location">Location</th>
        <th data-key="source">Scraped Via</th>
        <th data-key="date_posted">Posted</th>
        <th data-key="status">Status</th>
        <th data-key="flags">Flags</th>
      </tr>
    </thead>
    <tbody></tbody>
  </table>

<script>
const JOBS = {jobs_json};
const STATUSES = {statuses_json};
const STATUS_STYLES = {status_styles_json};
let sortKey = null, sortAsc = true;

function statusOptionsHtml(current) {{
  return STATUSES.map(s => `<option value="${{s}}" ${{s === current ? 'selected' : ''}}>${{s}}</option>`).join('');
}}

function populateSourceFilter() {{
  const select = document.getElementById('sourceFilter');
  const sources = [...new Set(JOBS.map(j => j.source))].sort();
  select.innerHTML = '<option value="">All sources</option>' +
    sources.map(s => `<option value="${{s}}">${{s}}</option>`).join('');
}}

function paintStatus(select, status) {{
  const c = STATUS_STYLES[status];
  select.style.color = c.text;
  select.style.backgroundColor = c.bg;
  select.style.borderColor = c.text;
}}

async function updateStatus(id, select) {{
  const newStatus = select.value;
  const job = JOBS.find(j => j.id === id);
  const previous = job ? job.status : null;
  try {{
    const resp = await fetch('/api/status', {{
      method: 'POST',
      headers: {{'Content-Type': 'application/json'}},
      body: JSON.stringify({{id, status: newStatus}}),
    }});
    const data = await resp.json();
    if (!resp.ok || !data.ok) throw new Error(data.error || ('HTTP ' + resp.status));
    if (job) job.status = newStatus;
    paintStatus(select, newStatus);
    document.getElementById('saveError').style.display = 'none';
  }} catch (err) {{
    if (job) select.value = previous;
    paintStatus(select, previous);
    const box = document.getElementById('saveError');
    box.textContent = 'Could not save status - is serve.py running? (' + err.message + ')';
    box.style.display = 'block';
  }}
}}

function render() {{
  const q = document.getElementById('search').value.toLowerCase();
  const company = document.getElementById('companyFilter').value;
  const source = document.getElementById('sourceFilter').value;
  const status = document.getElementById('statusFilter').value;
  const entryOnly = document.getElementById('entryOnly').checked;
  const newOnly = document.getElementById('newOnly').checked;

  let rows = JOBS.filter(j => {{
    if (company && j.matched_company !== company) return false;
    if (source && j.source !== source) return false;
    if (status && j.status !== status) return false;
    if (entryOnly && !j.is_entry_level) return false;
    if (newOnly && !j.is_new) return false;
    if (q) {{
      const hay = (j.title + ' ' + j.company + ' ' + j.location).toLowerCase();
      if (!hay.includes(q)) return false;
    }}
    return true;
  }});

  if (sortKey) {{
    rows.sort((a, b) => {{
      const av = (a[sortKey] || '').toString().toLowerCase();
      const bv = (b[sortKey] || '').toString().toLowerCase();
      if (av < bv) return sortAsc ? -1 : 1;
      if (av > bv) return sortAsc ? 1 : -1;
      return 0;
    }});
  }}

  document.getElementById('count').textContent = rows.length + ' of ' + JOBS.length + ' listings shown';

  const tbody = document.querySelector('#jobsTable tbody');
  tbody.innerHTML = rows.map(j => `
    <tr class="${{j.still_listed ? '' : 'delisted'}}">
      <td><a href="${{j.job_url}}" target="_blank" rel="noopener">${{j.title}}</a></td>
      <td>${{j.company}}</td>
      <td>${{j.location}}</td>
      <td>${{j.source}}</td>
      <td>${{j.date_posted}}</td>
      <td>
        <select class="status" onchange="updateStatus('${{j.id}}', this)"
                style="color:${{STATUS_STYLES[j.status].text}}; background-color:${{STATUS_STYLES[j.status].bg}}; border-color:${{STATUS_STYLES[j.status].text}}">
          ${{statusOptionsHtml(j.status)}}
        </select>
      </td>
      <td>
        ${{j.is_new ? '<span class="badge new">NEW</span> ' : ''}}
        ${{j.is_entry_level ? '<span class="badge entry">entry-level match</span> ' : ''}}
        ${{j.still_listed ? '' : '<span class="badge delisted">no longer listed</span>'}}
      </td>
    </tr>
  `).join('');
}}

populateSourceFilter();
document.getElementById('search').addEventListener('input', render);
document.getElementById('companyFilter').addEventListener('change', render);
document.getElementById('sourceFilter').addEventListener('change', render);
document.getElementById('statusFilter').addEventListener('change', render);
document.getElementById('entryOnly').addEventListener('change', render);
document.getElementById('newOnly').addEventListener('change', render);
document.querySelectorAll('#jobsTable th').forEach(th => {{
  th.addEventListener('click', () => {{
    const key = th.dataset.key;
    if (sortKey === key) {{ sortAsc = !sortAsc; }} else {{ sortKey = key; sortAsc = true; }}
    render();
  }});
}});

render();
</script>
</body>
</html>
"""

# Per-status pill colors: a light background with a matching darker text
# color, grouped into four visual categories -
#   blue/indigo/violet = active pipeline stages, amber = waiting on someone
#   else, green = positive outcomes, red = negative, gray/slate = neutral/closed.
_STATUS_STYLES = {
    "To Apply":            {"text": "#475569", "bg": "#F8FAFC"},  # slate
    "Applied":             {"text": "#1D4ED8", "bg": "#EFF6FF"},  # blue
    "Initial Interview":   {"text": "#0369A1", "bg": "#F0F9FF"},  # sky
    "Technical Interview": {"text": "#4338CA", "bg": "#EEF2FF"},  # indigo
    "Final Interview":     {"text": "#6D28D9", "bg": "#F5F3FF"},  # violet
    "Awaiting Decision":   {"text": "#B45309", "bg": "#FFFBEB"},  # amber
    "Offer Received":      {"text": "#047857", "bg": "#ECFDF5"},  # emerald
    "Offer Accepted":      {"text": "#15803D", "bg": "#F0FDF4"},  # green
    "Rejected":            {"text": "#B91C1C", "bg": "#FEF2F2"},  # red
    "Withdrawn":           {"text": "#374151", "bg": "#F9FAFB"},  # gray
    "No Response":         {"text": "#64748B", "bg": "#F1F5F9"},  # slate (lighter)
}


def generate(jobs, output_path, generated_at):
    status_options = "\n      ".join(
        f'<option value="{s}">{s}</option>' for s in config.STATUSES
    )
    company_options = "\n      ".join(
        f'<option value="{c}">{c}</option>' for c in config.TARGET_COMPANIES
    )
    html = _TEMPLATE.format(
        generated_at=generated_at,
        total=len(jobs),
        jobs_json=json.dumps(jobs, ensure_ascii=False),
        statuses_json=json.dumps(config.STATUSES, ensure_ascii=False),
        status_styles_json=json.dumps(_STATUS_STYLES, ensure_ascii=False),
        status_options=status_options,
        company_options=company_options,
    )
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(html)
