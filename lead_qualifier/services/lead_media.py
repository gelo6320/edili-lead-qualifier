from __future__ import annotations

import base64
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any

import httpx

from lead_qualifier.core.settings import Settings
from lead_qualifier.domain.bot_config import BotConfig
from lead_qualifier.domain.lead import InboundWhatsAppMessage, LeadImageAsset
from lead_qualifier.integrations.whatsapp.client import WhatsAppCloudClient


MEDIA_BUCKET_NAME = "lead-qualifier-media"
ALLOWED_IMAGE_MIME_TYPES = {
    "image/jpeg",
    "image/png",
    "image/gif",
    "image/webp",
}
MIME_EXTENSION_MAP = {
    "image/jpeg": "jpg",
    "image/png": "png",
    "image/gif": "gif",
    "image/webp": "webp",
}


class LeadMediaError(RuntimeError):
    pass


@dataclass(frozen=True)
class LeadMediaProcessingResult:
    anthropic_blocks: list[dict[str, Any]]
    image_asset: LeadImageAsset | None


def _clean(value: object) -> str:
    return str(value or "").strip()


def _normalize_mime_type(value: str) -> str:
    normalized = value.split(";", 1)[0].strip().lower()
    if normalized == "image/jpg":
        return "image/jpeg"
    return normalized


def _file_extension_for_mime_type(mime_type: str) -> str:
    normalized = _normalize_mime_type(mime_type)
    if normalized in MIME_EXTENSION_MAP:
        return MIME_EXTENSION_MAP[normalized]
    fallback = normalized.split("/", 1)[-1].strip()
    return fallback or "bin"


def _storage_object_path(bot_id: str, wa_id: str, message_id: str, mime_type: str) -> str:
    extension = _file_extension_for_mime_type(mime_type)
    safe_wa_id = "".join(char for char in wa_id if char.isdigit()) or "unknown"
    safe_message_id = "".join(char for char in message_id if char.isalnum() or char in {"-", "_"}) or "message"
    date_prefix = datetime.now(timezone.utc).strftime("%Y/%m/%d")
    return f"{bot_id}/{safe_wa_id}/{date_prefix}/{safe_message_id}.{extension}"


class LeadMediaService:
    def __init__(self, settings: Settings, whatsapp_client: WhatsAppCloudClient) -> None:
        self._settings = settings
        self._whatsapp_client = whatsapp_client
        self._bucket_checked = False

    @property
    def storage_enabled(self) -> bool:
        return bool(self._settings.supabase_url and self._settings.supabase_service_role_key)

    def process_inbound_image(
        self,
        *,
        config: BotConfig,
        message: InboundWhatsAppMessage,
        access_token: str,
    ) -> LeadMediaProcessingResult:
        media_id = _clean(message.image_media_id)
        if not media_id:
            raise LeadMediaError("Messaggio immagine privo di media_id.")

        metadata = self._whatsapp_client.get_media_metadata(
            media_id=media_id,
            access_token=access_token,
        )
        media_url = _clean(metadata.get("url"))
        if not media_url:
            raise LeadMediaError("Meta non ha restituito una URL media valida.")

        raw_bytes, downloaded_content_type = self._whatsapp_client.download_media(
            media_url=media_url,
            access_token=access_token,
        )
        mime_type = _normalize_mime_type(
            message.image_mime_type
            or _clean(metadata.get("mime_type"))
            or downloaded_content_type
        )
        if mime_type not in ALLOWED_IMAGE_MIME_TYPES:
            raise LeadMediaError(
                f"Tipo immagine non supportato per Claude: {mime_type or 'sconosciuto'}."
            )

        public_url = ""
        storage_path = ""
        if self.storage_enabled:
            try:
                storage_path, public_url = self._upload_public_image(
                    object_path=_storage_object_path(config.id, message.wa_id, message.message_id, mime_type),
                    payload=raw_bytes,
                    mime_type=mime_type,
                )
            except LeadMediaError:
                storage_path, public_url = "", ""

        caption = _clean(message.image_caption or message.text)
        intro_text = "Il lead ha inviato questa immagine del progetto."
        if caption:
            intro_text = f"{intro_text} Didascalia del lead: {caption}."

        uploaded_at = datetime.now(timezone.utc).isoformat()
        image_asset = LeadImageAsset(
            message_id=message.message_id,
            media_id=media_id,
            public_url=public_url,
            storage_path=storage_path,
            mime_type=mime_type,
            caption=caption,
            uploaded_at=uploaded_at,
        )

        anthropic_blocks: list[dict[str, Any]] = [
            {"type": "text", "text": intro_text},
            {
                "type": "image",
                "source": {
                    "type": "base64",
                    "media_type": mime_type,
                    "data": base64.b64encode(raw_bytes).decode("ascii"),
                },
                "cache_control": {"type": "ephemeral", "ttl": "1h"},
            },
        ]
        return LeadMediaProcessingResult(
            anthropic_blocks=anthropic_blocks,
            image_asset=image_asset,
        )

    def _upload_public_image(
        self,
        *,
        object_path: str,
        payload: bytes,
        mime_type: str,
    ) -> tuple[str, str]:
        if not self.storage_enabled:
            return "", ""

        self._ensure_public_bucket()
        base_url = self._settings.supabase_url.rstrip("/")
        headers = {
            "apikey": self._settings.supabase_service_role_key,
            "Authorization": f"Bearer {self._settings.supabase_service_role_key}",
            "Content-Type": mime_type,
            "x-upsert": "true",
        }
        try:
            response = httpx.post(
                f"{base_url}/storage/v1/object/{MEDIA_BUCKET_NAME}/{object_path}",
                headers=headers,
                content=payload,
                timeout=30.0,
            )
        except httpx.HTTPError as exc:
            raise LeadMediaError(str(exc)) from exc

        if not response.is_success:
            raise LeadMediaError(
                f"Upload media Supabase fallito: {response.text or response.status_code}."
            )

        public_url = (
            f"{base_url}/storage/v1/object/public/{MEDIA_BUCKET_NAME}/{object_path}"
        )
        return object_path, public_url

    def _ensure_public_bucket(self) -> None:
        if self._bucket_checked or not self.storage_enabled:
            return

        base_url = self._settings.supabase_url.rstrip("/")
        headers = {
            "apikey": self._settings.supabase_service_role_key,
            "Authorization": f"Bearer {self._settings.supabase_service_role_key}",
            "Content-Type": "application/json",
        }
        body = {
            "id": MEDIA_BUCKET_NAME,
            "name": MEDIA_BUCKET_NAME,
            "public": True,
            "allowed_mime_types": sorted(ALLOWED_IMAGE_MIME_TYPES),
        }
        try:
            response = httpx.post(
                f"{base_url}/storage/v1/bucket",
                headers=headers,
                json=body,
                timeout=30.0,
            )
        except httpx.HTTPError as exc:
            raise LeadMediaError(str(exc)) from exc

        response_text = response.text.lower()
        if response.is_success or (
            response.status_code in {400, 409}
            and any(snippet in response_text for snippet in ("already exists", "duplicate", "exists"))
        ):
            self._bucket_checked = True
            return
        raise LeadMediaError(
            f"Creazione bucket media fallita: {response.text or response.status_code}."
        )
