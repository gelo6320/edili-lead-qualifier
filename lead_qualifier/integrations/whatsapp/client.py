from __future__ import annotations

from collections.abc import Sequence
from typing import Any

import httpx

from lead_qualifier.core.settings import Settings


class WhatsAppCloudClient:
    def __init__(self, settings: Settings) -> None:
        self._settings = settings

    @staticmethod
    def _normalize_recipient(to: str) -> str:
        return "".join(ch for ch in str(to or "").strip() if ch.isdigit())

    def _build_endpoint(self, phone_number_id: str) -> str:
        return (
            f"{self._settings.whatsapp_api_base_url}/"
            f"{self._settings.whatsapp_graph_version}/"
            f"{phone_number_id}/messages"
        )

    def _headers(self, access_token: str | None = None) -> dict[str, str]:
        resolved_token = (access_token or self._settings.whatsapp_access_token).strip()
        return {
            "Authorization": f"Bearer {resolved_token}",
            "Content-Type": "application/json",
        }

    def _post_message(
        self,
        phone_number_id: str,
        payload: dict[str, Any],
        *,
        access_token: str | None = None,
    ) -> dict[str, Any]:
        response = httpx.post(
            self._build_endpoint(phone_number_id),
            headers=self._headers(access_token),
            json=payload,
            timeout=30.0,
        )
        response.raise_for_status()
        return response.json()

    def send_text_message(
        self,
        *,
        to: str,
        body: str,
        phone_number_id: str,
        reply_to_message_id: str | None = None,
        access_token: str | None = None,
    ) -> dict[str, Any]:
        if not (access_token or self._settings.whatsapp_access_token):
            raise RuntimeError("Token WhatsApp non configurato.")
        if not phone_number_id:
            raise RuntimeError("phone_number_id non configurato per il bot.")

        normalized_to = self._normalize_recipient(to)
        if not normalized_to:
            raise RuntimeError("Numero destinatario non valido.")

        payload: dict[str, Any] = {
            "messaging_product": "whatsapp",
            "recipient_type": "individual",
            "to": normalized_to,
            "type": "text",
            "text": {
                "body": body,
                "preview_url": False,
            },
        }
        if reply_to_message_id:
            payload["context"] = {"message_id": reply_to_message_id}

        return self._post_message(phone_number_id, payload, access_token=access_token)

    def send_template_message(
        self,
        *,
        to: str,
        phone_number_id: str,
        template_name: str,
        language_code: str,
        body_parameters: Sequence[str] | None = None,
        access_token: str | None = None,
    ) -> dict[str, Any]:
        if not (access_token or self._settings.whatsapp_access_token):
            raise RuntimeError("Token WhatsApp non configurato.")
        if not phone_number_id:
            raise RuntimeError("phone_number_id non configurato per il bot.")

        normalized_to = self._normalize_recipient(to)
        if not normalized_to:
            raise RuntimeError("Numero destinatario non valido.")

        normalized_parameters = [str(value).strip() for value in (body_parameters or []) if str(value).strip()]
        template: dict[str, Any] = {
            "name": template_name.strip(),
            "language": {"code": language_code.strip()},
        }
        if normalized_parameters:
            template["components"] = [
                {
                    "type": "body",
                    "parameters": [
                        {"type": "text", "text": parameter}
                        for parameter in normalized_parameters
                    ],
                }
            ]

        payload: dict[str, Any] = {
            "messaging_product": "whatsapp",
            "recipient_type": "individual",
            "to": normalized_to,
            "type": "template",
            "template": template,
        }
        return self._post_message(phone_number_id, payload, access_token=access_token)
