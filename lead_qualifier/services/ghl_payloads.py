from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class GhlLeadPayload:
    raw_payload: dict[str, Any]
    bot_id: str = ""
    location_id: str = ""
    phone: str = ""
    full_name: str = ""
    email: str = ""


def parse_ghl_lead_payload(payload: dict[str, Any]) -> GhlLeadPayload:
    contact = _as_dict(payload.get("contact"))
    location = _as_dict(payload.get("location"))
    custom_data = _as_dict(payload.get("custom_data"))
    custom_data_alt = _as_dict(payload.get("customData"))

    bot_id = _first_non_empty(
        payload.get("bot_id"),
        payload.get("botId"),
        payload.get("qualifier_bot_id"),
        payload.get("qualifierBotId"),
        custom_data.get("bot_id"),
        custom_data.get("qualifier_bot_id"),
        custom_data_alt.get("bot_id"),
        custom_data_alt.get("qualifier_bot_id"),
    )
    location_id = _first_non_empty(
        location.get("id"),
        payload.get("location_id"),
        payload.get("locationId"),
    )
    first_name = _first_non_empty(
        payload.get("first_name"),
        payload.get("firstName"),
        contact.get("first_name"),
        contact.get("firstName"),
    )
    last_name = _first_non_empty(
        payload.get("last_name"),
        payload.get("lastName"),
        contact.get("last_name"),
        contact.get("lastName"),
    )
    full_name = _first_non_empty(
        payload.get("full_name"),
        payload.get("fullName"),
        payload.get("name"),
        contact.get("full_name"),
        contact.get("fullName"),
        contact.get("name"),
        " ".join(part for part in (first_name, last_name) if part).strip(),
    )
    phone = _normalize_phone(
        _first_non_empty(
            payload.get("phone"),
            payload.get("phone_number"),
            payload.get("phoneNumber"),
            contact.get("phone"),
            contact.get("phone_number"),
            contact.get("phoneNumber"),
        )
    )
    email = _first_non_empty(
        payload.get("email"),
        contact.get("email"),
    )

    return GhlLeadPayload(
        raw_payload=payload,
        bot_id=bot_id,
        location_id=location_id,
        phone=phone,
        full_name=full_name,
        email=email,
    )


def _as_dict(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _first_non_empty(*values: object) -> str:
    for value in values:
        cleaned = str(value or "").strip()
        if cleaned:
            return cleaned
    return ""


def _normalize_phone(value: str) -> str:
    cleaned = "".join(ch for ch in str(value or "").strip() if ch.isdigit() or ch == "+")
    if cleaned.startswith("00"):
        return f"+{cleaned[2:]}"
    return cleaned
