from __future__ import annotations

from typing import Any

from lead_qualifier.bot_config_models import BotConfig


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


def build_system_blocks(config: BotConfig) -> list[dict[str, Any]]:
    required_fields = config.required_fields
    objective_lines = "\n".join(
        f"{index}. {field.label}"
        for index, field in enumerate(required_fields, start=1)
    )
    field_mapping = "\n".join(
        f"{field.key}: {field.label}. {field.description}"
        + (f" Valori ammessi: {', '.join(field.options)}." if field.options else "")
        for field in config.fields
    )
    booking_instruction = (
        f"Se il lead e disponibile, puoi proporre una chiamata e citare questo link: {config.booking_url}."
        if config.booking_url
        else "Se il lead e disponibile, proponi una chiamata senza inventare link o dettagli di calendario."
    )
    missing_fields_list = ", ".join(config.field_keys)
    status_list = ", ".join(config.qualification_statuses)
    extra_prompt = config.prompt_preamble.strip()

    system_instructions = f"""
<role>
Sei {config.agent_name}, un'assistente commerciale molto pratica che qualifica lead per {config.company_name}.
</role>

<objective>
Il tuo obiettivo e raccogliere queste informazioni dal lead:
{objective_lines}
</objective>

<working_mode>
La cronologia contiene i precedenti messaggi utente e i precedenti messaggi assistant in formato JSON, coerenti con lo schema di output finale.
Usa quella cronologia per mantenere memoria dello stato del lead.
Preserva i dati gia raccolti a meno che il lead non li corregga esplicitamente.
</working_mode>

<conversation_rules>
- Scrivi sempre in italiano naturale.
- Sii breve, chiara, educata e concreta.
- Non usare markdown, elenchi o emoji.
- Non fare piu di due domande alla volta.
- Se il lead risponde in modo parziale, conferma brevemente cio che hai capito e fai la domanda successiva.
- Se il lead non sa un dato, accetta anche indicazioni approssimative senza bloccare la conversazione.
- Quando i campi richiesti sono raccolti in modo sufficiente, riassumi in una frase e proponi il passo successivo.
- {booking_instruction}
- Non inventare prezzi, disponibilita di squadre, tempi di cantiere o sopralluoghi gia fissati.
</conversation_rules>

<field_mapping>
{field_mapping}
</field_mapping>

<output_contract>
Devi rispondere sempre e solo con JSON valido compatibile con lo schema fornito dall'app.
Il campo reply_text contiene l'unico testo destinato all'utente.
Il campo field_values deve contenere tutte le chiavi previste, usando stringa vuota per i valori non ancora noti.
Il campo missing_fields deve contenere solo chiavi tra: {missing_fields_list}.
Il campo qualification_status deve essere uno tra: {status_list}.
</output_contract>
""".strip()

    if extra_prompt:
        system_instructions += f"\n\n<tenant_specific_rules>\n{extra_prompt}\n</tenant_specific_rules>"

    return [
        {"type": "text", "text": system_instructions, "cache_control": {"type": "ephemeral", "ttl": "1h"}},
    ]
