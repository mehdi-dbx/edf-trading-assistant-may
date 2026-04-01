#!/usr/bin/env python3
"""Verify Databricks bundle app resources exist and the current identity can use them.

Reads `databricks.yml`, walks each app under `resources.apps.*.resources`, and checks:
  - sql_warehouse: warehouse exists; caller has required warehouse permission (default CAN_USE)
  - serving_endpoint: endpoint exists; caller has CAN_QUERY (or higher); if API omits id, try name, else warn-skip ACL
  - genie_space: space exists; caller has CAN_RUN (or higher) on genie object
  - experiment: MLflow experiment path exists; caller has required experiment permission
  - secret: secret scope exists; key listed; READ/MANAGE as declared (best-effort)

The MLflow experiment path is derived from `resources.experiments` name templates
(`${workspace.current_user.userName}`, `${bundle.name}`, `${bundle.target}`) and the
`--target` flag (same as bundle deploy target).

Usage:
  uv run python deploy/pre_deploy_verify_assets.py [--target template] [--yaml PATH] [--no-color]

Exit code 0 if all checks pass, 1 otherwise.

Environment: loads `.env.local` from repo root (same as other deploy scripts).
"""
from __future__ import annotations

import argparse
import os
import re
import sys
from pathlib import Path

import yaml
from databricks.sdk import WorkspaceClient
from databricks.sdk.core import DatabricksError
from databricks.sdk.service.iam import PermissionLevel
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[1]

# Databricks Apps attach limit (approximate; bundle may count differently)
APPS_RESOURCE_LIMIT_WARN = 20


def _use_color() -> bool:
    if os.environ.get("NO_COLOR", "").strip():
        return False
    return sys.stdout.isatty()


def _theme(use_color: bool):
    """ANSI styling (same spirit as scripts/init_check_dbx_env.py)."""
    if not use_color:

        class _NS:
            R = G = Y = B = M = C = W = BOLD = DIM = ""
            OK = "[OK]"
            FAIL = "[FAIL]"
            WARN = "[WARN]"
            SKIP = "[SKIP]"

        return _NS()

    class _NS:
        R = "\033[31m"
        G = "\033[32m"
        Y = "\033[33m"
        B = "\033[34m"
        M = "\033[35m"
        C = "\033[36m"
        W = "\033[0m"
        BOLD = "\033[1m"
        DIM = "\033[2m"
        OK = f"{G}✓{W}"
        FAIL = f"{R}✗{W}"
        WARN = f"{Y}⚠{W}"
        SKIP = f"{B}→{W}"

    return _NS()


# Highlight CAN_* / IS_OWNER in verify lines (ANSI only when t.G is set).
_PERM_TOKEN_RE = re.compile(r"\b(CAN_[A-Z_]+|IS_OWNER)\b")


def _colorize_permission_tokens(t, msg: str) -> str:
    """Color permission level tokens (authorizations)."""
    if not t.G:
        return msg

    def _repl(m: re.Match[str]) -> str:
        p = m.group(1)
        # Admin / full control
        if p == "IS_OWNER" or ("MANAGE" in p and p.startswith("CAN_")):
            return f"{t.M}{p}{t.W}"
        # Read / metadata
        if p.startswith("CAN_") and ("VIEW" in p or "READ" in p):
            return f"{t.Y}{p}{t.W}"
        # Use / query / run / edit
        if p.startswith("CAN_"):
            return f"{t.C}{p}{t.W}"
        return f"{t.DIM}{p}{t.W}"

    return _PERM_TOKEN_RE.sub(_repl, msg)


def _colorize_verify_line(t, msg: str) -> str:
    """Bold blue resource label before first ':'; color permission tokens in the rest."""
    if not t.G:
        return msg
    m = re.match(r"^([^:\n]+)(:)", msg)
    if m:
        rest = msg[len(m.group(0)) :]
        rest = _colorize_permission_tokens(t, rest)
        return f"{t.BOLD}{t.B}{m.group(1)}{t.W}:{rest}"
    return _colorize_permission_tokens(t, msg)


def _print_header(t, yml_path: Path, bundle_name: str, target: str) -> None:
    print()
    print(f"{t.BOLD}{t.C}═══ Pre-deploy verify — bundle assets ═══{t.W}")
    print(f"{t.DIM}  {yml_path}{t.W}")
    print(f"{t.DIM}  target={target!r}  bundle={bundle_name!r}{t.W}")
    print()


