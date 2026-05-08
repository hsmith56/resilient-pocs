# IBM SOAR Assignment Router Rules Proposal

This is the current proposed state of the IBM SOAR assignment-routing system.

The design goal is to keep automatic routing minimal and non-intrusive while giving users one friendly manual ownership action. Users should **not** manually edit internal fields such as `incident.owner_id`, `assignment_owner_locked`, `assignment_owner_lock_type`, `assignment_owner_lock_rule`, `assignment_owner_lock_reason`, or `assignment_owner_locked_at`. Those fields are system-managed by scripts/workflows.

## Recommended rules/actions

| # | Rule/action | Trigger | Script/workflow | Behavior |
|---:|---|---|---|---|
| 1 | Incident Created - Assignment Router | Incident is created | `resilient_example_script.py` / Assignment Router | Automatically evaluates assignment based on the ruleset. |
| 2 | Phase Changed - Assignment Router | Incident phase changes | `resilient_example_script.py` / Assignment Router | Re-evaluates assignment when lifecycle phase changes. |
| 3 | Routing Field Changed - Assignment Router | Any routing-relevant field changes | `resilient_example_script.py` / Assignment Router | Re-evaluates assignment when routing inputs change. |
| 4 | Manual Recalculate Assignment | User/admin manually triggers recalculation | `resilient_example_script.py` / Assignment Router | Re-runs routing only. Does not set or clear locks. |
| 5 | Manual Transfer Ownership | User/admin manually chooses a new owner | `manual_transfer.py` | Sets selected owner, sets or clears assignment protection based on `rule.input.lock`, and writes audit information. |

## Rule 3: Routing field changed trigger

Only trigger automatic recalculation from fields that actually affect routing:

- `incident.properties.cbd`
- `incident.properties.impact_rating`
- `incident.properties.causedby`
- `incident.properties.type`

Recommended: do **not** trigger Assignment Router from every owner change. Intentional owner changes should go through **Manual Transfer Ownership** so the user can decide whether the transfer should be protected from future automatic reassignment.

## Rule 4: Manual Recalculate Assignment

This action should be safe and predictable.

Behavior:

1. User/admin triggers **Manual Recalculate Assignment**.
2. SOAR runs `Assignment Router`.
3. No lock fields are set or cleared by this action.

Use this when:

- a routing field was corrected,
- a phase transition did not trigger as expected,
- an admin wants to re-run assignment logic,
- testing/signoff needs a clean rerun.

## Rule 5: Manual Transfer Ownership

This is the single user-facing ownership-transfer action.

The user does **not** edit owner/lock custom fields directly. The invocation form collects friendly inputs, and `manual_transfer.py` performs all internal updates.

### User inputs

| Input | Script input | Type | Required | Purpose |
|---|---|---|---:|---|
| Target owner | `rule.input.target_owner` preferred. Script also accepts `owner`, `new_owner`, or `transfer_owner`. | Owner/group/user picker | Yes | The owner the user wants to transfer the incident to. |
| Protect this transfer from automatic reassignment? | `rule.input.lock` | Boolean / Yes-No | Yes | Controls whether internal lock fields are set. |
| Reason/comment | `rule.input.reason` preferred. Script also accepts `comment` or `notes`. | Text | Optional | Included in the audit note / lock reason where applicable. |

### Current implementation

The manual transfer action is implemented in:

```text
manual_transfer.py
```

It runs on incident objects and expects SOAR to inject:

- `incident`
- `rule`
- `rule.input.lock`
- a target owner input
- optional reason/comment input

### Behavior when `rule.input.lock` is `False` / No

Use this when the user wants a simple transfer and accepts that future automatic routing events may change owner again.

`manual_transfer.py` does the following:

1. Reads the selected target owner from rule input.
2. Sets `incident.owner_id` to the selected target owner.
3. Clears existing assignment owner-lock fields:
   - `assignment_owner_locked = False`
   - `assignment_owner_lock_type = None`
   - `assignment_owner_lock_rule = None`
   - `assignment_owner_lock_reason = None`
   - `assignment_owner_locked_at = None`
