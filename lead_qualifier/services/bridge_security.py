from __future__ import annotations

import hashlib
import hmac
import time


BRIDGE_MAX_SKEW_SECONDS = 300


def build_bridge_signature(secret: str, timestamp: str, body: str) -> str:
    return hmac.new(
        secret.encode("utf-8"),
        f"{timestamp}.{body}".encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()


def verify_bridge_signature(
    *,
    secret: str,
    timestamp: str,
    body: str,
    provided_signature: str,
) -> bool:
    try:
        timestamp_int = int(timestamp)
    except (TypeError, ValueError):
        return False

    if abs(int(time.time()) - timestamp_int) > BRIDGE_MAX_SKEW_SECONDS:
        return False

    expected_signature = build_bridge_signature(secret, timestamp, body)
    return hmac.compare_digest(expected_signature, str(provided_signature or "").strip())
