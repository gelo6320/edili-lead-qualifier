from __future__ import annotations

from fastapi import APIRouter, Header, HTTPException, Request

from lead_qualifier.api.schemas import BridgeQualificationRequest
from lead_qualifier.core.settings import Settings
from lead_qualifier.services.bridge_security import verify_bridge_signature
from lead_qualifier.services.meta_integration import MetaIntegrationError, MetaIntegrationService
from lead_qualifier.services.outbound import OutboundMessageService
from lead_qualifier.storage.bot_config_store import BotConfigStore


def build_internal_router(
    settings: Settings,
    config_store: BotConfigStore,
    meta_integration: MetaIntegrationService,
    outbound_service: OutboundMessageService,
) -> APIRouter:
    router = APIRouter(prefix="/api/internal", tags=["internal"])

    def _require_lead_manager_api_key(x_api_key: str | None) -> None:
        expected = (settings.lead_manager_api_key or "").strip()
        if not expected:
            return
        if (x_api_key or "").strip() != expected:
            raise HTTPException(status_code=401, detail="Invalid API key.")

    @router.post("/qualification/start")
    async def start_qualification(
        payload: BridgeQualificationRequest,
        request: Request,
        x_gelo_bridge_timestamp: str | None = Header(default=None),
        x_gelo_bridge_signature: str | None = Header(default=None),
    ) -> dict:
        bridge = meta_integration.get_runtime_page_bridge(payload.page_id)
        if not bridge:
            raise HTTPException(status_code=404, detail="Bridge pagina non trovato.")
        expected_bot_id = str(bridge.get("qualifier_bot_id") or "").strip()
        if not expected_bot_id or expected_bot_id != payload.bot_id:
            raise HTTPException(status_code=403, detail="Configurazione bot non autorizzata per questa pagina.")

        secret_id = str(bridge.get("qualifier_bridge_secret_id") or "").strip()
        secret = str(bridge.get("bridge_secret") or "").strip()
        if not secret_id and not secret:
            raise HTTPException(status_code=403, detail="Bridge secret non configurato.")
        if not secret:
            try:
                secret = meta_integration.read_bridge_secret(secret_id)
            except MetaIntegrationError as exc:
                raise HTTPException(status_code=500, detail=str(exc)) from exc

        raw_body = (await request.body()).decode("utf-8")
        if not x_gelo_bridge_timestamp or not x_gelo_bridge_signature:
            raise HTTPException(status_code=401, detail="Firma bridge mancante.")
        if not verify_bridge_signature(
            secret=secret,
            timestamp=x_gelo_bridge_timestamp,
            body=raw_body,
            provided_signature=x_gelo_bridge_signature,
        ):
            raise HTTPException(status_code=401, detail="Firma bridge non valida.")

        try:
            response = outbound_service.start_qualification_from_bridge(
                bot_id=payload.bot_id,
                phone=payload.phone,
                full_name=payload.full_name or "",
            )
        except Exception as exc:  # noqa: BLE001
            raise HTTPException(status_code=502, detail=str(exc)) from exc

        return {
            "status": "started",
            "bot_id": payload.bot_id,
            "page_id": payload.page_id,
            "phone": payload.phone,
            "response": response,
        }

    @router.get("/qualifier/bots")
    async def list_internal_qualifier_bots(
        owner_user_id: str,
        x_api_key: str | None = Header(default=None),
    ) -> list[dict]:
        _require_lead_manager_api_key(x_api_key)
        cleaned_owner_user_id = owner_user_id.strip()
        return [
            {
                "id": config.id,
                "name": config.name,
                "lead_manager_page_id": config.lead_manager_page_id,
                "lead_manager_page_name": config.lead_manager_page_name,
                "phone_number_id": config.phone_number_id,
                "whatsapp_display_phone_number": config.whatsapp_display_phone_number,
                "default_template_name": config.default_template_name,
                "template_language": config.template_language,
            }
            for config in config_store.list_configs()
            if config.owner_user_id == cleaned_owner_user_id
        ]

    @router.post("/qualifier/page-link")
    async def sync_internal_page_link(
        payload: dict,
        x_api_key: str | None = Header(default=None),
    ) -> dict:
        _require_lead_manager_api_key(x_api_key)
        owner_user_id = str(payload.get("owner_user_id") or "").strip()
        bot_id = str(payload.get("bot_id") or "").strip()
        page_id = str(payload.get("page_id") or "").strip()
        page_name = str(payload.get("page_name") or "").strip()
        if not owner_user_id or not bot_id:
            raise HTTPException(status_code=400, detail="owner_user_id e bot_id sono obbligatori.")

        config = config_store.get(bot_id)
        if config is None or (config.owner_user_id and config.owner_user_id != owner_user_id):
            raise HTTPException(status_code=404, detail="Bot non trovato.")

        saved = config_store.upsert(
            config.model_copy(
                update={
                    "lead_manager_page_id": page_id,
                    "lead_manager_page_name": page_name,
                }
            )
        )
        return saved.model_dump(mode="json")

    return router
