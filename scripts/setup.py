#!/usr/bin/env python3
"""Interactive init/check of Databricks resources in .env.local.

For each resource: if not configured, prompt to enter. If configured, verify and offer
to keep, add new, or activate an inactive entry.

Usage:
  uv run setup                # interactive init (all steps)
  uv run setup --check        # quick check only (non-interactive)
  uv run setup --step ka      # run a single step
  uv run setup --steps        # list available steps
"""
import os
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
os.chdir(ROOT)

ENV_FILE = ROOT / ".env.local"

# ANSI
R, G, Y, B, M, C, W = "\033[31m", "\033[32m", "\033[33m", "\033[34m", "\033[35m", "\033[36m", "\033[0m"
BOLD = "\033[1m"
DIM = "\033[2m"
ORANGE = "\033[38;5;214m"
CONF = f"{BOLD}{ORANGE}"
OK, FAIL, WARN = f"{G}✓{W}", f"{R}✗{W}", f"{Y}⚠{W}"

FIX_FIRST_MSG = f"\n  {WARN} This needs to be fixed first before moving forward.{W}\n"

TABLES_TO_VERIFY = ["example_data"]
KA_LIST_PATH = ROOT / "data" / "ka.list"
DATABRICKS_YML = ROOT / "databricks.yml"


def abort_step() -> None:
    print(FIX_FIRST_MSG)
    sys.exit(1)


def section(title: str) -> None:
    print(f"\n{BOLD}{B}═══ {title} ═══{W}")


def _load_env():
    from dotenv import load_dotenv
    load_dotenv(ENV_FILE, override=True)


# ── Env file helpers ─────────────────────────────────────────────────────────


def parse_env_file(path: Path) -> tuple[dict[str, str], dict[str, list[tuple[int, str]]], list[str]]:
    """Return (active, inactive, raw_lines)."""
    if not path.exists():
        return {}, {}, []
    lines = path.read_text().splitlines()
    active: dict[str, str] = {}
    inactive: dict[str, list[tuple[int, str]]] = {}
    for i, line in enumerate(lines):
        stripped = line.strip()
        if not stripped or stripped.startswith("#") and "=" not in stripped.lstrip("#"):
            continue
        m = re.match(r"^#?\s*([A-Za-z_][A-Za-z0-9_]*)\s*=\s*(.*)$", stripped)
        if not m:
            continue
        key, val = m.group(1), m.group(2).strip().strip("'\"").strip()
        if stripped.startswith("#"):
            inactive.setdefault(key, []).append((i, val))
        else:
            active[key] = val
    return active, inactive, lines


def write_env_entry(path: Path, key: str, value: str) -> None:
    """Set key=value in env file. Replaces existing active line or appends."""
    lines = path.read_text().splitlines() if path.exists() else []
    new_lines: list[str] = []
    replaced = False
    for line in lines:
        m = re.match(r"^(\s*)(#?\s*)([A-Za-z_][A-Za-z0-9_]*)\s*=", line)
        if m and m.group(3) == key and not line.strip().startswith("#"):
            new_lines.append(f"{key}={value}")
            replaced = True
            continue
        new_lines.append(line)
    if not replaced:
        new_lines.append(f"{key}={value}")
    path.write_text("\n".join(new_lines) + "\n")


def comment_active_for_key(path: Path, key: str) -> None:
    lines = path.read_text().splitlines()
    for i, line in enumerate(lines):
        m = re.match(r"^(\s*)(#?\s*)([A-Za-z_][A-Za-z0-9_]*)\s*=", line)
        if m and m.group(3) == key and not line.strip().startswith("#"):
            lines[i] = "#" + line.lstrip()
            path.write_text("\n".join(lines) + "\n")
            return


def uncomment_line(path: Path, line_idx: int) -> None:
    lines = path.read_text().splitlines()
    if 0 <= line_idx < len(lines) and lines[line_idx].strip().startswith("#"):
        lines[line_idx] = lines[line_idx].lstrip("#").lstrip()
        path.write_text("\n".join(lines) + "\n")


def load_env_for_key(key: str, value: str) -> None:
    os.environ[key] = value


# ── UI helpers ───────────────────────────────────────────────────────────────


def prompt_choice(prompt: str, choices: list[str]) -> str:
    while True:
        print(f"\n  {C}{prompt}{W}")
        for i, c in enumerate(choices, 1):
            display = c.replace("Available : ", f"{G}Available :{W} ", 1) if c.startswith("Available : ") else c
            print(f"    {B}[{i}]{W} {display}")
        try:
            raw = input(f"  Choice (1-{len(choices)}): ").strip()
            idx = int(raw)
            if 1 <= idx <= len(choices):
                return choices[idx - 1]
        except (ValueError, EOFError):
            pass
        print(f"  {WARN} Invalid choice{W}")


def _print_inactive(inact: list[tuple[int, str]]) -> None:
    if not inact:
        return
    print(f"  {DIM}Inactive:{W}")
    for i, (_, val) in enumerate(inact, 1):
        print(f"    {DIM}[{i}] {val[:50]}{'...' if len(val) > 50 else ''}{W}")


