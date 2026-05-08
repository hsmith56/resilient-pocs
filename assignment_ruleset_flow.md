# Assignment Ruleset Logical Flow

This document visualizes the deterministic flow implemented in `assignment_ruleset.py` after the latest `requirements.txt` updates. Paths that are not explicitly defined by the written criteria are marked with **❓ gap**.

Legend:

- ✅ = explicit rule path
- 🔒 = owner lock behavior
- ❓ = behavior is not explicitly defined/needs clarification
- “No rule match” = script preserves current owner/members and writes skip/no-match audit

> User note applied: when CBD is missing, the flow leaves that path as a **❓** because the desired behavior is unknown.

## Priority order

The router evaluates all matching rules and applies scalar fields, like owner, from the highest-priority matching rule first.

| Priority | Rule |
|---:|---|
| 1000 | Criteria 5 - Preserve manual CIHT/WMA transfer |
| 900 | Criteria 2 - High impact routes to `DISO-{cbd}`, Triage or Response and Recovery |
| 800 | Criteria 4 - GF causedby CIHT hold |
| 790 | Criteria 4 - GF causedby/type CIHT hold |
| 700 | Criteria 2 - Response and Recovery AM/P&C/GWM low-medium impact business owner |
| 650 | Criteria 2 - Response and Recovery GF/IB impact 1-2 stays with CIHT |
| 500 | Criteria 1 - Triage GWM US owner |
| 100 | Criteria 1 - Triage default CIHT owner |

## Overall flow

```mermaid
flowchart TD
    Start([Incident evaluated]) --> Mode{assignment_mode is<br/>Manual Override or Locked?}
    Mode -- Yes --> Skip[Skip automatic routing<br/>Preserve current assignment]
    Mode -- No --> ExistingLock{Existing owner lock?}

    ExistingLock -- No --> ManualCheck{Criteria 5:<br/>manual_transfer_owner is<br/>DISO-CIHT or DISO-WMA<br/>and not high impact?}
    ExistingLock -- Yes --> LockRelease{Should lock release?}

    LockRelease -- manual or incident_lifetime --> KeepLock[Keep lock<br/>owner cannot be changed by rules]
    LockRelease -- condition_based no longer matches --> ReleaseLock[Release lock<br/>then re-evaluate context]
    LockRelease -- manual_transfer and impact >= 3 --> ReleaseLock
    LockRelease -- still valid --> KeepLock

    ReleaseLock --> ManualCheck
    KeepLock --> PhaseCheck{Phase?}
    ManualCheck -- Yes --> C5[✅ Criteria 5<br/>owner = current manual transfer owner<br/>DISO-CIHT or DISO-WMA<br/>🔒 manual_transfer lock]
    ManualCheck -- No --> PhaseCheck

    C5 --> End([Apply/audit])

    PhaseCheck -- Triage --> TriageFlow[[Triage flow]]
    PhaseCheck -- Response and Recovery --> RRFlow[[Response and Recovery flow]]
    PhaseCheck -- Other / completed / closed --> OtherPhase[No rule match<br/>Preserve owner/members<br/>❓ Exact completed/closed phase names not defined]

    TriageFlow --> End
    RRFlow --> End
    OtherPhase --> End
    Skip --> End
```

## Triage flow

```mermaid
flowchart TD
    TStart([Triage phase]) --> TImpact{impact_rating >= 3?}

    TImpact -- Yes --> TCBDPresent{CBD present?}
    TCBDPresent -- No --> THighMissing[❓ Gap<br/>High-impact CBD is missing<br/>Desired owner is unknown<br/>Current rules avoid assigning DISO-cbd]
    TCBDPresent -- Yes --> THigh[✅ Criteria 2 high impact<br/>owner = DISO-cbd<br/>members = existing + CIHT]

    TImpact -- No or missing/non-numeric --> TGF{CBD == GF<br/>and Criteria 4 hold condition?}

    TGF -- causedby IT systems<br/>or Other third party --> TGFHold1[✅ Criteria 4<br/>owner = DISO-CIHT<br/>🔒 condition_based lock]
    TGF -- causedby Employee<br/>or Other third party<br/>AND type cyber attack<br/>or cyber incident --> TGFHold2[✅ Criteria 4<br/>owner = DISO-CIHT<br/>🔒 condition_based lock]
    TGF -- No --> TGWMUS{cbd == GWM US?}

    TGWMUS -- Yes --> TGWMUSOwner[✅ Criteria 1<br/>owner = DISO-GWM US]
    TGWMUS -- No --> TDefault[✅ Criteria 1 fallback<br/>owner = DISO-CIHT]

    THighMissing --> TEnd([Triage result])
    THigh --> TEnd
    TGFHold1 --> TEnd
    TGFHold2 --> TEnd
    TGWMUSOwner --> TEnd
    TDefault --> TEnd
```

