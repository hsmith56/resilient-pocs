# IBM SOAR Assignment Router

## Purpose

`resilient_example_script.py` is an IBM Security SOAR / Resilient standalone script. IBM SOAR is expected to inject the global `incident` object at runtime.

The script evaluates a deterministic data-only ruleset and updates incident owner/members/lock/audit fields when a rule applies.

## Files

- `resilient_example_script.py` — generic routing engine and SOAR write/audit logic.
- `assignment_ruleset.py` — imported ruleset built from `requirements.txt`.
- `requirements.txt` — source criteria supplied by the user.

## Ruleset model

Rules are evaluated by descending `priority` from `assignment_ruleset.ROUTING_RULES`.

- Higher-priority scalar assignments win for fields like `owner` and `workspace`.
- Member changes are cumulative when a rule uses `EXISTING_MEMBERS`.
- Owner locks prevent later automated owner changes until their release condition is met.
- Rules only target active phases named `Triage` and `Response and Recovery`; other phases do not re-route, so completed/closed cases retain ownership.

## Implemented criteria mapping

### Criteria 1 — Triage

- In `Triage`, if `incident.properties.cbd == "DISO-xy"`, owner becomes `DISO-XY`.
- Otherwise in `Triage`, owner becomes `DISO-CIHT`.
- If `impact_rating >= 3`, the higher-priority Criteria 2 high-impact route applies immediately instead.

### Criteria 2 — Response and Recovery

- In `Response and Recovery`, `impact_rating >= 3` routes to the CBD owner and adds `CIHT` to existing members.
- In `Response and Recovery`, CBD `AM`, `P&C`, or `GWM` with `impact_rating >= 1` routes to `DISO-AM`, `DISO-P&C`, or `DISO-GM` respectively and adds `CIHT` to existing members.
- In `Response and Recovery`, CBD `GF` or `IB` with impact `1` or `2` routes to `DISO-CIHT` and leaves members unchanged.
- Impact changes are handled by re-running the same deterministic priority rules.

### Criteria 3 — Phase lifecycle

- Moving from `Triage` to `Response and Recovery` naturally causes Criteria 2 rules to be evaluated.
- Phases outside `Triage` and `Response and Recovery` have no routing rules, so ownership stays as-is after response/recovery completion or closure.

### Criteria 4 — GF CIHT hold

While phase is active, CBD is `GF`, and `impact_rating < 3`:

- `causedby` of `123` or `456` routes owner to `DISO-CIHT` and sets a condition-based owner lock.
- `causedby` of `234` or `567` plus `type` of `aaa` or `bbb` routes owner to `DISO-CIHT` and sets a condition-based owner lock.
- The lock releases when the Criteria 4 condition stops matching, including impact `>= 3` or CBD no longer `GF`.

### Criteria 5 — CIHT/WMA manual transfer protection

- The router persists `incident.properties.assignment_router_last_owner` after matched evaluations.
- If a later run observes manual movement between `DISO-CIHT` and `DISO-WMA`, it preserves the new owner with a `manual_transfer` owner lock.
- `DISO-WMA` is not assigned automatically by the requirements rules, so current owner `DISO-WMA` is treated as a manual transfer target.
- `manual_transfer` locks release for high-impact escalation (`impact_rating >= 3`).

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
- `incident.workspace` if configured by a future rule
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

## Assumptions used for deterministic implementation

The requirements contained ambiguous wording. The implemented assumptions are documented at the top of `assignment_ruleset.py`, including consistent use of `DISO-CIHT`, `GWM -> DISO-GM`, Criteria 4 applying only while current CBD is `GF`, and Criteria 5 detection through stored last-router owner state.
