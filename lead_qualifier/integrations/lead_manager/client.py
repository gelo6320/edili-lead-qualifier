from __future__ import annotations

from typing import Any

import httpx

from lead_qualifier.core.settings import Settings
from lead_qualifier.domain.bot_config import BotConfig
from lead_qualifier.domain.lead import LeadState


class LeadManagerClient:
    def __init__(self, settings: Settings) -> None:
        self._settings = settings

    def is_enabled_for(self, config: BotConfig) -> bool:
        return bool(
            self._settings.lead_manager_api_url
            and config.lead_manager_page_id
        )

    def forward_qualified_lead(
        self,
        *,
        config: BotConfig,
        wa_id: str,
        lead_state: LeadState,
        manager_note: str,
        contact_name: str,
    ) -> dict[str, Any]:
        if not self._settings.lead_manager_api_url:
            raise RuntimeError("LEAD_MANAGER_API_URL non configurato.")
        if not config.lead_manager_page_id:
            raise RuntimeError("lead_manager_page_id non configurato per il bot.")

        payload = {
            "page_id": config.lead_manager_page_id,
            "full_name": _resolve_full_name(lead_state, contact_name),
            "phone": _normalize_phone(wa_id),
            "source_label": f"WhatsApp Qualifier {config.company_name}",
            "form_responses": _build_form_responses(config, lead_state),
            "custom_fields": _build_custom_fields(config, wa_id, lead_state, manager_note),
        }

        headers = {"Content-Type": "application/json"}
        if self._settings.lead_manager_api_key:
            headers["X-API-Key"] = self._settings.lead_manager_api_key

        response = httpx.post(
            self._settings.lead_manager_api_url,
            json=payload,
            headers=headers,
            timeout=30.0,
        )
        response.raise_for_status()
        return response.json()


def _normalize_phone(wa_id: str) -> str:
    cleaned = wa_id.strip()
    if not cleaned:
        return ""
    if cleaned.startswith("+"):
        return cleaned
    return f"+{cleaned}"


def _resolve_full_name(lead_state: LeadState, contact_name: str) -> str | None:
    for key in ("nome_completo", "nome", "full_name", "ragione_sociale"):
        value = lead_state.field_values.get(key, "").strip()
        if value:
            return value
    cleaned_contact_name = contact_name.strip()
    return cleaned_contact_name or None


def _build_form_responses(config: BotConfig, lead_state: LeadState) -> list[str]:
    responses: list[str] = []
    for field in config.fields:
        value = lead_state.field_values.get(field.key, "").strip()
        if not value:
            continue
        responses.append(f"{field.label}: {value}")

    if lead_state.summary.strip():
        responses.append(f"Summary: {lead_state.summary.strip()}")

    return responses


def _build_custom_fields(
    config: BotConfig,
    wa_id: str,
    lead_state: LeadState,
    manager_note: str,
) -> dict[str, Any]:
    custom_fields: dict[str, Any] = {
        "wa_id": wa_id,
        "qualification_status": lead_state.qualification_status,
        "summary": lead_state.summary,
        "manager_note": manager_note.strip(),
        "company_name": config.company_name,
        "company_description": config.company_description,
        "service_area": config.service_area,
        "company_services": config.company_services,
        "agent_name": config.agent_name,
    }

    for field in config.fields:
        value = lead_state.field_values.get(field.key, "").strip()
        if value:
            custom_fields[field.key] = value

    return custom_fields
