"""
Assignment router for IBM Resilient/SOAR standalone scripts.

IBM SOAR provides the ``incident`` object at runtime. This script is not meant to
run as a normal local Python program. It evaluates the incident against ordered
routing rules, updates workspace/owner/members when needed, manages owner locks,
and writes audit fields/notes for traceability.

Routing model:
- Higher ``priority`` rules win for scalar assignment fields like workspace/owner.
- Lower priority rules can still fill fields not already set by a higher rule.
- Member assignments are cumulative when ``EXISTING_MEMBERS`` is used.
- Manual assignment modes and owner locks prevent unwanted automated owner changes.
"""

from datetime import datetime

from assignment_ruleset import (
    EXISTING_MEMBERS,
    MANUAL_TRANSFER_OWNERS,
    MISSING,
    ROUTING_RULES,
)


def utc_now_string():
    """Return an ISO UTC timestamp for SOAR custom datetime/text fields."""
    return datetime.utcnow().isoformat()


def is_missing(value):
    """Return True when an incident field should count as unset for routing."""
    return value is None or value == "" or value == []


def get_property(properties, name, default=None):
    """Safely read a SOAR custom property that may not exist in all orgs."""
    return getattr(properties, name, default)


def set_property(properties, name, value):
    """Write a SOAR custom property by name."""
    setattr(properties, name, value)


def normalize_impact_rating(value):
    """Normalize SOAR custom field values before numeric rule comparisons."""
    if is_missing(value):
        return None

    try:
        return int(value)
    except (TypeError, ValueError):
        return value


def detect_manual_transfer_owner(current_owner, last_router_owner):
    """Infer Criteria 5 CIHT/WMA manual transfer state from stored router state."""
    if current_owner not in MANUAL_TRANSFER_OWNERS:
        return None

    # DISO-WMA is not assigned by the automatic ruleset, so seeing it as the
    # current owner is enough to preserve it as a manual transfer target.
    if current_owner == "DISO-WMA":
        return current_owner

    # A transfer back from DISO-WMA to DISO-CIHT can be inferred when the last owner
    # saved by this router was also in the controlled pair and differs now.
    if (
        last_router_owner in MANUAL_TRANSFER_OWNERS
        and last_router_owner != current_owner
    ):
        return current_owner

    return None


def compare_value(actual_value, expected_value):
    """Compare a field value against a simple rule value or missing sentinel."""
    if expected_value is MISSING:
        return is_missing(actual_value)

    if isinstance(expected_value, list):
        return actual_value in expected_value

    return actual_value == expected_value


def compare_operator(actual_value, operator, expected_value):
    """Compare a field value using an explicit rule operator."""
    if operator == "missing":
        return is_missing(actual_value)

    if operator == "not_missing":
        return not is_missing(actual_value)

    # Missing values never satisfy other operator-based comparisons. Use MISSING
    # or the explicit missing/not_missing operators for blank/unset fields.
    if actual_value is None:
        return False

    try:
        if operator == "==":
            return actual_value == expected_value

        if operator == "!=":
            return actual_value != expected_value

        if operator == ">":
            return actual_value > expected_value

        if operator == ">=":
            return actual_value >= expected_value

        if operator == "<":
            return actual_value < expected_value

        if operator == "<=":
            return actual_value <= expected_value

        if operator == "in":
            return actual_value in expected_value

        if operator == "not_in":
            return actual_value not in expected_value
    except TypeError:
        return False

    raise ValueError("Unsupported operator: {}".format(operator))


def condition_matches(actual_value, expected_condition):
    """Return True when one incident field satisfies one configured condition."""
    if isinstance(expected_condition, dict):
        return compare_operator(
            actual_value=actual_value,
            operator=expected_condition["operator"],
            expected_value=expected_condition["value"],
        )

    return compare_value(actual_value, expected_condition)


def rule_matches(context, rule):
    """Return True when phase and every field condition match an incident."""
    if rule.get("phase") and context["phase"] != rule["phase"]:
        return False

    for field_name, expected_condition in rule.get("conditions", {}).items():
        actual_value = context.get(field_name)

        if not condition_matches(actual_value, expected_condition):
            return False

    return True


