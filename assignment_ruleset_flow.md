# Assignment Ruleset Logical Flow

This document describes the current deterministic flow implemented in `assignment_ruleset.py` from the present `requirements.txt` criteria.

Legend:

- ✅ = explicit rule path represented in the ruleset
- 🔒 = owner lock behavior
- “No rule match” = script preserves current owner/members and writes skip/no-match audit

## Priority order

The router evaluates matching rules by descending priority. Higher-priority scalar assignments, such as owner, win.

| Priority | Rule |
|---:|---|
| 1000 | Criteria 5 - Preserve manual transfer |
| 900 | Criteria 2 - High impact routes to `DISO-{cbd}`, Triage or Response and Recovery |
| 880 | Criteria 6 - Missing CBD routes to `DISO-CIHT`, Triage or Response and Recovery |
| 800 | Criteria 4 - GF causedby CIHT hold |
| 790 | Criteria 4 - GF causedby/type CIHT hold |
| 720 | Criteria 1 - Response and Recovery GWM US lifecycle owner |
| 700 | Criteria 2 - Response and Recovery AM/P&C/GWM/GWM WMI low-medium impact business owner |
| 650 | Criteria 2 - Response and Recovery GF/IB impact 1-2 stays with CIHT |
| 620 | Criteria 6 - Response and Recovery impact 0 GWM US owner |
| 600 | Criteria 6 - Response and Recovery impact 0 default CIHT owner |
| 500 | Criteria 1 - Triage GWM US owner |
| 100 | Criteria 1 - Triage default CIHT owner |

## Overall flow

```mermaid
flowchart TD
    Start([Incident evaluated]) --> Mode{assignment_mode is<br/>Manual Override or Locked?}
    Mode -- Yes --> Skip[Skip automatic routing<br/>Preserve current assignment]
    Mode -- No --> ExistingLock{Existing owner lock?}

    ExistingLock -- Yes --> LockRelease{Should lock release?}
    ExistingLock -- No --> ManualCheck{Criteria 5:<br/>current owner differs from<br/>last router owner<br/>and impact < 3?}

    LockRelease -- manual or incident_lifetime --> KeepLock[Keep lock<br/>owner cannot be changed by rules]
    LockRelease -- condition_based no longer matches --> ReleaseLock[Release lock<br/>then re-evaluate context]
    LockRelease -- manual_transfer and impact >= 3 --> ReleaseLock
    LockRelease -- still valid --> KeepLock

    ReleaseLock --> ManualCheck
    KeepLock --> PhaseCheck{Phase?}

    ManualCheck -- Yes --> C5[✅ Criteria 5<br/>owner = current transferred owner<br/>🔒 manual_transfer lock]
    ManualCheck -- No --> PhaseCheck

    C5 --> End([Apply/audit])
    PhaseCheck -- Triage --> TriageFlow[[Triage flow]]
    PhaseCheck -- Response and Recovery --> RRFlow[[Response and Recovery flow]]
    PhaseCheck -- Other phase --> OtherPhase[No rule match<br/>Preserve owner/members]

    TriageFlow --> End
    RRFlow --> End
    OtherPhase --> End
    Skip --> End
```

## Triage flow

```mermaid
flowchart TD
    TStart([Triage phase]) --> TImpact{impact_rating >= 3?}

    TImpact -- Yes --> TCBDPresent{CBD present and known?}
    TCBDPresent -- Yes --> THigh[✅ Criteria 2 high impact<br/>owner = DISO-cbd<br/>members = existing + CIHT]
    TCBDPresent -- No --> TMissingCBD[✅ Criteria 6 missing/unknown CBD<br/>owner = DISO-CIHT<br/>members unchanged]

    TImpact -- No --> TMissingCBD2{CBD missing/unknown?}
    TMissingCBD2 -- Yes --> TMissingCBDLow[✅ Criteria 6 missing/unknown CBD<br/>owner = DISO-CIHT<br/>members unchanged]
    TMissingCBD2 -- No --> TGF{CBD == GF<br/>and Criteria 4 hold condition?}

    TGF -- causedby IT systems<br/>or Other third party --> TGFHold1[✅ Criteria 4<br/>owner = DISO-CIHT<br/>🔒 condition_based lock]
    TGF -- causedby Employee<br/>or Other third party<br/>AND type cyber attack<br/>or cyber incident --> TGFHold2[✅ Criteria 4<br/>owner = DISO-CIHT<br/>🔒 condition_based lock]
    TGF -- No --> TGWMUS{cbd == GWM US?}

    TGWMUS -- Yes --> TGWMUSOwner[✅ Criteria 1<br/>owner = DISO-GWM US]
    TGWMUS -- No --> TDefault[✅ Criteria 1 fallback<br/>owner = DISO-CIHT]

    THigh --> TEnd([Triage result])
    TMissingCBD --> TEnd
    TMissingCBDLow --> TEnd
    TGFHold1 --> TEnd
    TGFHold2 --> TEnd
    TGWMUSOwner --> TEnd
    TDefault --> TEnd
```

