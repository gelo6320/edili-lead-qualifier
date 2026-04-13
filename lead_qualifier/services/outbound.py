from __future__ import annotations

import logging
import re
from typing import Any

from lead_qualifier.domain.bot_config import BotConfig
from lead_qualifier.domain.lead import StoredMessage
from lead_qualifier.integrations.whatsapp.client import WhatsAppCloudClient, WhatsAppCloudError
from lead_qualifier.services.lead_state import build_empty_lead_state, with_initial_template
from lead_qualifier.services.runtime_credentials import RuntimeCredentialsService
from lead_qualifier.storage.bot_config_store import BotConfigStore
from lead_qualifier.storage.protocol import LeadStore


TEMPLATE_PLACEHOLDER_PATTERN = re.compile(r"\{\{(\d+)\}\}")
LOGGER = logging.getLogger(__name__)


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
        is_default_template = _matches_default_template(config, template_name=template_name)
        if is_default_template and not config.default_template_body_text.strip():
            config = self._hydrate_default_template_context(
                config,
                access_token=access_token,
                template_name=template_name,
                language_code=resolved_language,
            )
        template_body = config.default_template_body_text if is_default_template else ""
        template_id = config.default_template_id if is_default_template else ""
        rendered_text = _render_template_body(template_body, body_parameters)
        self._validate_template_parameters(
            config=config,
            template_name=template_name,
            body_parameters=body_parameters,
        )

        LOGGER.info(
            "Sending template bot=%s to=%s template=%s lang=%s params=%d",
            bot_id, to, template_name, resolved_language, len(body_parameters),
        )
        try:
            response = self._whatsapp_client.send_template_message(
                to=to,
                phone_number_id=config.phone_number_id,
                template_name=template_name,
                language_code=resolved_language,
                body_parameters=body_parameters,
                access_token=access_token,
            )
        except WhatsAppCloudError as exc:
            LOGGER.error(
                "Template send failed bot=%s to=%s template=%s classification=%s: %s",
                bot_id, to, template_name, exc.classification, exc,
            )
            raise

        try:
            self._bootstrap_conversation(
                bot_id=config.id,
                wa_id=to,
                template_id=template_id,
                template_name=template_name,
                language_code=resolved_language,
                template_body=template_body,
                rendered_text=rendered_text,
                body_parameters=body_parameters,
            )
        except Exception as exc:
            LOGGER.error(
                "Bootstrap failed after template sent bot=%s to=%s: %s",
                bot_id, to, exc,
            )

        template_payload = {
            "kind": "outbound_template",
            "template_id": template_id,
            "template_name": template_name,
            "language_code": resolved_language,
            "template_body": template_body,
            "rendered_text": rendered_text,
            "body_parameters": body_parameters,
        }
        display = rendered_text or f"[template:{template_name}] {' | '.join(body_parameters)}".strip()
        self._store.save_message(
            config.id,
            to,
            StoredMessage.assistant(display=display, payload=template_payload),
        )

        LOGGER.info(
            "Template sent bot=%s to=%s template=%s rendered=%.80s",
            bot_id, to, template_name, rendered_text,
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

    def start_qualification_for_lead(
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
        template_id: str,
        template_name: str,
        language_code: str,
        template_body: str,
        rendered_text: str,
        body_parameters: list[str],
    ) -> None:
        config = self._config_store.require(bot_id)
        lead_state = self._store.get_lead_state(bot_id, wa_id) or build_empty_lead_state(config)
        lead_state = with_initial_template(
            lead_state,
            template_id=template_id,
            template_name=template_name,
            language_code=language_code,
            template_body=template_body,
            rendered_text=rendered_text,
            body_parameters=body_parameters,
        )
        self._store.save_lead_state(bot_id, wa_id, lead_state)

    def _hydrate_default_template_context(
        self,
        config: BotConfig,
        *,
        access_token: str,
        template_name: str,
        language_code: str,
    ) -> BotConfig:
        if not config.meta_waba_id.strip():
            return config

        try:
            templates = self._whatsapp_client.list_message_templates(
                waba_id=config.meta_waba_id,
                access_token=access_token,
            )
        except Exception as exc:
            LOGGER.warning(
                "Unable to hydrate template context for bot=%s template=%s: %s",
                config.id,
                template_name,
                exc,
            )
            return config

        match = _match_meta_template(
            templates,
            template_name=template_name,
            language_code=language_code,
        )
        if match is None:
            return config

        next_body = str(match.get("body_text", "")).strip()
        next_id = str(match.get("id", "")).strip()
        next_language = str(match.get("language", "")).strip() or config.template_language
        next_variable_count = max(int(match.get("body_variable_count") or 0), 0)

        if (
            config.default_template_id == next_id
            and config.default_template_name == template_name.strip()
            and config.default_template_body_text == next_body
            and config.default_template_variable_count == next_variable_count
            and config.template_language == next_language
        ):
            return config

        updated = config.model_copy(
            update={
                "default_template_id": next_id,
                "default_template_name": template_name.strip(),
                "default_template_body_text": next_body,
                "default_template_variable_count": next_variable_count,
                "template_language": next_language,
            }
        )
        return self._config_store.upsert(updated)

    @staticmethod
    def _validate_template_parameters(
        *,
        config,
        template_name: str,
        body_parameters: list[str],
    ) -> None:
        if template_name.strip() != (config.default_template_name or "").strip():
            return

        expected_count = max(int(getattr(config, "default_template_variable_count", 0) or 0), 0)
        actual_count = len(body_parameters)
        if expected_count == actual_count:
            return

        if expected_count == 0:
            raise RuntimeError(
                f"Il template {template_name} non richiede parametri body, ma ne hai inviati {actual_count}."
            )

        raise RuntimeError(
            f"Il template {template_name} richiede {expected_count} parametro/i body. "
            f"Ricevuti: {actual_count}."
        )


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


def _render_template_body(template_body: str, body_parameters: list[str]) -> str:
    cleaned_body = str(template_body or "").strip()
    if not cleaned_body:
        return ""

    def replace_placeholder(match: re.Match[str]) -> str:
        placeholder_index = int(match.group(1)) - 1
        if 0 <= placeholder_index < len(body_parameters):
            return body_parameters[placeholder_index].strip()
        return match.group(0)

    return TEMPLATE_PLACEHOLDER_PATTERN.sub(replace_placeholder, cleaned_body).strip()


def _matches_default_template(config, *, template_name: str) -> bool:
    return template_name.strip() == (config.default_template_name or "").strip()


def _match_meta_template(
    templates: list[dict[str, Any]],
    *,
    template_name: str,
    language_code: str,
) -> dict[str, Any] | None:
    normalized_name = template_name.strip()
    normalized_language = language_code.strip().lower()

    for template in templates:
        if str(template.get("status", "")).strip().upper() != "APPROVED":
            continue
        if str(template.get("name", "")).strip() != normalized_name:
            continue
        if str(template.get("language", "")).strip().lower() == normalized_language:
            return template

    for template in templates:
        if str(template.get("status", "")).strip().upper() != "APPROVED":
            continue
        if str(template.get("name", "")).strip() == normalized_name:
            return template

    return None
