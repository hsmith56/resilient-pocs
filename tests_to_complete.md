# IBM SOAR / Resilient User Signoff Test Scenarios

These are the end-user signoff scenarios to execute in an IBM SOAR / Resilient test environment after deploying the assignment router implementation.

The goal is to validate the behavior from the platform UI/API perspective: create or update incidents, run the assignment automation exactly as it will run in production, and confirm owner, members, locks, audit fields, and notes behave as expected.

## Test setup and common validation

### Required SOAR data setup

Before testing, confirm these owners/groups/users exist and can be assigned in the SOAR test org:

- `DISO-CIHT`
- `DISO-WMA`
- `DISO-GWM US`
- `DISO-AM`
- `DISO-P&C`
- `DISO-GWM WMI`
- `DISO-GF`
- `DISO-IB`
- `DISO-GWM`
- `DISO-UNKNOWN` or another controlled test owner created for an unknown CBD high-impact test, if the platform requires owners to pre-exist
- Member/user/group: `CIHT`

### Fields used in every scenario

Use the SOAR incident fields/properties below. If a field is not mentioned in a scenario, leave it unchanged from the scenario baseline.

- Phase: `Triage`, `Response and Recovery`, or closed/completed phase used by the SOAR org
- Owner
- Members
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

### Impact rating domain

- `impact_rating` is numeric only.
- Valid values are `0`, `1`, `2`, `3`, `4`, `5`.
- Do not test string/non-numeric impact values for user signoff.
- Routing condition `impact_rating >= 3` means impacts `3`, `4`, and `5` satisfy the condition.
- Routing condition `impact_rating in 1-2` means only impacts `1` and `2` satisfy the condition.
- Impact `0` is valid, but it does not satisfy the Response and Recovery low/medium `1-2` rules.

### Common pass criteria for each scenario

For every scenario, after saving the incident and running/waiting for the assignment automation, verify:

- [ ] Incident owner is exactly the expected owner.
- [ ] Incident members are exactly as expected: unchanged, or existing members plus `CIHT`.
- [ ] Existing members are not removed unless the expected result explicitly says so.
- [ ] `CIHT` is not duplicated if already present.
- [ ] Workspace is unchanged.
- [ ] Lock fields are set, kept, released, or unchanged as expected.
- [ ] `assignment_router_last_owner` is correct where the router is expected to write it.
- [ ] `last_assignment_rule_applied` reflects the matched rule(s) where applicable.
- [ ] `assignment_router_status` reflects matched rule, no match, skip, or no-change behavior.
- [ ] `last_assignment_evaluation_time` is updated.
- [ ] A SOAR note/audit entry is written when a change/skip is expected.
- [ ] No unrelated incident fields are changed.

## 1. Assignment mode opt-out scenarios

These confirm users can intentionally prevent automatic routing.

- [ ] SOAR-001 In any phase, set `assignment_mode = Manual Override`; run automation; owner, members, workspace, and lock fields remain unchanged.
- [ ] SOAR-002 In any phase, set `assignment_mode = Locked`; run automation; owner, members, workspace, and lock fields remain unchanged.
- [ ] SOAR-003 With `assignment_mode = Manual Override`, verify audit/status says automatic routing was skipped because assignment mode prevents routing.
- [ ] SOAR-004 With `assignment_mode = Locked`, verify audit/status says automatic routing was skipped because assignment mode prevents routing.
- [ ] SOAR-005 Clear `assignment_mode`; run automation again; normal routing resumes.

## 2. Triage phase routing scenarios

### 2.1 Triage impact `0`, `1`, or `2`

Run these with phase `Triage` and each impact value `0`, `1`, and `2`.

- [ ] SOAR-006 CBD `GWM US` -> owner becomes `DISO-GWM US`; members unchanged; no owner lock.
- [ ] SOAR-007 CBD `AM` -> owner becomes `DISO-CIHT`; members unchanged; no owner lock.
- [ ] SOAR-008 CBD `P&C` -> owner becomes `DISO-CIHT`; members unchanged; no owner lock.
- [ ] SOAR-009 CBD `GWM` -> owner becomes `DISO-CIHT`; members unchanged; no owner lock.
- [ ] SOAR-010 CBD `GWM WMI` -> owner becomes `DISO-CIHT`; members unchanged; no owner lock.
- [ ] SOAR-011 CBD `IB` -> owner becomes `DISO-CIHT`; members unchanged; no owner lock.
- [ ] SOAR-012 CBD `WMA` -> owner becomes `DISO-CIHT`; members unchanged; no owner lock.
- [ ] SOAR-013 CBD blank/missing -> owner becomes `DISO-CIHT`; members unchanged; no owner lock.
- [ ] SOAR-014 Any other CBD value -> owner becomes `DISO-CIHT`; members unchanged; no owner lock.