# ── Verify functions ─────────────────────────────────────────────────────────


def verify_host_only() -> tuple[bool, str]:
    host = os.environ.get("DATABRICKS_HOST", "").strip()
    if not host:
        return False, "not set"
    if not host.startswith("https://") and not host.startswith("http://"):
        return False, "should be https://..."
    return True, host


def verify_host_token() -> tuple[bool, str]:
    host = os.environ.get("DATABRICKS_HOST", "").strip()
    token = os.environ.get("DATABRICKS_TOKEN", "").strip()
    profile = os.environ.get("DATABRICKS_CONFIG_PROFILE", "").strip()
    if not host:
        return False, "DATABRICKS_HOST not set"
    if not token and not profile:
        return False, "Need DATABRICKS_TOKEN or DATABRICKS_CONFIG_PROFILE"
    try:
        from databricks.sdk import WorkspaceClient
        w = WorkspaceClient()
        me = w.current_user.me()
        return True, f"OK → {host} ({me.user_name})"
    except Exception as e:
        return False, str(e)


def verify_warehouse() -> tuple[bool, str]:
    wh = os.environ.get("DATABRICKS_WAREHOUSE_ID", "").strip()
    if not wh:
        return False, "not set"
    try:
        from databricks.sdk import WorkspaceClient
        w = WorkspaceClient()
        wh_obj = w.warehouses.get(wh)
        return True, getattr(wh_obj, "name", wh)
    except Exception as e:
        return False, str(e)


def verify_schema() -> tuple[bool, str]:
    spec = os.environ.get("UNITY_CATALOG_SCHEMA", "").strip()
    if "." not in spec:
        return False, "need catalog.schema"
    try:
        from databricks.sdk import WorkspaceClient
        w = WorkspaceClient()
        w.schemas.get(full_name=spec)
        return True, spec
    except Exception as e:
        return False, str(e)


def verify_tables() -> tuple[bool, str]:
    spec = os.environ.get("UNITY_CATALOG_SCHEMA", "").strip()
    if "." not in spec:
        return False, "UNITY_CATALOG_SCHEMA not set"
    missing = []
    try:
        from databricks.sdk import WorkspaceClient
        w = WorkspaceClient()
        for name in TABLES_TO_VERIFY:
            try:
                w.tables.get(full_name=f"{spec}.{name}")
            except Exception:
                missing.append(name)
        if missing:
            return False, f"missing: {', '.join(missing)}"
        return True, spec
    except Exception as e:
        return False, str(e)


def verify_genie() -> tuple[bool, str]:
    sid = os.environ.get("EDF_TRADING_GENIE_ROOM", "").strip()
    if not sid:
        return False, "not set"
    try:
        from databricks.sdk import WorkspaceClient
        w = WorkspaceClient()
        sp = w.genie.get_space(space_id=sid)
        return True, getattr(sp, "title", sid)
    except Exception as e:
        return False, str(e)


def verify_model_endpoint() -> tuple[bool, str]:
    endpoint = os.environ.get("AGENT_MODEL_ENDPOINT", "").strip()
    if not endpoint:
        return False, "not set"
    try:
        from databricks.sdk import WorkspaceClient
        w = WorkspaceClient()
        ep = w.serving_endpoints.get(name=endpoint)
        state = getattr(ep, "state", None)
        ready = str(getattr(state, "ready", "") or "") if state else ""
        return True, f"{endpoint} ({ready or 'OK'})"
    except Exception as e:
        return False, str(e)


def verify_mlflow() -> tuple[bool, str]:
    eid = os.environ.get("MLFLOW_EXPERIMENT_ID", "").strip()
    if not eid:
        return False, "not set"
    try:
        from databricks.sdk import WorkspaceClient
        w = WorkspaceClient()
        exp = w.experiments.get_experiment(experiment_id=eid)
        return True, getattr(exp, "name", eid)
    except Exception as e:
        return False, str(e)


def verify_ka() -> tuple[bool, str]:
    """Check that ka.list has entries and at least some match prompt refs."""
    from tools.ka_loader import load_ka_mapping
    mapping = load_ka_mapping()
    if not mapping:
        return False, "data/ka.list is empty or missing"
    return True, f"{len(mapping)} KA(s) loaded"


# ── List functions ───────────────────────────────────────────────────────────


def list_warehouses() -> list[tuple[str, str]]:
    try:
        from databricks.sdk import WorkspaceClient
        w = WorkspaceClient()
        whs = list(w.warehouses.list())
        return [(getattr(wh, "name", "") or str(wh.id), str(wh.id)) for wh in whs]
    except Exception:
        return []


def list_genie_spaces() -> list[tuple[str, str]]:
    try:
        from databricks.sdk import WorkspaceClient
        w = WorkspaceClient()
        r = w.genie.list_spaces()
        spaces = getattr(r, "spaces", []) or []
        return [
            (getattr(s, "title", "") or "?", getattr(s, "space_id", None) or getattr(s, "id", "") or "")
            for s in spaces
        ]
    except Exception:
        return []


