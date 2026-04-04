from __future__ import annotations

from typing import Any, Iterator

from lead_qualifier.models import InboundWhatsAppMessage


def iter_inbound_messages(payload: dict[str, Any]) -> Iterator[InboundWhatsAppMessage]:
    for entry in payload.get("entry", []):
        for change in entry.get("changes", []):
            value = change.get("value", {})
            metadata = value.get("metadata", {})
            contacts = value.get("contacts", [])
            contact_names = {
                contact.get("wa_id", ""): contact.get("profile", {}).get("name", "")
                for contact in contacts
            }
            for message in value.get("messages", []):
                wa_id = str(message.get("from", "")).strip()
                message_id = str(message.get("id", "")).strip()
                if not wa_id or not message_id:
                    continue
                yield InboundWhatsAppMessage(
                    message_id=message_id,
                    wa_id=wa_id,
                    text=_extract_text(message),
                    message_type=str(message.get("type", "")).strip(),
                    phone_number_id=str(metadata.get("phone_number_id", "")).strip(),
                    contact_name=str(contact_names.get(wa_id, "")).strip(),
                    timestamp=str(message.get("timestamp", "")).strip(),
                )


def _extract_text(message: dict[str, Any]) -> str:
    message_type = str(message.get("type", "")).strip()
    if message_type == "text":
        return str(message.get("text", {}).get("body", "")).strip()
    if message_type == "image":
        caption = str(message.get("image", {}).get("caption", "")).strip()
        if caption:
            return (
                "Il lead ha inviato una foto o immagine del lavoro. "
                f"Didascalia del lead: {caption}. "
                "Non puoi vedere il contenuto visivo, ma considera che il lead ha condiviso immagini utili per la valutazione."
            )
        return (
            "Il lead ha inviato una foto o immagine del lavoro. "
            "Non puoi vedere il contenuto visivo, ma considera che il lead ha condiviso immagini utili per la valutazione."
        )
    if message_type == "button":
        return str(message.get("button", {}).get("text", "")).strip()
    if message_type == "interactive":
        interactive = message.get("interactive", {})
        interactive_type = str(interactive.get("type", "")).strip()
        if interactive_type == "button_reply":
            return str(interactive.get("button_reply", {}).get("title", "")).strip()
        if interactive_type == "list_reply":
            return str(interactive.get("list_reply", {}).get("title", "")).strip()
    return ""