def _print_identity(t, user_name: str | None, sp_name: str | None) -> None:
    print(f"{t.BOLD}Identity{t.W}")
    print(f"  {t.DIM}user{t.W}   {user_name or '—'}")
    print(f"  {t.DIM}as SP{t.W}  {sp_name or '—'}")
    print()


def _section_app(t, app_key: str) -> None:
    print(f"{t.BOLD}{t.B}── App: {app_key} ──{t.W}")


def _line_result(t, ok: bool, msg: str, *, warn: bool = False) -> None:
    mark = t.WARN if warn else (t.OK if ok else t.FAIL)
    body = _colorize_verify_line(t, msg)
    print(f"  {mark}  {body}")


def _line_skip(t, msg: str) -> None:
    body = _colorize_verify_line(t, msg)
    print(f"  {t.SKIP}  {body}")


def _norm_level(level: object | None) -> str:
    if level is None:
        return ""
    if isinstance(level, PermissionLevel):
        return level.value
    s = str(level)
    return s.replace("PermissionLevel.", "")


# Minimum rank (higher = more capable) per domain for comparison
_RANK: dict[str, dict[str, int]] = {
    "serving": {
        "CAN_VIEW": 1,
        "CAN_QUERY": 2,
        "CAN_MANAGE": 3,
        "IS_OWNER": 3,
    },
    "warehouse": {
        "CAN_VIEW": 1,
        "CAN_USE": 2,
        "CAN_MANAGE": 3,
        "IS_OWNER": 3,
    },
    "experiment": {
        "CAN_READ": 1,
        "CAN_EDIT": 2,
        "CAN_MANAGE": 3,
        "IS_OWNER": 3,
    },
    "genie": {
        "CAN_VIEW": 1,
        "CAN_RUN": 2,
        "CAN_MANAGE": 3,
        "IS_OWNER": 3,
    },
}


def _rank(domain: str, level: str) -> int:
    return _RANK.get(domain, {}).get(level, 0)


def _satisfies(domain: str, have: str, need: str) -> bool:
    """True if permission `have` is at least `need` for the given domain."""
    rh = _rank(domain, have)
    rn = _rank(domain, need)
    if rn == 0:
        return bool(rh)
    return rh >= rn


def _collect_group_names(me) -> set[str]:
    out: set[str] = set()
    if not getattr(me, "groups", None):
        return out
    for g in me.groups:
        if g is None:
            continue
        if getattr(g, "display", None):
            out.add(g.display)
        if getattr(g, "value", None):
            out.add(g.value)
    return out


def _me_service_principal_name(me) -> str | None:
    """If the current identity is a service principal, return a name to match ACL service_principal_name."""
    schemas = getattr(me, "schemas", None) or []
    if any("ServicePrincipal" in str(s) for s in schemas):
        return me.user_name
    return None


def _acl_matches_principal(
    acl: object,
    user_name: str | None,
    group_names: set[str],
    service_principal_name: str | None,
) -> bool:
    if getattr(acl, "user_name", None) and acl.user_name == user_name:
        return True
    gn = getattr(acl, "group_name", None)
    if gn and gn in group_names:
        return True
    spn = getattr(acl, "service_principal_name", None)
    if spn and service_principal_name and spn == service_principal_name:
        return True
    return False


def _best_permission_for_principal(
    access_control_list: list | None,
    user_name: str | None,
    group_names: set[str],
    service_principal_name: str | None,
    domain: str,
) -> str:
    """Return strongest permission level string for current user/groups from ACL."""
    best = 0
    best_level = ""
    if not access_control_list:
        return best_level
    for acl in access_control_list:
        if not _acl_matches_principal(
            acl, user_name, group_names, service_principal_name
        ):
            continue
        perms = getattr(acl, "all_permissions", None) or []
        for p in perms:
            lv = _norm_level(getattr(p, "permission_level", None))
            if not lv:
                continue
            r = _rank(domain, lv)
            if r > best:
                best = r
                best_level = lv
    return best_level