def list_serving_endpoints() -> list[tuple[str, str]]:
    try:
        from databricks.sdk import WorkspaceClient
        w = WorkspaceClient()
        endpoints = list(w.serving_endpoints.list())
        result = []
        for ep in endpoints:
            name = getattr(ep, "name", "") or ""
            state = getattr(ep, "state", None)
            ready = str(getattr(state, "ready", "") or "") if state else ""
            result.append((name, ready))
        return result
    except Exception:
        return []


# ── Interactive resource steps ───────────────────────────────────────────────


def run_resource(
    key: str,
    label: str,
    verify_fn,
    prompt_hint: str = "",
) -> bool:
    """Generic interactive config for one env var resource."""
    _load_env()
    active, inactive, _ = parse_env_file(ENV_FILE)
    cur = active.get(key, "").strip()
    inact = inactive.get(key, [])

    section(label)
    ok, msg = False, ""
    if cur:
        load_env_for_key(key, cur)
        ok, msg = verify_fn()
        if ok:
            print(f"  {OK} Active: {C}{cur[:50]}{W} {G}({msg}){W}")
        else:
            print(f"  {FAIL} Active: {C}{cur[:50]}{W} {R}({msg}){W}")
    else:
        print(f"  {WARN} Not configured{W}")

    _print_inactive(inact)

    choices: list[str] = []
    if cur and ok:
        choices.append("keep")
    elif cur:
        choices.append("add new")
    else:
        choices.append("enter new")
    for i in range(1, len(inact) + 1):
        choices.append(f"activate [{i}]")

    choice = prompt_choice("Action?", choices)

    if choice == "keep":
        return True
    if choice.startswith("activate ["):
        num = int(choice.split("[")[1].rstrip("]"))
        if 1 <= num <= len(inact):
            line_idx = inact[num - 1][0]
            comment_active_for_key(ENV_FILE, key)
            uncomment_line(ENV_FILE, line_idx)
            _load_env()
            load_env_for_key(key, inact[num - 1][1])
            ok, msg = verify_fn()
            if ok:
                print(f"  {OK} Activated and verified: {msg}{W}")
            else:
                print(f"  {FAIL} Activated but verify failed: {msg}{W}")
                abort_step()
        return True

    hint = f" ({prompt_hint})" if prompt_hint else ""
    val = input(f"  Enter {key}{hint}: ").strip()
    if not val:
        return True
    if cur:
        comment_active_for_key(ENV_FILE, key)
    write_env_entry(ENV_FILE, key, val)
    _load_env()
    load_env_for_key(key, val)
    ok, msg = verify_fn()
    if ok:
        print(f"  {OK} Set and verified: {msg}{W}")
        print(f"\n  {CONF}✓  {label} configured.{W}")
    else:
        print(f"  {FAIL} Set but verify failed: {msg}{W}")
        abort_step()
    return True


def run_resource_warehouse() -> bool:
    """Interactive config for DATABRICKS_WAREHOUSE_ID with workspace list."""
    _load_env()
    key = "DATABRICKS_WAREHOUSE_ID"
    active, inactive, _ = parse_env_file(ENV_FILE)
    cur = active.get(key, "").strip()
    inact = inactive.get(key, [])

    section("DATABRICKS_WAREHOUSE_ID")

    whs = list_warehouses()
    if whs:
        for name, wh_id in whs:
            print(f"  {C}Available :{W} {name} {DIM}({wh_id}){W}")

    ok, msg = False, ""
    if cur:
        load_env_for_key(key, cur)
        ok, msg = verify_warehouse()
        if ok:
            print(f"  {OK} Active: {C}{cur}{W} {G}({msg}){W}")
        else:
            print(f"  {FAIL} Active: {C}{cur}{W} {R}({msg}){W}")
    else:
        print(f"  {WARN} Not configured{W}")

    _print_inactive(inact)

    choices: list[str] = []
    if cur and ok:
        choices.append("keep")
    if whs:
        for name, wh_id in whs:
            choices.append(f"Available : {name} ({wh_id})")
    choices.append("enter ID manually")
    for i in range(1, len(inact) + 1):
        choices.append(f"activate [{i}]")

    choice = prompt_choice("Action?", choices)

    if choice == "keep":
        return True
    if choice.startswith("activate ["):
        num = int(choice.split("[")[1].rstrip("]"))
        if 1 <= num <= len(inact):
            comment_active_for_key(ENV_FILE, key)
            uncomment_line(ENV_FILE, inact[num - 1][0])
            _load_env()
            load_env_for_key(key, inact[num - 1][1])
            ok, msg = verify_warehouse()
            if ok:
                print(f"  {OK} Activated and verified: {msg}{W}")
            else:
                print(f"  {FAIL} Verify failed: {msg}{W}")
                abort_step()
        return True

    wh_choices = [f"Available : {n} ({i})" for n, i in whs]
    if choice in wh_choices:
        val = whs[wh_choices.index(choice)][1]
    else:
        val = input(f"  Enter {key}: ").strip()
    if not val:
        return True
    if cur:
        comment_active_for_key(ENV_FILE, key)
    write_env_entry(ENV_FILE, key, val)
    _load_env()
    load_env_for_key(key, val)
    ok, msg = verify_warehouse()
    if ok:
        print(f"  {OK} Set and verified: {msg}{W}")
        print(f"\n  {CONF}✓  Warehouse configured.{W}")
    else:
        print(f"  {FAIL} Verify failed: {msg}{W}")
        abort_step()
    return True