### 2.2 Triage impact `3`, `4`, or `5`

Run these with phase `Triage` and each impact value `3`, `4`, and `5`.

- [ ] SOAR-015 CBD `AM` -> owner becomes `DISO-AM`; existing members plus `CIHT`.
- [ ] SOAR-016 CBD `P&C` -> owner becomes `DISO-P&C`; existing members plus `CIHT`.
- [ ] SOAR-017 CBD `GWM` -> owner becomes `DISO-GWM`; existing members plus `CIHT`.
- [ ] SOAR-018 CBD `GWM WMI` -> owner becomes `DISO-GWM WMI`; existing members plus `CIHT`.
- [ ] SOAR-019 CBD `GF` -> owner becomes `DISO-GF`; existing members plus `CIHT`.
- [ ] SOAR-020 CBD `IB` -> owner becomes `DISO-IB`; existing members plus `CIHT`.
- [ ] SOAR-021 CBD `GWM US` -> owner becomes `DISO-GWM US`; existing members plus `CIHT`; this confirms `impact_rating >= 3` routing takes precedence over the normal Triage GWM US rule.
- [ ] SOAR-022 CBD `WMA` -> owner becomes `DISO-WMA`; existing members plus `CIHT`.
- [ ] SOAR-023 Any other non-blank CBD value -> owner becomes `DISO-{CBD}`; existing members plus `CIHT`, assuming that owner exists in SOAR.
- [ ] SOAR-024 CBD blank/missing with impact `3`, `4`, or `5` -> Criteria 6 missing CBD rule applies; owner becomes `DISO-CIHT`; members unchanged.

## 3. Response and Recovery phase routing scenarios

### 3.1 Response and Recovery impact `1` or `2`

Run these with phase `Response and Recovery` and each impact value `1` and `2`.

- [ ] SOAR-025 CBD `AM` -> owner becomes `DISO-AM`; existing members plus `CIHT`.
- [ ] SOAR-026 CBD `P&C` -> owner becomes `DISO-P&C`; existing members plus `CIHT`.
- [ ] SOAR-027 CBD `GWM` -> owner becomes `DISO-GWM WMI`; existing members plus `CIHT`.
- [ ] SOAR-028 CBD `GWM WMI` -> owner becomes `DISO-GWM WMI`; existing members plus `CIHT`.
- [ ] SOAR-029 CBD `GF`, no Criteria 4 hold condition -> owner becomes `DISO-CIHT`; members unchanged; no new lock.
- [ ] SOAR-030 CBD `IB` -> owner becomes `DISO-CIHT`; members unchanged; no new lock.
- [ ] SOAR-031 CBD `GWM US` -> no matching Response and Recovery low/medium rule; current owner and members are preserved.
- [ ] SOAR-032 CBD `WMA` -> no matching Response and Recovery low/medium rule; current owner and members are preserved.
- [ ] SOAR-033 CBD blank/missing -> no matching Response and Recovery low/medium rule; current owner and members are preserved.
- [ ] SOAR-034 Any other CBD value -> no matching Response and Recovery low/medium rule; current owner and members are preserved.

### 3.2 Response and Recovery impact `0`

Run these with phase `Response and Recovery` and impact `0`.

- [ ] SOAR-035 CBD `AM` -> Criteria 6 impact 0 default applies; owner becomes `DISO-CIHT`; members unchanged.
- [ ] SOAR-036 CBD `P&C` -> Criteria 6 impact 0 default applies; owner becomes `DISO-CIHT`; members unchanged.
- [ ] SOAR-037 CBD `GWM` -> Criteria 6 impact 0 default applies; owner becomes `DISO-CIHT`; members unchanged.
- [ ] SOAR-038 CBD `GWM WMI` -> Criteria 6 impact 0 default applies; owner becomes `DISO-CIHT`; members unchanged.
- [ ] SOAR-039 CBD `GF`, no Criteria 4 hold condition -> Criteria 6 impact 0 default applies; owner becomes `DISO-CIHT`; members unchanged.
- [ ] SOAR-040 CBD `IB` -> Criteria 6 impact 0 default applies; owner becomes `DISO-CIHT`; members unchanged.
- [ ] SOAR-041 CBD `GF` with Criteria 4 hold condition -> Criteria 4 still applies because impact `0` does not satisfy `impact_rating >= 3`; owner becomes `DISO-CIHT` and condition-based lock is set.
- [ ] SOAR-041A CBD `GWM US` -> Criteria 6 impact 0 exception applies; owner becomes `DISO-GWM US`; members unchanged.
- [ ] SOAR-041B CBD blank/missing -> Criteria 6 impact 0 default applies; owner becomes `DISO-CIHT`; members unchanged.
- [ ] SOAR-041C Any other CBD value -> Criteria 6 impact 0 default applies; owner becomes `DISO-CIHT`; members unchanged.