def _substitute_experiment_name(template: str, *, user_name: str, bundle_name: str, target: str) -> str:
    s = template
    s = s.replace("${workspace.current_user.userName}", user_name)
    s = s.replace("${bundle.name}", bundle_name)
    s = s.replace("${bundle.target}", target)
    return s


def _parse_bundle_meta(doc: dict) -> tuple[str, dict]:
    bundle = doc.get("bundle") or {}
    name = str(bundle.get("name") or "agent_edf_trading_assistant")
    experiments = (doc.get("resources") or {}).get("experiments") or {}
    return name, experiments


def _load_yaml(path: Path) -> dict:
    text = path.read_text()
    return yaml.safe_load(text) or {}


def verify_warehouse(
    w: WorkspaceClient,
    *,
    wh_id: str,
    need: str,
    user_name: str | None,
    group_names: set[str],
    service_principal_name: str | None,
    label: str,
) -> tuple[bool, str]:
    try:
        _wh = w.warehouses.get(wh_id)
        if not _wh:
            return False, f"{label}: SQL warehouse id {wh_id!r} not found"
    except DatabricksError as e:
        return False, f"{label}: warehouse {wh_id!r}: {e}"
    try:
        perm = w.permissions.get(request_object_type="warehouses", request_object_id=wh_id)
    except DatabricksError as e:
        return False, f"{label}: permissions API for warehouse {wh_id!r}: {e}"
    best = _best_permission_for_principal(
        perm.access_control_list,
        user_name,
        group_names,
        service_principal_name,
        "warehouse",
    )
    if not best:
        return (
            False,
            f"{label}: no direct ACL entry for your user/groups on warehouse {wh_id!r} "
            f"(need {need}; inherited permissions are not resolved here)",
        )
    if not _satisfies("warehouse", best, need):
        return False, f"{label}: have {best} on warehouse {wh_id!r}, need at least {need}"
    return True, f"{label}: OK (warehouse {wh_id}, {best})"


def _resolve_serving_endpoint_id(w: WorkspaceClient, ep_name: str) -> tuple[bool, str | None]:
    """Return (ok, id_or_error). ok=False => error string; ok=True => id (may be None if API omits it)."""
    try:
        ep = w.serving_endpoints.get(ep_name)
    except DatabricksError as e:
        return False, str(e)
    eid = getattr(ep, "id", None)
    if eid:
        return True, eid
    for listed in w.serving_endpoints.list():
        if getattr(listed, "name", None) == ep_name:
            lid = getattr(listed, "id", None)
            if lid:
                return True, lid
    # Endpoint exists (get succeeded) but workspace omitted id (common for some Foundation Model endpoints).
    return True, None


def _get_serving_endpoint_permissions(
    w: WorkspaceClient, ep_name: str, ep_id: str | None
):
    """Permissions API normally wants id; some workspaces accept endpoint name when id is absent."""
    if ep_id:
        try:
            return w.permissions.get(
                request_object_type="serving-endpoints",
                request_object_id=ep_id,
            )
        except DatabricksError:
            pass
    try:
        return w.permissions.get(
            request_object_type="serving-endpoints",
            request_object_id=ep_name,
        )
    except DatabricksError:
        return None


def verify_serving_endpoint(
    w: WorkspaceClient,
    *,
    ep_name: str,
    need: str,
    user_name: str | None,
    group_names: set[str],
    service_principal_name: str | None,
    label: str,
) -> tuple[bool, str]:
    ok, ep_id = _resolve_serving_endpoint_id(w, ep_name)
    if not ok:
        return False, f"{label}: serving endpoint {ep_name!r}: {ep_id}"
    perm = _get_serving_endpoint_permissions(w, ep_name, ep_id)
    if perm is None:
        return (
            True,
            f"{label}: OK (endpoint {ep_name!r} exists; ACL not checked — no id and name not accepted by "
            f"Permissions API; bundle attach may still work)",
        )
    best = _best_permission_for_principal(
        perm.access_control_list,
        user_name,
        group_names,
        service_principal_name,
        "serving",
    )
    if not best:
        return (
            False,
            f"{label}: no direct ACL entry for your user/groups on {ep_name!r} "
            f"(need {need})",
        )
    if not _satisfies("serving", best, need):
        return False, f"{label}: have {best} on {ep_name!r}, need at least {need}"
    return True, f"{label}: OK (endpoint {ep_name}, {best})"