def run_resource_model_endpoint() -> bool:
    """Interactive config for AGENT_MODEL_ENDPOINT with serving endpoint list."""
    _load_env()
    key = "AGENT_MODEL_ENDPOINT"
    active, inactive, _ = parse_env_file(ENV_FILE)
    cur = active.get(key, "").strip()
    inact = inactive.get(key, [])

    section("AGENT_MODEL_ENDPOINT")

    endpoints = list_serving_endpoints()
    if endpoints:
        for name, state in endpoints:
            status = f"{G}[{state}]{W}" if state == "READY" else f"{DIM}[{state or '?'}]{W}"
            print(f"  {C}Available :{W} {name} {status}")

    ok, msg = False, ""
    if cur:
        load_env_for_key(key, cur)
        ok, msg = verify_model_endpoint()
        if ok:
            print(f"  {OK} Active: {C}{cur}{W} {G}({msg}){W}")
        else:
            print(f"  {FAIL} Active: {C}{cur}{W} {R}({msg}){W}")
    else:
        print(f"  {WARN} Not configured{W}")

    _print_inactive(inact)

    choices: list[str] = []
    if cur and ok:
        choices.append("keep")
    if endpoints:
        for name, _ in endpoints:
            choices.append(f"Available : {name}")
    choices.append("enter endpoint name")
    for i in range(1, len(inact) + 1):
        choices.append(f"activate [{i}]")

    choice = prompt_choice("Action?", choices)

    if choice == "keep":
        return True
    if choice.startswith("activate ["):
        num = int(choice.split("[")[1].rstrip("]"))
        if 1 <= num <= len(inact):
            comment_active_for_key(ENV_FILE, key)
            uncomment_line(ENV_FILE, inact[num - 1][0])
            _load_env()
            load_env_for_key(key, inact[num - 1][1])
            ok, msg = verify_model_endpoint()
            if ok:
                print(f"  {OK} Activated and verified: {msg}{W}")
            else:
                print(f"  {FAIL} Verify failed: {msg}{W}")
                abort_step()
        return True

    ep_choices = [f"Available : {n}" for n, _ in endpoints]
    if choice in ep_choices:
        val = endpoints[ep_choices.index(choice)][0]
    else:
        val = input(f"  Enter {key}: ").strip()
    if not val:
        return True
    if cur:
        comment_active_for_key(ENV_FILE, key)
    write_env_entry(ENV_FILE, key, val)
    _load_env()
    load_env_for_key(key, val)
    ok, msg = verify_model_endpoint()
    if ok:
        print(f"  {OK} Set and verified: {msg}{W}")
        print(f"\n  {CONF}✓  Model endpoint configured.{W}")
    else:
        print(f"  {FAIL} Verify failed: {msg}{W}")
        abort_step()
    return True


def run_resource_genie() -> bool:
    """Interactive config for EDF_TRADING_GENIE_ROOM with Genie space list."""
    _load_env()
    key = "EDF_TRADING_GENIE_ROOM"
    active, inactive, _ = parse_env_file(ENV_FILE)
    cur = active.get(key, "").strip()
    inact = inactive.get(key, [])

    section("EDF_TRADING_GENIE_ROOM")

    spaces = list_genie_spaces()
    if spaces:
        for title, space_id in spaces:
            print(f"  {C}Available :{W} {title} {DIM}({space_id}){W}")

    ok, msg = False, ""
    if cur:
        load_env_for_key(key, cur)
        ok, msg = verify_genie()
        if ok:
            print(f"  {OK} Active: {C}{cur}{W} {G}({msg}){W}")
        else:
            print(f"  {FAIL} Active: {C}{cur}{W} {R}({msg}){W}")
    else:
        print(f"  {WARN} Not configured{W}")

    _print_inactive(inact)

    choices: list[str] = []
    if cur and ok:
        choices.append("keep")
    if spaces:
        for title, space_id in spaces:
            choices.append(f"Available : {title} ({space_id})")
    choices.append("enter space ID")
    for i in range(1, len(inact) + 1):
        choices.append(f"activate [{i}]")

    choice = prompt_choice("Action?", choices)

    if choice == "keep":
        return True
    if choice.startswith("activate ["):
        num = int(choice.split("[")[1].rstrip("]"))
        if 1 <= num <= len(inact):
            comment_active_for_key(ENV_FILE, key)
            uncomment_line(ENV_FILE, inact[num - 1][0])
            _load_env()
            load_env_for_key(key, inact[num - 1][1])
            ok, msg = verify_genie()
            if ok:
                print(f"  {OK} Activated and verified: {msg}{W}")
            else:
                print(f"  {FAIL} Verify failed: {msg}{W}")
                abort_step()
        return True

    space_choices = [f"Available : {t} ({i})" for t, i in spaces]
    if choice in space_choices:
        val = spaces[space_choices.index(choice)][1]
    else:
        val = input(f"  Enter {key}: ").strip()
    if not val:
        return True
    if cur:
        comment_active_for_key(ENV_FILE, key)
    write_env_entry(ENV_FILE, key, val)
    _load_env()
    load_env_for_key(key, val)

    # Also update databricks.yml genie space_id
    _update_genie_in_yml(val)

    ok, msg = verify_genie()
    if ok:
        print(f"  {OK} Set and verified: {msg}{W}")
        print(f"\n  {CONF}✓  Genie space configured.{W}")
    else:
        print(f"  {FAIL} Verify failed: {msg}{W}")
        abort_step()
    return True


