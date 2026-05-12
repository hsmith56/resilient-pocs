# Current Assignment Ruleset Proposal

This document summarizes the current implementation represented by `requirements.txt`, `assignment_ruleset.py`, `resilient_example_script.py`, and `manual_transfer.py`.

## Ruleset source of truth

- `requirements.txt` contains the current business criteria.
- `assignment_ruleset.py` contains the data rules evaluated by the router.
- `resilient_example_script.py` applies those rules, manages locks, and writes audit fields.
- `manual_transfer.py` supports Criteria 5 protected transfers from any owner `X` to any owner `Y`.

## Current routing behavior

### Criteria 1 — Triage

- CBD `GWM US` routes to `DISO-GWM US` for impact `0`, `1`, or `2`.
- Non-high-impact Triage cases that do not match a higher-priority rule route to `DISO-CIHT`.
- Impact `3` or higher follows the high-impact `DISO-{cbd}` rule when CBD is present.

### Criteria 2 — Response and Recovery

- Impact `3` or higher routes to `DISO-{incident.properties.cbd}` and adds `CIHT` to current members when CBD is present.
- Impact `1` or `2` with CBD `AM`, `P&C`, `GWM`, or `GWM WMI` routes to the configured business DISO owner and adds `CIHT` to current members.
- Impact `1` or `2` with CBD `GF` or `IB` routes to `DISO-CIHT` and leaves members unchanged.
- CBD `GWM US` with impact `1` or `2` routes to `DISO-GWM US` through lifecycle routing.

### Criteria 3 — Lifecycle

- When the incident moves from `Triage` to `Response and Recovery`, Response and Recovery routing applies.
- Phases outside `Triage` and `Response and Recovery` preserve the current assignment unless Criteria 5 manual-transfer protection applies.

### Criteria 4 — GF CIHT hold

- Applies only while CBD is `GF` and impact is below `3`.
- `causedby = IT systems` or `Other third party` routes to `DISO-CIHT` and sets a `condition_based` owner lock.
- `causedby = Employee` or `Other third party` plus `type = cyber attack` or `cyber incident` routes to `DISO-CIHT` and sets a `condition_based` owner lock.
- The condition-based lock releases when the creating rule no longer matches.

### Criteria 5 — Manual transfer

- Protected transfers from any owner `X` to any owner `Y` create a `manual_transfer` owner lock.
- The lock preserves the transferred owner while impact is below `3`.
- The lock releases when impact becomes `3` or higher so high-impact routing can apply.

### Criteria 6 — Impact 0 and missing CBD

- In active phases, missing CBD and CBD values listed in `CBD_UNKNOWN_VALUES` route to `DISO-CIHT`.
- In active phases, impact `0` routes to `DISO-CIHT` except CBD `GWM US`, which routes to `DISO-GWM US`.

## Lock types

| Lock type | Created by | Release behavior |
|---|---|---|
| `manual_transfer` | Criteria 5 in the router or `manual_transfer.py` protected transfers | Releases when impact becomes `3` or higher |
| `condition_based` | Criteria 4 GF CIHT hold rules | Releases when the creating rule no longer matches |
| `manual` | External/admin process if present | Preserved until explicitly cleared |
| `incident_lifetime` | External/admin process if present | Preserved until explicitly cleared |

## Audit fields

The router writes matched rule names, status, last evaluation time, lock state, and `assignment_router_last_owner` so subsequent evaluations can preserve protected transfers and explain routing decisions.
