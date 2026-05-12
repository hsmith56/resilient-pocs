"""
Deterministic assignment ruleset for ``resilient_example_script.py``.

The rules below encode requirements.txt as the smallest practical set of data
rules supported by the router. Priority is part of the deterministic contract:
higher-priority rules win for scalar fields such as owner, while member updates
remain cumulative.

Consolidation choices:
- Triage and Response and Recovery rules that perform the same assignment are
  represented once with an explicit active-phase condition.
- Rules use the requirements.txt field name ``impact_rating`` directly instead
  of introducing any additional impact classification concept.
- The Criteria 4 causedby/type rule only needs ``Employee`` because ``Other
  third party`` is already fully covered by the broader causedby rule.
"""

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