def find_rule_by_name(rule_name):
    """Return the configured routing rule with the requested name, if present."""
    for rule in ROUTING_RULES:
        if rule["name"] == rule_name:
            return rule

    return None


def normalize_members(members):
    """Return sorted unique member IDs/emails, excluding blanks and markers."""
    if not members:
        return []

    return sorted(
        set(member for member in members if member and member != EXISTING_MEMBERS)
    )


def resolve_members(current_members, configured_members):
    """Resolve rule members into the desired full incident member list."""
    configured_members = configured_members or []

    if EXISTING_MEMBERS in configured_members:
        combined_members = list(current_members or [])

        for member in configured_members:
            if member != EXISTING_MEMBERS:
                combined_members.append(member)

        return normalize_members(combined_members)

    return normalize_members(configured_members)


def resolve_assignment_value(configured_value, context):
    """Resolve static, context-derived, or map/template assignment values."""
    if not isinstance(configured_value, dict):
        return configured_value

    if "context" in configured_value:
        return context.get(configured_value["context"])

    if "field" in configured_value:
        field_value = context.get(configured_value["field"])

        if is_missing(field_value):
            return configured_value.get("missing_value")

        value_map = configured_value.get("map", {})

        if field_value in value_map:
            return value_map[field_value]

        if configured_value.get("default_template"):
            return configured_value["default_template"].format(**context)

        return configured_value.get("default")

    return configured_value


def get_incident_context(incident):
    """Read all SOAR incident values used by the router into a plain dict."""
    properties = incident.properties
    current_owner = incident.owner_id
    last_router_owner = get_property(properties, "assignment_router_last_owner")

    impact_rating = normalize_impact_rating(get_property(properties, "impact_rating"))

    return {
        "id": incident.id,
        "name": incident.name,
        # Phase and routing fields from requirements.txt.
        "phase": incident.phase_id.name if incident.phase_id else None,
        "severity": incident.severity_code,
        "impact_rating": impact_rating,
        "is_high_impact": (
            isinstance(impact_rating, (int, float)) and impact_rating >= 3
        ),
        "cbd": get_property(properties, "cbd"),
        "causedby": get_property(properties, "causedby"),
        "type": get_property(properties, "type"),
        # Criteria 5 manual transfer state.
        "manual_transfer_owner": detect_manual_transfer_owner(
            current_owner=current_owner,
            last_router_owner=last_router_owner,
        ),
        "assignment_router_last_owner": last_router_owner,
        # Manual routing control. Expected values include "Manual Override" and
        # "Locked" for opt-out from automatic routing.
        "assignment_mode": get_property(properties, "assignment_mode"),
        # Existing lock state. These custom fields let previous runs protect owner
        # changes from later automated routing.
        "assignment_owner_locked": bool(
            get_property(properties, "assignment_owner_locked", False)
        ),
        "assignment_owner_lock_type": get_property(
            properties, "assignment_owner_lock_type"
        ),
        "assignment_owner_lock_rule": get_property(
            properties, "assignment_owner_lock_rule"
        ),
        "assignment_owner_lock_reason": get_property(
            properties, "assignment_owner_lock_reason"
        ),
        # Current assignment state.
        "current_workspace": incident.workspace,
        "current_owner": current_owner,
        "current_members": list(incident.members or []),
    }


def should_release_owner_lock(context):
    """Return True when an automated owner lock no longer applies."""
    if not context["assignment_owner_locked"]:
        return False

    lock_type = context["assignment_owner_lock_type"]
    lock_rule_name = context["assignment_owner_lock_rule"]

    # Manual/lifetime locks are intentionally durable. Only explicit user/admin
    # action should clear them.
    if lock_type == "manual":
        return False

    if lock_type == "incident_lifetime":
        return False

    # If Criteria 5 detects a manual CIHT/WMA transfer while a condition-based
    # automated lock exists, release the older automated lock so the manual
    # transfer lock can take precedence deterministically. Unknown lock types are
    # not released here because the safest behavior is to keep protecting owner.
    if context.get("manual_transfer_owner") and lock_type == "condition_based":
        return True

    # Criteria 5 manual transfer locks persist for the active case lifecycle but
    # yield to explicit high-impact escalation.
    if lock_type == "manual_transfer":
        impact_rating = context.get("impact_rating")
        return isinstance(impact_rating, (int, float)) and impact_rating >= 3

    # Condition locks last while the rule that created them still matches. If the
    # rule was deleted/renamed, release the stale lock so routing can recover.
    if lock_type == "condition_based":
        lock_rule = find_rule_by_name(lock_rule_name)

        if not lock_rule:
            return True

        return not rule_matches(context, lock_rule)

    return False


