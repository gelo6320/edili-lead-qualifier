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
    def user_blocks(
        display: str,
        content_blocks: list[dict[str, Any]],
        *,
        images: list[dict[str, str]] | None = None,
    ) -> "StoredMessage":
        payload: dict[str, Any] = {
            "kind": "user_multimodal",
            "content": _strip_cache_control(content_blocks),
        }
        normalized_images = _normalize_message_images(images)
        if normalized_images:
            payload["images"] = normalized_images
        return StoredMessage(
            role="user",
            display=display,
            api_content=json.dumps(payload, ensure_ascii=False),
        )

    @staticmethod
    def assistant(display: str, payload: dict[str, Any]) -> "StoredMessage":
        return StoredMessage(
            role="assistant",
            display=display,
            api_content=json.dumps(payload, ensure_ascii=False),
        )


@dataclass(frozen=True)
class LeadImageAsset:
    message_id: str = ""
    media_id: str = ""
    public_url: str = ""
    storage_path: str = ""
    mime_type: str = ""
    caption: str = ""
    uploaded_at: str = ""

    @classmethod
    def from_payload(cls, payload: dict[str, Any] | None) -> "LeadImageAsset":
        payload = payload or {}
        return cls(
            message_id=str(payload.get("message_id", "")).strip(),
            media_id=str(payload.get("media_id", "")).strip(),
            public_url=str(payload.get("public_url", "")).strip(),
            storage_path=str(payload.get("storage_path", "")).strip(),
            mime_type=str(payload.get("mime_type", "")).strip(),
            caption=str(payload.get("caption", "")).strip(),
            uploaded_at=str(payload.get("uploaded_at", "")).strip(),
        )


@dataclass(frozen=True)
class LeadRuntimeMetadata:
    initial_template_id: str = ""
    initial_template_name: str = ""
    initial_template_language: str = ""
    initial_template_body: str = ""
    initial_template_rendered_text: str = ""
    initial_template_parameters: list[str] = field(default_factory=list)
    images: list[LeadImageAsset] = field(default_factory=list)
    qualified_handoff_sent_at: str = ""
    qualified_handoff_reference: str = ""
    qualified_handoff_note: str = ""
    latest_contact_name: str = ""
    ai_stopped_at: str = ""
    ai_stopped_reason: str = ""
    ai_stopped_by: str = ""

    @classmethod
    def from_payload(cls, payload: dict[str, Any] | None) -> "LeadRuntimeMetadata":
        payload = payload or {}
        return cls(
            initial_template_id=str(payload.get("initial_template_id", "")).strip(),
            initial_template_name=str(payload.get("initial_template_name", "")).strip(),
            initial_template_language=str(payload.get("initial_template_language", "")).strip(),
            initial_template_body=str(payload.get("initial_template_body", "")).strip(),
            initial_template_rendered_text=str(payload.get("initial_template_rendered_text", "")).strip(),
            initial_template_parameters=[
                str(item).strip()
                for item in payload.get("initial_template_parameters", [])
                if str(item).strip()
            ]
            if isinstance(payload.get("initial_template_parameters", []), list)
            else [],
            images=[
                LeadImageAsset.from_payload(item)
                for item in payload.get("images", [])
                if isinstance(item, dict)
            ]
            if isinstance(payload.get("images", []), list)
            else [],
            qualified_handoff_sent_at=str(payload.get("qualified_handoff_sent_at", "")).strip(),
            qualified_handoff_reference=str(payload.get("qualified_handoff_reference", "")).strip(),
            qualified_handoff_note=str(payload.get("qualified_handoff_note", "")).strip(),
            latest_contact_name=str(payload.get("latest_contact_name", "")).strip(),
            ai_stopped_at=str(payload.get("ai_stopped_at", "")).strip(),
            ai_stopped_reason=str(payload.get("ai_stopped_reason", "")).strip(),
            ai_stopped_by=str(payload.get("ai_stopped_by", "")).strip(),
        )

    @property
    def has_initial_template(self) -> bool:
        return bool(
            self.initial_template_id
            or self.initial_template_name
            or self.initial_template_rendered_text
        )

    @property
    def has_qualified_handoff(self) -> bool:
        return bool(self.qualified_handoff_sent_at)

    @property
    def has_images(self) -> bool:
        return bool(self.images)

    @property
    def has_ai_stopped(self) -> bool:
        return bool(self.ai_stopped_at)

    @property
    def image_public_urls(self) -> list[str]:
        return [image.public_url for image in self.images if image.public_url]


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
    image_media_id: str = ""
    image_mime_type: str = ""
    image_caption: str = ""

    @property
    def has_text_or_media(self) -> bool:
        return bool(self.text or self.image_media_id)


def _strip_cache_control(value: Any) -> Any:
    if isinstance(value, list):
        return [_strip_cache_control(item) for item in value]
    if isinstance(value, dict):
        return {
            key: _strip_cache_control(item)
            for key, item in value.items()
            if key != "cache_control"
        }
    return value


def _normalize_message_images(images: list[dict[str, str]] | None) -> list[dict[str, str]]:
    if not images:
        return []

    normalized: list[dict[str, str]] = []
    for image in images:
        if not isinstance(image, dict):
            continue
        url = str(image.get("url", "")).strip()
        if not url:
            continue
        normalized_image = {"url": url}
        mime_type = str(image.get("mime_type", "")).strip()
        caption = str(image.get("caption", "")).strip()
        if mime_type:
            normalized_image["mime_type"] = mime_type
        if caption:
            normalized_image["caption"] = caption
        normalized.append(normalized_image)
    return normalized
