"""Append-oriented audit operations used by domain services."""

from .events import (
    record_audit_event,
    record_denied_action,
    record_failed_action,
    record_successful_action,
)

__all__ = [
    "record_audit_event",
    "record_denied_action",
    "record_failed_action",
    "record_successful_action",
]