def release_owner_lock(incident):
    """Clear owner lock custom fields on the SOAR incident."""
    incident.properties.assignment_owner_locked = False
    incident.properties.assignment_owner_lock_type = None
    incident.properties.assignment_owner_lock_rule = None
    incident.properties.assignment_owner_lock_reason = None
    incident.properties.assignment_owner_locked_at = None


def get_matching_rules(context):
    """Return matching routing rules sorted from highest to lowest priority."""
    matching_rules = [rule for rule in ROUTING_RULES if rule_matches(context, rule)]

    return sorted(
        matching_rules,
        key=lambda rule: rule.get("priority", 0),
        reverse=True,
    )


def determine_assignment(context):
    """Build desired assignment state from current incident state and rules."""
    if context["assignment_mode"] in ["Manual Override", "Locked"]:
        return {
            "should_apply": False,
            "reason": "Assignment mode prevents automatic routing.",
            "matched_rules": [],
            "workspace": context["current_workspace"],
            "owner": context["current_owner"],
            "members": context["current_members"],
            "locks_to_set": {},
        }

    matching_rules = get_matching_rules(context)

    desired = {
        "should_apply": bool(matching_rules),
        "reason": (
            "Matched routing rule."
            if matching_rules
            else "No matching routing rule found."
        ),
        "matched_rules": [],
        "workspace": context["current_workspace"],
        "owner": context["current_owner"],
        "members": context["current_members"],
        "locks_to_set": {},
    }

    # Track scalar fields already supplied by higher-priority rules. This keeps a
    # fallback/default rule from overwriting a specific high-priority match.
    assigned_fields = set()

    for rule in matching_rules:
        desired["matched_rules"].append(rule["name"])
        assignment = rule.get("assignment", {})

        if "workspace" in assignment and "workspace" not in assigned_fields:
            desired["workspace"] = resolve_assignment_value(
                assignment["workspace"], context
            )
            assigned_fields.add("workspace")

        if "owner" in assignment and "owner" not in assigned_fields:
            if not context["assignment_owner_locked"]:
                desired["owner"] = resolve_assignment_value(assignment["owner"], context)
                assigned_fields.add("owner")

        if "members" in assignment:
            desired["members"] = resolve_members(
                current_members=desired["members"],
                configured_members=assignment["members"],
            )

        owner_lock = rule.get("locks", {}).get("owner")

        if owner_lock and owner_lock.get("enabled"):
            desired["locks_to_set"]["owner"] = {
                "locked": True,
                "type": owner_lock.get("type", "condition_based"),
                "rule": rule["name"],
                "reason": owner_lock.get("reason", "Owner locked by routing rule."),
            }

    return desired


def get_assignment_changes(context, assignment):
    """Compare current incident state to desired state and return deltas."""
    current_members = set(normalize_members(context["current_members"]))
    desired_members = set(normalize_members(assignment["members"]))

    return {
        "workspace_changed": (context["current_workspace"] != assignment["workspace"]),
        "owner_changed": (context["current_owner"] != assignment["owner"]),
        "members_to_add": sorted(desired_members - current_members),
        "members_to_remove": sorted(current_members - desired_members),
        "owner_lock_changed": (
            "owner" in assignment["locks_to_set"]
            and not context["assignment_owner_locked"]
        ),
    }


