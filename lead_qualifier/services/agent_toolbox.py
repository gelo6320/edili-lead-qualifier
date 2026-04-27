from __future__ import annotations

from dataclasses import dataclass, replace
from datetime import datetime, timezone
from typing import Any

from lead_qualifier.domain.bot_config import BotConfig
from lead_qualifier.domain.lead import LeadRuntimeMetadata, LeadState
from lead_qualifier.integrations.qualified_lead_webhook.client import QualifiedLeadWebhookClient


SEND_QUALIFIED_LEAD_TOOL_NAME = "send_qualified_lead_webhook"
STOP_AI_CHAT_TOOL_NAME = "stop_ai_chat"


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
    def __init__(self, qualified_lead_client: QualifiedLeadWebhookClient) -> None:
        self._qualified_lead_client = qualified_lead_client

    def definitions(self, context: LeadQualifierToolContext) -> list[dict[str, Any]]:
        if context.lead_state.metadata.has_ai_stopped:
            return []

        tools: list[dict[str, Any]] = []
        if (
            self._qualified_lead_client.is_enabled_for(context.config)
            and not context.lead_state.metadata.has_qualified_handoff
        ):
            tools.append(
                {
                    "name": SEND_QUALIFIED_LEAD_TOOL_NAME,
                    "description": (
                        "Invia il lead qualificato al webhook operativo configurato per questo bot. "
                        "Usa questo tool solo come ultimo step, quando i requisiti principali sono stati raccolti, "
                        "il riassunto e pronto e il requisito immagini e stato chiuso con foto ricevute oppure "
                        "esplicitamente non disponibili."
                    ),
                    "input_schema": {
                        "type": "object",
                        "properties": {
                            "handoff_note": {
                                "type": "string",
                                "description": (
                                    "Nota breve per il team operativo che riceve il lead, "
                                    "con priorita percepita e prossimo passo consigliato."
                                ),
                            }
                        },
                        "required": ["handoff_note"],
                        "additionalProperties": False,
                    },
                },
            )

        if not context.lead_state.metadata.has_ai_stopped:
            tools.append(
                {
                    "name": STOP_AI_CHAT_TOOL_NAME,
                    "description": (
                        "Ferma le risposte automatiche dell'AI solo per questa chat WhatsApp. "
                        "Usalo quando hai gia provato almeno tre volte a capire o risolvere la richiesta, "
                        "non riesci a proseguire in modo utile e stai indirizzando il lead al supporto umano."
                    ),
                    "input_schema": {
                        "type": "object",
                        "properties": {
                            "reason": {
                                "type": "string",
                                "description": (
                                    "Motivo breve per il team umano, ad esempio cosa non e chiaro "
                                    "o cosa non funziona nella conversazione."
                                ),
                            },
                            "support_escalation_count": {
                                "type": "integer",
                                "minimum": 3,
                                "description": (
                                    "Numero di volte in questa chat in cui hai gia dovuto dire "
                                    "che non puoi aiutare o che serve contattare il supporto umano."
                                ),
                            },
                        },
                        "required": ["reason", "support_escalation_count"],
                        "additionalProperties": False,
                    },
                },
            )

        return tools

    def tool_rules(self, context: LeadQualifierToolContext) -> str:
        if context.lead_state.metadata.has_ai_stopped:
            return (
                "L'AI e stata fermata per questa chat. Non usare altri tool. "
                "Scrivi solo un messaggio finale breve dicendo che la conversazione passa a un operatore umano."
            )

        stop_rules = (
            "Hai anche il tool stop_ai_chat: usalo solo dalla terza escalation verso supporto umano "
            "nella stessa chat, quando non capisci la richiesta o il flusso non funziona e non puoi "
            "piu proseguire in modo utile. Dopo averlo usato, scrivi un messaggio finale breve al lead "
            "dicendo che la conversazione passa a un operatore umano."
        )
        if not self._qualified_lead_client.is_enabled_for(context.config):
            return (
                "Non hai tool operativi disponibili in questo tenant. "
                "Quando il lead e qualificato, limita la risposta al riepilogo e al prossimo passo. "
                f"{stop_rules}"
            )
        if context.lead_state.metadata.has_qualified_handoff:
            return (
                "Il lead e gia stato inviato al webhook operativo. "
                "Non usare di nuovo il tool di invio salvo una correzione esplicita del lead. "
                f"{stop_rules}"
            )
        return (
            "Quando il lead e qualificato in modo sufficiente, il requisito immagini e stato risolto "
            "(foto ricevute oppure non disponibili) e il lead e pronto per il passaggio, "
            "usa il tool send_qualified_lead_webhook prima di confermare al lead il passo successivo. "
            f"{stop_rules}"
        )

    def execute(
        self,
        *,
        tool_name: str,
        tool_input: dict[str, Any],
        context: LeadQualifierToolContext,
        metadata: LeadRuntimeMetadata,
    ) -> ToolExecutionOutcome:
        if tool_name == STOP_AI_CHAT_TOOL_NAME:
            return self._stop_ai_chat(tool_input=tool_input, metadata=metadata)

        if tool_name != SEND_QUALIFIED_LEAD_TOOL_NAME:
            raise RuntimeError(f"Tool non supportato: {tool_name}")

        handoff_note = str(tool_input.get("handoff_note", "")).strip()
        if not handoff_note:
            raise RuntimeError("handoff_note obbligatoria.")

        response = self._qualified_lead_client.deliver(
            config=context.config,
            wa_id=context.wa_id,
            lead_state=context.lead_state,
            handoff_note=handoff_note,
            contact_name=context.contact_name or metadata.latest_contact_name,
        )

        sent_at = datetime.now(timezone.utc).isoformat()
        response_body = response.get("body")
        reference = ""
        if isinstance(response_body, dict):
            reference = (
                str(response_body.get("id", "")).strip()
                or str(response_body.get("reference", "")).strip()
                or str(response_body.get("leadgen_id", "")).strip()
            )
        next_metadata = replace(
            metadata,
            qualified_handoff_sent_at=sent_at,
            qualified_handoff_reference=reference,
            qualified_handoff_note=handoff_note,
        )
        return ToolExecutionOutcome(
            result={
                "status": "sent",
                "sent_at": sent_at,
                "reference": reference,
                "response": response,
            },
            metadata=next_metadata,
        )

    def _stop_ai_chat(
        self,
        *,
        tool_input: dict[str, Any],
        metadata: LeadRuntimeMetadata,
    ) -> ToolExecutionOutcome:
        reason = str(tool_input.get("reason", "")).strip()
        if not reason:
            raise RuntimeError("reason obbligatoria.")

        try:
            support_escalation_count = int(tool_input.get("support_escalation_count", 0))
        except (TypeError, ValueError) as exc:
            raise RuntimeError("support_escalation_count deve essere un numero.") from exc

        if support_escalation_count < 3:
            raise RuntimeError("stop_ai_chat puo essere usato solo dalla terza escalation al supporto umano.")

        stopped_at = datetime.now(timezone.utc).isoformat()
        next_metadata = replace(
            metadata,
            ai_stopped_at=stopped_at,
            ai_stopped_reason=reason,
            ai_stopped_by="claude",
        )
        return ToolExecutionOutcome(
            result={
                "status": "ai_stopped",
                "stopped_at": stopped_at,
                "reason": reason,
            },
            metadata=next_metadata,
        )