### 3.3 Response and Recovery impact `3`, `4`, or `5`

Run these with phase `Response and Recovery` and each impact value `3`, `4`, and `5`.

- [ ] SOAR-042 CBD `AM` -> owner becomes `DISO-AM`; existing members plus `CIHT`.
- [ ] SOAR-043 CBD `P&C` -> owner becomes `DISO-P&C`; existing members plus `CIHT`.
- [ ] SOAR-044 CBD `GWM` -> owner becomes `DISO-GWM`; existing members plus `CIHT`.
- [ ] SOAR-045 CBD `GWM WMI` -> owner becomes `DISO-GWM WMI`; existing members plus `CIHT`.
- [ ] SOAR-046 CBD `GF` -> owner becomes `DISO-GF`; existing members plus `CIHT`.
- [ ] SOAR-047 CBD `IB` -> owner becomes `DISO-IB`; existing members plus `CIHT`.
- [ ] SOAR-048 CBD `GWM US` -> owner becomes `DISO-GWM US`; existing members plus `CIHT`.
- [ ] SOAR-049 CBD `WMA` -> owner becomes `DISO-WMA`; existing members plus `CIHT`.
- [ ] SOAR-050 Any other non-blank CBD value -> owner becomes `DISO-{CBD}`; existing members plus `CIHT`, assuming that owner exists in SOAR.
- [ ] SOAR-051 CBD blank/missing with impact `3`, `4`, or `5` -> Criteria 6 missing CBD rule applies; owner becomes `DISO-CIHT`; members unchanged.

## 4. Criteria 4 GF CIHT hold scenarios

These apply in active phases `Triage` and `Response and Recovery` when `cbd = GF` and impact does not satisfy `impact_rating >= 3`.

Run each scenario in both `Triage` and `Response and Recovery` with impact `0`, `1`, and `2` unless otherwise specified.

- [ ] SOAR-052 CBD `GF`, `causedby = IT systems` -> owner becomes `DISO-CIHT`; condition-based owner lock is set.
- [ ] SOAR-053 CBD `GF`, `causedby = Other third party`, type blank/non-cyber -> owner becomes `DISO-CIHT`; condition-based owner lock is set.
- [ ] SOAR-054 CBD `GF`, `causedby = Employee`, `type = cyber attack` -> owner becomes `DISO-CIHT`; condition-based owner lock is set.
- [ ] SOAR-055 CBD `GF`, `causedby = Employee`, `type = cyber incident` -> owner becomes `DISO-CIHT`; condition-based owner lock is set.
- [ ] SOAR-056 CBD `GF`, `causedby = Other third party`, `type = cyber attack` -> owner becomes `DISO-CIHT`; condition-based owner lock is set; verify the expected lock rule/audit order is stable.
- [ ] SOAR-057 CBD `GF`, `causedby = Other third party`, `type = cyber incident` -> owner becomes `DISO-CIHT`; condition-based owner lock is set; verify the expected lock rule/audit order is stable.
- [ ] SOAR-058 CBD `GF`, `causedby = Employee`, `type` not `cyber attack` or `cyber incident` -> Criteria 4 causedby/type rule does not match.
- [ ] SOAR-059 CBD `GF`, `causedby` not in the Criteria 4 lists -> Criteria 4 does not match.
- [ ] SOAR-060 CBD not `GF`, with Criteria 4 causedby/type values -> Criteria 4 does not match.
- [ ] SOAR-061 CBD `GF`, Criteria 4 causedby/type values, impact `3`, `4`, or `5` -> Criteria 4 does not hold; `impact_rating >= 3` owner route applies instead.
- [ ] SOAR-062 Verify Criteria 4 matching is exact: lower/upper-case variants such as `gf`, `it systems`, or `Cyber Attack` do not match unless the field values exactly match the expected configured values.

## 5. Criteria 4 lock release scenarios

Start each scenario from an incident that already has a Criteria 4 condition-based owner lock.

