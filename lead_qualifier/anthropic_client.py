from __future__ import annotations

import json
from dataclasses import replace
from typing import Any

from anthropic import Anthropic
from anthropic.types import ToolUseBlock

from lead_qualifier.agent_tools import LeadQualifierToolContext, LeadQualifierToolbox
from lead_qualifier.bot_config_models import BotConfig
from lead_qualifier.models import LeadQualificationResponse, LeadRuntimeMetadata, LeadState, StoredMessage
from lead_qualifier.prompting import build_response_schema, build_system_blocks
from lead_qualifier.settings import Settings


class AnthropicLeadQualifier:
    def __init__(self, settings: Settings, toolbox: LeadQualifierToolbox) -> None:
        self._settings = settings
        self._toolbox = toolbox
        self._client = Anthropic(api_key=settings.anthropic_api_key) if settings.anthropic_api_key else None

    def _require_client(self) -> Anthropic:
        if self._client is None:
            raise RuntimeError("ANTHROPIC_API_KEY non configurata.")
        return self._client

    def generate_reply(
        self,
        config: BotConfig,
        messages: list[StoredMessage],
        *,
        lead_state: LeadState,
        wa_id: str,
        contact_name: str,
    ) -> tuple[LeadQualificationResponse, LeadRuntimeMetadata, dict[str, int]]:
        tool_context = LeadQualifierToolContext(
            config=config,
            wa_id=wa_id,
            contact_name=contact_name,
            lead_state=lead_state,
        )
        response_schema = build_response_schema(config)
        anthropic_messages = [
            anthropic_message
            for message in messages
            if (anthropic_message := _to_anthropic_message(message)) is not None
        ]

        current_metadata = lead_state.metadata
        total_usage: dict[str, int] = {}

        for _ in range(3):
            tools = self._toolbox.definitions(tool_context)
            system_blocks = build_system_blocks(
                config,
                tool_context.lead_state,
                tool_rules=self._toolbox.tool_rules(tool_context),
            )
            response = self._require_client().messages.create(
                model=self._settings.anthropic_model,
                max_tokens=900,
                temperature=0.25,
                system=system_blocks,
                messages=anthropic_messages,
                cache_control={"type": "ephemeral"},
                output_config={"format": {"type": "json_schema", "schema": response_schema}},
                tools=tools,
            )
            _accumulate_usage(total_usage, _extract_usage(response))

            tool_use_blocks = [
                block for block in response.content if getattr(block, "type", None) == "tool_use"
            ]
            if tool_use_blocks:
                anthropic_messages.append(
                    {
                        "role": "assistant",
                        "content": _serialize_content_blocks(response.content),
                    }
                )

                tool_results: list[dict[str, Any]] = []
                for block in tool_use_blocks:
                    if not isinstance(block, ToolUseBlock):
                        continue
                    try:
                        outcome = self._toolbox.execute(
                            tool_name=block.name,
                            tool_input=block.input,
                            context=tool_context,
                            metadata=current_metadata,
                        )
                        current_metadata = outcome.metadata
                        updated_lead_state = replace(tool_context.lead_state, metadata=current_metadata)
                        tool_context = LeadQualifierToolContext(
                            config=config,
                            wa_id=wa_id,
                            contact_name=contact_name,
                            lead_state=updated_lead_state,
                        )
                        tool_results.append(
                            {
                                "type": "tool_result",
                                "tool_use_id": block.id,
                                "content": json.dumps(outcome.result, ensure_ascii=False),
                            }
                        )
                    except Exception as exc:
                        tool_results.append(
                            {
                                "type": "tool_result",
                                "tool_use_id": block.id,
                                "content": json.dumps({"error": str(exc)}, ensure_ascii=False),
                                "is_error": True,
                            }
                        )

                anthropic_messages.append(
                    {
                        "role": "user",
                        "content": tool_results,
                    }
                )
                continue

            payload = json.loads(_extract_text(response))
            qualification = LeadQualificationResponse.from_payload(
                payload,
                allowed_field_keys=config.field_keys,
                required_field_keys=config.required_field_keys,
                allowed_statuses=set(config.qualification_statuses),
                default_status=config.default_status,
                existing_field_values=tool_context.lead_state.field_values,
            )
            return qualification, current_metadata, total_usage

        raise RuntimeError("Claude non ha prodotto una risposta finale valida dopo i tool.")


def _to_anthropic_message(message: StoredMessage) -> dict[str, Any] | None:
    if message.role == "assistant":
        try:
            payload = json.loads(message.api_content)
        except json.JSONDecodeError:
            return {"role": message.role, "content": message.api_content}
        if payload.get("kind") == "outbound_template":
            return None
        return {"role": message.role, "content": message.api_content}
    return {"role": message.role, "content": message.api_content}


def _serialize_content_blocks(blocks: list[Any]) -> list[dict[str, Any]]:
    serialized: list[dict[str, Any]] = []
    for block in blocks:
        block_type = getattr(block, "type", None)
        if block_type == "text":
            serialized.append({"type": "text", "text": getattr(block, "text", "")})
        elif block_type == "tool_use":
            serialized.append(
                {
                    "type": "tool_use",
                    "id": getattr(block, "id", ""),
                    "name": getattr(block, "name", ""),
                    "input": getattr(block, "input", {}),
                }
            )
    return serialized


def _extract_text(message: Any) -> str:
    text_parts: list[str] = []
    for block in message.content:
        if getattr(block, "type", None) == "text":
            text_parts.append(getattr(block, "text", ""))
    return "".join(text_parts)


def _extract_usage(message: Any) -> dict[str, int]:
    usage = getattr(message, "usage", None)
    if not usage:
        return {}

    return {
        "input_tokens": int(getattr(usage, "input_tokens", 0) or 0),
        "output_tokens": int(getattr(usage, "output_tokens", 0) or 0),
        "cache_creation_input_tokens": int(getattr(usage, "cache_creation_input_tokens", 0) or 0),
        "cache_read_input_tokens": int(getattr(usage, "cache_read_input_tokens", 0) or 0),
    }


def _accumulate_usage(target: dict[str, int], usage: dict[str, int]) -> None:
    for key, value in usage.items():
        target[key] = target.get(key, 0) + int(value or 0)
