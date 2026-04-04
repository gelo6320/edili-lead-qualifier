from __future__ import annotations

from typing import Any

from lead_qualifier.domain.lead import StoredMessage
from lead_qualifier.integrations.whatsapp.client import WhatsAppCloudClient
from lead_qualifier.services.lead_state import build_empty_lead_state, with_initial_template
from lead_qualifier.storage.bot_config_store import BotConfigStore
from lead_qualifier.storage.protocol import LeadStore


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

        self._bootstrap_conversation(
            bot_id=config.id,
            wa_id=to,
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
        return {
            "meta": response,
            "conversation_created": True,
        }

    def send_test_template(
        self,
        *,
        bot_id: str,
        to: str,
        body_parameters: list[str],
        template_name: str | None = None,
        language_code: str | None = None,
    ) -> dict[str, Any]:
        config = self._config_store.require(bot_id)
        resolved_template_name = template_name or config.default_template_name
        if not resolved_template_name:
            raise RuntimeError("default_template_name non configurato per il bot.")

        return self.send_template(
            bot_id=bot_id,
            to=to,
            template_name=resolved_template_name,
            language_code=language_code or config.template_language,
            body_parameters=body_parameters,
        )

    def _bootstrap_conversation(
        self,
        *,
        bot_id: str,
        wa_id: str,
        template_name: str,
        language_code: str,
        body_parameters: list[str],
    ) -> None:
        config = self._config_store.require(bot_id)
        lead_state = self._store.get_lead_state(bot_id, wa_id) or build_empty_lead_state(config)
        lead_state = with_initial_template(
            lead_state,
            template_name=template_name,
            language_code=language_code,
            body_parameters=body_parameters,
        )
        self._store.save_lead_state(bot_id, wa_id, lead_state)
