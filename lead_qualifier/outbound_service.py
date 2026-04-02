from __future__ import annotations

from typing import Any

from lead_qualifier.whatsapp_client import WhatsAppCloudClient


class OutboundMessageService:
    def __init__(self, whatsapp_client: WhatsAppCloudClient) -> None:
        self._whatsapp_client = whatsapp_client

    def send_template(
        self,
        *,
        to: str,
        template_name: str,
        language_code: str,
        body_parameters: list[str],
    ) -> dict[str, Any]:
        return self._whatsapp_client.send_template_message(
            to=to,
            template_name=template_name,
            language_code=language_code,
            body_parameters=body_parameters,
        )
