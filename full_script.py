# Marker used inside a rule's member list to mean "keep current members, then add
# the remaining configured members." This value is stripped before saving.
EXISTING_MEMBERS = "_existing_members"

# Sentinel used in rules to match missing incident values. A unique object avoids
# confusing an intentional expected value of None/""/[] with the missing marker.

TRIAGE_PHASE = "Triage"

OWNER_CIHT = "DISO-CIHT"
OWNER_GWM_US = "DISO-GWM US"
MEMBER_CIHT = "CIHT"
CBD_MISSING_OR_UNKNOWN_VALUES = [None, "", [], "Unknown", "UNKNOWN", "unknown"]

CBD_BUSINESS_OWNER_MAP = {
    "AM": "DISO-AM",
    "P&C": "DISO-P&C",
    "GWM": "DISO-GWM WMI",
    "GWM WMI": "DISO-GWM WMI",
}

CBD_OWNER_FROM_CONTEXT = {
    "field": "cbd",
    "default_template": "DISO-{cbd}",
}

CBD_BUSINESS_OWNER_FROM_CONTEXT = {
    "field": "cbd",
    "map": CBD_BUSINESS_OWNER_MAP,
}

NOT_IN_TRIAGE_CONDITION = {
    "operator": "not_in",
    "value": [TRIAGE_PHASE]
}

IMPACT_BELOW_3_CONDITION = {
    "operator": "<",
    "value": 3,
}

IMPACT_1_OR_2_CONDITION = {
    "operator": "in",
    "value": [1, 2],
}

# Criteria 5 is intentionally handled before ROUTING_RULES are evaluated.
# resilient_example_script.py exits immediately when
# incident.properties.assignment_owner_lock_type == "manually_set", so manually
# set ownership remains at the top of the decision chain without needing a data
# rule below.
#
# Conceptual top priority:
# {
#     "name": "Criteria 5 - Preserve manually-set assignment",
#     "priority": 1000,
#     "conditions": {
#         "assignment_owner_lock_type": "manually_set",
#     },
#     "assignment": "preserve current owner and members",
# }
#
# Routing rules are evaluated by descending priority after Criteria 5 is checked.
ROUTING_RULES = [
    {
        "name": "Criteria 1 - Triage missing or unknown CBD routes to CIHT",
        "priority": 950,
        "phase": TRIAGE_PHASE,
        "conditions": {
            "cbd": {
                "operator": "in",
                "value": CBD_MISSING_OR_UNKNOWN_VALUES,
            },
        },
        "assignment": {
            "owner": OWNER_CIHT,
        },
        "locks": {},
    },
    {
        "name": "Criteria 1 - Triage impact rating 3+ routes to respective CBD owner",
        "priority": 900,
        "phase": TRIAGE_PHASE,
        "conditions": {
            "impact_rating": {
                "operator": ">=",
                "value": 3,
            },
            "cbd": {
                "operator": "not_in",
                "value": CBD_MISSING_OR_UNKNOWN_VALUES,
            },
        },
        "assignment": {
            "owner": CBD_OWNER_FROM_CONTEXT,
        },
        "locks": {},
    },
    {
        "name": "Criteria 2 - After Triage impact rating 3+ routes to respective CBD owner",
        "priority": 900,
        "conditions": {
            "phase": NOT_IN_TRIAGE_CONDITION,
            "impact_rating": {
                "operator": ">=",
                "value": 3,
            },
            "cbd": {
                "operator": "not_in",
                "value": CBD_MISSING_OR_UNKNOWN_VALUES,
            },
        },
        "assignment": {
            "owner": CBD_OWNER_FROM_CONTEXT,
            "members": [
                EXISTING_MEMBERS,
                MEMBER_CIHT,
            ],
        },
        "locks": {},
    },
    {
        "name": "Criteria 4 - After Triage GF causedby routes to CIHT with condition lock",
        "priority": 800,
        "conditions": {
            "phase": NOT_IN_TRIAGE_CONDITION,
            "cbd": "GF",
            "impact_rating": IMPACT_BELOW_3_CONDITION,
            "causedby": {
                "operator": "in",
                "value": ["IT systems", "Other third party"],
            },
        },
        "assignment": {
            "owner": OWNER_CIHT,
        },
        "locks": {
            "owner": {
                "enabled": True,
                "type": "condition_based",
                "reason": "Owner held with CIHT by Criteria 4 causedby rule.",
            }
        },
    },
    {
        "name": "Criteria 4 - After Triage GF employee cyber routes to CIHT with condition lock",
        "priority": 790,
        "conditions": {
            "phase": NOT_IN_TRIAGE_CONDITION,
            "cbd": "GF",
            "impact_rating": IMPACT_BELOW_3_CONDITION,
            "causedby": "Employee",
            "type": {
                "operator": "in",
                "value": ["cyber attack", "cyber incident"],
            },
        },
        "assignment": {
            "owner": OWNER_CIHT,
        },
        "locks": {
            "owner": {
                "enabled": True,
                "type": "condition_based",
                "reason": "Owner held with CIHT by Criteria 4 causedby/type rule.",
            }
        },
    },
    {
        "name": "Criteria 1/6 - GWM US routes to DISO-GWM US with condition lock",
        "priority": 720,
        "conditions": {
            "cbd": "GWM US",
        },
        "assignment": {
            "owner": OWNER_GWM_US,
        },
        "locks": {
            "owner": {
                "enabled": True,
                "type": "condition_based",
                "reason": "GWM US locked to owner",
            }
        },
    },
    {
        "name": "Criteria 2 - After Triage business impact rating 1-2 routes to business owner",
        "priority": 700,
        "phase": NOT_IN_TRIAGE_CONDITION,
        "conditions": {
            "cbd": {
                "operator": "in",
                "value": ["AM", "P&C", "GWM", "GWM WMI"],
            },
            "impact_rating": IMPACT_1_OR_2_CONDITION,
        },
        "assignment": {
            "owner": CBD_BUSINESS_OWNER_FROM_CONTEXT,
            "members": [
                EXISTING_MEMBERS,
                MEMBER_CIHT,
            ],
        },
        "locks": {},
    },
    {
        "name": "Criteria 2 - After Triage GF/IB impact rating 1-2 routes to CIHT",
        "priority": 650,
        "phase": NOT_IN_TRIAGE_CONDITION,
        "conditions": {
            "cbd": {
                "operator": "in",
                "value": ["GF", "IB"],
            },
            "impact_rating": IMPACT_1_OR_2_CONDITION,
        },
        "assignment": {
            "owner": OWNER_CIHT,
        },
        "locks": {},
    },
    {
        "name": "Criteria 6 - Impact rating 0 default routes to CIHT",
        "priority": 600,
        "conditions": {
            "impact_rating": 0,
        },
        "assignment": {
            "owner": OWNER_CIHT,
        },
        "locks": {},
    },
    {
        "name": "Criteria 1/6 - Triage impact rating below 3 default routes to CIHT",
        "priority": 100,
        "phase": TRIAGE_PHASE,
        "conditions": {
            "impact_rating": IMPACT_BELOW_3_CONDITION,
        },
        "assignment": {
            "owner": OWNER_CIHT,
        },
        "locks": {},
    },
]

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
