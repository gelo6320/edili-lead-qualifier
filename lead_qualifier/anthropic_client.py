from __future__ import annotations

import json
from typing import Any

from anthropic import Anthropic

from lead_qualifier.models import LeadQualificationResponse, StoredMessage
from lead_qualifier.prompting import RESPONSE_SCHEMA, build_system_blocks
from lead_qualifier.settings import Settings


class AnthropicLeadQualifier:
    def __init__(self, settings: Settings) -> None:
        self._settings = settings
        self._system_blocks = build_system_blocks(
            company_name=settings.company_name,
            agent_name=settings.agent_name,
            booking_url=settings.call_booking_url,
        )
        self._client = Anthropic(api_key=settings.anthropic_api_key) if settings.anthropic_api_key else None

    def _require_client(self) -> Anthropic:
        if self._client is None:
            raise RuntimeError("ANTHROPIC_API_KEY non configurata.")
        return self._client

    def generate_reply(self, messages: list[StoredMessage]) -> tuple[LeadQualificationResponse, dict[str, int]]:
        anthropic_messages = [
            {"role": message.role, "content": message.api_content}
            for message in messages
        ]

        with self._require_client().messages.stream(
            model=self._settings.anthropic_model,
            max_tokens=900,
            temperature=0.25,
            system=self._system_blocks,
            messages=anthropic_messages,
            cache_control={"type": "ephemeral"},
            output_config={"format": {"type": "json_schema", "schema": RESPONSE_SCHEMA}},
        ) as stream:
            final_message = stream.get_final_message()

        payload = json.loads(self._extract_text(final_message))
        response = LeadQualificationResponse.from_payload(payload)
        usage = self._extract_usage(final_message)
        return response, usage

    @staticmethod
    def _extract_text(message: Any) -> str:
        text_parts: list[str] = []
        for block in message.content:
            if getattr(block, "type", None) == "text":
                text_parts.append(getattr(block, "text", ""))
        return "".join(text_parts)

    @staticmethod
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
