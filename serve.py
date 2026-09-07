"""Serves the technical support job tracker dashboard and saves status
changes it makes.

A dashboard.html opened directly as a file (file://) can't write back to
disk - browsers don't allow that. This is a small local-only web server
(stdlib only, no new dependencies) that serves the same file over HTTP
instead, so its "Status" dropdown can POST changes to /api/status, which
get written straight to tracker.json (and jobs.csv/dashboard.html get
regenerated from it immediately).

Usage:
    python serve.py

Opens your browser to the dashboard automatically. Leave this running
while you use the tracker; Ctrl+C to stop. It only listens on localhost,
so nothing outside your own machine can reach it.
"""

import json
import os
import sys
import webbrowser
from datetime import datetime, timezone
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer

# Allow running this script directly (`python serve.py` from inside this
# folder, or `python technical_support/serve.py` from job-applications) by
# putting the folder that contains the technical_support package on
# sys.path, so the package's internal relative imports keep working.
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from technical_support import config, outputs, tracker


class Handler(SimpleHTTPRequestHandler):
    def do_GET(self):
        if self.path == "/":
            self.send_response(302)
            self.send_header("Location", "/dashboard.html")
            self.end_headers()
            return
        super().do_GET()

    def do_POST(self):
        if self.path != "/api/status":
            self.send_error(404)
            return

        length = int(self.headers.get("Content-Length", 0))
        try:
            payload = json.loads(self.rfile.read(length))
            job_id = payload["id"]
            status = payload["status"]
        except (json.JSONDecodeError, KeyError, TypeError):
            self._send_json(400, {"ok": False, "error": "invalid request body"})
            return

        try:
            updated_tracker = tracker.update_status(job_id, status)
        except (ValueError, KeyError) as exc:
            self._send_json(400, {"ok": False, "error": str(exc)})
            return

        outputs.regenerate(updated_tracker, generated_at=datetime.now(timezone.utc).isoformat())
        self._send_json(200, {"ok": True})

    def _send_json(self, code, obj):
        body = json.dumps(obj).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)


def main():
    handler = partial(Handler, directory=config.DATA_DIR)
    httpd = ThreadingHTTPServer((config.SERVER_HOST, config.SERVER_PORT), handler)
    url = f"http://{config.SERVER_HOST}:{config.SERVER_PORT}/dashboard.html"

    print(f"Serving the tracker at {url}")
    print("Press Ctrl+C to stop.")
    webbrowser.open(url)

    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        httpd.server_close()


if __name__ == "__main__":
    main()