def _update_genie_in_yml(space_id: str) -> None:
    """Update the genie_space space_id in databricks.yml."""
    if not DATABRICKS_YML.exists():
        return
    content = DATABRICKS_YML.read_text()
    new_content = re.sub(
        r"(genie_space:\s*\n\s*name:\s*'[^']*'\s*\n\s*space_id:\s*')[^']*(')",
        rf"\g<1>{space_id}\2",
        content,
    )
    if new_content != content:
        DATABRICKS_YML.write_text(new_content)
        print(f"  {OK} Updated space_id in databricks.yml{W}")


def run_resource_ka() -> bool:
    """Interactive KA setup: fetch → ka.list → databricks.yml → prompt check."""
    _load_env()

    section("Knowledge Assistants")

    # 1. Fetch KAs from workspace
    print(f"  {C}Fetching KA endpoints from workspace...{W}")
    try:
        from scripts.list_ka_endpoints import list_knowledge_assistants, build_ka_list_text
        kas = list_knowledge_assistants()
    except Exception as e:
        print(f"  {FAIL} Could not fetch KAs: {e}{W}")
        print(f"  {DIM}Ensure DATABRICKS_HOST and DATABRICKS_TOKEN are set in .env.local{W}")
        return False

    if not kas:
        print(f"  {WARN} No Knowledge Assistants found in this workspace{W}")
        print(f"  {DIM}Create KAs first, then re-run setup.{W}")
        return True

    # Show found KAs
    with_endpoint = [ka for ka in kas if ka.get("endpoint_name")]
    without_endpoint = [ka for ka in kas if not ka.get("endpoint_name")]
    print(f"  {OK} Found {G}{len(kas)}{W} KA(s) ({len(with_endpoint)} with endpoints)")
    for ka in with_endpoint:
        print(f"    {G}+{W} {ka.get('display_name', '?')} {DIM}({ka.get('endpoint_name', '')}){W}")
    for ka in without_endpoint:
        print(f"    {Y}-{W} {ka.get('display_name', '?')} {DIM}(no endpoint yet){W}")

    if not with_endpoint:
        print(f"  {WARN} No KAs have serving endpoints yet. Wait for provisioning.{W}")
        return True

    # Check current ka.list
    from tools.ka_loader import load_ka_mapping
    current = load_ka_mapping()
    if current:
        print(f"\n  {DIM}Current ka.list has {len(current)} entry/entries{W}")

    choices = ["write ka.list + sync databricks.yml"]
    if current:
        choices.insert(0, "keep current ka.list")
    choices.append("skip")

    choice = prompt_choice("Action?", choices)

    if choice == "skip" or choice == "keep current ka.list":
        if choice == "keep current ka.list":
            _run_ka_prompt_check()
        return True

    # 2. Write ka.list
    ka_text = build_ka_list_text(kas)
    KA_LIST_PATH.write_text(ka_text)
    print(f"  {OK} Wrote {len(with_endpoint)} KA endpoint(s) to {DIM}data/ka.list{W}")

    # 3. Sync to databricks.yml
    try:
        from deploy.sync_ka_endpoints_to_yml import parse_ka_list, build_ka_section
        endpoints = parse_ka_list()
        if endpoints:
            KA_SECTION_START = "        # --- KA endpoints (from data/ka.list) ---"
            KA_SECTION_END = "        # --- end KA endpoints ---"
            new_section = build_ka_section(endpoints)
            content = DATABRICKS_YML.read_text()
            if KA_SECTION_START in content and KA_SECTION_END in content:
                content = re.sub(
                    re.escape(KA_SECTION_START) + r".*?" + re.escape(KA_SECTION_END) + r"\n?",
                    new_section.rstrip() + "\n",
                    content,
                    flags=re.DOTALL,
                )
                DATABRICKS_YML.write_text(content)
                print(f"  {OK} Synced {len(endpoints)} KA endpoint(s) to {DIM}databricks.yml{W}")
            else:
                print(f"  {WARN} KA section markers not found in databricks.yml — run deploy/sync_ka_endpoints_to_yml.py manually{W}")
        else:
            print(f"  {WARN} No endpoints parsed from ka.list{W}")
    except Exception as e:
        print(f"  {WARN} Could not sync to databricks.yml: {e}{W}")
        print(f"  {DIM}Run: uv run python deploy/sync_ka_endpoints_to_yml.py{W}")

    # 4. Prompt validation
    _run_ka_prompt_check()

    print(f"\n  {CONF}✓  Knowledge Assistants configured.{W}")
    return True