def apply_assignment(incident, assignment, changes):
    """Apply calculated workspace/owner/member/lock changes to the incident."""
    if changes["workspace_changed"]:
        incident.workspace = assignment["workspace"]

    if changes["owner_changed"]:
        incident.owner_id = assignment["owner"]

    if changes["members_to_add"] or changes["members_to_remove"]:
        current_members = set(incident.members or [])

        for member in changes["members_to_add"]:
            current_members.add(member)

        for member in changes["members_to_remove"]:
            current_members.discard(member)

        incident.members = sorted(current_members)

    if changes["owner_lock_changed"]:
        owner_lock = assignment["locks_to_set"]["owner"]

        incident.properties.assignment_owner_locked = True
        incident.properties.assignment_owner_lock_type = owner_lock["type"]
        incident.properties.assignment_owner_lock_rule = owner_lock["rule"]
        incident.properties.assignment_owner_lock_reason = owner_lock["reason"]
        incident.properties.assignment_owner_locked_at = utc_now_string()


def write_router_last_owner(incident):
    """Persist the last owner seen after router evaluation for Criteria 5."""
    set_property(
        incident.properties,
        "assignment_router_last_owner",
        incident.owner_id,
    )


def write_audit_fields(incident, assignment, changes, lock_released):
    """Write custom audit fields and a detailed note after changes apply."""
    write_router_last_owner(incident)
    incident.properties.last_assignment_rule_applied = ", ".join(
        assignment["matched_rules"]
    )
    incident.properties.assignment_router_status = assignment["reason"]
    incident.properties.last_assignment_evaluation_time = utc_now_string()

    note_lines = [
        "Assignment Router evaluated incident.",
        "Matched rules: {}".format(", ".join(assignment["matched_rules"])),
        "Reason: {}".format(assignment["reason"]),
        "Owner lock released: {}".format(lock_released),
        "Workspace changed: {}".format(changes["workspace_changed"]),
        "Owner changed: {}".format(changes["owner_changed"]),
        "Members added: {}".format(changes["members_to_add"]),
        "Members removed: {}".format(changes["members_to_remove"]),
        "Owner lock changed: {}".format(changes["owner_lock_changed"]),
    ]

    incident.addNote("\n".join(note_lines))


def write_skip_audit(incident, assignment, lock_released):
    """Write minimal audit info when automatic routing is skipped."""
    incident.properties.assignment_router_status = assignment["reason"]
    incident.properties.last_assignment_evaluation_time = utc_now_string()

    incident.addNote(
        "Assignment Router skipped. Reason: {}. Owner lock released: {}.".format(
            assignment["reason"],
            lock_released,
        )
    )


def write_no_change_audit(incident, assignment, lock_released):
    """Write audit fields when rule evaluation causes no incident changes."""
    write_router_last_owner(incident)
    incident.properties.last_assignment_rule_applied = ", ".join(
        assignment["matched_rules"]
    )
    incident.properties.assignment_router_status = "No assignment changes needed."
    incident.properties.last_assignment_evaluation_time = utc_now_string()

    # Avoid noisy notes on every no-op run. Add a note only when the no-op run
    # still changed lock state by releasing an expired condition-based lock.
    if lock_released:
        incident.addNote(
            "Assignment Router evaluated incident. No assignment changes needed. "
            "Owner lock was released."
        )


def run_assignment_router(incident):
    """Main orchestration entry point called with the SOAR-provided incident."""
    lock_released = False

    # Snapshot incident fields once, then refresh only if releasing a lock changes
    # values used by later routing decisions.
    context = get_incident_context(incident)

    if should_release_owner_lock(context):
        release_owner_lock(incident)
        lock_released = True
        context = get_incident_context(incident)

    assignment = determine_assignment(context)

    if not assignment["should_apply"]:
        write_skip_audit(incident, assignment, lock_released)
        return

    changes = get_assignment_changes(context, assignment)

    no_changes_needed = (
        not changes["workspace_changed"]
        and not changes["owner_changed"]
        and not changes["members_to_add"]
        and not changes["members_to_remove"]
        and not changes["owner_lock_changed"]
    )

    if no_changes_needed:
        write_no_change_audit(incident, assignment, lock_released)
        return

    apply_assignment(incident, assignment, changes)
    write_audit_fields(incident, assignment, changes, lock_released)


# IBM SOAR injects ``incident`` into the standalone script runtime.
run_assignment_router(incident)
