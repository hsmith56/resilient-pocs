#!/usr/bin/env python3
"""
Independent deterministic ruleset validator + truth-table generator.

Usage:
  python validate_ruleset_determinism.py --no-write
  python validate_ruleset_determinism.py
  pytest validate_ruleset_determinism.py
"""

from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path
from typing import Any, Dict, Iterable, List, Tuple

import assignment_ruleset as rs

PHASES = [rs.TRIAGE_PHASE, rs.RESPONSE_RECOVERY_PHASE, "Closed"]
IMPACTS = [0, 1, 2, 3, 4, 5]
CBDS = [None, "AM", "P&C", "GWM", "GWM WMI", "GF", "IB", "GWM US", "WMA", "UNKNOWN"]
CAUSEDBYS = [None, "IT systems", "Other third party", "Employee", "Vendor"]
TYPES = [None, "cyber attack", "cyber incident", "phishing"]
ASSIGNMENT_MODES = [None, "Manual Override", "Locked"]
CURRENT_OWNERS = ["DISO-ORIGINAL", rs.OWNER_CIHT, rs.OWNER_WMA]
LAST_ROUTER_OWNERS = [None, rs.OWNER_CIHT, rs.OWNER_WMA]
MEMBER_CASES = [("USER-A",), ("USER-A", rs.MEMBER_CIHT)]
CONDITION_LOCK_RULES = [r["name"] for r in rs.ROUTING_RULES if r.get("locks", {}).get("owner", {}).get("type") == "condition_based"]
LOCK_CASES = [
    (False, None, None),
    (True, "manual", "Manual Transfer Ownership"),
    (True, "incident_lifetime", "Incident Lifetime Lock"),
    (True, "manual_transfer", "Criteria 5 - Preserve manual CIHT/WMA transfer"),
    (True, "unknown", "Unknown Lock"),
    (True, "condition_based", "Missing Rule"),
] + [(True, "condition_based", name) for name in CONDITION_LOCK_RULES]


def is_missing(value: Any) -> bool:
    return value is None or value == "" or value == []


def detect_manual_transfer_owner(current_owner: str, last_owner: str | None) -> str | None:
    if current_owner not in rs.MANUAL_TRANSFER_OWNERS:
        return None
    if current_owner == rs.OWNER_WMA:
        return current_owner
    if last_owner in rs.MANUAL_TRANSFER_OWNERS and last_owner != current_owner:
        return current_owner
    return None


def context(row: Dict[str, Any]) -> Dict[str, Any]:
    impact = row["impact_rating"]
    return {
        "phase": row["phase"],
        "impact_rating": impact,
        "is_high_impact": isinstance(impact, (int, float)) and impact >= 3,
        "cbd": row["cbd"],
        "causedby": row["causedby"],
        "type": row["type"],
        "manual_transfer_owner": detect_manual_transfer_owner(row["current_owner"], row["last_router_owner"]),
        "assignment_mode": row["assignment_mode"],
        "assignment_owner_locked": row["lock_active"],
        "assignment_owner_lock_type": row["lock_type"],
        "assignment_owner_lock_rule": row["lock_rule"],
        "current_owner": row["current_owner"],
        "current_members": list(row["current_members"]),
        "current_workspace": "WS",
    }


def op(actual: Any, operator: str, expected: Any) -> bool:
    if operator == "missing":
        return is_missing(actual)
    if operator == "not_missing":
        return not is_missing(actual)
    if actual is None:
        return False
    try:
        return {
            "==": actual == expected,
            "!=": actual != expected,
            ">": actual > expected,
            ">=": actual >= expected,
            "<": actual < expected,
            "<=": actual <= expected,
            "in": actual in expected,
            "not_in": actual not in expected,
        }[operator]
    except TypeError:
        return False


def condition_matches(actual: Any, cond: Any) -> bool:
    if isinstance(cond, dict):
        return op(actual, cond["operator"], cond["value"])
    if isinstance(cond, list):
        return actual in cond
    if cond is rs.MISSING:
        return is_missing(actual)
    return actual == cond


def rule_matches(ctx: Dict[str, Any], rule: Dict[str, Any]) -> bool:
    if rule.get("phase") and ctx["phase"] != rule["phase"]:
        return False
    return all(condition_matches(ctx.get(k), v) for k, v in rule.get("conditions", {}).items())


def find_rule(name: str | None) -> Dict[str, Any] | None:
    for rule in rs.ROUTING_RULES:
        if rule["name"] == name:
            return rule
    return None


def should_release_lock(ctx: Dict[str, Any]) -> bool:
    if not ctx["assignment_owner_locked"]:
        return False
    lock_type = ctx["assignment_owner_lock_type"]
    if lock_type in {"manual", "incident_lifetime"}:
        return False
    if ctx.get("manual_transfer_owner") and lock_type == "condition_based":
        return True
    if lock_type == "manual_transfer":
        return ctx["impact_rating"] >= 3
    if lock_type == "condition_based":
        rule = find_rule(ctx["assignment_owner_lock_rule"])
        return True if rule is None else not rule_matches(ctx, rule)
    return False