- [ ] SOAR-063 Leave CBD `GF`, same causedby/type, impact `0`, `1`, or `2`; rerun automation; lock remains and owner remains protected as `DISO-CIHT`.
- [ ] SOAR-064 Change impact from `0`, `1`, or `2` to `3`; rerun automation; condition-based lock releases and `impact_rating >= 3` route applies.
- [ ] SOAR-065 Change impact from `0`, `1`, or `2` to `4`; rerun automation; condition-based lock releases and `impact_rating >= 3` route applies.
- [ ] SOAR-066 Change impact from `0`, `1`, or `2` to `5`; rerun automation; condition-based lock releases and `impact_rating >= 3` route applies.
- [ ] SOAR-067 Change CBD from `GF` to `AM`; rerun automation; condition-based lock releases and phase-appropriate routing applies.
- [ ] SOAR-068 Change CBD from `GF` to `IB`; rerun automation; condition-based lock releases and phase-appropriate routing applies.
- [ ] SOAR-069 Change `causedby` so the original Criteria 4 rule no longer matches; rerun automation; condition-based lock releases and phase-appropriate routing applies.
- [ ] SOAR-070 For causedby/type lock, change `type` so the original Criteria 4 rule no longer matches; rerun automation; condition-based lock releases and phase-appropriate routing applies.
- [ ] SOAR-071 Verify released lock fields are cleared: locked false, type blank, rule blank, reason blank, locked timestamp blank.

## 6. Criteria 5 manual CIHT/WMA transfer scenarios

These validate that protected movement between `DISO-CIHT` and `DISO-WMA` does not bounce back during later lifecycle stages when impact is `0`, `1`, or `2`. For normal user signoff, use **Manual Transfer Ownership** rather than direct Owner edits.

- [ ] SOAR-072 Start with an automatically routed `DISO-CIHT` incident. Use Manual Transfer Ownership to transfer to `DISO-WMA` with protection enabled. Keep impact `0`, `1`, or `2`. Rerun automation. Owner remains `DISO-WMA`; manual-transfer lock is set.
- [ ] SOAR-073 With owner `DISO-WMA` and manual-transfer lock, move from `Triage` to `Response and Recovery` with impact `1` or `2`; rerun automation. Owner remains `DISO-WMA` even if normal Response and Recovery routing would assign a business owner.
- [ ] SOAR-074 With owner `DISO-WMA` and manual-transfer lock, change CBD to `AM`, `P&C`, `GWM`, `GWM WMI`, `GF`, or `IB` while impact is `0`, `1`, or `2`; rerun automation. Owner remains `DISO-WMA`.
- [ ] SOAR-075 With owner `DISO-WMA` and manual-transfer lock, rerun automation multiple times without changing fields. Owner remains `DISO-WMA`; lock remains stable.
- [ ] SOAR-076 Use Manual Transfer Ownership to transfer owner from `DISO-WMA` back to `DISO-CIHT` with protection enabled while impact is `0`, `1`, or `2`; rerun automation. Owner remains `DISO-CIHT`; manual-transfer lock is set/kept.
- [ ] SOAR-077 Current owner `DISO-CIHT` with no prior router state showing `DISO-WMA`; rerun automation. Criteria 5 should not falsely trigger.
- [ ] SOAR-078 Current owner is not `DISO-CIHT` or `DISO-WMA`; rerun automation. Criteria 5 should not trigger.
- [ ] SOAR-079 Existing manual-transfer lock with impact changed to `3`; rerun automation. Manual-transfer lock releases and `impact_rating >= 3` owner route applies.
- [ ] SOAR-080 Existing manual-transfer lock with impact changed to `4`; rerun automation. Manual-transfer lock releases and `impact_rating >= 3` owner route applies.
- [ ] SOAR-081 Existing manual-transfer lock with impact changed to `5`; rerun automation. Manual-transfer lock releases and `impact_rating >= 3` owner route applies.
- [ ] SOAR-082 Use Manual Transfer Ownership to transfer to `DISO-WMA` in a closed/completed phase with impact `0`, `1`, or `2`; rerun automation. Manual-transfer preservation applies if automation is still run in that phase.

## 7. Other owner lock scenarios

These validate owner-lock protection visible in SOAR.

- [ ] SOAR-083 Existing owner lock type `manual` -> owner does not change even when a routing rule would normally change it.
- [ ] SOAR-084 Existing owner lock type `incident_lifetime` -> owner does not change even when a routing rule would normally change it.
- [ ] SOAR-085 Existing owner lock type unknown/unrecognized -> owner does not change; verify audit/status and current implementation behavior are acceptable.
- [ ] SOAR-086 With owner locked and a matching rule that adds `CIHT` as member, verify owner remains protected but members are still updated as expected.
- [ ] SOAR-087 Existing stale condition-based lock whose referenced rule no longer exists or no longer matches -> lock is released and routing recovers.

## 8. Phase lifecycle scenarios

