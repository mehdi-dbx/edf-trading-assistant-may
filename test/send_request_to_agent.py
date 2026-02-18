#!/usr/bin/env python3
"""
Send a request to the agent the same way the frontend does (URL, auth, body).

Uses API_PROXY or localhost:8000/invocations and Authorization: Bearer <DATABRICKS_TOKEN>
so the backend sees the same flow as when the chat UI sends a prompt.

  python test/send_request_to_agent.py "hello"
  python test/send_request_to_agent.py "What are total check-ins by airline?"
  python test/send_request_to_agent.py '{"input":[{"role":"user","content":"hello"}]}'

Run from repo root. Loads .env and .env.local for DATABRICKS_TOKEN and API_PROXY.
"""

import json
import os
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

# Load env from repo root (same as frontend/Node)
ROOT = Path(__file__).resolve().parent.parent
for name in (".env", ".env.local"):
    path = ROOT / name
    if path.exists():
        for line in path.read_text().splitlines():
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, _, v = line.partition("=")
                os.environ.setdefault(k.strip(), v.strip().strip('"').strip("'"))

AGENT_URL = os.environ.get("API_PROXY") or os.environ.get("AGENT_URL")
if not AGENT_URL:
    host = os.environ.get("AGENT_HOST", "localhost")
    port = os.environ.get("AGENT_PORT", "8000")
    AGENT_URL = f"http://{host}:{port}/invocations"


def main() -> int:
    if len(sys.argv) < 2:
        print("Usage: send_request_to_agent.py <message_or_payload>", file=sys.stderr)
        return 1

    raw = sys.argv[1].strip()
    if raw.startswith("{"):
        try:
            payload = json.loads(raw)
        except json.JSONDecodeError as e:
            print(f"Invalid JSON payload: {e}", file=sys.stderr)
            return 1
    else:
        payload = {"input": [{"role": "user", "content": raw}]}

    body = json.dumps(payload).encode("utf-8")

    headers = {"Content-Type": "application/json"}
    token = os.environ.get("DATABRICKS_TOKEN")
    if token:
        headers["Authorization"] = f"Bearer {token}"

    req = urllib.request.Request(
        AGENT_URL,
        data=body,
        headers=headers,
        method="POST",
    )

    print("Agent URL:", AGENT_URL)
    print("Request body:", json.dumps(payload, indent=2))
    print("-" * 40)

    start = time.perf_counter()
    try:
        with urllib.request.urlopen(req, timeout=60) as resp:
            elapsed = time.perf_counter() - start
            response_raw = resp.read().decode("utf-8")
            try:
                data = json.loads(response_raw)
                print("Response (parsed):")
                print(json.dumps(data, indent=2))
            except json.JSONDecodeError:
                print("Response (raw):")
                print(response_raw)
            print("-" * 40)
            print(f"Status: {resp.status}")
            print(f"Time:  {elapsed:.2f}s")
            return 0
    except urllib.error.HTTPError as e:
        elapsed = time.perf_counter() - start
        print(f"HTTP error: {e.code} {e.reason}")
        try:
            err_body = e.read().decode("utf-8")
            print("Body:", err_body)
        except Exception:
            pass
        print(f"Time:  {elapsed:.2f}s")
        return 1
    except urllib.error.URLError as e:
        elapsed = time.perf_counter() - start
        print(f"Request failed: {e.reason}")
        print("Is the agent server running? (e.g. ./scripts/start_local.sh)")
        print(f"Time:  {elapsed:.2f}s")
        return 1


if __name__ == "__main__":
    sys.exit(main())
