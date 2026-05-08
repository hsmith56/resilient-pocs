"""
Manual Transfer Ownership script for IBM SOAR / Resilient incident objects.

Expected runtime objects injected by SOAR:
- incident
- rule

Expected rule input fields:
- rule.input.lock
    Boolean or Yes/No-style value.
    True/Yes  = protect this transfer from automatic reassignment.
    False/No  = do not protect this transfer; clear existing assignment lock fields.

- rule.input.target_owner, rule.input.owner, or rule.input.new_owner
    The selected owner/group/user to transfer the incident to.
    Configure the rule invocation form to expose one target owner field. The
    script checks several common names so the form label can be friendly.

- rule.input.reason or rule.input.comment, optional
    User/admin reason for audit note.

Behavior:
- Sets incident.owner_id to the selected target owner.
- If lock is true:
    - Uses manual_transfer lock only for transfers between DISO-CIHT and DISO-WMA.
    - Uses manual lock for all other protected transfers.
- If lock is false:
    - Clears existing assignment owner-lock fields.
- Writes an audit note.

This script intentionally does not run Assignment Router immediately. For an
unprotected transfer, immediately running the router could undo the user's owner
selection. Protected transfers are safe for later router runs because the router
respects these lock fields.
"""

from datetime import datetime


OWNER_CIHT = "DISO-CIHT"
OWNER_WMA = "DISO-WMA"
MANUAL_TRANSFER_OWNERS = [OWNER_CIHT, OWNER_WMA]

LOCK_TYPE_MANUAL = "manual"
LOCK_TYPE_MANUAL_TRANSFER = "manual_transfer"

MANUAL_TRANSFER_RULE_NAME = "Criteria 5 - Preserve manual CIHT/WMA transfer"
MANUAL_TRANSFER_ACTION_NAME = "Manual Transfer Ownership"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def utc_now_string():
    """Return an ISO UTC timestamp for SOAR custom datetime/text fields."""
    return datetime.utcnow().isoformat()


def get_property(obj, name, default=None):
    """Safely read an attribute that may not exist in all SOAR orgs/forms."""
    return getattr(obj, name, default)


def set_property(obj, name, value):
    """Safely write an attribute by name."""
    setattr(obj, name, value)


def get_rule_input(name, default=None):
    """Read rule.input.<name> safely."""
    rule_input = get_property(rule, "input", None)

    if rule_input is None:
        return default

    return get_property(rule_input, name, default)


def first_present_rule_input(names, default=None):
    """Return the first non-empty rule input from a list of possible names."""
    for name in names:
        value = get_rule_input(name)

        if value is not None and value != "" and value != []:
            return value

    return default


def normalize_bool(value):
    """Convert common SOAR input values into a boolean."""
    if isinstance(value, bool):
        return value

    if value is None:
        return False

    if isinstance(value, (int, float)):
        return value != 0

    text = str(value).strip().lower()

    return text in ["true", "yes", "y", "1", "on", "lock", "locked", "protect"]


def owner_to_text(owner_value):
    """
    Normalize a selected owner value to the value expected by incident.owner_id.

    In most SOAR script configurations this will already be a string. If the
    platform supplies an object, try common display/id attributes before falling
    back to str(...).
    """
    if owner_value is None:
        return None

    if isinstance(owner_value, str):
        return owner_value

    for attr_name in ["name", "display_name", "principal_name", "email", "id"]:
        attr_value = get_property(owner_value, attr_name, None)

        if attr_value is not None and attr_value != "":
            return str(attr_value)

    return str(owner_value)


def is_ciht_wma_transfer(previous_owner, target_owner):
    """Return True only for explicit transfers between DISO-CIHT and DISO-WMA."""
    return (
        previous_owner in MANUAL_TRANSFER_OWNERS
        and target_owner in MANUAL_TRANSFER_OWNERS
        and previous_owner != target_owner
    )