### Triage gap notes

- ❓ High-impact Triage with missing `cbd` is intentionally left undefined in the flow. The ruleset does not apply the `DISO-{cbd}` high-impact owner formula when CBD is missing.
- ❓ Non-numeric or missing `impact_rating` is treated as not high impact; if this should be invalid or separately routed, that needs clarification.
- ❓ Accepted values and case sensitivity for `cbd`, `causedby`, and `type` are not defined. Current code uses exact string matching.

## Response and Recovery flow

```mermaid
flowchart TD
    RStart([Response and Recovery phase]) --> RImpactHigh{impact_rating >= 3?}

    RImpactHigh -- Yes --> RCBDPresent{CBD present?}
    RCBDPresent -- No --> RHighMissing[❓ Gap<br/>High-impact CBD is missing<br/>Desired owner is unknown<br/>Current rules avoid assigning DISO-cbd]
    RCBDPresent -- Yes --> RHigh[✅ Criteria 2 high impact<br/>owner = DISO-cbd<br/>members = existing + CIHT]

    RImpactHigh -- No or missing/non-numeric --> RGFHold{CBD == GF<br/>and Criteria 4 hold condition?}

    RGFHold -- causedby IT systems<br/>or Other third party --> RGFHold1[✅ Criteria 4<br/>owner = DISO-CIHT<br/>🔒 condition_based lock]
    RGFHold -- causedby Employee<br/>or Other third party<br/>AND type cyber attack<br/>or cyber incident --> RGFHold2[✅ Criteria 4<br/>owner = DISO-CIHT<br/>🔒 condition_based lock]
    RGFHold -- No --> RBusiness{CBD in AM, P&C, GWM, GWM WMI<br/>and impact_rating is 1 or 2?}

    RBusiness -- AM --> RAM[✅ Criteria 2<br/>owner = DISO-AM<br/>members = existing + CIHT]
    RBusiness -- P&C --> RPC[✅ Criteria 2<br/>owner = DISO-P&C<br/>members = existing + CIHT]
    RBusiness -- GWM --> RGWM[✅ Criteria 2<br/>owner = DISO-GWM WMI<br/>members = existing + CIHT]
    RBusiness -- GWM WMI --> RGWMWMI[✅ Criteria 2<br/>owner = DISO-GWM WMI<br/>members = existing + CIHT]
    RBusiness -- No --> RGFIB{CBD in GF or IB<br/>and impact_rating is 1 or 2?}

    RGFIB -- Yes --> RCIHT[✅ Criteria 2<br/>owner = DISO-CIHT<br/>members unchanged]
    RGFIB -- No --> RNoMatch[❓ Gap / no rule match<br/>Preserve current owner/members]

    RHighMissing --> REnd([Response and Recovery result])
    RHigh --> REnd
    RGFHold1 --> REnd
    RGFHold2 --> REnd
    RAM --> REnd
    RPC --> REnd
    RGWM --> REnd
    RGWMWMI --> REnd
    RCIHT --> REnd
    RNoMatch --> REnd
```

### Response and Recovery gap notes

The following Response and Recovery paths have no explicit assignment rule and therefore preserve current assignment:

