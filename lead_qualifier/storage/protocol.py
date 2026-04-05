from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from lead_qualifier.domain.lead import LeadState, StoredMessage


@dataclass(frozen=True)
class LeadConversationSummary:
    """Lightweight summary returned by list_leads."""

    wa_id: str
    qualification_status: str
    summary: str
    message_count: int
    last_message_at: str


class LeadStore(Protocol):
    def list_leads(self, bot_id: str) -> list[LeadConversationSummary]:
        ...

    def list_messages(self, bot_id: str, wa_id: str) -> list[StoredMessage]:
        ...

    def save_message(self, bot_id: str, wa_id: str, message: StoredMessage) -> None:
        ...

    def get_lead_state(self, bot_id: str, wa_id: str) -> LeadState | None:
        ...

    def save_lead_state(self, bot_id: str, wa_id: str, lead_state: LeadState) -> None:
        ...

    def delete_lead_conversation(self, bot_id: str, wa_id: str) -> None:
        ...

    def reserve_inbound_message(self, message_id: str, bot_id: str, wa_id: str) -> bool:
        ...

    def mark_inbound_message_completed(self, message_id: str) -> None:
        ...

    def mark_inbound_message_failed(self, message_id: str, error: str) -> None:
        ...

    def healthcheck(self) -> None:
        ...

    def close(self) -> None:
        ...
