#!/usr/bin/env python3
"""
Send "hello" to the agent backend and print the full response.

Run from repo root:
  python test/send_hello_to_agent.py

Or from test/:
  python send_hello_to_agent.py

Requires the agent server to be running (e.g. via ./scripts/start_local.sh).
"""

import json
import os
import sys
import time
import urllib.error
import urllib.request

# Default: agent server on port 8000 (matches start_local.sh backend)
AGENT_HOST = os.environ.get("AGENT_HOST", "localhost")
AGENT_PORT = os.environ.get("AGENT_PORT", "8000")
AGENT_URL = os.environ.get("AGENT_URL", f"http://{AGENT_HOST}:{AGENT_PORT}/invocations")


def main() -> int:
    payload = {
        "input": [{"role": "user", "content": "hello"}],
    }
    body = json.dumps(payload).encode("utf-8")

    req = urllib.request.Request(
        AGENT_URL,
        data=body,
        headers={"Content-Type": "application/json"},
        method="POST",
    )

    print("Agent URL:", AGENT_URL)
    print("Request body:", json.dumps(payload, indent=2))
    print("-" * 40)

    start = time.perf_counter()
    try:
        with urllib.request.urlopen(req, timeout=60) as resp:
            elapsed = time.perf_counter() - start
            raw = resp.read().decode("utf-8")
            try:
                data = json.loads(raw)
                print("Response (parsed):")
                print(json.dumps(data, indent=2))
            except json.JSONDecodeError:
                print("Response (raw):")
                print(raw)
            print("-" * 40)
            print(f"Status: {resp.status}")
            print(f"Time:  {elapsed:.2f}s")
            return 0
    except urllib.error.HTTPError as e:
        elapsed = time.perf_counter() - start
        print(f"HTTP error: {e.code} {e.reason}")
        try:
            body = e.read().decode("utf-8")
            print("Body:", body)
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
