"""
Simple assignment router for IBM Resilient/SOAR.

Resilient gives this script the current ``incident``.
The script looks at the incident details, finds the first matching rule in
``assignment_ruleset.py``, and then updates the incident owner and members.

High level flow:
1. If the incident was manually locked, do nothing.
2. Otherwise, find the highest-priority rule that matches the incident.
3. If an old condition lock no longer matches, clear it and check rules again.
4. If a rule matches, apply that rule's owner, members, and lock type.

The only router lock field used here is:
``incident.properties.assignment_owner_lock_type``

Supported lock values:
- ``manually_set``: a person manually locked the incident; this script stops.
- ``condition_based``: the lock only lasts while the matching condition is true.
"""

from assignment_ruleset import EXISTING_MEMBERS, ROUTING_RULES

CONDITION_BASED_LOCK = "condition_based"
MANUALLY_SET_LOCK = "manually_set"


def is_missing(value):
    """A Resilient field is missing if it has no useful value."""
    return value is None or value == "" or value == []


def normalize_impact_rating(value):
    """Turn the Resilient impact rating into a number when possible."""
    if is_missing(value):
        return None

    try:
        return int(value)
    except (TypeError, ValueError):
        return value


def condition_matches(actual_value, expected_condition):
    """Check one rule condition against one incident value."""
    # Simple rule value, like: cbd == "GF"
    if not isinstance(expected_condition, dict):
        if isinstance(expected_condition, list):
            return actual_value in expected_condition
        return actual_value == expected_condition

    # Operator rule value, like: impact_rating >= 3
    operator = expected_condition["operator"]
    expected_value = expected_condition["value"]

    if operator == "not_missing":
        return not is_missing(actual_value)

    # Blank Resilient fields should not pass number/list comparisons.
    if is_missing(actual_value):
        return False

    try:
        if operator == ">=":
            return actual_value >= expected_value
        if operator == "<":
            return actual_value < expected_value
        if operator == "in":
            return actual_value in expected_value
        if operator == "not_in":
            return actual_value not in expected_value
    except TypeError:
        return False

    raise ValueError("Unsupported operator: {}".format(operator))


def rule_matches(context, rule):
    """Check whether one assignment rule matches this Resilient incident."""
    # A rule can be limited to one Resilient phase, like Triage.
    if rule.get("phase") and context["phase"] != rule["phase"]:
        return False

    # Every condition in the rule must match.
    for field_name, expected_condition in rule.get("conditions", {}).items():
        if not condition_matches(context.get(field_name), expected_condition):
            return False

    return True


def first_matching_rule(context):
    """Find the highest-priority rule that matches the incident."""
    # Bigger priority numbers go first. Stop as soon as one rule matches.
    for rule in sorted(
        ROUTING_RULES,
        key=lambda item: item.get("priority", 0),
        reverse=True,
    ):
        if rule_matches(context, rule):
            return rule

    return None


def lock_type_from_rule(rule):
    """Get the lock type a rule wants to set, if any."""
    owner_lock = (rule or {}).get("locks", {}).get("owner")

    if not owner_lock or not owner_lock.get("enabled"):
        return None

    if owner_lock.get("type") == CONDITION_BASED_LOCK:
        return CONDITION_BASED_LOCK

    return MANUALLY_SET_LOCK


def normalize_members(members):
    """Clean up Resilient members so we compare a tidy sorted list."""
    return sorted(
        set(member for member in (members or []) if member and member != EXISTING_MEMBERS)
    )


def resolve_members(current_members, configured_members):
    """Build the member list requested by a rule."""
    configured_members = configured_members or []

    # If the rule does not say "keep existing members", replace the list.
    if EXISTING_MEMBERS not in configured_members:
        return normalize_members(configured_members)

    # If the rule says "keep existing members", add the new members to them.
    members = list(current_members or [])
    members.extend(member for member in configured_members if member != EXISTING_MEMBERS)
    return normalize_members(members)


def resolve_assignment_value(configured_value, context):
    """Turn a rule's owner setting into the real owner value for Resilient."""
    # Example: "DISO-CIHT"
    if not isinstance(configured_value, dict):
        return configured_value

    # Example: use another value already read from the incident.
    if "context" in configured_value:
        return context.get(configured_value["context"])

    # Example: owner = "DISO-{cbd}" or owner from a CBD map.
    field_value = context.get(configured_value["field"])

    if is_missing(field_value):
        return configured_value.get("missing_value")

    value_map = configured_value.get("map", {})

    if field_value in value_map:
        return value_map[field_value]

    if configured_value.get("default_template"):
        return configured_value["default_template"].format(**context)

    return configured_value.get("default")


def incident_context(incident):
    """Read only the Resilient incident fields needed by the rules."""
    properties = incident.properties

    return {
        "phase": incident.phase_id.name if incident.phase_id else None,
        "impact_rating": normalize_impact_rating(properties.impact_rating),
        "cbd": properties.cbd,
        "causedby": properties.causedby,
        "type": properties.type,
        "assignment_owner_lock_type": properties.assignment_owner_lock_type,
        "current_owner": incident.owner_id,
        "current_members": list(incident.members or []),
    }


def desired_assignment(context, rule):
    """Use the matched rule to decide the wanted owner, members, and lock."""
    assignment = rule.get("assignment", {})

    # Start with what the incident already has. Only change what the rule says.
    owner = context["current_owner"]
    members = context["current_members"]

    if "owner" in assignment:
        owner = resolve_assignment_value(assignment["owner"], context)

    if "members" in assignment:
        members = resolve_members(context["current_members"], assignment["members"])

    return {
        "owner": owner,
        "members": members,
        "lock_type": lock_type_from_rule(rule),
    }


def apply_assignment(incident, context, desired):
    """Write the wanted owner, members, and lock back to Resilient."""
    if incident.owner_id != desired["owner"]:
        incident.owner_id = desired["owner"]

    current_members = set(normalize_members(context["current_members"]))
    desired_members = set(normalize_members(desired["members"]))

    if current_members != desired_members:
        incident.members = sorted(desired_members)

    if (
        desired["lock_type"]
        and context["assignment_owner_lock_type"] != desired["lock_type"]
    ):
        incident.properties.assignment_owner_lock_type = desired["lock_type"]


def run_assignment_router(incident):
    """Run the simple Resilient assignment router."""
    context = incident_context(incident)

    # Criteria 5: if a person manually locked the assignment, the router stops.
    if context["assignment_owner_lock_type"] == MANUALLY_SET_LOCK:
        return

    rule = first_matching_rule(context)

    # If an old condition lock no longer matches, clear it and check again.
    if (
        context["assignment_owner_lock_type"] == CONDITION_BASED_LOCK
        and lock_type_from_rule(rule) != CONDITION_BASED_LOCK
    ):
        incident.properties.assignment_owner_lock_type = None
        context = incident_context(incident)
        rule = first_matching_rule(context)

    # No matching rule means Resilient keeps the owner and members as-is.
    if not rule:
        return

    apply_assignment(incident, context, desired_assignment(context, rule))


# IBM SOAR injects ``incident`` into the standalone script runtime.
run_assignment_router(incident)
