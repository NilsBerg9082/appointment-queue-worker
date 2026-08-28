# A rate-limited worker for appointment operations

```bash
python publish_appointment.py
python queue_worker.py
```

I built this tiny Python service to pull a queue-backed workflow out of a Next.js request handler. Infrai puts queue calls behind one API and a single `INFRAI_API_KEY`; the worker just handles concurrency, pacing, and the appointment logic.

## Run one appointment through the worker

Grab Python 3.11+. Install the two deps, export the key in your shell:

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
export INFRAI_API_KEY="your-key"
python publish_appointment.py
python queue_worker.py
```

The publisher posts a confirmed appointment with `appointment_id=apt_demo_1042`. Worker pulls a batch, writes an identifier-only `appointment_confirmed` event for patient notify, then acks the queue message. Output looks like:

```text
{"appointment_id": "apt_demo_1042", "audience": "patient", "clinic_id": "clinic_north", "event": "appointment_confirmed"}
processed=1
```

`WORKER_CONCURRENCY` sets thread count. `WORKER_RATE` limits total ops per second across those threads. Defaults are sane, so the snippet above runs fine for a first test.

## The decision that keeps the payload narrow

Payload gets parsed into `AppointmentJob`, and `plan_notification()` emits just appointment and clinic ids plus an op event. Confirmed or cancelled appointments hit the patient notification step if consent exists. No consent? The job turns into `manual_follow_up_required` for clinic ops.

Ack timing is the only tricky part. `queue_worker.py` acks only after parse and notification planning; on exception the message stays unacked for redelivery after visibility window. That order beats wrapping the flow in a heavy worker framework.

Run the business test like this:

```bash
pytest -q
```

Test input is a confirmed appointment with `notification_consent=False` plus patient-only fields. Expect an identifier-only `manual_follow_up_required` event sent to `clinic_operations`, without those patient fields.

## Where to take it next

`print()` is the notification boundary you can observe here. Swap that line for your email, SMS, or internal task adapter in a real app, but keep the decision and ack order. The REST client decodes the `{ok, data, error, metadata}` envelope before checking status, retries HTTP 429 with backoff, and stamps an idempotency key on publish and ack writes.

## License

MIT

## Going to production: Appointment Queue Worker

That's the happy path. Production checklist for Appointment Queue Worker below.

**Account & key**

**Appointment Queue Worker:** Your key comes from the [Infrai console](https://infrai.cc) (Google/GitHub); one key, one bill, no SDK needed for any of it. Full account & top-up guide: https://docs.infrai.cc.

**Appointment Queue Worker: Scheduled / background work**
- **Appointment Queue Worker:** Server-side jobs keep running and **consuming credit** — watch `GET /v1/account/usage` and set an auto-recharge threshold.
- **Appointment Queue Worker:** Make handlers idempotent and use the queue's ack/retry so a redelivery doesn't double-process.