"""
Deterministic assignment ruleset for ``resilient_example_script.py``.

The rules below encode the criteria in requirements.txt as data, separate from
routing execution logic. Priority is part of the deterministic contract: higher
priority rules win for scalar fields such as owner.

Assumptions applied from the ambiguous requirements:
- The CIHT owner is represented consistently as ``DISO-CIHT`` where the criteria
  use either ``CIHT`` or ``DISO-CIHT``.
- The member added by escalation rules is represented as ``CIHT``.
- In active phases, CBD ``GWM US`` with impact 0 maps to owner ``DISO-GWM US``.
- In Triage, CBD ``GWM US`` with impact 1-2 maps to owner ``DISO-GWM US``.
- In Response and Recovery low/medium impact routing, CBD ``GWM`` and
  ``GWM WMI`` map to owner ``DISO-GWM WMI``.
- For impact_rating >= 3, ownership uses the explicit high-impact formula
  ``DISO-{incident.properties.cbd}``.
- The "every change of impact_rating" sentence means the router re-evaluates
  these same priority rules whenever the script runs after impact changes.
- Criteria 4's "unless cbd is changed to anything other than GF" is implemented
  as: the CIHT hold applies only while the current CBD is ``GF`` and impact is
  not high-impact.
- Criteria 5 manual transfer protection is driven by the current/last router
  owner state maintained by the script.
- Criteria 6 impact 0 routing applies in active phases only so completed/closed
  phases still preserve current assignment.
- Missing/unknown CBD routes to ``DISO-CIHT`` in active phases.
"""

# Marker used inside a rule's member list to mean "keep current members, then add
# the remaining configured members." This value is stripped before saving.
EXISTING_MEMBERS = "_existing_members"

# Sentinel used in rules to match missing incident values. A unique object avoids
# confusing an intentional expected value of None/""/[] with the missing marker.
MISSING = object()

TRIAGE_PHASE = "Triage"
RESPONSE_RECOVERY_PHASE = "Response and Recovery"

OWNER_CIHT = "DISO-CIHT"
OWNER_WMA = "DISO-WMA"
MEMBER_CIHT = "CIHT"

MANUAL_TRANSFER_OWNERS = [OWNER_CIHT, OWNER_WMA]

CBD_BUSINESS_OWNER_MAP = {
    "AM": "DISO-AM",
    "P&C": "DISO-P&C",
    "GWM": "DISO-GWM WMI",
    "GWM WMI": "DISO-GWM WMI",
}

CBD_HIGH_IMPACT_OWNER_FROM_CONTEXT = {
    "field": "cbd",
    "default_template": "DISO-{cbd}",
}

CBD_BUSINESS_OWNER_FROM_CONTEXT = {
    "field": "cbd",
    "map": CBD_BUSINESS_OWNER_MAP,
}

MANUAL_TRANSFER_OWNER_FROM_CONTEXT = {
    "context": "manual_transfer_owner",
}

