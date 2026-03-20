#!/usr/bin/env python3
"""
DEYEM Agent Status Server
Runs a simple HTTP server that serves agent status and accepts updates.
Dashboard polls /status.json, agents POST to /update
"""
import http.server
import json
import os
from datetime import datetime
from urllib.parse import urlparse, parse_qs

STATUS_FILE = "/data/.openclaw/workspace/deyem-hub/agent-status.json"
PORT = 8080

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
                data["_server_time"] = datetime.utcnow().isoformat()
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

            # Load current status
            if os.path.exists(STATUS_FILE):
                with open(STATUS_FILE) as f:
                    status = json.load(f)
            else:
                self._send_json(404, {"error": "status file not found"})
                return

            # Apply updates
            agent = update.get("agent")
            if agent and agent in status["agents"]:
                # Update agent
                for k, v in update.items():
                    if k != "agent":
                        status["agents"][agent][k] = v

            # Add activity if provided
            if "activity" in update:
                activity_entry = {
                    "agent": update.get("agent", "unknown"),
                    "icon": update.get("icon", "ok"),
                    "text": update.get("text", ""),
                    "time": datetime.now().strftime("%H:%M")
                }
                status["activity"].insert(0, activity_entry)
                # Keep only last 20
                status["activity"] = status["activity"][:20]

            # Add timeline entry if provided
            if "timeline" in update:
                tl_entry = {
                    "agent": update.get("agent", "unknown"),
                    "text": update.get("timeline", ""),
                    "time": datetime.now().strftime("%H:%M")
                }
                status["timeline"].insert(0, tl_entry)
                status["timeline"] = status["timeline"][:30]

            status["last_updated"] = datetime.now().isoformat()

            # Write back
            with open(STATUS_FILE, "w") as f:
                json.dump(status, f, indent=2)

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
