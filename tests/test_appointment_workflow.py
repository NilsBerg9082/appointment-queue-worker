from dataclasses import asdict

from appointment_workflow import AppointmentJob, plan_notification


def test_without_consent_routes_an_identifier_only_event_to_clinic_operations() -> None:
    payload = {
        "appointment_id": "apt_1042",
        "clinic_id": "clinic_north",
        "state": "confirmed",
        "notification_consent": False,
        "patient_name": "Data that must not be forwarded",
        "reason_for_visit": "Data that must not be forwarded",
    }

    notification = plan_notification(AppointmentJob.from_payload(payload))

    assert asdict(notification) == {
        "appointment_id": "apt_1042",
        "clinic_id": "clinic_north",
        "event": "manual_follow_up_required",
        "audience": "clinic_operations",
    }
    assert "patient_name" not in asdict(notification)
    assert "reason_for_visit" not in asdict(notification)