4. Updates `assignment_router_last_owner` to the target owner.
5. Writes:
   - `last_assignment_rule_applied = Manual Transfer Ownership`
   - `assignment_router_status = Manual transfer ownership completed...`
   - `last_assignment_evaluation_time`
6. Adds an incident note documenting previous owner, target owner, protection setting, lock type, and reason/comment if supplied.
7. Does **not** run Assignment Router immediately.

Reason for not immediately running Assignment Router: an unprotected manual transfer may be immediately overwritten by normal routing if the router is run in the same transaction.

### Behavior when `rule.input.lock` is `True` / Yes

Use this when the user wants the selected owner to remain in place until a defined release condition occurs.

`manual_transfer.py` sets `incident.owner_id` to the selected target owner, then chooses the correct lock type.

#### Case A: transfer is specifically between `DISO-CIHT` and `DISO-WMA`

If the previous owner and target owner are both in the controlled CIHT/WMA pair and they are different, the script sets a `manual_transfer` lock.

Fields set:

- `assignment_owner_locked = True`
- `assignment_owner_lock_type = manual_transfer`
- `assignment_owner_lock_rule = Criteria 5 - Preserve manual CIHT/WMA transfer`
- `assignment_owner_lock_reason = Owner locked after manual transfer between DISO-CIHT and DISO-WMA.`
- `assignment_owner_locked_at = current timestamp`
- `assignment_router_last_owner = target owner`
- `last_assignment_rule_applied = Manual Transfer Ownership`
- `assignment_router_status = Manual transfer ownership completed...`
- `last_assignment_evaluation_time = current timestamp`

Expected later router behavior:

- The Assignment Router respects the `manual_transfer` lock while impact is `0`, `1`, or `2`.
- The Assignment Router automatically releases the `manual_transfer` lock when `impact_rating` becomes `3`, `4`, or `5`.
- After release, normal `impact_rating >= 3` routing applies.

#### Case B: transfer is to any other owner

For protected transfers outside the CIHT/WMA pair, the script sets a durable `manual` lock.

Fields set:

- `assignment_owner_locked = True`
- `assignment_owner_lock_type = manual`
- `assignment_owner_lock_rule = Manual Transfer Ownership`
- `assignment_owner_lock_reason = Manually transferred and protected by user/admin. Reason/comment: ...`
- `assignment_owner_locked_at = current timestamp`
- `assignment_router_last_owner = target owner`
- `last_assignment_rule_applied = Manual Transfer Ownership`
- `assignment_router_status = Manual transfer ownership completed...`
- `last_assignment_evaluation_time = current timestamp`

Expected later router behavior:

- Owner remains the selected target owner because `manual` lock protects it.
- Matching assignment rules may still update members, for example adding `CIHT` where applicable.
- The `manual` lock does **not** automatically release.
- To remove manual protection, run **Manual Transfer Ownership** again with `rule.input.lock = False`.

### How users remove protection

To keep the UI minimal, there is no separate unlock action in the initial proposal.

A user/admin removes protection by running **Manual Transfer Ownership** again with:

- target owner = the desired owner, usually the current owner
- `rule.input.lock = False`
- optional reason/comment

The script clears lock fields and writes an audit note. The next automatic trigger or **Manual Recalculate Assignment** can then route normally.

If UAT shows users find this confusing, add a separate **Remove Assignment Protection** action later. It is not required for the minimal rollout.

## Direct owner edits outside Manual Transfer Ownership

Users should be instructed to use **Manual Transfer Ownership** instead of directly editing the incident owner when they want the transfer to persist.

If someone directly changes `incident.owner_id` without using the action, the result depends on the owner and the next router trigger:

| Direct owner edit | Likely outcome |
|---|---|
| Owner manually changed to `DISO-WMA` | The Assignment Router may later infer a Criteria 5 CIHT/WMA transfer and set a `manual_transfer` lock if impact is `0-2`, but this depends on stored router state and is less explicit than using the action. |
| Owner manually changed from `DISO-WMA` back to `DISO-CIHT` | The Assignment Router may preserve it if `assignment_router_last_owner` indicates the prior WMA state, but this is inferred rather than guaranteed from true owner-change history. |
| Owner manually changed to any other team/user | The next Assignment Router run may overwrite the direct owner change if a routing rule matches, because direct edits do not automatically set `assignment_owner_locked`. |
| Owner manually changed while a lock already exists | The router respects the existing lock according to its lock type, but the direct owner edit does not reliably create or update protection. |

Main risk:

> A user may think they transferred ownership, but the next automatic router event may move the incident back.

### Recommended user instruction

Use this wording in SOAR help text, playbook descriptions, training material, or incident-layout guidance:

> **To transfer ownership, use Actions → Manual Transfer Ownership.**
>
> Do not change the incident owner directly unless the change is temporary. Direct owner changes may be overwritten the next time assignment automation runs.
>
> The Manual Transfer Ownership action lets you choose the new owner and decide whether to protect the transfer from automatic reassignment.

### Recommended action description

For the **Manual Transfer Ownership** action in SOAR:

> Transfer this incident to a selected owner. Choose whether the transfer should be protected from future automatic reassignment. Use this instead of directly editing the Owner field when you want the ownership change to persist.

### Recommended `rule.input.lock` help text

For the invocation field **Protect this transfer from automatic reassignment?**:

> Select **Yes** if this owner should remain assigned even when routing fields or phase change. Select **No** if this is a temporary transfer and future routing may update the owner.

### Recommended owner-field warning

If SOAR allows a tooltip, section note, or layout instruction near the Owner field, use:

> Manual changes to Owner are not automatically protected. To make an ownership transfer persist, use **Manual Transfer Ownership** from the Actions menu.



## Expected lock types

| Lock type | Set by | Automatically released? | Release condition |
|---|---|---:|---|
| `condition_based` | Assignment Router Criteria 4 | Yes | Original Criteria 4 rule no longer matches: CBD changes away from `GF`, impact becomes `3-5`, caused-by/type changes, or the rule no longer exists. |
| `manual_transfer` | `manual_transfer.py` for protected CIHT/WMA transfer; Assignment Router Criteria 5 can also set it if it detects CIHT/WMA transfer state | Yes | Impact becomes `3-5`. |
| `manual` | `manual_transfer.py` when protected transfer is not specifically between `DISO-CIHT` and `DISO-WMA` | No | User/admin removes protection by running Manual Transfer Ownership with lock = No. |
| `incident_lifetime` | Not proposed for minimal rollout | No | User/admin/admin workflow clears it if introduced later. |

## Current script responsibilities

### `resilient_example_script.py` / Assignment Router

Responsible for:

- Criteria 1 Triage routing.
- Criteria 2 Response and Recovery routing.
- Criteria 2 impact `>= 3` escalation routing in active phases.
- Criteria 3 phase/lifecycle re-evaluation.
- Criteria 4 GF CIHT hold and `condition_based` locks.
- Criteria 5 CIHT/WMA manual-transfer preservation.
- Respecting existing `manual`, `manual_transfer`, `condition_based`, and `incident_lifetime` locks.
- Releasing `condition_based` locks when their original rule no longer matches.
- Releasing `manual_transfer` locks when impact becomes `3-5`.
- Preserving `manual` and `incident_lifetime` locks until explicit user/admin action.
- Updating audit fields and notes.

Not responsible for:

- Displaying a user form for manual transfer.
- Reading `rule.input.lock`.
- Creating a protected transfer to arbitrary non-CIHT/WMA owners; that is handled by `manual_transfer.py`.

### `manual_transfer.py` / Manual Transfer Ownership

Responsible for:

- Reading the user-selected target owner.
- Reading `rule.input.lock`.
- Reading optional reason/comment.
- Setting `incident.owner_id`.
- Setting `manual_transfer` lock for protected CIHT/WMA transfers.
- Setting `manual` lock for protected transfers to any other owner.
- Clearing lock fields for unprotected transfers / protection removal.
- Updating assignment audit fields.
- Adding an incident note.

Not responsible for:

- Running the full routing ruleset.
- Reassigning based on CBD/impact/phase.
- Setting Criteria 4 condition-based locks.

## Audit of current implementation

### `assignment_ruleset.py`

Status: **Compliant with the proposed automatic routing rules.**

Confirmed:

- Defines all required constants:
  - `TRIAGE_PHASE`
  - `RESPONSE_RECOVERY_PHASE`
  - `OWNER_CIHT = "DISO-CIHT"`
  - `OWNER_WMA = "DISO-WMA"`
  - `MEMBER_CIHT = "CIHT"`
  - `MANUAL_TRANSFER_OWNERS`
  - CBD owner maps
- Criteria 1 Triage routing is represented.
- Criteria 2 Response and Recovery routing is represented.
- Criteria 2 impact `>= 3` routing is represented in both Triage and Response and Recovery.
- Criteria 4 GF CIHT hold is represented in both active phases and sets `condition_based` lock.
- Criteria 5 CIHT/WMA manual-transfer preservation is represented and sets `manual_transfer` lock if detected by the router.
- No ruleset rule automatically sets `manual` or `incident_lifetime`, which is correct. `manual` is set only by `manual_transfer.py` when users explicitly protect a non-CIHT/WMA transfer.

Known accepted gaps still present:

- Missing CBD when impact is `3-5` does not produce `DISO-{cbd}` owner.
- Response and Recovery impact `0` has no low/medium routing unless Criteria 4 matches.
- Response and Recovery CBD outside configured values at impact `0-2` has no route.
- Exact case-sensitive matching is used.

### `resilient_example_script.py`

Status: **Compliant.**

Confirmed:

- Reads all required routing fields from `incident` and `incident.properties`.
- Computes `is_high_impact` from numeric `impact_rating >= 3`.
- Detects CIHT/WMA manual transfer for Criteria 5.
- Evaluates routing rules by descending priority.
- Applies owner, members, workspace, locks, and audit fields.
- Preserves owner when `assignment_owner_locked` is true.
- Still allows member changes while owner is locked.
- Releases `manual_transfer` lock when impact becomes `3-5`.
- Releases `condition_based` lock when the creating rule no longer matches.
- Keeps `manual` and `incident_lifetime` locks until explicit user/admin action clears them.
- Keeps unknown lock types conservative by not releasing them automatically.

### `manual_transfer.py`

Status: **Compliant with the Manual Transfer Ownership design.**

Confirmed:

- Reads `rule.input.lock`.
- Reads target owner from `target_owner`, `owner`, `new_owner`, or `transfer_owner`.
- Reads optional reason/comment from `reason`, `comment`, or `notes`.
- Sets `incident.owner_id` to the selected owner.
- If `lock` is false, clears assignment owner-lock fields.
- If `lock` is true and transfer is specifically between `DISO-CIHT` and `DISO-WMA`, sets `manual_transfer` lock.
- If `lock` is true for any other transfer, sets `manual` lock.
- Updates `assignment_router_last_owner`, `last_assignment_rule_applied`, `assignment_router_status`, and `last_assignment_evaluation_time`.
- Adds an incident note documenting the manual transfer.
- Does not immediately run Assignment Router, preventing unprotected transfers from being instantly overwritten.

## Final recommendation

Implement the five rules/actions listed above.

Do not expose internal assignment lock fields to users. Keep those fields hidden or admin-only in SOAR layouts. Users interact only with:

- **Manual Recalculate Assignment** when they want routing recalculated.
- **Manual Transfer Ownership** when they want to choose an owner and optionally protect that choice from future automatic reassignment.

This gives users practical control without requiring them to understand or modify system-managed routing fields.