- ❓ `cbd` is missing, including when impact is high. Desired behavior is unknown.
- ❓ `cbd` is `AM`, `P&C`, `GWM`, or `GWM WMI` but `impact_rating` is missing, non-numeric, `0`, or below `1`.
- ❓ `cbd` is `GF` or `IB` but `impact_rating` is missing, non-numeric, `0`, or below `1`.
- ❓ `cbd` is `GWM US`, `WMA`, or any other non-listed value with impact below `3`.
- ❓ Whether the CBD value should be `GWM`, `GWM WMI`, or both in Response and Recovery was not fully explicit; current rules support both for low-medium impact routing to `DISO-GWM WMI`.
- ❓ Accepted values and case sensitivity for `cbd`, `causedby`, and `type` are not defined. Current code uses exact string matching.

## Owner lock flow

```mermaid
flowchart TD
    LStart([Existing owner lock]) --> LType{Lock type?}

    LType -- manual --> LManual[Keep lock forever<br/>until explicitly cleared]
    LType -- incident_lifetime --> LLife[Keep lock for incident lifetime]
    LType -- manual_transfer --> LManualTransfer{impact_rating >= 3?}
    LType -- condition_based --> LCondition{Original lock rule<br/>still matches?}
    LType -- unknown --> LUnknown[❓ Unknown lock type<br/>Current code does not release]

    LManualTransfer -- Yes --> LRelease1[Release lock<br/>allow high-impact Criteria 2 routing]
    LManualTransfer -- No --> LKeep1[Keep manual transfer lock]

    LCondition -- Yes --> LKeep2[Keep condition lock]
    LCondition -- No --> LRelease2[Release condition lock]

    LManual --> LEnd([Lock result])
    LLife --> LEnd
    LUnknown --> LEnd
    LRelease1 --> LEnd
    LKeep1 --> LEnd
    LKeep2 --> LEnd
    LRelease2 --> LEnd
```

## Criteria 5 manual transfer detection

```mermaid
flowchart TD
    MStart([Evaluate Criteria 5]) --> MOwner{current_owner is<br/>DISO-CIHT or DISO-WMA?}
    MOwner -- No --> MNo[Not a Criteria 5 manual transfer]
    MOwner -- DISO-WMA --> MWMA[Assume manual transfer to DISO-WMA<br/>❓ Inferred because script has no event history]
    MOwner -- DISO-CIHT --> MLast{assignment_router_last_owner<br/>was DISO-WMA?}

    MLast -- Yes --> MCIHT[Assume manual transfer back to DISO-CIHT]
    MLast -- No / missing --> MNo

    MWMA --> MImpact{high impact?}
    MCIHT --> MImpact
    MImpact -- Yes --> MHigh[Do not preserve manual transfer<br/>Criteria 2 high-impact may route]
    MImpact -- No --> MPreserve[✅ owner = current_owner<br/>🔒 manual_transfer lock]
```

### Criteria 5 gap notes

- ❓ The script cannot see true previous-owner event history; it infers manual transfer from current owner plus `assignment_router_last_owner`.
- ❓ The requirements say “rest of the case lifecycle,” but also high-impact escalation rules exist. Current implementation lets high impact override the manual-transfer lock.
- ❓ The criteria use `CIHT` in this section, while other criteria use `DISO-CIHT`. Current rules consistently use owner `DISO-CIHT`.

## Consolidated unresolved clarification list

1. ❓ What should happen when `cbd` is missing? This is intentionally shown as unknown in the diagrams.
2. ❓ What should happen when `impact_rating` is missing, zero, below one, or non-numeric?
3. ❓ What should happen in Response and Recovery for CBD values outside `AM`, `P&C`, `GWM`, `GWM WMI`, `GF`, and `IB` when impact is below `3`?
4. ❓ Should high-impact unknown but non-missing CBD values always use `DISO-{cbd}`?
5. ❓ Should Criteria 5 manual transfer protection override high-impact escalation, or should high impact override manual transfer?
6. ❓ What are the exact closed/completed phase names, and should they be explicit no-op rules?
7. ❓ Are field values case-sensitive exactly as shown, or should the router normalize values like `gf`, `GF`, `Gf`?
