# IBM SOAR Assignment Router

## Purpose

`resilient_example_script.py` is an IBM Security SOAR / Resilient standalone script. IBM SOAR is expected to inject the global `incident` object at runtime.

The script evaluates the current `requirements.txt` criteria through the data-only rules in `assignment_ruleset.py` and updates incident owner, members, lock fields, and audit fields when a rule applies.

## Files

- `requirements.txt` — current source criteria.
- `assignment_ruleset.py` — deterministic ruleset built from the current criteria.
- `resilient_example_script.py` — routing engine and SOAR write/audit logic.
- `manual_transfer.py` — Manual Transfer Ownership action that can protect transfers from any owner `X` to any owner `Y`.
- `assignment_ruleset_flow.md` — readable flow of the current ruleset.

## Ruleset model

Rules are evaluated by descending `priority` from `assignment_ruleset.ROUTING_RULES`.

- Higher-priority scalar assignments win for fields like `owner` and `workspace`.
- Member changes are cumulative when a rule uses `EXISTING_MEMBERS`.
- Owner locks prevent automated owner changes until their release condition is met.
- Active automatic routing phases are `Triage` and `Response and Recovery`.
- Other phases preserve current owner/members unless Criteria 5 manual-transfer protection applies.

## Current criteria mapping

### Criteria 1 — Triage

- In `Triage`, CBD `GWM US` routes to `DISO-GWM US` for impact `0`, `1`, or `2`.
- In `Triage`, non-high-impact cases that do not match a higher-priority rule route to `DISO-CIHT`.
- In `Triage`, impact `3` or higher follows the high-impact `DISO-{cbd}` rule when CBD is present.

### Criteria 2 — Response and Recovery

- Impact `3` or higher routes to `DISO-{incident.properties.cbd}` and adds `CIHT` to existing members when CBD is present.
- CBD `AM`, `P&C`, `GWM`, or `GWM WMI` with impact `1` or `2` routes to the respective business owner and adds `CIHT` to existing members.
- CBD `GF` or `IB` with impact `1` or `2` routes to `DISO-CIHT` and leaves members unchanged.
- CBD `GWM US` with impact `1` or `2` routes to `DISO-GWM US` through lifecycle routing.

### Criteria 3 — Phase lifecycle

- Moving from `Triage` to `Response and Recovery` causes Response and Recovery rules to apply.
- After Response and Recovery completion or task closure, phases outside active routing preserve current owner/members.

### Criteria 4 — GF CIHT hold

While phase is active, CBD is `GF`, and impact is below `3`:

- `causedby` of `IT systems` or `Other third party` routes owner to `DISO-CIHT` and sets a condition-based owner lock.
- `causedby` of `Employee` or `Other third party` plus `type` of `cyber attack` or `cyber incident` routes owner to `DISO-CIHT` and sets a condition-based owner lock.
- The lock releases when CBD changes away from `GF`, impact becomes `3` or higher, or the creating condition stops matching.

### Criteria 5 — Manual transfer protection

- Transfers from any owner `X` to any owner `Y` can be protected.
- Protected transfers set a `manual_transfer` owner lock and preserve the transferred owner while impact is below `3`.
- `manual_transfer` locks release when impact becomes `3` or higher so high-impact routing can apply.

### Criteria 6 — Impact 0 and missing CBD

- In active phases, missing CBD and CBD values listed in `CBD_UNKNOWN_VALUES` route to `DISO-CIHT`.
- In active phases, impact `0` routes to `DISO-CIHT` except CBD `GWM US`, which routes to `DISO-GWM US`.

## Incident fields read

Standard fields:

- `incident.id`
- `incident.name`
- `incident.phase_id.name`
- `incident.severity_code`
- `incident.workspace`
- `incident.owner_id`
- `incident.members`

Custom properties:

- `incident.properties.cbd`
- `incident.properties.impact_rating`
- `incident.properties.causedby`
- `incident.properties.type`
- `incident.properties.assignment_mode`
- `incident.properties.assignment_owner_locked`
- `incident.properties.assignment_owner_lock_type`
- `incident.properties.assignment_owner_lock_rule`
- `incident.properties.assignment_owner_lock_reason`
- `incident.properties.assignment_router_last_owner`

## Incident fields written

Assignment fields:

- `incident.owner_id`
- `incident.workspace` if configured by a rule
- `incident.members`

Custom properties:

- `incident.properties.assignment_owner_locked`
- `incident.properties.assignment_owner_lock_type`
- `incident.properties.assignment_owner_lock_rule`
- `incident.properties.assignment_owner_lock_reason`
- `incident.properties.assignment_owner_locked_at`
- `incident.properties.assignment_router_last_owner`
- `incident.properties.last_assignment_rule_applied`
- `incident.properties.assignment_router_status`
- `incident.properties.last_assignment_evaluation_time`

Notes:

- `incident.addNote(...)`
