from __future__ import annotations

from typing import Any

from lead_qualifier.domain.lead import StoredMessage
from lead_qualifier.integrations.whatsapp.client import WhatsAppCloudClient
from lead_qualifier.services.lead_state import build_empty_lead_state, with_initial_template
from lead_qualifier.services.runtime_credentials import RuntimeCredentialsService
from lead_qualifier.storage.bot_config_store import BotConfigStore
from lead_qualifier.storage.protocol import LeadStore


class OutboundMessageService:
    def __init__(
        self,
        store: LeadStore,
        config_store: BotConfigStore,
        whatsapp_client: WhatsAppCloudClient,
        runtime_credentials: RuntimeCredentialsService,
    ) -> None:
        self._store = store
        self._config_store = config_store
        self._whatsapp_client = whatsapp_client
        self._runtime_credentials = runtime_credentials

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
        access_token = self._runtime_credentials.get_whatsapp_access_token(config)
        resolved_language = language_code or config.template_language
        response = self._whatsapp_client.send_template_message(
            to=to,
            phone_number_id=config.phone_number_id,
            template_name=template_name,
            language_code=resolved_language,
            body_parameters=body_parameters,
            access_token=access_token,
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

    def start_qualification_from_bridge(
        self,
        *,
        bot_id: str,
        phone: str,
        full_name: str = "",
    ) -> dict[str, Any]:
        config = self._config_store.require(bot_id)
        resolved_template_name = config.default_template_name
        if not resolved_template_name:
            raise RuntimeError("default_template_name non configurato per il bot.")
        return self.send_template(
            bot_id=bot_id,
            to=phone,
            template_name=resolved_template_name,
            language_code=config.template_language,
            body_parameters=_build_default_template_parameters(
                config,
                full_name=full_name,
            ),
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


def _build_default_template_parameters(config, *, full_name: str) -> list[str]:
    variable_count = max(int(getattr(config, "default_template_variable_count", 0) or 0), 0)
    if variable_count <= 0:
        return []

    seed_values = [
        str(full_name or "").strip(),
        str(config.company_name or "").strip(),
        str(config.service_area or "").strip(),
        str(config.booking_url or "").strip(),
    ]
    parameters: list[str] = []
    for value in seed_values:
        if len(parameters) >= variable_count:
            break
        if value:
            parameters.append(value)

    while len(parameters) < variable_count:
        parameters.append(config.company_name or "-")
    return parameters
