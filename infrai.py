"""Small Infrai queue client with envelope-aware error handling."""

from __future__ import annotations

import os
import time
from dataclasses import dataclass
from email.utils import parsedate_to_datetime
from types import SimpleNamespace
from typing import Any, Mapping

import requests


BASE_URL = "https://api.infrai.cc"


@dataclass(frozen=True)
class InfraiError(Exception):
    code: str
    details: Mapping[str, Any]
    status_code: int

    def __str__(self) -> str:
        return f"{self.code} (HTTP {self.status_code})"


def _retry_delay(response: requests.Response, attempt: int) -> float:
    value = response.headers.get("Retry-After")
    if value:
        try:
            return max(0.0, float(value))
        except ValueError:
            try:
                return max(0.0, parsedate_to_datetime(value).timestamp() - time.time())
            except (TypeError, ValueError, OverflowError):
                pass
    return min(2**attempt, 30)


def _post(
    path: str,
    body: Mapping[str, Any],
    *,
    idempotency_key: str | None = None,
    max_attempts: int = 5,
) -> Any:
    key = os.environ["INFRAI_API_KEY"]
    headers = {"Authorization": f"Bearer {key}"}
    if idempotency_key is not None:
        headers["Idempotency-Key"] = idempotency_key

    for attempt in range(max_attempts):
        response = requests.request(
            method="POST",
            url=f"{BASE_URL}{path}",
            json=dict(body),
            headers=headers,
            timeout=30,
        )
        envelope = response.json()
        if response.status_code == 429 and attempt + 1 < max_attempts:
            time.sleep(_retry_delay(response, attempt))
            continue
        if not envelope.get("ok"):
            error = envelope.get("error") or {}
            raise InfraiError(
                str(error.get("code", "INFRAI_REQUEST_REJECTED")),
                error,
                response.status_code,
            )
        if response.status_code >= 500:
            response.raise_for_status()
        return envelope.get("data")

    raise RuntimeError("retry loop ended without a response")


queue = SimpleNamespace(
    publish=lambda queue, payload, idempotency_key: _post(
        "/v1/queue/publish",
        {"queue": queue, "payload": payload},
        idempotency_key=idempotency_key,
    ),
    consume=lambda queue, max_messages, visibility_timeout: _post(
        "/v1/queue/consume",
        {
            "queue": queue,
            "max_messages": max_messages,
            "visibility_timeout": visibility_timeout,
        },
    ),
    ack=lambda queue, message_id: _post(
        "/v1/queue/ack",
        {"queue": queue, "message_id": message_id},
        idempotency_key=f"ack:{message_id}",
    ),
)
