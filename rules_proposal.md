# IBM SOAR Assignment Router Rules Proposal

This document describes the minimal IBM SOAR rules/actions needed to support the assignment router.

The routing logic should live in the script (`full_script.py`). SOAR rules should only decide **when** to run that script or when to mark an assignment as manually set.

Users should not edit internal routing fields directly. The script manages `incident.owner_id` and `incident.properties.assignment_owner_lock_type`.

## Minimal SOAR rules/actions

| # | Rule/action | Trigger | Script | Purpose |
|---:|---|---|---|---|
| 1 | Incident Created - Assignment Router | Incident is created | `full_script.py` | Run routing when a new incident enters SOAR. |
| 2 | Phase Changed - Assignment Router | Incident phase changes | `full_script.py` | Re-run routing when the lifecycle phase changes. |
| 3 | Routing Field Changed - Assignment Router | Routing input field changes | `full_script.py` | Re-run routing when a field that affects ownership changes. |
| 4 | Manual Recalculate Assignment | User/admin action | `full_script.py` | Re-run routing on demand. |
| 5 | Manual Transfer Ownership | User/admin action after manually selecting owner | `manual_transfer.py` | Mark the current owner as manually set so the router preserves it. |

## Rule 3: routing field changed trigger

Only trigger automatic recalculation from fields that affect routing:

- `incident.properties.cbd`
- `incident.properties.impact_rating`
- `incident.properties.causedby`
- `incident.properties.type`

Do **not** trigger the Assignment Router from every owner change. If a user intentionally changes owner and wants that owner preserved, they should use **Manual Transfer Ownership**.

## Rule 4: Manual Recalculate Assignment

Manual recalculation should only run the router.

Behavior:

1. User/admin triggers **Manual Recalculate Assignment**.
2. SOAR runs `full_script.py`.
3. Router evaluates the current incident state.
4. Router updates `incident.owner_id` only if a routing rule matches and no manual lock blocks routing.
5. Router adds a note when it changes owner.

This action should not directly set or clear manual ownership protection.

## Rule 5: Manual Transfer Ownership

Manual transfer ownership is the user-facing way to preserve a manually selected owner.

Expected user flow:

1. User manually sets the incident owner in SOAR.
2. User runs **Manual Transfer Ownership**.
3. SOAR runs `manual_transfer.py`.
4. `manual_transfer.py` sets:

```python
incident.properties.assignment_owner_lock_type = "manually_set"
```

After that, `full_script.py` exits early and preserves the current owner.

## Current routing behavior in `full_script.py`

`full_script.py` evaluates routing rules by descending priority.

Current owner routing rules:

| Priority | Condition | Owner result | Lock |
|---:|---|---|---|
| 960 | CBD is `GWM US` | `DISO-GWM US` | `condition_based` |
| 950 | Phase is `Triage` and CBD is missing/unknown | `DISO-CIHT` | none |
| 900 | Phase is `Triage`, impact rating `>= 3`, CBD present | CBD business owner from `CBD_BUSINESS_OWNER_MAP`, default `DISO-CIHT` | none |
| 900 | Phase is not `Triage`, impact rating `>= 3`, CBD present | CBD business owner from `CBD_BUSINESS_OWNER_MAP`, default `DISO-CIHT` | none |
| 800 | Phase is not `Triage`, CBD `GF`, impact `< 3`, caused by `IT systems` or `Other third party` | `DISO-CIHT` | `condition_based` |
| 790 | Phase is not `Triage`, CBD `GF`, impact `< 3`, caused by `Employee`, type is `cyber attack` or `cyber incident` | `DISO-CIHT` | `condition_based` |
| 700 | Phase is not `Triage`, CBD is `AM`, `P&C`, `GWM`, or `GWM WMI`, impact is `1` or `2` | CBD business owner from `CBD_BUSINESS_OWNER_MAP`, default `DISO-CIHT` | none |
| 650 | Phase is not `Triage`, CBD is `GF` or `IB`, impact is `1` or `2` | `DISO-CIHT` | none |
| 600 | Impact rating is `0` | `DISO-CIHT` | none |
| 100 | Phase is `Triage`, impact rating `< 3` | `DISO-CIHT` | none |

## Current lock behavior

`full_script.py` supports two lock types:

| Lock type | Set by | Behavior |
|---|---|---|
| `manually_set` | `manual_transfer.py` | Router exits immediately and preserves current owner. |
| `condition_based` | GWM US rule and Criteria 4 GF rules | Router preserves lock while another condition-based rule still matches. If no condition-based rule matches, router clears the lock and re-evaluates. |

## Current audit/note behavior

When `full_script.py` changes owner, it adds an incident note:

```text
Assignment router changed owner_id from {old_owner} to {new_owner} using rule: {rule_name}
```

No note is added when:

- no routing rule matches,
- matched rule keeps the same owner,
- routing exits because `assignment_owner_lock_type == "manually_set"`.

## Members handling

Members handling is currently disabled in `full_script.py`.

The older member-related logic is commented out, including:

- `EXISTING_MEMBERS`
- `MEMBER_CIHT`
- member blocks inside routing rule assignments
- `normalize_members()`
- `resolve_members()`
- reading `incident.members`
- writing `incident.members`

Current routing changes owner only. It does not add or remove members.

## Audit of current implementation

Status: **truthful for the current working-tree implementation with the pending `full_script.py` edits.**

Confirmed:

- `full_script.py` reads routing inputs from:
  - `incident.phase_id.name`
  - `incident.properties.impact_rating`
  - `incident.properties.cbd`
  - `incident.properties.causedby`
  - `incident.properties.type`
  - `incident.properties.assignment_owner_lock_type`
  - `incident.owner_id`
- `full_script.py` writes owner changes to `incident.owner_id`.
- CBD business-owner lookup uses `CBD_BUSINESS_OWNER_MAP`.
- CBD business-owner fallback is hard-coded as `DISO-CIHT`.
- `manual_transfer.py` only sets `assignment_owner_lock_type = "manually_set"`.
- `full_script.py` exits early when `assignment_owner_lock_type == "manually_set"`.
- `full_script.py` can set `condition_based` lock for matching condition-based rules.
- `full_script.py` clears stale `condition_based` lock when no condition-based rule matches.
- `full_script.py` adds an incident note when owner changes.
- Members are currently disabled.

Not currently implemented:

- protected transfer input form,
- target-owner input handling in `manual_transfer.py`,
- optional reason/comment handling,
- multiple manual lock types such as `manual`, `manual_transfer`, or `incident_lifetime`,
- lock reason/audit fields beyond `assignment_owner_lock_type`,
- member updates.

## Final recommendation

Create only the five SOAR rules/actions listed above.

Keep SOAR rules minimal. Put routing decisions in `full_script.py`. Use `manual_transfer.py` only to mark current ownership as manually set when users want to protect a manual transfer.
