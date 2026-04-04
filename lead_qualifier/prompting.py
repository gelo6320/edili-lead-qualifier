from __future__ import annotations

from typing import Any

from lead_qualifier.bot_config_models import BotConfig
from lead_qualifier.models import LeadState
from lead_qualifier.prompt_templates import MAIN_PROMPT_TEMPLATE, SYSTEM_PROMPT_TEMPLATE


def build_response_schema(config: BotConfig) -> dict[str, Any]:
    field_properties: dict[str, Any] = {}
    for field in config.fields:
        field_schema: dict[str, Any] = {
            "type": "string",
            "description": field.description,
        }
        if field.options:
            field_schema["enum"] = [""] + field.options
        field_properties[field.key] = field_schema

    return {
        "type": "object",
        "properties": {
            "reply_text": {
                "type": "string",
                "description": "Messaggio visibile all'utente finale. Italiano naturale, niente markdown, massimo 450 caratteri.",
            },
            "field_values": {
                "type": "object",
                "properties": field_properties,
                "required": config.field_keys,
                "additionalProperties": False,
            },
            "qualification_status": {
                "type": "string",
                "enum": config.qualification_statuses,
                "description": "Stato interno della qualifica del lead.",
            },
            "missing_fields": {
                "type": "array",
                "items": {
                    "type": "string",
                    "enum": config.field_keys,
                },
                "description": "Elenco dei campi ancora da raccogliere.",
            },
            "summary": {
                "type": "string",
                "description": "Breve riassunto interno del lead in 1-2 frasi. Stringa vuota se troppo presto.",
            },
        },
        "required": [
            "reply_text",
            "field_values",
            "qualification_status",
            "missing_fields",
            "summary",
        ],
        "additionalProperties": False,
    }


def build_system_blocks(
    config: BotConfig,
    lead_state: LeadState,
    *,
    tool_rules: str,
) -> list[dict[str, Any]]:
    objective_lines = "\n".join(
        f"{index}. {field.label}"
        for index, field in enumerate(config.required_fields, start=1)
    )
    field_mapping = "\n".join(
        f"{field.key}: {field.label}. {field.description}"
        + (f" Valori ammessi: {', '.join(field.options)}." if field.options else "")
        for field in config.fields
    )
    missing_fields_list = ", ".join(config.field_keys)
    status_list = ", ".join(config.qualification_statuses)
    booking_instruction = (
        f"Se il lead e disponibile, puoi proporre una chiamata e citare questo link: {config.booking_url}."
        if config.booking_url
        else "Se il lead e disponibile, proponi una chiamata senza inventare link o dettagli di calendario."
    )

    system_prompt = SYSTEM_PROMPT_TEMPLATE.format(
        agent_name=config.agent_name,
        company_name=config.company_name,
        booking_instruction=booking_instruction,
        tool_rules=tool_rules,
        missing_fields_list=missing_fields_list,
        status_list=status_list,
    )

    runtime_prompt = MAIN_PROMPT_TEMPLATE.format(
        company_context=_build_company_context(config),
        objective_lines=objective_lines or "1. Nessun requisito configurato.",
        field_mapping=field_mapping or "Nessun campo configurato.",
        qualification_status=lead_state.qualification_status or config.default_status,
        missing_fields=_format_missing_fields(lead_state),
        field_values=_format_field_values(config, lead_state),
        summary=lead_state.summary.strip() or "Nessun riassunto ancora disponibile.",
        conversation_bootstrap=_format_conversation_bootstrap(lead_state),
        lead_manager_status=_format_lead_manager_status(lead_state),
    )

    return [
        {
            "type": "text",
            "text": system_prompt,
            "cache_control": {"type": "ephemeral", "ttl": "1h"},
        },
        {
            "type": "text",
            "text": runtime_prompt,
            "cache_control": {"type": "ephemeral", "ttl": "1h"},
        },
    ]


def _build_company_context(config: BotConfig) -> str:
    lines = [f"Azienda: {config.company_name}"]
    if config.company_description.strip():
        lines.append(f"Descrizione: {config.company_description.strip()}")
    if config.service_area.strip():
        lines.append(f"Area di servizio: {config.service_area.strip()}")
    if config.company_services:
        lines.append(f"Servizi principali: {', '.join(config.company_services)}")
    if config.booking_url.strip():
        lines.append(f"Booking URL: {config.booking_url.strip()}")
    return "\n".join(lines)


def _format_missing_fields(lead_state: LeadState) -> str:
    if not lead_state.missing_fields:
        return "Nessuno."
    return ", ".join(lead_state.missing_fields)


def _format_field_values(config: BotConfig, lead_state: LeadState) -> str:
    lines: list[str] = []
    for field in config.fields:
        value = lead_state.field_values.get(field.key, "").strip() or "non ancora raccolto"
        lines.append(f"- {field.label}: {value}")
    return "\n".join(lines)


def _format_conversation_bootstrap(lead_state: LeadState) -> str:
    metadata = lead_state.metadata
    if not metadata.has_initial_template:
        return "Nessun template iniziale registrato."
    parameters = ", ".join(metadata.initial_template_parameters) or "nessun parametro body"
    return (
        f"Conversazione aperta con template Meta '{metadata.initial_template_name}' "
        f"in lingua '{metadata.initial_template_language or 'default'}' con parametri: {parameters}."
    )


def _format_lead_manager_status(lead_state: LeadState) -> str:
    metadata = lead_state.metadata
    if not metadata.is_forwarded_to_lead_manager:
        return "Lead non ancora inviato al lead manager."
    reference = metadata.lead_manager_reference or "n/d"
    return (
        f"Lead gia inviato al lead manager il {metadata.lead_manager_forwarded_at}. "
        f"Riferimento: {reference}. Nota invio: {metadata.lead_manager_note or 'nessuna'}."
    )