def _run_ka_prompt_check() -> None:
    """Validate prompt KA name references against ka.list."""
    from tools.ka_loader import load_ka_mapping, get_endpoint_for_assistant

    mapping = load_ka_mapping()
    if not mapping:
        return

    prompt_path = ROOT / "prompt" / "main.prompt"
    kb_path = ROOT / "prompt" / "knowledge.base"

    backtick_re = re.compile(r"`([^`]+)`")
    bad: list[tuple[str, str]] = []

    for path in [prompt_path, kb_path]:
        if not path.exists():
            continue
        text = path.read_text(encoding="utf-8")
        for tok in backtick_re.findall(text):
            t = tok.strip()
            # Skip non-KA tokens: wildcards, schema refs, short tokens, parens (code)
            if not t or "*" in t or "." in t or len(t) < 4 or t.startswith("-"):
                continue
            # KA names contain hyphens (cwg-wind-...) or underscores with digits (daily_outlook_2020_2025)
            # Skip tool/code refs like get_current_time, query_knowledge_assistant
            if "-" not in t and not re.search(r"\d", t):
                continue
            if get_endpoint_for_assistant(t, mapping) is None:
                bad.append((str(path.relative_to(ROOT)), t))

    if not bad:
        print(f"  {OK} Prompt KA references all resolve{W}")
    else:
        print(f"  {WARN} {len(bad)} prompt ref(s) don't match ka.list:{W}")
        for rel, tok in bad[:10]:
            print(f"    {Y}•{W} {rel}: `{tok}`")
        print(f"  {DIM}Update prompt/main.prompt to match your KA display names{W}")


def run_resource_schema() -> bool:
    """Interactive config for UNITY_CATALOG_SCHEMA with asset creation."""
    _load_env()
    key = "UNITY_CATALOG_SCHEMA"
    active, _, _ = parse_env_file(ENV_FILE)
    cur = active.get(key, "").strip()

    section("UNITY_CATALOG_SCHEMA")

    if cur:
        load_env_for_key(key, cur)
        ok, msg = verify_schema()
        if ok:
            print(f"  {OK} Active: {C}{cur}{W} {G}({msg}){W}")
            # Check tables too
            tok, tmsg = verify_tables()
            if tok:
                print(f"  {OK} Tables: {G}{tmsg}{W}")
                choices = ["keep"]
            else:
                print(f"  {WARN} Tables: {Y}{tmsg}{W}")
                choices = ["keep", "create missing assets"]
        else:
            print(f"  {FAIL} Active: {C}{cur}{W} {R}({msg}){W}")
            choices = ["create assets", "enter new"]
    else:
        print(f"  {WARN} Not configured{W}")
        choices = ["enter new"]

    choice = prompt_choice("Action?", choices)

    if choice == "keep":
        return True

    if choice in ("create assets", "create missing assets"):
        print(f"  {B}Creating schema and tables ...{W}\n")
        rc = subprocess.call(["uv", "run", "python", "data/init/create_all_assets.py"], cwd=ROOT)
        if rc == 0:
            print(f"\n  {OK} {G}Assets created.{W}")
            print(f"\n  {CONF}✓  Schema configured.{W}")
        else:
            print(f"\n  {FAIL} Asset creation failed (exit {rc}){W}")
            abort_step()
        return True

    # enter new
    val = input(f"  Enter {key} (catalog.schema): ").strip()
    if not val:
        return True
    if cur:
        comment_active_for_key(ENV_FILE, key)
    write_env_entry(ENV_FILE, key, val)
    _load_env()
    load_env_for_key(key, val)
    ok, msg = verify_schema()
    if ok:
        print(f"  {OK} Set and verified: {msg}{W}")
        print(f"\n  {CONF}✓  Schema configured.{W}")
    else:
        print(f"  {WARN} Schema not found — creating assets...{W}")
        rc = subprocess.call(["uv", "run", "python", "data/init/create_all_assets.py"], cwd=ROOT)
        if rc == 0:
            print(f"\n  {OK} {G}Assets created.{W}")
        else:
            print(f"\n  {FAIL} Asset creation failed{W}")
            abort_step()
    return True


