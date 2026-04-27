from __future__ import annotations

from typing import Any

from lead_qualifier.domain.bot_config import BotConfig
from lead_qualifier.domain.lead import LeadState
from lead_qualifier.prompting.templates import MAIN_PROMPT_TEMPLATE, SYSTEM_PROMPT_TEMPLATE


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
    knowledge_context: str = "",
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
        images_status=_format_images_status(lead_state),
        qualified_handoff_status=_format_qualified_handoff_status(lead_state),
        ai_stop_status=_format_ai_stop_status(lead_state),
    )

    if knowledge_context.strip():
        runtime_prompt = (
            f"{runtime_prompt}\n\n"
            "Knowledge base rilevante per questa richiesta:\n"
            f"{knowledge_context.strip()}\n\n"
            "Usa questa knowledge base in priorita quando aiuta a rispondere in modo diretto o a collegare il lead "
            "ai servizi reali dell'azienda. Se il contesto non basta, non inventare dettagli."
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
    identifier = metadata.initial_template_id or metadata.initial_template_name or "n/d"
    rendered_text = metadata.initial_template_rendered_text.strip()
    if rendered_text:
        return (
            f"Conversazione aperta con messaggio iniziale Meta id '{identifier}' "
            f"(lingua '{metadata.initial_template_language or 'default'}'). "
            f"Body template: {metadata.initial_template_body or 'n/d'}. "
            f"Messaggio effettivamente inviato: {rendered_text}. "
            f"Parametri: {parameters}."
        )
    return (
        f"Conversazione aperta con template Meta id '{identifier}' "
        f"in lingua '{metadata.initial_template_language or 'default'}'. "
        f"Body template: {metadata.initial_template_body or 'n/d'}. "
        f"Parametri: {parameters}."
    )


def _format_images_status(lead_state: LeadState) -> str:
    metadata = lead_state.metadata
    if not metadata.images:
        return "Nessuna immagine ancora ricevuta."

    lines = []
    for index, image in enumerate(metadata.images, start=1):
        caption = image.caption or "nessuna didascalia"
        location = image.public_url or image.storage_path or image.media_id or "n/d"
        lines.append(
            f"{index}. mime={image.mime_type or 'n/d'}; caption={caption}; riferimento={location}"
        )
    return "\n".join(lines)


def _format_qualified_handoff_status(lead_state: LeadState) -> str:
    metadata = lead_state.metadata
    if not metadata.has_qualified_handoff:
        return "Lead non ancora inviato al webhook operativo."
    reference = metadata.qualified_handoff_reference or "n/d"
    return (
        f"Lead gia inviato al webhook operativo il {metadata.qualified_handoff_sent_at}. "
        f"Riferimento: {reference}. Nota invio: {metadata.qualified_handoff_note or 'nessuna'}."
    )


def _format_ai_stop_status(lead_state: LeadState) -> str:
    metadata = lead_state.metadata
    if not metadata.has_ai_stopped:
        return "AI attiva per questa chat."
    reason = metadata.ai_stopped_reason or "n/d"
    stopped_by = metadata.ai_stopped_by or "n/d"
    return f"AI fermata il {metadata.ai_stopped_at} da {stopped_by}. Motivo: {reason}."
