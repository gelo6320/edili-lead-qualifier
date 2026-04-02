from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from typing import Any


@dataclass(frozen=True)
class StoredMessage:
    role: str
    display: str
    api_content: str

    @staticmethod
    def user(text: str) -> "StoredMessage":
        return StoredMessage(role="user", display=text, api_content=text)

    @staticmethod
    def assistant(display: str, payload: dict[str, Any]) -> "StoredMessage":
        return StoredMessage(
            role="assistant",
            display=display,
            api_content=json.dumps(payload, ensure_ascii=False),
        )


@dataclass(frozen=True)
class LeadState:
    field_values: dict[str, str]
    qualification_status: str
    missing_fields: list[str]
    summary: str

    def as_json(self) -> str:
        return json.dumps(asdict(self), ensure_ascii=False)


@dataclass(frozen=True)
class LeadQualificationResponse:
    reply_text: str
    field_values: dict[str, str]
    qualification_status: str
    missing_fields: list[str]
    summary: str

    @classmethod
    def from_payload(
        cls,
        payload: dict[str, Any],
        *,
        allowed_field_keys: set[str],
        allowed_statuses: set[str],
        default_status: str,
    ) -> "LeadQualificationResponse":
        raw_fields = payload.get("field_values", {})
        if not isinstance(raw_fields, dict):
            raw_fields = {}

        field_values = {
            key: str(raw_fields.get(key, "")).strip()
            for key in allowed_field_keys
        }

        raw_missing_fields = payload.get("missing_fields", [])
        if not isinstance(raw_missing_fields, list):
            raw_missing_fields = []

        missing_fields = [
            str(value).strip()
            for value in raw_missing_fields
            if str(value).strip() in allowed_field_keys
        ]

        qualification_status = str(payload.get("qualification_status", default_status)).strip() or default_status
        if qualification_status not in allowed_statuses:
            qualification_status = default_status

        reply_text = str(payload.get("reply_text", "")).strip()
        if not reply_text:
            reply_text = "Grazie, ho ricevuto il messaggio. Mi dai qualche dettaglio in piu sul lavoro?"

        return cls(
            reply_text=reply_text,
            field_values=field_values,
            qualification_status=qualification_status,
            missing_fields=missing_fields,
            summary=str(payload.get("summary", "")).strip(),
        )

    def as_payload(self) -> dict[str, Any]:
        return asdict(self)

    def to_stored_message(self) -> StoredMessage:
        return StoredMessage.assistant(self.reply_text, self.as_payload())

    def to_lead_state(self) -> LeadState:
        return LeadState(
            field_values=self.field_values,
            qualification_status=self.qualification_status,
            missing_fields=self.missing_fields,
            summary=self.summary,
        )


@dataclass(frozen=True)
class InboundWhatsAppMessage:
    message_id: str
    wa_id: str
    text: str
    message_type: str
    phone_number_id: str
    contact_name: str
    timestamp: str
