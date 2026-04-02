from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from typing import Any

ALLOWED_MISSING_FIELDS = {
    "zona_lavoro",
    "tipo_lavoro",
    "tempistica",
    "budget_indicativo",
    "disponibile_chiamata",
}
ALLOWED_AVAILABILITY = {"si", "no", "forse", "sconosciuto"}
ALLOWED_QUALIFICATION_STATUS = {"nuovo", "in_qualifica", "qualificato", "da_richiamare"}


@dataclass(frozen=True)
class StoredMessage:
    role: str
    display: str
    api_content: str

    @staticmethod
    def user(text: str) -> "StoredMessage":
        return StoredMessage(role="user", display=text, api_content=text)


@dataclass(frozen=True)
class LeadState:
    zona_lavoro: str
    tipo_lavoro: str
    tempistica: str
    budget_indicativo: str
    disponibile_chiamata: str
    disponibile_sopralluogo: str
    stato_qualifica: str
    missing_fields: list[str]
    summary: str

    @staticmethod
    def empty() -> "LeadState":
        return LeadState(
            zona_lavoro="",
            tipo_lavoro="",
            tempistica="",
            budget_indicativo="",
            disponibile_chiamata="sconosciuto",
            disponibile_sopralluogo="sconosciuto",
            stato_qualifica="nuovo",
            missing_fields=[
                "zona_lavoro",
                "tipo_lavoro",
                "tempistica",
                "budget_indicativo",
                "disponibile_chiamata",
            ],
            summary="",
        )

    def as_json(self) -> str:
        return json.dumps(asdict(self), ensure_ascii=False)


@dataclass(frozen=True)
class LeadQualificationResponse:
    reply_text: str
    zona_lavoro: str
    tipo_lavoro: str
    tempistica: str
    budget_indicativo: str
    disponibile_chiamata: str
    disponibile_sopralluogo: str
    stato_qualifica: str
    missing_fields: list[str]
    summary: str

    @classmethod
    def from_payload(cls, payload: dict[str, Any]) -> "LeadQualificationResponse":
        missing_fields = payload.get("missing_fields", [])
        if not isinstance(missing_fields, list):
            missing_fields = []
        normalized_missing_fields = [
            str(value).strip()
            for value in missing_fields
            if str(value).strip() in ALLOWED_MISSING_FIELDS
        ]

        disponibile_chiamata = str(payload.get("disponibile_chiamata", "sconosciuto")).strip() or "sconosciuto"
        if disponibile_chiamata not in ALLOWED_AVAILABILITY:
            disponibile_chiamata = "sconosciuto"

        disponibile_sopralluogo = str(payload.get("disponibile_sopralluogo", "sconosciuto")).strip() or "sconosciuto"
        if disponibile_sopralluogo not in ALLOWED_AVAILABILITY:
            disponibile_sopralluogo = "sconosciuto"

        stato_qualifica = str(payload.get("stato_qualifica", "in_qualifica")).strip() or "in_qualifica"
        if stato_qualifica not in ALLOWED_QUALIFICATION_STATUS:
            stato_qualifica = "in_qualifica"

        reply_text = str(payload.get("reply_text", "")).strip()
        if not reply_text:
            reply_text = "Grazie, ho ricevuto il messaggio. Mi dai qualche dettaglio in piu sul lavoro?"

        return cls(
            reply_text=reply_text,
            zona_lavoro=str(payload.get("zona_lavoro", "")).strip(),
            tipo_lavoro=str(payload.get("tipo_lavoro", "")).strip(),
            tempistica=str(payload.get("tempistica", "")).strip(),
            budget_indicativo=str(payload.get("budget_indicativo", "")).strip(),
            disponibile_chiamata=disponibile_chiamata,
            disponibile_sopralluogo=disponibile_sopralluogo,
            stato_qualifica=stato_qualifica,
            missing_fields=normalized_missing_fields,
            summary=str(payload.get("summary", "")).strip(),
        )

    def as_payload(self) -> dict[str, Any]:
        return asdict(self)

    def to_stored_message(self) -> StoredMessage:
        return StoredMessage(
            role="assistant",
            display=self.reply_text,
            api_content=json.dumps(self.as_payload(), ensure_ascii=False),
        )

    def to_lead_state(self) -> LeadState:
        return LeadState(
            zona_lavoro=self.zona_lavoro,
            tipo_lavoro=self.tipo_lavoro,
            tempistica=self.tempistica,
            budget_indicativo=self.budget_indicativo,
            disponibile_chiamata=self.disponibile_chiamata,
            disponibile_sopralluogo=self.disponibile_sopralluogo,
            stato_qualifica=self.stato_qualifica,
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
