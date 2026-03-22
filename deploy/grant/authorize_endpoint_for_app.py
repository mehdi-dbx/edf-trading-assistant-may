#!/usr/bin/env python3
"""Add serving_endpoint resource so app SP gets CAN_QUERY. Reads endpoint name from databricks.yml."""
import os
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
YML = ROOT / "databricks.yml"


def main() -> int:
    content = YML.read_text()

    m = re.search(r"serving_endpoint:.*?name: '([^']*)'", content, re.DOTALL)
    endpoint = m.group(1) if m else None
    if not endpoint:
        from dotenv import load_dotenv
        load_dotenv(ROOT / ".env.local")
        endpoint = os.environ.get("AGENT_MODEL_ENDPOINT", "").strip()
        if not endpoint and (ROOT / "app.yaml").exists():
            lines = (ROOT / "app.yaml").read_text().splitlines()
            for i, line in enumerate(lines):
                if "AGENT_MODEL_ENDPOINT" in line and "name:" in line:
                    for j in range(i + 1, min(i + 3, len(lines))):
                        if "value:" in lines[j]:
                            endpoint = lines[j].split("value:")[-1].strip().strip('"').strip("'")
                            if endpoint and not endpoint.startswith("#"):
                                break
                    break
        if not endpoint:
            print("Error: No endpoint in databricks.yml, AGENT_MODEL_ENDPOINT, or app.yaml", file=sys.stderr)
            return 1

    if "serving_endpoint:" in content and endpoint in content:
        print(f"serving_endpoint ({endpoint}) already in databricks.yml")
        return 0

    block = f"""        - name: 'serving_endpoint'
          serving_endpoint:
            name: '{endpoint}'
            permission: 'CAN_QUERY'
"""
    m2 = re.search(r"(        - name: 'genie_trading'\n          genie_space:.*?permission: 'CAN_RUN'\n)", content, re.DOTALL)
    if not m2:
        m2 = re.search(r"(        - name: 'genie_checkin'\n          genie_space:.*?permission: 'CAN_RUN'\n)", content, re.DOTALL)
    if not m2:
        m2 = re.search(r"(        - name: 'sql_warehouse'\n          sql_warehouse:.*?permission: 'CAN_USE'\n)", content)
    if not m2:
        print("Error: Could not find genie_trading, genie_checkin, or sql_warehouse block in databricks.yml", file=sys.stderr)
        return 1
    content = content.replace(m2.group(1), m2.group(1).rstrip() + "\n" + block)
    YML.write_text(content)
    print(f"Added serving_endpoint ({endpoint}) to databricks.yml")
    return 0


if __name__ == "__main__":
    sys.exit(main())