def verify_genie_space(
    w: WorkspaceClient,
    *,
    space_id: str,
    need: str,
    user_name: str | None,
    group_names: set[str],
    service_principal_name: str | None,
    label: str,
) -> tuple[bool, str]:
    try:
        w.genie.get_space(space_id, include_serialized_space=False)
    except DatabricksError as e:
        return False, f"{label}: genie space {space_id!r}: {e}"
    try:
        perm = w.permissions.get(request_object_type="genie", request_object_id=space_id)
    except DatabricksError as e:
        return False, f"{label}: permissions API for genie {space_id!r}: {e}"
    best = _best_permission_for_principal(
        perm.access_control_list,
        user_name,
        group_names,
        service_principal_name,
        "genie",
    )
    if not best:
        return (
            False,
            f"{label}: no direct ACL entry for your user/groups on genie space {space_id!r} "
            f"(need {need})",
        )
    if not _satisfies("genie", best, need):
        return False, f"{label}: have {best} on genie {space_id!r}, need at least {need}"
    return True, f"{label}: OK (genie {space_id}, {best})"


def verify_experiment(
    w: WorkspaceClient,
    *,
    experiment_name: str,
    need: str,
    user_name: str | None,
    group_names: set[str],
    service_principal_name: str | None,
    label: str,
    allow_missing: bool,
) -> tuple[bool, str]:
    exp_id: str | None = None
    try:
        for ex in w.experiments.search_experiments(
            filter=f"name = '{experiment_name.replace(chr(39), chr(39)+chr(39))}'",
            max_results=10,
        ):
            if ex.name == experiment_name:
                exp_id = ex.experiment_id
                break
    except DatabricksError as e:
        return False, f"{label}: search experiments: {e}"

    if not exp_id:
        if allow_missing:
            return True, (
                f"{label}: experiment {experiment_name!r} not found "
                f"(allowed by --allow-missing-experiment)"
            )
        return (
            False,
            f"{label}: experiment {experiment_name!r} not found "
            f"(create it or pass --allow-missing-experiment for first deploy)",
        )

    try:
        perm = w.permissions.get(
            request_object_type="experiments",
            request_object_id=exp_id,
        )
    except DatabricksError as e:
        return False, f"{label}: permissions API for experiment {experiment_name!r}: {e}"
    best = _best_permission_for_principal(
        perm.access_control_list,
        user_name,
        group_names,
        service_principal_name,
        "experiment",
    )
    if not best:
        return (
            False,
            f"{label}: no direct ACL entry for your user/groups on experiment {experiment_name!r}",
        )
    if not _satisfies("experiment", best, need):
        return False, f"{label}: have {best} on experiment, need at least {need}"
    return True, f"{label}: OK (experiment {experiment_name}, {best})"


def verify_secret(
    w: WorkspaceClient,
    *,
    scope: str,
    key: str,
    permission: str,
    label: str,
) -> tuple[bool, str]:
    scope_names = {s.name for s in w.secrets.list_scopes()}
    if scope not in scope_names:
        return False, f"{label}: secret scope {scope!r} not found"
    keys = {m.key for m in w.secrets.list_secrets(scope)}
    if key not in keys:
        return False, f"{label}: key {key!r} not in scope {scope!r}"
    need = "MANAGE" if permission.upper() == "MANAGE" else "READ"
    try:
        me = w.current_user.me()
        principal = me.user_name or ""
        if not principal:
            return True, f"{label}: scope/key present (could not resolve principal for ACL check)"
        acl = w.secrets.get_acl(scope, principal)
        got = (acl.permission or "").upper()
        if need == "READ" and got in ("READ", "WRITE", "MANAGE"):
            return True, f"{label}: OK (scope {scope}, key {key}, {got})"
        if need == "MANAGE" and got == "MANAGE":
            return True, f"{label}: OK (scope {scope}, key {key}, MANAGE)"
        return False, f"{label}: secret ACL for {principal!r} is {got!r}, need {need}"
    except DatabricksError as e:
        return True, f"{label}: scope/key OK (could not verify ACL: {e})"


