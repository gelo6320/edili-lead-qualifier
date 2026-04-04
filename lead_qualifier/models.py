from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
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
class LeadRuntimeMetadata:
    initial_template_name: str = ""
    initial_template_language: str = ""
    initial_template_parameters: list[str] = field(default_factory=list)
    lead_manager_forwarded_at: str = ""
    lead_manager_reference: str = ""
    lead_manager_note: str = ""
    latest_contact_name: str = ""

    @classmethod
    def from_payload(cls, payload: dict[str, Any] | None) -> "LeadRuntimeMetadata":
        payload = payload or {}
        return cls(
            initial_template_name=str(payload.get("initial_template_name", "")).strip(),
            initial_template_language=str(payload.get("initial_template_language", "")).strip(),
            initial_template_parameters=[
                str(item).strip()
                for item in payload.get("initial_template_parameters", [])
                if str(item).strip()
            ]
            if isinstance(payload.get("initial_template_parameters", []), list)
            else [],
            lead_manager_forwarded_at=str(payload.get("lead_manager_forwarded_at", "")).strip(),
            lead_manager_reference=str(payload.get("lead_manager_reference", "")).strip(),
            lead_manager_note=str(payload.get("lead_manager_note", "")).strip(),
            latest_contact_name=str(payload.get("latest_contact_name", "")).strip(),
        )

    @property
    def has_initial_template(self) -> bool:
        return bool(self.initial_template_name)

    @property
    def is_forwarded_to_lead_manager(self) -> bool:
        return bool(self.lead_manager_forwarded_at)


@dataclass(frozen=True)
class LeadState:
    field_values: dict[str, str]
    qualification_status: str
    missing_fields: list[str]
    summary: str
    metadata: LeadRuntimeMetadata = field(default_factory=LeadRuntimeMetadata)

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
        allowed_field_keys: list[str],
        required_field_keys: list[str],
        allowed_statuses: set[str],
        default_status: str,
        existing_field_values: dict[str, str] | None = None,
    ) -> "LeadQualificationResponse":
        existing_field_values = existing_field_values or {}
        raw_fields = payload.get("field_values", {})
        if not isinstance(raw_fields, dict):
            raw_fields = {}

        field_values = {
            key: str(raw_fields.get(key, "")).strip() or str(existing_field_values.get(key, "")).strip()
            for key in allowed_field_keys
        }

        missing_fields = [
            key
            for key in required_field_keys
            if not field_values.get(key, "").strip()
        ]

        qualification_status = str(payload.get("qualification_status", default_status)).strip() or default_status
        if qualification_status not in allowed_statuses:
            qualification_status = default_status
        if missing_fields and qualification_status == "qualified":
            qualification_status = "in_progress" if "in_progress" in allowed_statuses else default_status

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

    def to_lead_state(self, metadata: LeadRuntimeMetadata | None = None) -> LeadState:
        return LeadState(
            field_values=self.field_values,
            qualification_status=self.qualification_status,
            missing_fields=self.missing_fields,
            summary=self.summary,
            metadata=metadata or LeadRuntimeMetadata(),
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
