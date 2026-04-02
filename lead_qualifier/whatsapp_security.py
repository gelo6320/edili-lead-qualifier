from __future__ import annotations

import hashlib
import hmac


def is_valid_meta_signature(app_secret: str, raw_body: bytes, signature_header: str | None) -> bool:
    if not app_secret:
        return False
    if not signature_header:
        return False
    if not signature_header.startswith("sha256="):
        return False

    expected_signature = hmac.new(
        app_secret.encode("utf-8"),
        raw_body,
        hashlib.sha256,
    ).hexdigest()
    received_signature = signature_header.removeprefix("sha256=").strip()
    return hmac.compare_digest(expected_signature, received_signature)
