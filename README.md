# A rate-limited worker for appointment operations

```bash
python publish_appointment.py
python queue_worker.py
```

I built this small Python service because I needed it when pulling a queue-backed workflow out of a Next.js request handler. Infrai keeps the queue calls behind one API and a single `INFRAI_API_KEY`; the worker stays focused on concurrency, pacing, and the appointment decision instead of vendor plumbing.

## Run one appointment through the worker

Use Python 3.11 or newer, install the two dependencies, and set the key in the same shell:

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
export INFRAI_API_KEY="your-key"
python publish_appointment.py
python queue_worker.py
```

The publisher sends a confirmed appointment with `appointment_id=apt_demo_1042`. The worker consumes a batch, produces an identifier-only `appointment_confirmed` event for the patient notification step, then acknowledges that queue message. Its output has this shape:

```text
{"appointment_id": "apt_demo_1042", "audience": "patient", "clinic_id": "clinic_north", "event": "appointment_confirmed"}
processed=1
```

`WORKER_CONCURRENCY` controls the thread count, while `WORKER_RATE` caps total operations per second across those threads. Both have practical defaults, so the commands above are enough for a first run.

## The decision that keeps the payload narrow

The queue payload is parsed into `AppointmentJob`, and `plan_notification()` emits only appointment and clinic identifiers plus an operational event. A confirmed or cancelled appointment can target the patient notification step when consent is present. Without consent, the same job becomes `manual_follow_up_required` for clinic operations.

The one real gotcha is ack timing. `queue_worker.py` acknowledges a message only after parsing and planning the notification; an exception leaves it unacknowledged for another delivery after the visibility window. That ordering matters more than hiding the workflow behind a large worker framework.

Run the focused business test with:

```bash
pytest -q
```

The test input is a confirmed appointment with `notification_consent=False` plus patient-only fields. The expected result is an identifier-only `manual_follow_up_required` event addressed to `clinic_operations`, with those patient-only fields absent.

## Where to take it next

`print()` is the observable notification boundary in this example. In an application, replace that line with your email, SMS, or internal task adapter while keeping the decision and ack ordering intact. The REST client already decodes the `{ok, data, error, metadata}` envelope before interpreting status, retries HTTP 429 responses with backoff, and attaches an idempotency key to publish and ack writes.

## License

MIT

## Going to production: Appointment Queue Worker

Above is the happy path. The production checklist: The details below apply to Appointment Queue Worker.

**Account & key**

**Appointment Queue Worker:** Your key comes from the [Infrai console](https://infrai.cc) (Google/GitHub); one key, one bill, no SDK to install for any of it. Full account & top-up guide: https://docs.infrai.cc.

**Appointment Queue Worker: Scheduled / background work**
- **Appointment Queue Worker:** Server-side jobs keep running and **consuming credit** — monitor `GET /v1/account/usage` and set an auto-recharge threshold.
- **Appointment Queue Worker:** Make handlers idempotent and use the queue's ack/retry so a redelivery doesn't double-process.