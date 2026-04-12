from __future__ import annotations

from typing import Any

import httpx

from lead_qualifier.core.settings import Settings
from lead_qualifier.domain.bot_config import BotConfig
from lead_qualifier.domain.lead import LeadState


class QualifiedLeadWebhookClient:
    def __init__(self, settings: Settings) -> None:
        self._settings = settings

    def is_enabled_for(self, config: BotConfig) -> bool:
        return bool(config.qualified_lead_webhook_url)

    def deliver(
        self,
        *,
        config: BotConfig,
        wa_id: str,
        lead_state: LeadState,
        handoff_note: str,
        contact_name: str,
    ) -> dict[str, Any]:
        target_url = config.qualified_lead_webhook_url.strip()
        if not target_url:
            raise RuntimeError("qualified_lead_webhook_url non configurato per il bot.")

        payload = {
            "bot": {
                "id": config.id,
                "name": config.name,
                "company_name": config.company_name,
                "ghl_location_id": config.ghl_location_id,
            },
            "lead": {
                "full_name": _resolve_full_name(lead_state, contact_name),
                "phone": _normalize_phone(wa_id),
                "email": _resolve_email(config, lead_state),
                "qualification_status": lead_state.qualification_status,
                "summary": lead_state.summary.strip(),
                "handoff_note": handoff_note.strip(),
                "field_values": _build_field_values(config, lead_state),
                "images": _build_image_payloads(lead_state),
            },
        }

        try:
            response = httpx.post(
                target_url,
                json=payload,
                headers={"Content-Type": "application/json"},
                timeout=self._settings.http_timeout_seconds,
            )
        except httpx.HTTPError as exc:
            raise RuntimeError(str(exc)) from exc

        if not response.is_success:
            raise RuntimeError(_format_error_message(response))

        try:
            body: Any = response.json()
        except ValueError:
            body = {"raw": response.text}

        return {
            "status_code": response.status_code,
            "body": body,
        }


def _normalize_phone(wa_id: str) -> str:
    digits = "".join(ch for ch in str(wa_id or "").strip() if ch.isdigit())
    if not digits:
        return ""
    return f"+{digits}"


def _resolve_full_name(lead_state: LeadState, contact_name: str) -> str | None:
    for key in ("nome_completo", "full_name", "nome", "ragione_sociale"):
        value = lead_state.field_values.get(key, "").strip()
        if value:
            return value

    cleaned_contact_name = str(contact_name or "").strip()
    return cleaned_contact_name or None


def _resolve_email(config: BotConfig, lead_state: LeadState) -> str | None:
    for field in config.fields:
        haystack = " ".join((field.key, field.label, field.description)).lower()
        if "mail" not in haystack and "email" not in haystack:
            continue
        value = lead_state.field_values.get(field.key, "").strip()
        if value:
            return value
    return None


def _build_field_values(config: BotConfig, lead_state: LeadState) -> dict[str, str]:
    field_values: dict[str, str] = {}
    for field in config.fields:
        value = lead_state.field_values.get(field.key, "").strip()
        if value:
            field_values[field.key] = value
    return field_values


def _build_image_payloads(lead_state: LeadState) -> list[dict[str, str]]:
    return [
        {
            "message_id": image.message_id,
            "media_id": image.media_id,
            "public_url": image.public_url,
            "mime_type": image.mime_type,
            "caption": image.caption,
            "uploaded_at": image.uploaded_at,
        }
        for image in lead_state.metadata.images
    ]


def _format_error_message(response: httpx.Response) -> str:
    try:
        payload = response.json()
    except ValueError:
        payload = response.text
    return f"Webhook lead qualificato fallito ({response.status_code}): {payload}"
