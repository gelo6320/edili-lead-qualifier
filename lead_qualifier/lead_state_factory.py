from __future__ import annotations

import json
from dataclasses import replace

from lead_qualifier.bot_config_models import BotConfig
from lead_qualifier.models import LeadRuntimeMetadata, LeadState, StoredMessage


def build_empty_lead_state(config: BotConfig, *, contact_name: str = "") -> LeadState:
    return LeadState(
        field_values={key: "" for key in config.field_keys},
        qualification_status=config.default_status,
        missing_fields=config.required_field_keys,
        summary="",
        metadata=LeadRuntimeMetadata(
            latest_contact_name=contact_name.strip(),
        ),
    )


def with_contact_name(lead_state: LeadState, contact_name: str) -> LeadState:
    cleaned_name = contact_name.strip()
    if not cleaned_name or cleaned_name == lead_state.metadata.latest_contact_name:
        return lead_state
    return replace(
        lead_state,
        metadata=replace(lead_state.metadata, latest_contact_name=cleaned_name),
    )


def with_initial_template(
    lead_state: LeadState,
    *,
    template_name: str,
    language_code: str,
    body_parameters: list[str],
) -> LeadState:
    return replace(
        lead_state,
        metadata=replace(
            lead_state.metadata,
            initial_template_name=template_name.strip(),
            initial_template_language=language_code.strip(),
            initial_template_parameters=[value.strip() for value in body_parameters if value.strip()],
        ),
    )


def with_lead_manager_forwarding(
    lead_state: LeadState,
    *,
    forwarded_at: str,
    reference: str,
    manager_note: str,
) -> LeadState:
    return replace(
        lead_state,
        metadata=replace(
            lead_state.metadata,
            lead_manager_forwarded_at=forwarded_at.strip(),
            lead_manager_reference=reference.strip(),
            lead_manager_note=manager_note.strip(),
        ),
    )


def infer_initial_template_from_history(lead_state: LeadState, history: list[StoredMessage]) -> LeadState:
    if lead_state.metadata.has_initial_template:
        return lead_state

    for message in history:
        if message.role != "assistant":
            continue
        try:
            payload = json.loads(message.api_content)
        except json.JSONDecodeError:
            continue
        if payload.get("kind") != "outbound_template":
            continue
        return with_initial_template(
            lead_state,
            template_name=str(payload.get("template_name", "")).strip(),
            language_code=str(payload.get("language_code", "")).strip(),
            body_parameters=[
                str(value).strip()
                for value in payload.get("body_parameters", [])
                if str(value).strip()
            ],
        )

    return lead_state
