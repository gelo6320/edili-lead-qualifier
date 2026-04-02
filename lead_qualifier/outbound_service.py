from __future__ import annotations

from typing import Any

from lead_qualifier.bot_config_store import BotConfigStore
from lead_qualifier.models import StoredMessage
from lead_qualifier.store_protocol import LeadStore
from lead_qualifier.whatsapp_client import WhatsAppCloudClient


class OutboundMessageService:
    def __init__(
        self,
        store: LeadStore,
        config_store: BotConfigStore,
        whatsapp_client: WhatsAppCloudClient,
    ) -> None:
        self._store = store
        self._config_store = config_store
        self._whatsapp_client = whatsapp_client

    def send_template(
        self,
        *,
        bot_id: str,
        to: str,
        template_name: str,
        language_code: str | None,
        body_parameters: list[str],
    ) -> dict[str, Any]:
        config = self._config_store.require(bot_id)
        resolved_language = language_code or config.template_language
        response = self._whatsapp_client.send_template_message(
            to=to,
            phone_number_id=config.phone_number_id,
            template_name=template_name,
            language_code=resolved_language,
            body_parameters=body_parameters,
        )

        template_payload = {
            "kind": "outbound_template",
            "template_name": template_name,
            "language_code": resolved_language,
            "body_parameters": body_parameters,
        }
        display = f"[template:{template_name}] {' | '.join(body_parameters)}".strip()
        self._store.save_message(
            config.id,
            to,
            StoredMessage.assistant(display=display, payload=template_payload),
        )
        return response