- [ ] SOAR-088 Create incident in `Triage`, CBD `AM`, impact `1`; run automation. Owner becomes `DISO-CIHT`.
- [ ] SOAR-089 Move same incident to `Response and Recovery`; run automation. Owner becomes `DISO-AM`; members include existing members plus `CIHT`.
- [ ] SOAR-090 In `Response and Recovery`, change impact from `1` to `3`; run automation. Owner follows `DISO-{CBD}` and members include `CIHT`.
- [ ] SOAR-091 In `Response and Recovery`, CBD `GF`, impact `1`, no Criteria 4 condition; run automation. Owner becomes `DISO-CIHT`; members unchanged.
- [ ] SOAR-092 In `Response and Recovery`, CBD `GF`, impact changes from `1` to `3`; run automation. Owner becomes `DISO-GF`; members include `CIHT`.
- [ ] SOAR-093 Complete/close the Response and Recovery phase using the actual SOAR closed/completed state. Rerun automation if it is triggered. Owner and members remain as-is.
- [ ] SOAR-094 Close a task or move the incident to the org's closed/completed phase. Rerun automation if it is triggered. Owner and members remain as-is.
- [ ] SOAR-095 Phase value outside `Triage` and `Response and Recovery`, with no Criteria 5 manual transfer condition. Run automation. Owner and members are preserved.

## 9. Member handling scenarios

- [ ] SOAR-096 Existing members empty; route through any `impact_rating >= 3` scenario. Final members contain `CIHT`.
- [ ] SOAR-097 Existing members contain one user/group; route through any `impact_rating >= 3` scenario. Final members contain original member plus `CIHT`.
- [ ] SOAR-098 Existing members already contain `CIHT`; route through any member-add scenario. Final members contain only one `CIHT`.
- [ ] SOAR-099 Response and Recovery business-owner route for `AM`, `P&C`, `GWM`, or `GWM WMI` with impact `1` or `2` adds `CIHT` and keeps existing members.
- [ ] SOAR-100 Response and Recovery `GF` or `IB` with impact `1` or `2` leaves members unchanged.
- [ ] SOAR-101 Triage default and Triage `GWM US` low-impact routes leave members unchanged.
- [ ] SOAR-102 Criteria 4 GF hold leaves members unchanged.

## 10. Audit, notes, and custom-field scenarios

- [ ] SOAR-103 Any successful owner change writes/updates `assignment_router_last_owner` to the final owner.
- [ ] SOAR-104 Any successful rule match writes `last_assignment_rule_applied` with the matched rule name(s).
- [ ] SOAR-105 Any successful rule match writes `assignment_router_status` indicating a matched routing rule or no assignment changes needed.
- [ ] SOAR-106 Any no-match/gap scenario writes status indicating no matching route, while preserving owner and members.
- [ ] SOAR-107 Any assignment-mode skip writes status indicating automatic routing was skipped.
- [ ] SOAR-108 Any applied change writes a SOAR note containing matched rules, reason, owner changed, members added/removed, and lock changed/released details.
- [ ] SOAR-109 A no-change rerun does not create noisy duplicate notes unless a lock was released.
- [ ] SOAR-110 Lock creation writes locked flag, lock type, lock rule, lock reason, and locked timestamp.
- [ ] SOAR-111 Lock release clears locked flag, lock type, lock rule, lock reason, and locked timestamp.
- [ ] SOAR-112 Workspace is unchanged across all current routing scenarios.

## 11. Exact value matching scenarios

- [ ] SOAR-113 CBD matching is exact: `GF` matches Criteria 4, but `gf`, `Gf`, or `GF ` do not.
- [ ] SOAR-114 CBD `P&C` routes, but `P&C` does not route as `P&C`.
- [ ] SOAR-115 CBD `GWM WMI` routes as configured, but spelling/spacing variants do not.
- [ ] SOAR-116 `causedby = IT systems` matches, but casing/spelling variants do not.
- [ ] SOAR-117 `causedby = Other third party` matches, but casing/spelling variants do not.
- [ ] SOAR-118 `type = cyber attack` matches, but casing/spelling variants do not.
- [ ] SOAR-119 `type = cyber incident` matches, but casing/spelling variants do not.

## 12. Known gap acceptance scenarios

These are known undefined/gap behaviors shown in the Mermaid graph. They must either be accepted as-is by the product owner or clarified before production signoff.

