from __future__ import annotations

import logging

from lead_qualifier.anthropic_client import AnthropicLeadQualifier
from lead_qualifier.models import InboundWhatsAppMessage, StoredMessage
from lead_qualifier.store_protocol import LeadStore
from lead_qualifier.whatsapp_client import WhatsAppCloudClient
from lead_qualifier.whatsapp_parser import iter_inbound_messages

LOGGER = logging.getLogger(__name__)

UNSUPPORTED_MESSAGE_REPLY = (
    "Per aiutarti bene, scrivimi in testo la zona del lavoro, il tipo di intervento richiesto "
    "e quando vorresti farlo."
)


class InboundMessageService:
    def __init__(
        self,
        store: LeadStore,
        qualifier: AnthropicLeadQualifier,
        whatsapp_client: WhatsAppCloudClient,
    ) -> None:
        self._store = store
        self._qualifier = qualifier
        self._whatsapp_client = whatsapp_client

    def process_payload(self, payload: dict) -> None:
        for message in iter_inbound_messages(payload):
            self.process_inbound_message(message)

    def process_inbound_message(self, message: InboundWhatsAppMessage) -> None:
        if not self._store.reserve_inbound_message(message.message_id, message.wa_id):
            LOGGER.info("Duplicate inbound message ignored: %s", message.message_id)
            return

        try:
            if not message.text:
                self._whatsapp_client.send_text_message(
                    to=message.wa_id,
                    body=UNSUPPORTED_MESSAGE_REPLY,
                    reply_to_message_id=message.message_id,
                )
                self._store.mark_inbound_message_completed(message.message_id)
                return

            history = self._store.list_messages(message.wa_id)
            user_message = StoredMessage.user(message.text)
            self._store.save_message(message.wa_id, user_message)

            response, usage = self._qualifier.generate_reply(history + [user_message])
            self._whatsapp_client.send_text_message(
                to=message.wa_id,
                body=response.reply_text,
                reply_to_message_id=message.message_id,
            )
            self._store.save_message(message.wa_id, response.to_stored_message())
            self._store.save_lead_state(message.wa_id, response.to_lead_state())
            self._store.mark_inbound_message_completed(message.message_id)

            LOGGER.info(
                "Processed inbound message %s for %s usage=%s",
                message.message_id,
                message.wa_id,
                usage,
            )
        except Exception as exc:
            self._store.mark_inbound_message_failed(message.message_id, str(exc))
            LOGGER.exception("Failed to process inbound message %s", message.message_id)