def run_resource_mlflow() -> bool:
    """Interactive config for MLFLOW_EXPERIMENT_ID."""
    _load_env()
    key = "MLFLOW_EXPERIMENT_ID"
    active, inactive, _ = parse_env_file(ENV_FILE)
    cur = active.get(key, "").strip()
    inact = inactive.get(key, [])

    section("MLFLOW_EXPERIMENT_ID")

    ok, msg = False, ""
    if cur:
        load_env_for_key(key, cur)
        ok, msg = verify_mlflow()
        if ok:
            print(f"  {OK} Active: {C}{cur}{W} {G}({msg}){W}")
        else:
            print(f"  {FAIL} Active: {C}{cur}{W} {R}({msg}){W}")
    else:
        print(f"  {WARN} Not configured{W}")

    _print_inactive(inact)

    choices: list[str] = []
    if cur and ok:
        choices.append("keep")
    choices.append("enter ID manually")
    choices.append("create new experiment")
    for i in range(1, len(inact) + 1):
        choices.append(f"activate [{i}]")

    choice = prompt_choice("Action?", choices)

    if choice == "keep":
        return True
    if choice == "create new experiment":
        print(f"  {B}Creating MLflow experiment ...{W}\n")
        rc = subprocess.call(["uv", "run", "python", "data/init/create_mlflow_experiment.py"], cwd=ROOT)
        if rc == 0:
            _load_env()
            new_id = os.environ.get(key, "").strip()
            if new_id:
                print(f"\n  {OK} {G}MLflow experiment created: {new_id}{W}")
            else:
                print(f"\n  {OK} {G}MLflow experiment created. Re-run to verify.{W}")
            print(f"\n  {CONF}✓  MLflow configured.{W}")
        else:
            print(f"\n  {FAIL} MLflow creation failed (exit {rc}){W}")
            abort_step()
        return True
    if choice.startswith("activate ["):
        num = int(choice.split("[")[1].rstrip("]"))
        if 1 <= num <= len(inact):
            comment_active_for_key(ENV_FILE, key)
            uncomment_line(ENV_FILE, inact[num - 1][0])
            _load_env()
            load_env_for_key(key, inact[num - 1][1])
            ok, msg = verify_mlflow()
            if ok:
                print(f"  {OK} Activated and verified: {msg}{W}")
            else:
                print(f"  {FAIL} Verify failed: {msg}{W}")
                abort_step()
        return True

    val = input(f"  Enter {key}: ").strip()
    if not val:
        return True
    if cur:
        comment_active_for_key(ENV_FILE, key)
    write_env_entry(ENV_FILE, key, val)
    _load_env()
    load_env_for_key(key, val)
    ok, msg = verify_mlflow()
    if ok:
        print(f"  {OK} Set and verified: {msg}{W}")
        print(f"\n  {CONF}✓  MLflow configured.{W}")
    else:
        print(f"  {FAIL} Verify failed: {msg}{W}")
        abort_step()
    return True


# ── Check-only mode ──────────────────────────────────────────────────────────


def run_check_only() -> None:
    """Quick non-interactive check of all resources."""
    _load_env()

    print(f"\n{BOLD}{M}╔══════════════════════════════════════════╗{W}")
    print(f"{BOLD}{M}║  EDF Trading Assistant — Environment Check║{W}")
    print(f"{BOLD}{M}╚══════════════════════════════════════════╝{W}")

    all_ok = True

    section("Connection")
    ok, msg = verify_host_token()
    if ok:
        print(f"  {OK} Connection {C}({msg}){W}")
    else:
        print(f"  {FAIL} Connection {C}({msg}){W}")
        all_ok = False

    section("Warehouse")
    ok, msg = verify_warehouse()
    print(f"  {OK if ok else FAIL} DATABRICKS_WAREHOUSE_ID {C}({msg}){W}")
    if not ok:
        all_ok = False

    section("Unity Catalog")
    ok, msg = verify_schema()
    print(f"  {OK if ok else FAIL} UNITY_CATALOG_SCHEMA {C}({msg}){W}")
    if not ok:
        all_ok = False
    else:
        spec = os.environ.get("UNITY_CATALOG_SCHEMA", "").strip()
        from databricks.sdk import WorkspaceClient
        w = WorkspaceClient()
        for i, name in enumerate(TABLES_TO_VERIFY):
            branch = "  \\-- " if i == len(TABLES_TO_VERIFY) - 1 else "  |-- "
            full_name = f"{spec}.{name}"
            try:
                w.tables.get(full_name)
                print(f"  {branch}{OK} {name}")
            except Exception:
                print(f"  {branch}{FAIL} {name}")
                all_ok = False

    section("Model Endpoint")
    ok, msg = verify_model_endpoint()
    print(f"  {OK if ok else FAIL} AGENT_MODEL_ENDPOINT {C}({msg}){W}")
    if not ok:
        all_ok = False

    section("Knowledge Assistants")
    ok, msg = verify_ka()
    print(f"  {OK if ok else FAIL} data/ka.list {C}({msg}){W}")
    if not ok:
        all_ok = False
    else:
        _run_ka_prompt_check()

    section("Genie Space")
    ok, msg = verify_genie()
    print(f"  {OK if ok else FAIL} EDF_TRADING_GENIE_ROOM {C}({msg}){W}")
    if not ok:
        all_ok = False

    section("MLflow")
    ok, msg = verify_mlflow()
    print(f"  {OK if ok else FAIL} MLFLOW_EXPERIMENT_ID {C}({msg}){W}")
    if not ok:
        all_ok = False

    section("Summary")
    if all_ok:
        print(f"  {OK} {G}All resources OK{W}\n")
    else:
        print(f"  {FAIL} {R}Some checks failed — run: uv run setup{W}\n")
        sys.exit(1)