- [ ] SOAR-120 Impact `3`, `4`, or `5` with missing CBD in `Triage` routes to `DISO-CIHT` with members unchanged. Product owner accepts Criteria 6 missing CBD behavior.
- [ ] SOAR-121 Impact `3`, `4`, or `5` with missing CBD in `Response and Recovery` routes to `DISO-CIHT` with members unchanged. Product owner accepts Criteria 6 missing CBD behavior.
- [ ] SOAR-122 Response and Recovery impact `0` for any CBD except `GWM US` routes to `DISO-CIHT` with members unchanged. Product owner accepts Criteria 6 behavior.
- [ ] SOAR-123 Response and Recovery impact `0` for CBD `GWM US` routes to `DISO-GWM US` with members unchanged. Product owner accepts Criteria 6 exception behavior.
- [ ] SOAR-124 Response and Recovery impact `1` or `2` for CBD outside `AM`, `P&C`, `GWM`, `GWM WMI`, `GF`, and `IB` preserves current owner/members. Product owner accepts this behavior or supplies a new expected owner.
- [ ] SOAR-125 Closed/completed phase names are verified against the actual SOAR org configuration. Product owner confirms no routing should occur there except Criteria 5 if automation is run and manual-transfer conditions match.
- [ ] SOAR-126 Product owner accepts that manual CIHT/WMA transfer protection is inferred from current owner plus `assignment_router_last_owner`, not from full SOAR owner-change event history.
- [ ] SOAR-127 Product owner accepts that impact `3`, `4`, or `5` overrides manual-transfer protection.
- [ ] SOAR-128 Product owner accepts exact case-sensitive field matching, or requests normalization as a new requirement.


## 13. Manual Transfer Ownership action scenarios

These validate the user-facing **Manual Transfer Ownership** action backed by `manual_transfer.py`. Users should not directly edit internal owner-lock fields; the action must perform those updates.

### 13.1 Action configuration and inputs

- [ ] SOAR-129 The **Manual Transfer Ownership** action is available on incident objects.
- [ ] SOAR-130 The action invokes `manual_transfer.py`.
- [ ] SOAR-131 The action exposes a required target owner picker mapped to one supported input name, preferably `rule.input.target_owner`.
- [ ] SOAR-132 The action exposes **Protect this transfer from automatic reassignment?** mapped to `rule.input.lock`.
- [ ] SOAR-133 The action exposes an optional reason/comment mapped to `rule.input.reason`, `rule.input.comment`, or `rule.input.notes`.
- [ ] SOAR-134 Standard users cannot directly edit `assignment_owner_locked`, `assignment_owner_lock_type`, `assignment_owner_lock_rule`, `assignment_owner_lock_reason`, or `assignment_owner_locked_at` from the incident layout.
- [ ] SOAR-135 The action help text tells users to use **Manual Transfer Ownership** instead of direct Owner edits when they want a persistent transfer.

### 13.2 Missing or invalid action input

- [ ] SOAR-136 Run Manual Transfer Ownership without a target owner, if the UI allows it. The script does not change owner, writes failure status, updates evaluation timestamp, and adds a failure note.
- [ ] SOAR-137 Run Manual Transfer Ownership with target owner supplied and no reason/comment. The action succeeds and the audit note omits or leaves blank the reason/comment.
- [ ] SOAR-138 Run Manual Transfer Ownership with target owner and reason/comment. The action succeeds and the note includes the reason/comment.

### 13.3 Unprotected transfer: `rule.input.lock = No/False`

Use these when the selected owner is intended to be temporary and future routing may reassign the incident.

- [ ] SOAR-139 From any owner, run Manual Transfer Ownership to `DISO-AM` with lock = No. Owner becomes `DISO-AM`.
- [ ] SOAR-140 Same unprotected transfer clears `assignment_owner_locked` to false.
- [ ] SOAR-141 Same unprotected transfer clears lock type, lock rule, lock reason, and locked timestamp.
- [ ] SOAR-142 Same unprotected transfer writes `assignment_router_last_owner = DISO-AM`.
- [ ] SOAR-143 Same unprotected transfer writes `last_assignment_rule_applied = Manual Transfer Ownership`.
- [ ] SOAR-144 Same unprotected transfer writes assignment-router status indicating manual transfer completed and protection disabled.
- [ ] SOAR-145 Same unprotected transfer writes evaluation timestamp.
- [ ] SOAR-146 Same unprotected transfer writes a SOAR note with previous owner, target owner, protection = false, and lock type = none.
- [ ] SOAR-147 Same unprotected transfer does not immediately run Assignment Router or otherwise instantly overwrite the selected target owner.
- [ ] SOAR-148 After an unprotected transfer, change a routing field or manually recalculate. Normal Assignment Router behavior may overwrite the owner if a rule matches.
- [ ] SOAR-149 Unprotected transfer from an incident with an existing `manual` lock clears the lock and leaves owner as selected target owner until a later router trigger.
- [ ] SOAR-150 Unprotected transfer from an incident with an existing `manual_transfer` lock clears the lock and leaves owner as selected target owner until a later router trigger.
- [ ] SOAR-151 Unprotected transfer from an incident with an existing `condition_based` lock clears the lock and leaves owner as selected target owner until a later router trigger, if this is accepted operational behavior.

