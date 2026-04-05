from __future__ import annotations

import logging
from dataclasses import replace

from lead_qualifier.domain.bot_config import BotConfig
from lead_qualifier.domain.lead import InboundWhatsAppMessage, LeadState, StoredMessage
from lead_qualifier.integrations.anthropic.client import AnthropicLeadQualifier
from lead_qualifier.integrations.whatsapp.client import WhatsAppCloudClient
from lead_qualifier.integrations.whatsapp.parser import iter_inbound_messages
from lead_qualifier.services.lead_media import LeadMediaError, LeadMediaService
from lead_qualifier.services.lead_state import (
    build_empty_lead_state,
    infer_initial_template_from_history,
    with_image_asset,
    with_contact_name,
)
from lead_qualifier.services.runtime_credentials import RuntimeCredentialsService
from lead_qualifier.services.website_personalization import WebsitePersonalizationService
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
        lead_media: LeadMediaService,
        runtime_credentials: RuntimeCredentialsService,
        website_personalization: WebsitePersonalizationService,
    ) -> None:
        self._store = store
        self._config_store = config_store
        self._qualifier = qualifier
        self._whatsapp_client = whatsapp_client
        self._lead_media = lead_media
        self._runtime_credentials = runtime_credentials
        self._website_personalization = website_personalization

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
            access_token = self._runtime_credentials.get_whatsapp_access_token(config)
            if not message.has_text_or_media:
                self._whatsapp_client.send_text_message(
                    to=message.wa_id,
                    body=UNSUPPORTED_MESSAGE_REPLY,
                    phone_number_id=config.phone_number_id,
                    reply_to_message_id=message.message_id,
                    access_token=access_token,
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

            user_message, lead_state = self._build_user_message(
                config=config,
                message=message,
                lead_state=lead_state,
                access_token=access_token,
            )
            self._store.save_message(config.id, message.wa_id, user_message)

            knowledge_query = message.text.strip()
            if not knowledge_query and message.image_caption.strip():
                knowledge_query = message.image_caption.strip()

            response, metadata, usage = self._qualifier.generate_reply(
                config,
                history + [user_message],
                lead_state=lead_state,
                wa_id=message.wa_id,
                contact_name=message.contact_name,
                knowledge_context=self._website_personalization.search_context(
                    bot_id=config.id,
                    query=knowledge_query,
                ),
            )
            self._whatsapp_client.send_text_message(
                to=message.wa_id,
                body=response.reply_text,
                phone_number_id=config.phone_number_id,
                reply_to_message_id=message.message_id,
                access_token=access_token,
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

    def _build_user_message(
        self,
        *,
        config: BotConfig,
        message: InboundWhatsAppMessage,
        lead_state: LeadState,
        access_token: str,
    ) -> tuple[StoredMessage, LeadState]:
        if message.image_media_id:
            try:
                media_result = self._lead_media.process_inbound_image(
                    config=config,
                    message=message,
                    access_token=access_token,
                )
            except LeadMediaError:
                fallback_text = "Il lead ha inviato un'immagine del progetto."
                if message.image_caption.strip():
                    fallback_text = f"{fallback_text} Didascalia: {message.image_caption.strip()}."
                return StoredMessage.user(fallback_text), lead_state

            next_lead_state = lead_state
            if media_result.image_asset is not None:
                next_lead_state = with_image_asset(next_lead_state, media_result.image_asset)
                next_lead_state = _mark_image_requirement_as_received(config, next_lead_state)
            display_parts = ["[immagine ricevuta]"]
            if message.image_caption.strip():
                display_parts.append(message.image_caption.strip())
            return (
                StoredMessage.user_blocks(
                    " ".join(display_parts).strip(),
                    media_result.anthropic_blocks,
                    images=[
                        {
                            "url": media_result.image_asset.public_url,
                            "mime_type": media_result.image_asset.mime_type,
                            "caption": media_result.image_asset.caption,
                        }
                    ]
                    if media_result.image_asset and media_result.image_asset.public_url
                    else None,
                ),
                next_lead_state,
            )

        return StoredMessage.user(message.text), lead_state


def _mark_image_requirement_as_received(config: BotConfig, lead_state: LeadState) -> LeadState:
    if not config.image_field_keys:
        return lead_state
    next_field_values = dict(lead_state.field_values)
    changed = False
    for field_key in config.image_field_keys:
        if next_field_values.get(field_key, "").strip():
            continue
        next_field_values[field_key] = "ricevute"
        changed = True
    if not changed:
        return lead_state
    next_missing_fields = [field_key for field_key in lead_state.missing_fields if field_key not in config.image_field_keys]
    return replace(
        lead_state,
        field_values=next_field_values,
        missing_fields=next_missing_fields,
    )
