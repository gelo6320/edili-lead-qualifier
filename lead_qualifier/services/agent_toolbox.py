from __future__ import annotations

from dataclasses import dataclass, replace
from datetime import datetime, timezone
from typing import Any

from lead_qualifier.domain.bot_config import BotConfig
from lead_qualifier.domain.lead import LeadRuntimeMetadata, LeadState
from lead_qualifier.integrations.lead_manager.client import LeadManagerClient


SEND_QUALIFIED_LEAD_TOOL_NAME = "send_qualified_lead_to_manager"


@dataclass(frozen=True)
class LeadQualifierToolContext:
    config: BotConfig
    wa_id: str
    contact_name: str
    lead_state: LeadState


@dataclass(frozen=True)
class ToolExecutionOutcome:
    result: dict[str, Any]
    metadata: LeadRuntimeMetadata


class LeadQualifierToolbox:
    def __init__(self, lead_manager_client: LeadManagerClient) -> None:
        self._lead_manager_client = lead_manager_client

    def definitions(self, context: LeadQualifierToolContext) -> list[dict[str, Any]]:
        if (
            not self._lead_manager_client.is_enabled_for(context.config)
            or context.lead_state.metadata.is_forwarded_to_lead_manager
        ):
            return []

        return [
            {
                "name": SEND_QUALIFIED_LEAD_TOOL_NAME,
                "description": (
                    "Invia il lead qualificato al lead manager operativo. "
                    "Usa questo tool solo quando i requisiti principali sono stati raccolti "
                    "e il lead e pronto per il passaggio."
                ),
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "manager_note": {
                            "type": "string",
                            "description": (
                                "Nota breve per il lead manager con contesto utile, "
                                "priorita percepita e prossimo passo consigliato."
                            ),
                        }
                    },
                    "required": ["manager_note"],
                    "additionalProperties": False,
                },
            }
        ]

    def tool_rules(self, context: LeadQualifierToolContext) -> str:
        if not self._lead_manager_client.is_enabled_for(context.config):
            return (
                "Non hai tool operativi disponibili in questo tenant. "
                "Quando il lead e qualificato, limita la risposta al riepilogo e al prossimo passo."
            )
        if context.lead_state.metadata.is_forwarded_to_lead_manager:
            return (
                "Il lead e gia stato inviato al lead manager. "
                "Non usare di nuovo il tool di invio salvo una correzione esplicita del lead."
            )
        return (
            "Quando il lead e qualificato in modo sufficiente e pronto per il passaggio, "
            "usa il tool send_qualified_lead_to_manager prima di confermare al lead il passo successivo."
        )

    def execute(
        self,
        *,
        tool_name: str,
        tool_input: dict[str, Any],
        context: LeadQualifierToolContext,
        metadata: LeadRuntimeMetadata,
    ) -> ToolExecutionOutcome:
        if tool_name != SEND_QUALIFIED_LEAD_TOOL_NAME:
            raise RuntimeError(f"Tool non supportato: {tool_name}")

        manager_note = str(tool_input.get("manager_note", "")).strip()
        if not manager_note:
            raise RuntimeError("manager_note obbligatoria.")

        response = self._lead_manager_client.forward_qualified_lead(
            config=context.config,
            wa_id=context.wa_id,
            lead_state=context.lead_state,
            manager_note=manager_note,
            contact_name=context.contact_name or metadata.latest_contact_name,
        )

        forwarded_at = datetime.now(timezone.utc).isoformat()
        reference = str(response.get("leadgen_id", "")).strip() or str(response.get("id", "")).strip()
        next_metadata = replace(
            metadata,
            lead_manager_forwarded_at=forwarded_at,
            lead_manager_reference=reference,
            lead_manager_note=manager_note,
        )
        return ToolExecutionOutcome(
            result={
                "status": "sent",
                "forwarded_at": forwarded_at,
                "reference": reference,
                "response": response,
            },
            metadata=next_metadata,
        )