# Routing rules are evaluated by descending priority.
ROUTING_RULES = [
    {
        "name": "Criteria 5 - Preserve manual CIHT/WMA transfer",
        "priority": 1000,
        "conditions": {
            "manual_transfer_owner": {
                "operator": "in",
                "value": MANUAL_TRANSFER_OWNERS,
            },
            "is_high_impact": False,
        },
        "assignment": {
            "owner": MANUAL_TRANSFER_OWNER_FROM_CONTEXT,
        },
        "locks": {
            "owner": {
                "enabled": True,
                "type": "manual_transfer",
                "reason": "Owner locked after manual transfer between DISO-CIHT and DISO-WMA.",
            }
        },
    },
    {
        "name": "Criteria 2 - Triage high impact routes to CBD owner",
        "priority": 900,
        "phase": TRIAGE_PHASE,
        "conditions": {
            "impact_rating": {
                "operator": ">=",
                "value": 3,
            },
            "cbd": {
                "operator": "not_missing",
                "value": True,
            },
        },
        "assignment": {
            "owner": CBD_HIGH_IMPACT_OWNER_FROM_CONTEXT,
            "members": [
                EXISTING_MEMBERS,
                MEMBER_CIHT,
            ],
        },
        "locks": {},
    },
    {
        "name": "Criteria 2 - Response and Recovery high impact routes to CBD owner",
        "priority": 900,
        "phase": RESPONSE_RECOVERY_PHASE,
        "conditions": {
            "impact_rating": {
                "operator": ">=",
                "value": 3,
            },
            "cbd": {
                "operator": "not_missing",
                "value": True,
            },
        },
        "assignment": {
            "owner": CBD_HIGH_IMPACT_OWNER_FROM_CONTEXT,
            "members": [
                EXISTING_MEMBERS,
                MEMBER_CIHT,
            ],
        },
        "locks": {},
    },
    {
        "name": "Criteria 6 - Triage missing CBD routes to CIHT",
        "priority": 880,
        "phase": TRIAGE_PHASE,
        "conditions": {
            "cbd": {
                "operator": "missing",
                "value": True,
            },
        },
        "assignment": {
            "owner": OWNER_CIHT,
        },
        "locks": {},
    },
    {
        "name": "Criteria 6 - Response and Recovery missing CBD routes to CIHT",
        "priority": 880,
        "phase": RESPONSE_RECOVERY_PHASE,
        "conditions": {
            "cbd": {
                "operator": "missing",
                "value": True,
            },
        },
        "assignment": {
            "owner": OWNER_CIHT,
        },
        "locks": {},
    },
    {
        "name": "Criteria 4 - Triage GF causedby CIHT hold",
        "priority": 800,
        "phase": TRIAGE_PHASE,
        "conditions": {
            "cbd": "GF",
            "is_high_impact": False,
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
        "name": "Criteria 4 - Response and Recovery GF causedby CIHT hold",
        "priority": 800,
        "phase": RESPONSE_RECOVERY_PHASE,
        "conditions": {
            "cbd": "GF",
            "is_high_impact": False,
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
        "name": "Criteria 4 - Triage GF causedby/type CIHT hold",
        "priority": 790,
        "phase": TRIAGE_PHASE,
        "conditions": {
            "cbd": "GF",
            "is_high_impact": False,
            "causedby": {
                "operator": "in",
                "value": ["Employee", "Other third party"],
            },
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
        "name": "Criteria 4 - Response and Recovery GF causedby/type CIHT hold",
        "priority": 790,
        "phase": RESPONSE_RECOVERY_PHASE,
        "conditions": {
            "cbd": "GF",
            "is_high_impact": False,
            "causedby": {
                "operator": "in",
                "value": ["Employee", "Other third party"],
            },
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
        "name": "Criteria 2 - Response and Recovery AM/P&C/GWM low-medium impact routes to business owner",
        "priority": 700,
        "phase": RESPONSE_RECOVERY_PHASE,
        "conditions": {
            "cbd": {
                "operator": "in",
                "value": ["AM", "P&C", "GWM", "GWM WMI"],
            },
            "impact_rating": {
                "operator": "in",
                "value": [1, 2],
            },
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
        "name": "Criteria 2 - Response and Recovery GF/IB impact 1-2 stays with CIHT",
        "priority": 650,
        "phase": RESPONSE_RECOVERY_PHASE,
        "conditions": {
            "cbd": {
                "operator": "in",
                "value": ["GF", "IB"],
            },
            "impact_rating": {
                "operator": "in",
                "value": [1, 2],
            },
        },
        "assignment": {
            "owner": OWNER_CIHT,
        },
        "locks": {},
    },
    {
        "name": "Criteria 6 - Response and Recovery impact 0 GWM US owner",
        "priority": 620,
        "phase": RESPONSE_RECOVERY_PHASE,
        "conditions": {
            "cbd": "GWM US",
            "impact_rating": 0,
        },
        "assignment": {
            "owner": "DISO-GWM US",
        },
        "locks": {},
    },
    {
        "name": "Criteria 6 - Response and Recovery impact 0 default CIHT owner",
        "priority": 600,
        "phase": RESPONSE_RECOVERY_PHASE,
        "conditions": {
            "impact_rating": 0,
        },
        "assignment": {
            "owner": OWNER_CIHT,
        },
        "locks": {},
    },
    {
        "name": "Criteria 1 - Triage GWM US owner",
        "priority": 500,
        "phase": TRIAGE_PHASE,
        "conditions": {
            "cbd": "GWM US",
            "is_high_impact": False,
        },
        "assignment": {
            "owner": "DISO-GWM US",
        },
        "locks": {},
    },
    {
        "name": "Criteria 1 - Triage default CIHT owner",
        "priority": 100,
        "phase": TRIAGE_PHASE,
        "conditions": {
            "is_high_impact": False,
        },
        "assignment": {
            "owner": OWNER_CIHT,
        },
        "locks": {},
    },
]