def main() -> int:
    load_dotenv(ROOT / ".env.local")

    default_target = os.environ.get("DEPLOY_TARGET", "template").strip() or "template"
    parser = argparse.ArgumentParser(
        description="Verify databricks.yml app resources exist and are permissioned for the current user.",
    )
    parser.add_argument(
        "--yaml",
        type=Path,
        default=ROOT / "databricks.yml",
        help="Path to databricks.yml",
    )
    parser.add_argument(
        "-t",
        "--target",
        default=default_target,
        help="Bundle target name (default: DEPLOY_TARGET or template)",
    )
    parser.add_argument(
        "--allow-missing-experiment",
        action="store_true",
        help="Do not fail if the MLflow experiment path does not exist yet",
    )
    parser.add_argument(
        "--skip-secret-acl",
        action="store_true",
        help="Only check secret scope exists and key is listed; skip get_acl check",
    )
    parser.add_argument(
        "--no-color",
        action="store_true",
        help="Plain text (no ANSI colors); also respects NO_COLOR env",
    )
    args = parser.parse_args()

    t = _theme(_use_color() and not args.no_color)

    yml_path: Path = args.yaml
    if not yml_path.is_file():
        print(f"{t.FAIL}  {yml_path} not found", file=sys.stderr)
        return 1

    doc = _load_yaml(yml_path)
    bundle_name, experiments_cfg = _parse_bundle_meta(doc)

    _print_header(t, yml_path, bundle_name, args.target)

    w = WorkspaceClient()
    try:
        me = w.current_user.me()
    except DatabricksError as e:
        print(f"{t.FAIL}  cannot resolve current user: {e}", file=sys.stderr)
        return 1

    user_name = me.user_name
    group_names = _collect_group_names(me)
    service_principal_name = _me_service_principal_name(me)
    _print_identity(t, user_name, service_principal_name)

    apps = (doc.get("resources") or {}).get("apps") or {}
    if not apps:
        print(f"{t.FAIL}  no resources.apps in databricks.yml", file=sys.stderr)
        return 1

    failures: list[str] = []
    resource_count = 0
    n_ok = 0
    n_fail = 0
    n_skip = 0

    for app_key, app_body in apps.items():
        if not isinstance(app_body, dict):
            continue
        res_list = app_body.get("resources")
        if not isinstance(res_list, list):
            continue
        _section_app(t, app_key)
        print()
        for block in res_list:
            if not isinstance(block, dict):
                continue
            resource_count += 1
            label = str(block.get("name") or "?")

            if "sql_warehouse" in block:
                wh = block["sql_warehouse"] or {}
                need = str(wh.get("permission") or "CAN_USE")
                wh_id = str(wh.get("id") or "").strip()
                ok, msg = verify_warehouse(
                    w,
                    wh_id=wh_id,
                    need=need,
                    user_name=user_name,
                    group_names=group_names,
                    service_principal_name=service_principal_name,
                    label=label,
                )
                _line_result(t, ok, msg)
                if ok:
                    n_ok += 1
                else:
                    n_fail += 1
                    failures.append(msg)

            elif "serving_endpoint" in block:
                se = block["serving_endpoint"] or {}
                need = str(se.get("permission") or "CAN_QUERY")
                name = str(se.get("name") or "").strip()
                ok, msg = verify_serving_endpoint(
                    w,
                    ep_name=name,
                    need=need,
                    user_name=user_name,
                    group_names=group_names,
                    service_principal_name=service_principal_name,
                    label=label,
                )
                warn_line = ok and "ACL not checked" in msg
                _line_result(t, ok, msg, warn=warn_line)
                if ok:
                    n_ok += 1
                else:
                    n_fail += 1
                    failures.append(msg)

            elif "genie_space" in block:
                gs = block["genie_space"] or {}
                need = str(gs.get("permission") or "CAN_RUN")
                space_id = str(gs.get("space_id") or "").strip()
                ok, msg = verify_genie_space(
                    w,
                    space_id=space_id,
                    need=need,
                    user_name=user_name,
                    group_names=group_names,
                    service_principal_name=service_principal_name,
                    label=label,
                )
                _line_result(t, ok, msg)
                if ok:
                    n_ok += 1
                else:
                    n_fail += 1
                    failures.append(msg)

            elif "experiment" in block:
                exp_block = block["experiment"] or {}
                need = str(exp_block.get("permission") or "CAN_MANAGE")
                exp_name_resolved: str | None = None
                for _ek, ev in experiments_cfg.items():
                    if not isinstance(ev, dict):
                        continue
                    tmpl = ev.get("name")
                    if not isinstance(tmpl, str):
                        continue
                    if "${" in tmpl:
                        exp_name_resolved = _substitute_experiment_name(
                            tmpl,
                            user_name=user_name or "",
                            bundle_name=bundle_name,
                            target=args.target,
                        )
                        break
                    exp_name_resolved = tmpl
                    break
                if not exp_name_resolved:
                    exp_name_resolved = _substitute_experiment_name(
                        f"/Users/${{workspace.current_user.userName}}/{bundle_name}-${{bundle.target}}",
                        user_name=user_name or "",
                        bundle_name=bundle_name,
                        target=args.target,
                    )
                ok, msg = verify_experiment(
                    w,
                    experiment_name=exp_name_resolved,
                    need=need,
                    user_name=user_name,
                    group_names=group_names,
                    service_principal_name=service_principal_name,
                    label=label,
                    allow_missing=args.allow_missing_experiment,
                )
                warn_line = ok and (
                    "allow-missing" in msg.lower() or "allowed by" in msg.lower()
                )
                _line_result(t, ok, msg, warn=warn_line)
                if ok:
                    n_ok += 1
                else:
                    n_fail += 1
                    failures.append(msg)

            elif "secret" in block:
                sec = block["secret"] or {}
                scope = str(sec.get("scope") or "").strip()
                key = str(sec.get("key") or "").strip()
                perm = str(sec.get("permission") or "READ")
                if args.skip_secret_acl:
                    scope_names = {s.name for s in w.secrets.list_scopes()}
                    if scope not in scope_names:
                        msg = f"{label}: secret scope {scope!r} not found"
                        _line_result(t, False, msg)
                        n_fail += 1
                        failures.append(msg)
                    else:
                        try:
                            keys = {m.key for m in w.secrets.list_secrets(scope)}
                        except DatabricksError as e:
                            msg = f"{label}: list_secrets({scope!r}): {e}"
                            _line_result(t, False, msg)
                            n_fail += 1
                            failures.append(msg)
                        else:
                            if key not in keys:
                                msg = f"{label}: key {key!r} not in scope {scope!r}"
                                _line_result(t, False, msg)
                                n_fail += 1
                                failures.append(msg)
                            else:
                                _line_result(
                                    t,
                                    True,
                                    f"{label}: scope/key present (--skip-secret-acl)",
                                )
                                n_ok += 1
                else:
                    ok, msg = verify_secret(
                        w, scope=scope, key=key, permission=perm, label=label
                    )
                    warn_line = ok and (
                        "could not verify acl" in msg.lower()
                        or "could not resolve principal" in msg.lower()
                    )
                    _line_result(t, ok, msg, warn=warn_line)
                    if ok:
                        n_ok += 1
                    else:
                        n_fail += 1
                        failures.append(msg)
            else:
                _line_skip(
                    t,
                    f"{label}: unknown resource block keys {list(block.keys())}",
                )
                n_skip += 1

        print()

    if resource_count > APPS_RESOURCE_LIMIT_WARN:
        print(
            f"{t.WARN}  {resource_count} resource entries in app resources "
            f"(Apps often limit attachments to ~{APPS_RESOURCE_LIMIT_WARN}; "
            "trim KA endpoints if deploy fails).",
            file=sys.stderr,
        )
        print(file=sys.stderr)

    print(f"{t.BOLD}{t.C}── Summary ──{t.W}")
    print(f"  {t.DIM}resources in app:{t.W}  {resource_count}")
    print(f"  {t.OK}  passed: {t.G}{n_ok}{t.W}")
    if n_fail:
        print(f"  {t.FAIL}  failed: {t.R}{n_fail}{t.W}")
    if n_skip:
        print(f"  {t.SKIP}  skipped: {t.DIM}{n_skip}{t.W}")
    print()

    if failures:
        print(f"{t.FAIL}  {len(failures)} check(s) failed.", file=sys.stderr)
        return 1
    print(f"{t.BOLD}{t.G}All checks passed.{t.W}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