## Response and Recovery flow

```mermaid
flowchart TD
    RStart([Response and Recovery phase]) --> RImpactHigh{impact_rating >= 3?}

    RImpactHigh -- Yes --> RCBDPresent{CBD present and known?}
    RCBDPresent -- Yes --> RHigh[✅ Criteria 2 high impact<br/>owner = DISO-cbd<br/>members = existing + CIHT]
    RCBDPresent -- No --> RMissingCBDHigh[✅ Criteria 6 missing/unknown CBD<br/>owner = DISO-CIHT<br/>members unchanged]

    RImpactHigh -- No --> RMissingCBD{CBD missing/unknown?}
    RMissingCBD -- Yes --> RMissingCBDLow[✅ Criteria 6 missing/unknown CBD<br/>owner = DISO-CIHT<br/>members unchanged]
    RMissingCBD -- No --> RGFHold{CBD == GF<br/>and Criteria 4 hold condition?}

    RGFHold -- causedby IT systems<br/>or Other third party --> RGFHold1[✅ Criteria 4<br/>owner = DISO-CIHT<br/>🔒 condition_based lock]
    RGFHold -- causedby Employee<br/>or Other third party<br/>AND type cyber attack<br/>or cyber incident --> RGFHold2[✅ Criteria 4<br/>owner = DISO-CIHT<br/>🔒 condition_based lock]
    RGFHold -- No --> RBusiness{CBD in AM, P&C, GWM, GWM WMI<br/>and impact_rating is 1 or 2?}

    RBusiness -- AM --> RAM[✅ Criteria 2<br/>owner = DISO-AM<br/>members = existing + CIHT]
    RBusiness -- P&C --> RPC[✅ Criteria 2<br/>owner = DISO-P&C<br/>members = existing + CIHT]
    RBusiness -- GWM --> RGWM[✅ Criteria 2<br/>owner = DISO-GWM WMI<br/>members = existing + CIHT]
    RBusiness -- GWM WMI --> RGWMWMI[✅ Criteria 2<br/>owner = DISO-GWM WMI<br/>members = existing + CIHT]
    RBusiness -- No --> RGFIB{CBD in GF or IB<br/>and impact_rating is 1 or 2?}

    RGFIB -- Yes --> RCIHT[✅ Criteria 2<br/>owner = DISO-CIHT<br/>members unchanged]
    RGFIB -- No --> RGWMUS{CBD == GWM US?}

    RGWMUS -- impact 1 or 2 --> RGWMUSOwner[✅ Criteria 1 lifecycle<br/>owner = DISO-GWM US]
    RGWMUS -- impact 0 --> RGWMUSZero[✅ Criteria 6 exception<br/>owner = DISO-GWM US]
    RGWMUS -- No --> RZero{impact_rating == 0?}

    RZero -- Yes --> RZeroDefault[✅ Criteria 6<br/>owner = DISO-CIHT]
    RZero -- No --> RNoMatch[No rule match<br/>Preserve current owner/members]

    RHigh --> REnd([Response and Recovery result])
    RMissingCBDHigh --> REnd
    RMissingCBDLow --> REnd
    RGFHold1 --> REnd
    RGFHold2 --> REnd
    RAM --> REnd
    RPC --> REnd
    RGWM --> REnd
    RGWMWMI --> REnd
    RCIHT --> REnd
    RGWMUSOwner --> REnd
    RGWMUSZero --> REnd
    RZeroDefault --> REnd
    RNoMatch --> REnd
```

## Criteria 5 manual transfer protection

```mermaid
flowchart TD
    MStart([Evaluate Criteria 5]) --> MChanged{current owner differs from<br/>assignment_router_last_owner?}
    MChanged -- No --> MNo[No Criteria 5 match]
    MChanged -- Yes --> MImpact{impact_rating >= 3?}
    MImpact -- Yes --> MHigh[High-impact routing applies]
    MImpact -- No --> MPreserve[✅ Preserve current transferred owner<br/>🔒 set manual_transfer lock]
```

Criteria 5 is generic for transfers from any owner `X` to any owner `Y`. Protected manual transfers created through `manual_transfer.py` write the same `manual_transfer` lock directly.

## Lock behavior

- `manual_transfer` locks preserve the transferred owner while impact is below `3`; they release when impact becomes `3` or higher so high-impact routing can apply.
- `condition_based` locks created by Criteria 4 remain only while their creating Criteria 4 rule still matches.
- `manual` and `incident_lifetime` locks protect the owner until explicitly cleared by an authorized user/admin process.
