"""
Manual transfer lock script for IBM SOAR / Resilient incident objects.

This script only marks the assignment as manually set so the assignment router
will leave the current owner and members alone.
"""

incident.properties.assignment_owner_lock_type = "manually_set"