def resolve(value: Any, ctx: Dict[str, Any]) -> Any:
    if not isinstance(value, dict):
        return value
    if "context" in value:
        return ctx.get(value["context"])
    if "field" in value:
        field_value = ctx.get(value["field"])
        if is_missing(field_value):
            return value.get("missing_value")
        if field_value in value.get("map", {}):
            return value["map"][field_value]
        if value.get("default_template"):
            return value["default_template"].format(**ctx)
        return value.get("default")
    return value


def normalize_members(members: Iterable[str]) -> Tuple[str, ...]:
    return tuple(sorted({m for m in members if m and m != rs.EXISTING_MEMBERS}))


def resolve_members(current: Iterable[str], configured: Iterable[str]) -> Tuple[str, ...]:
    configured = list(configured or [])
    if rs.EXISTING_MEMBERS in configured:
        return normalize_members(list(current) + [m for m in configured if m != rs.EXISTING_MEMBERS])
    return normalize_members(configured)


def evaluate(row: Dict[str, Any]) -> Dict[str, Any]:
    ctx = context(row)
    lock_released = should_release_lock(ctx)
    if lock_released:
        ctx.update({"assignment_owner_locked": False, "assignment_owner_lock_type": None, "assignment_owner_lock_rule": None})

    if ctx["assignment_mode"] in ["Manual Override", "Locked"]:
        return {"reason": "Assignment mode prevents automatic routing.", "matched_rules": (), "owner": ctx["current_owner"], "members": normalize_members(ctx["current_members"]), "lock_released": lock_released, "lock_type": ctx["assignment_owner_lock_type"]}

    matched = sorted([r for r in rs.ROUTING_RULES if rule_matches(ctx, r)], key=lambda r: r.get("priority", 0), reverse=True)
    owner = ctx["current_owner"]
    members = tuple(ctx["current_members"])
    assigned_owner = False
    lock_type = ctx["assignment_owner_lock_type"]

    for rule in matched:
        assignment = rule.get("assignment", {})
        if "owner" in assignment and not assigned_owner:
            if not ctx["assignment_owner_locked"]:
                owner = resolve(assignment["owner"], ctx)
                assigned_owner = True
        if "members" in assignment:
            members = resolve_members(members, assignment["members"])
        owner_lock = rule.get("locks", {}).get("owner")
        if owner_lock and owner_lock.get("enabled") and not ctx["assignment_owner_locked"]:
            lock_type = owner_lock.get("type", "condition_based")

    return {"reason": "Matched routing rule." if matched else "No matching routing rule found.", "matched_rules": tuple(r["name"] for r in matched), "owner": owner, "members": normalize_members(members), "lock_released": lock_released, "lock_type": lock_type}


def scenario_rows() -> Iterable[Dict[str, Any]]:
    for phase in PHASES:
        for impact in IMPACTS:
            for cbd in CBDS:
                for causedby in CAUSEDBYS:
                    for typ in TYPES:
                        for mode in ASSIGNMENT_MODES:
                            for owner in CURRENT_OWNERS:
                                for last_owner in LAST_ROUTER_OWNERS:
                                    for members in MEMBER_CASES:
                                        for lock_active, lock_type, lock_rule in LOCK_CASES:
                                            yield {"phase": phase, "impact_rating": impact, "cbd": cbd, "causedby": causedby, "type": typ, "assignment_mode": mode, "current_owner": owner, "last_router_owner": last_owner, "current_members": members, "lock_active": lock_active, "lock_type": lock_type, "lock_rule": lock_rule}


def validate(write_csv: Path | None = None) -> int:
    handle = write_csv.open("w", newline="", encoding="utf-8") if write_csv else None
    writer = None
    count = 0
    try:
        for row in scenario_rows():
            count += 1
            first = evaluate(row)
            second = evaluate(row)
            assert first == second, (row, first, second)
            assert len(first["members"]) == len(set(first["members"])), (row, first)
            out = {**{k: ("|".join(v) if isinstance(v, tuple) else v) for k, v in row.items()}, **{f"expected_{k}": ("|".join(v) if isinstance(v, tuple) else v) for k, v in first.items()}}
            if handle:
                if writer is None:
                    writer = csv.DictWriter(handle, fieldnames=list(out.keys()))
                    writer.writeheader()
                writer.writerow(out)
    finally:
        if handle:
            handle.close()
    return count


def test_truth_table_deterministic() -> None:
    assert validate(None) > 0


def test_ruleset_lock_types() -> None:
    lock_types = sorted({r.get("locks", {}).get("owner", {}).get("type") for r in rs.ROUTING_RULES if r.get("locks", {}).get("owner", {}).get("enabled")})
    assert lock_types == ["condition_based", "manual_transfer"]


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--no-write", action="store_true")
    parser.add_argument("--csv", default="ruleset_truth_table.csv")
    args = parser.parse_args()
    count = validate(None if args.no_write else Path(args.csv))
    summary = {"status": "PASS", "scenarios": count, "rules": len(rs.ROUTING_RULES)}
    if not args.no_write:
        Path("ruleset_truth_table_summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
        print(f"Wrote truth table: {Path(args.csv).resolve()} ({count} rows)")
    print("Determinism validation: PASS")
    print(f"Scenarios validated: {count}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
