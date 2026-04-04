from __future__ import annotations

import logging

from lead_qualifier.domain.lead import InboundWhatsAppMessage, StoredMessage
from lead_qualifier.integrations.anthropic.client import AnthropicLeadQualifier
from lead_qualifier.integrations.whatsapp.client import WhatsAppCloudClient
from lead_qualifier.integrations.whatsapp.parser import iter_inbound_messages
from lead_qualifier.services.lead_state import (
    build_empty_lead_state,
    infer_initial_template_from_history,
    with_contact_name,
)
from lead_qualifier.storage.bot_config_store import BotConfigStore
from lead_qualifier.storage.protocol import LeadStore

LOGGER = logging.getLogger(__name__)

UNSUPPORTED_MESSAGE_REPLY = (
    "Per aiutarti bene, scrivimi in testo i dettagli della richiesta, cosi posso raccogliere le informazioni giuste."
)


class InboundMessageService:
    def __init__(
        self,
        store: LeadStore,
        config_store: BotConfigStore,
        qualifier: AnthropicLeadQualifier,
        whatsapp_client: WhatsAppCloudClient,
    ) -> None:
        self._store = store
        self._config_store = config_store
        self._qualifier = qualifier
        self._whatsapp_client = whatsapp_client

    def process_payload(self, payload: dict) -> None:
        for message in iter_inbound_messages(payload):
            self.process_inbound_message(message)

    def process_inbound_message(self, message: InboundWhatsAppMessage) -> None:
        config = self._config_store.get_by_phone_number_id(message.phone_number_id)
        if config is None:
            LOGGER.warning(
                "Inbound message %s ignored: no bot config for phone_number_id=%s",
                message.message_id,
                message.phone_number_id,
            )
            return

        if not self._store.reserve_inbound_message(message.message_id, config.id, message.wa_id):
            LOGGER.info("Duplicate inbound message ignored: %s", message.message_id)
            return

        try:
            if not message.text:
                self._whatsapp_client.send_text_message(
                    to=message.wa_id,
                    body=UNSUPPORTED_MESSAGE_REPLY,
                    phone_number_id=config.phone_number_id,
                    reply_to_message_id=message.message_id,
                )
                self._store.mark_inbound_message_completed(message.message_id)
                return

            history = self._store.list_messages(config.id, message.wa_id)
            lead_state = self._store.get_lead_state(config.id, message.wa_id) or build_empty_lead_state(
                config,
                contact_name=message.contact_name,
            )
            lead_state = infer_initial_template_from_history(lead_state, history)
            lead_state = with_contact_name(lead_state, message.contact_name)

            user_message = StoredMessage.user(message.text)
            self._store.save_message(config.id, message.wa_id, user_message)

            response, metadata, usage = self._qualifier.generate_reply(
                config,
                history + [user_message],
                lead_state=lead_state,
                wa_id=message.wa_id,
                contact_name=message.contact_name,
            )
            self._whatsapp_client.send_text_message(
                to=message.wa_id,
                body=response.reply_text,
                phone_number_id=config.phone_number_id,
                reply_to_message_id=message.message_id,
            )
            self._store.save_message(config.id, message.wa_id, response.to_stored_message())
            self._store.save_lead_state(config.id, message.wa_id, response.to_lead_state(metadata))
            self._store.mark_inbound_message_completed(message.message_id)

            LOGGER.info(
                "Processed inbound message %s bot=%s wa_id=%s usage=%s",
                message.message_id,
                config.id,
                message.wa_id,
                usage,
            )
        except Exception as exc:
            self._store.mark_inbound_message_failed(message.message_id, str(exc))
            LOGGER.exception("Failed to process inbound message %s", message.message_id)