# ── Step registry ────────────────────────────────────────────────────────────


STEPS = [
    ("host",      "DATABRICKS_HOST",           lambda: run_resource("DATABRICKS_HOST", "DATABRICKS_HOST", verify_host_only, "https://....databricks.com")),
    ("auth",      "Auth (TOKEN or PROFILE)",   lambda: _run_step_auth()),
    ("warehouse", "DATABRICKS_WAREHOUSE_ID",   run_resource_warehouse),
    ("schema",    "UNITY_CATALOG_SCHEMA",      run_resource_schema),
    ("model",     "AGENT_MODEL_ENDPOINT",      run_resource_model_endpoint),
    ("ka",        "Knowledge Assistants",       run_resource_ka),
    ("genie",     "EDF_TRADING_GENIE_ROOM",    run_resource_genie),
    ("mlflow",    "MLFLOW_EXPERIMENT_ID",       run_resource_mlflow),
    ("check",     "Full status check",          run_check_only),
]

_STEP_MAP = {name: fn for name, _, fn in STEPS}


def _run_step_auth() -> bool:
    _load_env()
    token = os.environ.get("DATABRICKS_TOKEN", "").strip()
    profile = os.environ.get("DATABRICKS_CONFIG_PROFILE", "").strip()
    if token:
        return run_resource("DATABRICKS_TOKEN", "DATABRICKS_TOKEN", verify_host_token, "dapi...")
    elif profile:
        return run_resource("DATABRICKS_CONFIG_PROFILE", "DATABRICKS_CONFIG_PROFILE", verify_host_token, "profile name")
    else:
        choices = ["DATABRICKS_TOKEN", "DATABRICKS_CONFIG_PROFILE"]
        c = prompt_choice("Which auth method?", choices)
        if "TOKEN" in c:
            return run_resource("DATABRICKS_TOKEN", "DATABRICKS_TOKEN", verify_host_token, "dapi...")
        else:
            return run_resource("DATABRICKS_CONFIG_PROFILE", "DATABRICKS_CONFIG_PROFILE", verify_host_token, "profile name")


# ── Main ─────────────────────────────────────────────────────────────────────


def main() -> None:
    if "--check" in sys.argv:
        run_check_only()
        return

    if "--steps" in sys.argv:
        print(f"\n{BOLD}{B}EDF Trading Assistant — Setup Steps{W}\n")
        for i, (name, desc, _) in enumerate(STEPS, 1):
            print(f"  {B}[{i:2}]{W} {C}{name:<12}{W} {desc}")
        print(f"\n  Usage: {DIM}uv run setup --step <name>{W}\n")
        return

    if "--step" in sys.argv:
        idx = sys.argv.index("--step")
        step = sys.argv[idx + 1] if idx + 1 < len(sys.argv) else None
        if not step or step not in _STEP_MAP:
            valid = ", ".join(n for n, _, _ in STEPS)
            print(f"  {FAIL} Unknown step '{step}'. Valid: {valid}")
            sys.exit(1)
        _load_env()
        _STEP_MAP[step]()
        return

    _load_env()

    print(f"\n{BOLD}{M}╔══════════════════════════════════════════════════╗{W}")
    print(f"{BOLD}{M}║  EDF Trading Assistant — Workspace Setup          ║{W}")
    print(f"{BOLD}{M}╚══════════════════════════════════════════════════╝{W}")

    # 1. Connection
    run_resource("DATABRICKS_HOST", "DATABRICKS_HOST", verify_host_only, "https://....databricks.com")
    _load_env()
    if not os.environ.get("DATABRICKS_HOST"):
        print(f"  {FAIL} DATABRICKS_HOST required. Aborting.{W}")
        sys.exit(1)
    _run_step_auth()

    # 2. Infrastructure
    _load_env()
    run_resource_warehouse()
    run_resource_schema()

    # 3. Agent resources
    _load_env()
    run_resource_model_endpoint()
    run_resource_ka()
    run_resource_genie()

    # 4. Tracing
    run_resource_mlflow()

    # 5. Done
    section("Done")
    print(f"  {OK} {G}Configuration saved to {ENV_FILE}{W}\n")
    print(f"  {BOLD}{G}╔════════════════════════════════════════╗{W}")
    print(f"  {BOLD}{G}║  {OK} You're All Set!{W}                     {BOLD}{G}║{W}")
    print(f"  {BOLD}{G}╚════════════════════════════════════════╝{W}")
    print(f"\n  Next: {C}uv run start-app{W}  or  {C}databricks bundle deploy{W}\n")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print(f"\n  {WARN} Interrupted{W}")
        sys.exit(130)
    except Exception as e:
        print(f"\n  {FAIL} {e}{W}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
