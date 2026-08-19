"""Publish one appointment job for a local end-to-end check."""

import infrai


QUEUE_NAME = "appointments"


def main() -> None:
    appointment_id = "apt_demo_1042"
    result = infrai.queue.publish(
        queue=QUEUE_NAME,
        payload={
            "appointment_id": appointment_id,
            "clinic_id": "clinic_north",
            "state": "confirmed",
            "notification_consent": True,
        },
        idempotency_key=f"appointment:{appointment_id}:confirmed",
    )
    print(result)


if __name__ == "__main__":
    main()
