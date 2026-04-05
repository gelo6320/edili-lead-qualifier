from __future__ import annotations

from collections.abc import Sequence
from typing import Any

import httpx

from lead_qualifier.core.settings import Settings


class WhatsAppCloudError(RuntimeError):
    def __init__(
        self,
        message: str,
        *,
        status_code: int = 500,
        payload: dict[str, Any] | None = None,
        error_code: str = "",
        error_subcode: str = "",
        error_type: str = "",
        classification: str = "unknown",
        retryable: bool = False,
    ) -> None:
        super().__init__(message)
        self.status_code = status_code
        self.payload = payload or {}
        self.error_code = error_code
        self.error_subcode = error_subcode
        self.error_type = error_type
        self.classification = classification
        self.retryable = retryable


def _parse_json(response: httpx.Response) -> Any:
    try:
        return response.json()
    except ValueError:
        return {"raw": response.text}


def _raise_for_error(response: httpx.Response, data: Any) -> None:
    if response.is_success:
        return
    meta_error = _extract_meta_error_info(data, response.status_code)
    raise WhatsAppCloudError(
        meta_error["message"],
        status_code=response.status_code,
        payload=data if isinstance(data, dict) else {"response": data},
        error_code=meta_error["error_code"],
        error_subcode=meta_error["error_subcode"],
        error_type=meta_error["error_type"],
        classification=meta_error["classification"],
        retryable=meta_error["retryable"],
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
        if len(normalized_to) < 6 or len(normalized_to) > 15:
            raise RuntimeError(
                "Numero destinatario non valido. Usa il formato internazionale completo."
            )

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
        if len(normalized_to) < 6 or len(normalized_to) > 15:
            raise RuntimeError(
                "Numero destinatario non valido. Usa il formato internazionale completo."
            )
        if not template_name.strip():
            raise RuntimeError("template_name non valido.")
        if not language_code.strip():
            raise RuntimeError("language_code non valido.")

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


def _extract_meta_error_info(payload: object, status_code: int) -> dict[str, Any]:
    error_code = ""
    error_subcode = ""
    error_type = ""
    message = _format_meta_error(payload, status_code)

    if isinstance(payload, dict):
        error = payload.get("error")
        if isinstance(error, dict):
            error_code = str(error.get("code") or "").strip()
            error_subcode = str(error.get("error_subcode") or "").strip()
            error_type = str(error.get("type") or "").strip()

    classification = _classify_meta_error(
        payload,
        status_code=status_code,
        error_code=error_code,
        error_subcode=error_subcode,
        error_type=error_type,
    )
    retryable = _is_retryable_meta_error(classification, status_code)
    user_message = _build_user_safe_meta_error(
        payload,
        classification=classification,
        error_code=error_code,
        error_subcode=error_subcode,
        status_code=status_code,
    )

    return {
        "message": user_message or message,
        "error_code": error_code,
        "error_subcode": error_subcode,
        "error_type": error_type,
        "classification": classification,
        "retryable": retryable,
    }


def _classify_meta_error(
    payload: object,
    *,
    status_code: int,
    error_code: str,
    error_subcode: str,
    error_type: str,
) -> str:
    normalized = " ".join(
        str(part or "").strip().lower()
        for part in [
            error_type,
            _extract_meta_error_message(payload),
            _extract_meta_error_details(payload),
        ]
        if str(part or "").strip()
    )

    if error_code in {"131026"}:
        return "recipient"
    if error_code in {"133010"}:
        return "sender"
    if error_code in {"4", "80007", "130429", "131048"}:
        return "throttling"
    if error_code in {"1", "2", "131000"} or status_code >= 500:
        return "transient"
    if status_code in {401, 403}:
        return "authorization"
    if error_code == "100":
        if any(token in normalized for token in ("template", "language", "component", "parameter")):
            return "template"
        if any(token in normalized for token in ("phone", "recipient", "wa_id", "to")):
            return "recipient"
        return "invalid_request"
    if any(token in normalized for token in ("recipient", "receiver", "undeliverable", "not a valid whatsapp")):
        return "recipient"
    if any(token in normalized for token in ("template", "language", "parameter", "component")):
        return "template"
    if any(token in normalized for token in ("phone_number_id", "not registered", "sender")):
        return "sender"
    return "unknown"


def _is_retryable_meta_error(classification: str, status_code: int) -> bool:
    if classification in {"throttling", "transient"}:
        return True
    return status_code >= 500


def _build_user_safe_meta_error(
    payload: object,
    *,
    classification: str,
    error_code: str,
    error_subcode: str,
    status_code: int,
) -> str:
    meta_message = _extract_meta_error_message(payload)
    meta_details = _extract_meta_error_details(payload)
    diagnostic = " ".join(part for part in [meta_message, meta_details] if part).strip()

    if classification == "recipient":
        base = (
            "Meta ha rifiutato il messaggio: il numero destinatario non e valido "
            "oppure non puo ricevere messaggi WhatsApp."
        )
    elif classification == "template":
        base = (
            "Meta ha rifiutato il template: controlla nome template, lingua e parametri inviati."
        )
    elif classification == "sender":
        base = (
            "Meta ha rifiutato il messaggio: il numero WhatsApp del bot non e configurato "
            "o registrato correttamente."
        )
    elif classification == "authorization":
        base = "Meta ha rifiutato la richiesta per un problema di autorizzazione o permessi."
    elif classification == "throttling":
        base = "Meta non ha accettato l'invio per limiti temporanei. Riprova tra poco."
    elif classification == "transient":
        base = "Meta non e riuscita a processare l'invio in questo momento. Riprova."
    elif classification == "invalid_request":
        base = "Meta ha rifiutato la richiesta per parametri non validi."
    else:
        base = diagnostic or f"Errore Meta HTTP {status_code}."

    suffix = ""
    if error_code and error_subcode:
        suffix = f" (code {error_code}, subcode {error_subcode})"
    elif error_code:
        suffix = f" (code {error_code})"

    if diagnostic and diagnostic not in base:
        return f"{base}{suffix} Dettaglio Meta: {diagnostic}".strip()
    return f"{base}{suffix}".strip()


def _extract_meta_error_message(payload: object) -> str:
    if not isinstance(payload, dict):
        return ""
    error = payload.get("error")
    if not isinstance(error, dict):
        return ""
    return str(error.get("message") or "").strip()


def _extract_meta_error_details(payload: object) -> str:
    if not isinstance(payload, dict):
        return ""
    error = payload.get("error")
    if not isinstance(error, dict):
        return ""
    error_data = error.get("error_data")
    if not isinstance(error_data, dict):
        return ""
    return str(error_data.get("details") or "").strip()


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