### 13.4 Protected CIHT/WMA transfers: `rule.input.lock = Yes/True`

These validate that explicit protected transfers between the controlled CIHT/WMA pair create a `manual_transfer` lock.

- [ ] SOAR-152 Starting owner `DISO-CIHT`, run Manual Transfer Ownership to `DISO-WMA` with lock = Yes. Owner becomes `DISO-WMA`.
- [ ] SOAR-153 Same transfer sets `assignment_owner_locked = True`.
- [ ] SOAR-154 Same transfer sets `assignment_owner_lock_type = manual_transfer`.
- [ ] SOAR-155 Same transfer sets `assignment_owner_lock_rule = Criteria 5 - Preserve manual CIHT/WMA transfer`.
- [ ] SOAR-156 Same transfer sets lock reason describing manual transfer between `DISO-CIHT` and `DISO-WMA`.
- [ ] SOAR-157 Same transfer sets locked timestamp.
- [ ] SOAR-158 Same transfer writes `assignment_router_last_owner = DISO-WMA`.
- [ ] SOAR-159 Same transfer writes manual-transfer audit status, timestamp, and note.
- [ ] SOAR-160 Starting owner `DISO-WMA`, run Manual Transfer Ownership to `DISO-CIHT` with lock = Yes. Owner becomes `DISO-CIHT` and lock type is `manual_transfer`.
- [ ] SOAR-161 With `manual_transfer` lock and impact `0`, run Assignment Router. Owner remains protected.
- [ ] SOAR-162 With `manual_transfer` lock and impact `1`, run Assignment Router. Owner remains protected.
- [ ] SOAR-163 With `manual_transfer` lock and impact `2`, run Assignment Router. Owner remains protected.
- [ ] SOAR-164 With `manual_transfer` lock, change impact to `3` and run Assignment Router. Lock releases and `impact_rating >= 3` routing applies.
- [ ] SOAR-165 With `manual_transfer` lock, change impact to `4` and run Assignment Router. Lock releases and `impact_rating >= 3` routing applies.
- [ ] SOAR-166 With `manual_transfer` lock, change impact to `5` and run Assignment Router. Lock releases and `impact_rating >= 3` routing applies.

### 13.5 Protected non-CIHT/WMA transfers: `rule.input.lock = Yes/True`

These validate that protected transfers outside the controlled pair create a durable `manual` lock.

- [ ] SOAR-167 Starting owner `DISO-CIHT`, run Manual Transfer Ownership to `DISO-AM` with lock = Yes. Owner becomes `DISO-AM`.
- [ ] SOAR-168 Same transfer sets `assignment_owner_locked = True`.
- [ ] SOAR-169 Same transfer sets `assignment_owner_lock_type = manual`.
- [ ] SOAR-170 Same transfer sets `assignment_owner_lock_rule = Manual Transfer Ownership`.
- [ ] SOAR-171 Same transfer sets lock reason including manually transferred/protected text and the supplied reason/comment if provided.
- [ ] SOAR-172 Same transfer sets locked timestamp.
- [ ] SOAR-173 Same transfer writes `assignment_router_last_owner = DISO-AM`.
- [ ] SOAR-174 Same transfer writes manual-transfer audit status, timestamp, and note.
- [ ] SOAR-175 With this `manual` lock, run Assignment Router in Triage where normal routing would choose `DISO-CIHT`. Owner remains `DISO-AM`.
- [ ] SOAR-176 With this `manual` lock, run Assignment Router in Response and Recovery where normal routing would choose a business owner. Owner remains the manually selected owner.
- [ ] SOAR-177 With this `manual` lock and impact `3`, `4`, or `5`, run Assignment Router. Owner remains manually selected; high-impact routing does not override `manual` lock.
- [ ] SOAR-178 With this `manual` lock and a matching member-add rule, run Assignment Router. Owner remains protected and members can still add `CIHT`.
- [ ] SOAR-179 Transfer from `DISO-AM` to `DISO-WMA` with lock = Yes. Because previous owner is not in the CIHT/WMA pair, lock type is `manual`, not `manual_transfer`.
- [ ] SOAR-180 Transfer from `DISO-CIHT` to `DISO-CIHT` with lock = Yes. Because previous and target owner are not different, lock type is `manual`, not `manual_transfer`.

