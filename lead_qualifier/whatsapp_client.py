from __future__ import annotations

from collections.abc import Sequence
from typing import Any

import httpx

from lead_qualifier.settings import Settings


class WhatsAppCloudClient:
    def __init__(self, settings: Settings) -> None:
        self._settings = settings

    def _build_endpoint(self) -> str:
        return (
            f"{self._settings.whatsapp_api_base_url}/"
            f"{self._settings.whatsapp_graph_version}/"
            f"{self._settings.whatsapp_phone_number_id}/messages"
        )

    def _headers(self) -> dict[str, str]:
        return {
            "Authorization": f"Bearer {self._settings.whatsapp_access_token}",
            "Content-Type": "application/json",
        }

    def _post_message(self, payload: dict[str, Any]) -> dict[str, Any]:
        response = httpx.post(
            self._build_endpoint(),
            headers=self._headers(),
            json=payload,
            timeout=30.0,
        )
        response.raise_for_status()
        return response.json()

    def send_text_message(self, to: str, body: str, reply_to_message_id: str | None = None) -> dict[str, Any]:
        if not self._settings.whatsapp_access_token:
            raise RuntimeError("WHATSAPP_ACCESS_TOKEN non configurato.")
        if not self._settings.whatsapp_phone_number_id:
            raise RuntimeError("WHATSAPP_PHONE_NUMBER_ID non configurato.")

        payload: dict[str, Any] = {
            "messaging_product": "whatsapp",
            "recipient_type": "individual",
            "to": to,
            "type": "text",
            "text": {
                "body": body,
                "preview_url": False,
            },
        }
        if reply_to_message_id:
            payload["context"] = {"message_id": reply_to_message_id}

        return self._post_message(payload)

    def send_template_message(
        self,
        *,
        to: str,
        template_name: str,
        language_code: str,
        body_parameters: Sequence[str] | None = None,
    ) -> dict[str, Any]:
        if not self._settings.whatsapp_access_token:
            raise RuntimeError("WHATSAPP_ACCESS_TOKEN non configurato.")
        if not self._settings.whatsapp_phone_number_id:
            raise RuntimeError("WHATSAPP_PHONE_NUMBER_ID non configurato.")

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
            "to": to,
            "type": "template",
            "template": template,
        }
        return self._post_message(payload)
