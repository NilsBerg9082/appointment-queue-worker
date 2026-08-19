"""Appointment job validation and patient-safe notification decisions."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Literal, Mapping


AppointmentState = Literal["requested", "confirmed", "cancelled"]
NotificationAudience = Literal["patient", "clinic_operations"]


@dataclass(frozen=True)
class AppointmentJob:
    appointment_id: str
    clinic_id: str
    state: AppointmentState
    notification_consent: bool

    @classmethod
    def from_payload(cls, payload: Mapping[str, Any]) -> "AppointmentJob":
        state = payload.get("state")
        if state not in {"requested", "confirmed", "cancelled"}:
            raise ValueError("state must be requested, confirmed, or cancelled")
        return cls(
            appointment_id=str(payload["appointment_id"]),
            clinic_id=str(payload["clinic_id"]),
            state=state,
            notification_consent=bool(payload["notification_consent"]),
        )


@dataclass(frozen=True)
class OperationalNotification:
    appointment_id: str
    clinic_id: str
    event: str
    audience: NotificationAudience


def plan_notification(job: AppointmentJob) -> OperationalNotification:
    """Return an identifier-only event suitable for the next notification step."""
    if not job.notification_consent:
        return OperationalNotification(
            appointment_id=job.appointment_id,
            clinic_id=job.clinic_id,
            event="manual_follow_up_required",
            audience="clinic_operations",
        )

    events = {
        "requested": "appointment_request_received",
        "confirmed": "appointment_confirmed",
        "cancelled": "appointment_cancelled",
    }
    return OperationalNotification(
        appointment_id=job.appointment_id,
        clinic_id=job.clinic_id,
        event=events[job.state],
        audience="patient",
    )