### 13.6 Removing protection using the same Manual Transfer Ownership action

- [ ] SOAR-181 Start with an incident protected by `manual` lock. Run Manual Transfer Ownership to the current owner with lock = No. Lock fields are cleared and owner remains current owner.
- [ ] SOAR-182 Start with an incident protected by `manual_transfer` lock. Run Manual Transfer Ownership to the current owner with lock = No. Lock fields are cleared and owner remains current owner.
- [ ] SOAR-183 After removing protection, run Manual Recalculate Assignment. Normal routing resumes and may change owner according to ruleset.
- [ ] SOAR-184 After removing protection, change a routing field. Automatic routing resumes and may change owner according to ruleset.

### 13.7 `rule.input.lock` value handling

- [ ] SOAR-185 `rule.input.lock = True` or boolean true enables protection.
- [ ] SOAR-186 `rule.input.lock = False` or boolean false disables protection.
- [ ] SOAR-187 If the SOAR form supplies text values, `Yes`, `true`, `1`, `on`, `lock`, `locked`, or `protect` enable protection.
- [ ] SOAR-188 If the SOAR form supplies text values, `No`, `false`, `0`, blank, or missing disables protection.

## 14. Direct owner edit and user-instruction scenarios

These validate the operational guidance that users should use **Manual Transfer Ownership** instead of direct Owner edits when they want persistence.

- [ ] SOAR-189 Directly edit Owner to a non-CIHT/WMA owner without using Manual Transfer Ownership. Confirm no new `manual` lock is created automatically.
- [ ] SOAR-190 After direct Owner edit to a non-CIHT/WMA owner, run Assignment Router via Manual Recalculate or routing-field change. Confirm the owner may be overwritten by normal routing if a rule matches.
- [ ] SOAR-191 Directly edit Owner to `DISO-WMA` without using Manual Transfer Ownership and run Assignment Router at impact `0`, `1`, or `2`. Confirm Criteria 5 behavior is inferred only if router state allows it.
- [ ] SOAR-192 Directly edit Owner from `DISO-WMA` back to `DISO-CIHT` without using Manual Transfer Ownership and run Assignment Router. Confirm Criteria 5 behavior is inferred only if router state allows it.
- [ ] SOAR-193 Directly edit Owner while a `manual` lock already exists. Confirm Assignment Router continues respecting the existing lock.
- [ ] SOAR-194 Directly edit Owner while a `manual_transfer` lock already exists. Confirm Assignment Router behavior follows the existing manual-transfer lock and impact release rules.
- [ ] SOAR-195 The incident layout or action instructions warn: direct Owner changes are not automatically protected and may be overwritten by assignment automation.
- [ ] SOAR-196 The **Manual Transfer Ownership** action description states that it should be used instead of directly editing Owner when the transfer should persist.
- [ ] SOAR-197 The **Protect this transfer from automatic reassignment?** input help text explains Yes vs No behavior.
- [ ] SOAR-198 Internal assignment lock fields are hidden from standard users or clearly marked system-managed/admin-only.
- [ ] SOAR-199 Users involved in UAT can identify where to find **Manual Transfer Ownership** and can describe when to choose protection = Yes vs No.

## Final signoff checklist

- [ ] SIGNOFF-001 All assignment-mode opt-out scenarios pass.
- [ ] SIGNOFF-002 All Triage scenarios pass for impacts `0` through `5`.
- [ ] SIGNOFF-003 All Response and Recovery scenarios pass for impacts `0` through `5`.
- [ ] SIGNOFF-004 All Criteria 4 GF hold and lock-release scenarios pass.
- [ ] SIGNOFF-005 All Criteria 5 CIHT/WMA manual-transfer scenarios pass.
- [ ] SIGNOFF-006 All phase lifecycle scenarios pass in the actual SOAR workflow.
- [ ] SIGNOFF-007 All member handling scenarios pass.
- [ ] SIGNOFF-008 All audit/note/custom-field scenarios pass.
- [ ] SIGNOFF-009 All exact matching scenarios pass.
- [ ] SIGNOFF-010 All Manual Transfer Ownership scenarios pass.
- [ ] SIGNOFF-011 All direct owner edit and user-instruction scenarios pass.
- [ ] SIGNOFF-012 Product owner accepts or resolves all known gap scenarios.
- [ ] SIGNOFF-013 No open defect remains against ownership, members, locks, lifecycle behavior, manual transfer, audit fields, or notes.
- [ ] SIGNOFF-014 Business owner signs off that the IBM SOAR implementation behaves as expected in the platform.
