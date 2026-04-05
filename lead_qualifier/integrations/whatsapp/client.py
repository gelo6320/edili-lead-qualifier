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


def _parse_json(response: httpx.Response) -> Any:
    try:
        return response.json()
    except ValueError:
        return {"raw": response.text}


def _raise_for_error(response: httpx.Response, data: Any) -> None:
    if response.is_success:
        return
    raise WhatsAppCloudError(
        _format_meta_error(data, response.status_code),
        status_code=response.status_code,
        payload=data if isinstance(data, dict) else {"response": data},
    )


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

    def _build_media_endpoint(self, media_id: str) -> str:
        return (
            f"{self._settings.whatsapp_api_base_url}/"
            f"{self._settings.whatsapp_graph_version}/"
            f"{media_id}"
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
                timeout=self._settings.http_timeout_seconds,
            )
        except httpx.HTTPError as exc:
            raise WhatsAppCloudError(str(exc), status_code=502) from exc

        data = _parse_json(response)
        _raise_for_error(response, data)

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

    def get_media_metadata(
        self,
        *,
        media_id: str,
        access_token: str | None = None,
    ) -> dict[str, Any]:
        if not (access_token or self._settings.whatsapp_access_token):
            raise RuntimeError("Token WhatsApp non configurato.")
        cleaned_media_id = str(media_id or "").strip()
        if not cleaned_media_id:
            raise RuntimeError("media_id non valido.")

        try:
            response = httpx.get(
                self._build_media_endpoint(cleaned_media_id),
                headers=self._headers(access_token),
                timeout=self._settings.http_timeout_seconds,
            )
        except httpx.HTTPError as exc:
            raise WhatsAppCloudError(str(exc), status_code=502) from exc

        data = _parse_json(response)
        _raise_for_error(response, data)
        if not isinstance(data, dict):
            raise WhatsAppCloudError("Risposta media Meta non valida.", status_code=502)
        return data

    def download_media(
        self,
        *,
        media_url: str,
        access_token: str | None = None,
    ) -> tuple[bytes, str]:
        if not (access_token or self._settings.whatsapp_access_token):
            raise RuntimeError("Token WhatsApp non configurato.")
        cleaned_url = str(media_url or "").strip()
        if not cleaned_url:
            raise RuntimeError("media_url non valida.")

        try:
            response = httpx.get(
                cleaned_url,
                headers=self._headers(access_token),
                timeout=self._settings.http_timeout_seconds,
            )
        except httpx.HTTPError as exc:
            raise WhatsAppCloudError(str(exc), status_code=502) from exc

        if not response.is_success:
            data = _parse_json(response)
            raise WhatsAppCloudError(
                _format_meta_error(data, response.status_code),
                status_code=response.status_code,
                payload=data if isinstance(data, dict) else {"response": data},
            )

        return response.content, str(response.headers.get("Content-Type") or "").strip()

    def list_message_templates(
        self,
        *,
        waba_id: str,
        access_token: str | None = None,
    ) -> list[dict[str, Any]]:
        if not (access_token or self._settings.whatsapp_access_token):
            raise RuntimeError("Token WhatsApp non configurato.")
        cleaned_waba_id = str(waba_id or "").strip()
        if not cleaned_waba_id:
            raise RuntimeError("waba_id non valido.")

        url = (
            f"{self._settings.whatsapp_api_base_url}/"
            f"{self._settings.whatsapp_graph_version}/"
            f"{cleaned_waba_id}/message_templates"
        )
        params: dict[str, Any] | None = {
            "fields": "id,name,language,status,category,components",
            "limit": 200,
        }
        templates: list[dict[str, Any]] = []

        while url:
            try:
                response = httpx.get(
                    url,
                    headers=self._headers(access_token),
                    params=params,
                    timeout=self._settings.http_timeout_seconds,
                )
            except httpx.HTTPError as exc:
                raise WhatsAppCloudError(str(exc), status_code=502) from exc

            data = _parse_json(response)
            _raise_for_error(response, data)
            if not isinstance(data, dict):
                raise WhatsAppCloudError("Risposta template Meta non valida.", status_code=502)

            for item in data.get("data", []):
                if not isinstance(item, dict):
                    continue
                templates.append(
                    {
                        "id": _clean(item.get("id")),
                        "name": _clean(item.get("name")),
                        "language": _clean(item.get("language")) or "it",
                        "status": _clean(item.get("status")).upper(),
                        "category": _clean(item.get("category")),
                        "body_text": _extract_template_body_text(item.get("components")),
                        "body_variable_count": _infer_template_variable_count(item.get("components")),
                    }
                )

            next_url = data.get("paging", {}).get("next")
            url = str(next_url or "").strip()
            params = None

        return templates


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


def _clean(value: object) -> str:
    return str(value or "").strip()


def _extract_template_body_text(components: object) -> str:
    if not isinstance(components, list):
        return ""
    for component in components:
        if not isinstance(component, dict):
            continue
        if _clean(component.get("type")).upper() != "BODY":
            continue
        return _clean(component.get("text"))
    return ""


def _infer_template_variable_count(components: object) -> int:
    body_text = _extract_template_body_text(components)
    if not body_text:
        return 0

    max_placeholder = 0
    cursor = 0
    while cursor < len(body_text):
        start = body_text.find("{{", cursor)
        if start < 0:
            break
        end = body_text.find("}}", start + 2)
        if end < 0:
            break
        token = body_text[start + 2 : end].strip()
        if token.isdigit():
            max_placeholder = max(max_placeholder, int(token))
        cursor = end + 2
    return max_placeholder
