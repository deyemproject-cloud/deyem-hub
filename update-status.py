#!/usr/bin/env python3
"""
DEYEM Status Updater
Writes agent status to agent-status.json in the GitHub repo
"""
import urllib.request, json, os, sys
from datetime import datetime

REPO = "deyemproject-cloud/deyem-hub"
TOKEN = os.environ.get("GITHUB_TOKEN", "")
BRANCH = "main"
FILE_PATH = "agent-status.json"
API_URL = f"https://api.github.com/repos/{REPO}/contents/{FILE_PATH}"

def read_file():
    req = urllib.request.Request(API_URL, method="GET")
    req.add_header("Authorization", f"Bearer {TOKEN}")
    req.add_header("Accept", "application/vnd.github+json")
    try:
        resp = urllib.request.urlopen(req)
        data = json.load(resp)
        import base64
        return json.loads(base64.b64decode(data["content"]).decode())
    except:
        return {"agents": {}, "activity": [], "timeline": []}

def write_file(content):
    import base64
    data = json.dumps({"message": "Update agent status", "content": base64.b64encode(json.dumps(content, indent=2).encode()).decode(), "branch": BRANCH})
    req = urllib.request.Request(API_URL, data=data.encode(), method="PUT")
    req.add_header("Authorization", f"Bearer {TOKEN}")
    req.add_header("Content-Type", "application/vnd.github+json")
    resp = urllib.request.urlopen(req)
    return json.load(resp)

def update_status(agent, icon, text, timeline_text=None):
    status = read_file()
    now = datetime.now().strftime("%H:%M")
    
    # Update agent
    if agent in status["agents"]:
        status["agents"][agent]["activity"].insert(0, {"icon": icon, "text": text, "time": now})
        status["agents"][agent]["activity"] = status["agents"][agent]["activity"][:5]
        status["agents"][agent]["last_updated"] = now
    
    # Timeline
    if timeline_text:
        status["timeline"].insert(0, {"agent": agent, "text": timeline_text, "time": now})
        status["timeline"] = status["timeline"][:30]
    
    status["last_updated"] = datetime.now().isoformat()
    write_file(status)
    print(f"Updated {agent}: {text}")

if __name__ == "__main__":
    if len(sys.argv) < 4:
        print("Usage: update_status.py <agent> <icon> <text> [timeline_text]")
        sys.exit(1)
    update_status(sys.argv[1], sys.argv[2], sys.argv[3], sys.argv[4] if len(sys.argv) > 4 else None)