def clear_owner_lock(properties):
    """Clear assignment owner-lock fields."""
    set_property(properties, "assignment_owner_locked", False)
    set_property(properties, "assignment_owner_lock_type", None)
    set_property(properties, "assignment_owner_lock_rule", None)
    set_property(properties, "assignment_owner_lock_reason", None)
    set_property(properties, "assignment_owner_locked_at", None)


def set_owner_lock(properties, lock_type, lock_rule, lock_reason):
    """Set assignment owner-lock fields."""
    set_property(properties, "assignment_owner_locked", True)
    set_property(properties, "assignment_owner_lock_type", lock_type)
    set_property(properties, "assignment_owner_lock_rule", lock_rule)
    set_property(properties, "assignment_owner_lock_reason", lock_reason)
    set_property(properties, "assignment_owner_locked_at", utc_now_string())


def add_audit_note(previous_owner, target_owner, protect_transfer, lock_type, reason):
    """Write a SOAR note documenting the manual transfer action."""
    note_lines = [
        "Manual Transfer Ownership executed.",
        "Previous owner: {}".format(previous_owner),
        "Target owner: {}".format(target_owner),
        "Protected from automatic reassignment: {}".format(protect_transfer),
        "Lock type set: {}".format(lock_type or "None"),
    ]

    if reason:
        note_lines.append("Reason/comment: {}".format(reason))

    incident.addNote("\n".join(note_lines))


# ---------------------------------------------------------------------------
# Main script body
# ---------------------------------------------------------------------------

properties = incident.properties
previous_owner = incident.owner_id

raw_target_owner = first_present_rule_input(
    ["target_owner", "owner", "new_owner", "transfer_owner"],
    default=None,
)
target_owner = owner_to_text(raw_target_owner)

protect_transfer = normalize_bool(get_rule_input("lock", False))
reason = first_present_rule_input(["reason", "comment", "notes"], default="")

if target_owner is None or target_owner == "":
    incident.properties.assignment_router_status = (
        "Manual transfer failed: no target owner was supplied."
    )
    incident.properties.last_assignment_evaluation_time = utc_now_string()
    incident.addNote(
        "Manual Transfer Ownership failed. No target owner was supplied in the rule input."
    )
else:
    incident.owner_id = target_owner

    lock_type_set = None

    if protect_transfer:
        if is_ciht_wma_transfer(previous_owner, target_owner):
            lock_type_set = LOCK_TYPE_MANUAL_TRANSFER
            set_owner_lock(
                properties=properties,
                lock_type=LOCK_TYPE_MANUAL_TRANSFER,
                lock_rule=MANUAL_TRANSFER_RULE_NAME,
                lock_reason=(
                    "Owner locked after manual transfer between DISO-CIHT and DISO-WMA."
                ),
            )
        else:
            lock_type_set = LOCK_TYPE_MANUAL
            manual_reason = "Manually transferred and protected by user/admin."

            if reason:
                manual_reason = manual_reason + " Reason/comment: " + str(reason)

            set_owner_lock(
                properties=properties,
                lock_type=LOCK_TYPE_MANUAL,
                lock_rule=MANUAL_TRANSFER_ACTION_NAME,
                lock_reason=manual_reason,
            )
    else:
        clear_owner_lock(properties)

    # Keep the router's last-owner memory aligned with this explicit manual
    # action. This helps avoid stale Criteria 5 detection after unprotected
    # transfers and gives future router runs an accurate current owner snapshot.
    set_property(properties, "assignment_router_last_owner", target_owner)

    set_property(properties, "last_assignment_rule_applied", MANUAL_TRANSFER_ACTION_NAME)
    set_property(
        properties,
        "assignment_router_status",
        "Manual transfer ownership completed. Protection enabled: {}.".format(
            protect_transfer
        ),
    )
    set_property(properties, "last_assignment_evaluation_time", utc_now_string())

    add_audit_note(
        previous_owner=previous_owner,
        target_owner=target_owner,
        protect_transfer=protect_transfer,
        lock_type=lock_type_set,
        reason=reason,
    )
