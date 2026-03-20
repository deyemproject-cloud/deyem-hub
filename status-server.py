#!/usr/bin/env python3
"""
DEYEM Agent Status Server
- Serves agent status at /status.json (for local access)
- Pushes status to GitHub on every update
- Dashboard polls https://raw.githubusercontent.com/deyemproject-cloud/deyem-hub/main/agent-status.json
"""
import http.server
import json
import os
import base64
import urllib.request
import urllib.error
from datetime import datetime, timezone

STATUS_FILE = "/data/.openclaw/workspace/deyem-hub/agent-status.json"
REPO_FILE_PATH = "agent-status.json"
REPO = "deyemproject-cloud/deyem-hub"
TOKEN = os.environ.get("GITHUB_TOKEN", "")
PORT = 8080

def github_api(url, data=None, method=None):
    """Make authenticated GitHub API call."""
    body = json.dumps(data).encode() if data else None
    req = urllib.request.Request(url, data=body, method=method or ("PATCH" if data else "GET"))
    req.add_header("Authorization", f"Bearer {TOKEN}")
    req.add_header("Accept", "application/vnd.github+json")
    if data:
        req.add_header("Content-Type", "application/json")
    try:
        resp = urllib.request.urlopen(req)
        return json.loads(resp.read()), resp.getcode()
    except urllib.error.HTTPError as e:
        return {"error": e.read().decode()}, e.code

def get_file_sha():
    """Get current file SHA for update."""
    url = f"https://api.github.com/repos/{REPO}/contents/{REPO_FILE_PATH}"
    data, code = github_api(url)
    if code == 200:
        return data.get("sha")
    return None

def push_to_github(status_data):
    """Push updated status to GitHub."""
    url = f"https://api.github.com/repos/{REPO}/contents/{REPO_FILE_PATH}"
    content = json.dumps(status_data, indent=2)
    payload = {
        "message": f"Update agent status {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}",
        "content": base64.b64encode(content.encode()).decode(),
        "branch": "main"
    }
    sha = get_file_sha()
    if sha:
        payload["sha"] = sha
    result, code = github_api(url, data=payload, method="PUT")
    if code in (200, 201):
        print(f"  → GitHub push OK")
    else:
        print(f"  → GitHub push failed: {result}")

class Handler(http.server.BaseHTTPRequestHandler):
    def _send_json(self, status_code, data):
        self.send_response(status_code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Cache-Control", "no-cache")
        self.end_headers()
        self.wfile.write(json.dumps(data).encode())

    def do_GET(self):
        if self.path == "/status.json" or self.path == "/":
            if os.path.exists(STATUS_FILE):
                with open(STATUS_FILE) as f:
                    data = json.load(f)
                data["_server_time"] = datetime.now(timezone.utc).isoformat()
                self._send_json(200, data)
            else:
                self._send_json(404, {"error": "status file not found"})
        else:
            self._send_json(404, {"error": "not found"})

    def do_POST(self):
        if self.path == "/update":
            length = int(self.headers.get("Content-Length", 0))
            body = self.rfile.read(length)
            try:
                update = json.loads(body)
            except:
                self._send_json(400, {"error": "invalid json"})
                return

            if os.path.exists(STATUS_FILE):
                with open(STATUS_FILE) as f:
                    status = json.load(f)
            else:
                self._send_json(404, {"error": "status file not found"})
                return

            agent = update.get("agent")
            if agent and agent in status["agents"]:
                for k, v in update.items():
                    if k != "agent":
                        status["agents"][agent][k] = v

            if "activity" in update:
                entry = {
                    "agent": update.get("agent", "unknown"),
                    "icon": update.get("icon", "ok"),
                    "text": update.get("text", ""),
                    "time": datetime.now().strftime("%H:%M")
                }
                status["activity"].insert(0, entry)
                status["activity"] = status["activity"][:20]

            if "timeline" in update:
                tl_entry = {
                    "agent": update.get("agent", "unknown"),
                    "text": update.get("timeline", ""),
                    "time": datetime.now().strftime("%H:%M")
                }
                status["timeline"].insert(0, tl_entry)
                status["timeline"] = status["timeline"][:30]

            status["last_updated"] = datetime.now(timezone.utc).isoformat()

            with open(STATUS_FILE, "w") as f:
                json.dump(status, f, indent=2)

            # Push to GitHub
            print(f"  Pushing to GitHub...")
            push_to_github(status)

            self._send_json(200, {"ok": True})
        else:
            self._send_json(404, {"error": "not found"})

    def do_OPTIONS(self):
        self.send_response(200)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()

if __name__ == "__main__":
    server = http.server.HTTPServer(("", PORT), Handler)
    print(f"DEYEM Status Server running on :{PORT}")
    server.serve_forever()
