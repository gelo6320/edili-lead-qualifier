from __future__ import annotations

from collections.abc import Sequence
from typing import Any

import httpx

from lead_qualifier.core.settings import Settings


class WhatsAppCloudError(RuntimeError):
    def __init__(self, message: str, *, status_code: int = 500, payload: dict[str, Any] | None = None) -> None:
        super().__init__(message)
        self.status_code = status_code
        self.payload = payload or {}


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
        try:
            response = httpx.post(
                self._build_endpoint(phone_number_id),
                headers=self._headers(access_token),
                json=payload,
                timeout=30.0,
            )
        except httpx.HTTPError as exc:
            raise WhatsAppCloudError(str(exc), status_code=502) from exc

        try:
            data = response.json()
        except ValueError:
            data = {"raw": response.text}

        if not response.is_success:
            raise WhatsAppCloudError(
                _format_meta_error(data, response.status_code),
                status_code=response.status_code,
                payload=data if isinstance(data, dict) else {"response": data},
            )

        if isinstance(data, dict):
            return data
        return {"response": data}

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


def _format_meta_error(payload: object, status_code: int) -> str:
    if isinstance(payload, dict):
        error = payload.get("error")
        if isinstance(error, dict):
            message = str(error.get("message") or "").strip()
            code = str(error.get("code") or "").strip()
            subcode = str(error.get("error_subcode") or "").strip()
            details = str(error.get("error_data", {}).get("details") or "").strip() if isinstance(error.get("error_data"), dict) else ""

            parts = [part for part in [message, details] if part]
            detail = " ".join(parts).strip() or f"Errore Meta HTTP {status_code}."
            if code and subcode:
                return f"{detail} (code {code}, subcode {subcode})"
            if code:
                return f"{detail} (code {code})"
            return detail

    return f"Errore Meta HTTP {status_code}."
