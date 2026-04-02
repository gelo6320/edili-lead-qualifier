from __future__ import annotations

from fastapi import APIRouter, HTTPException, Request

from lead_qualifier.api_models import BotConfigRequest, TemplateSendRequest
from lead_qualifier.bot_config_store import BotConfigStore
from lead_qualifier.dashboard_auth import require_dashboard_user
from lead_qualifier.outbound_service import OutboundMessageService
from lead_qualifier.settings import Settings


def build_dashboard_api_router(
    settings: Settings,
    config_store: BotConfigStore,
    outbound_service: OutboundMessageService,
) -> APIRouter:
    router = APIRouter(prefix="/api/dashboard", tags=["dashboard"])

    @router.get("/app-config")
    async def get_app_config() -> dict:
        return {
            "supabase_url": settings.supabase_url,
            "supabase_publishable_key": settings.supabase_publishable_key,
        }

    @router.get("/session")
    async def get_session(request: Request) -> dict:
        user = await require_dashboard_user(request, settings)
        return {
            "user": {
                "id": user.id,
                "email": user.email,
            },
        }

    @router.get("/bots")
    async def list_bots(request: Request) -> list[dict]:
        await require_dashboard_user(request, settings)
        return [config.model_dump(mode="json") for config in config_store.list_configs()]

    @router.get("/bots/{bot_id}")
    async def get_bot(bot_id: str, request: Request) -> dict:
        await require_dashboard_user(request, settings)
        config = config_store.get(bot_id)
        if config is None:
            raise HTTPException(status_code=404, detail="Bot non trovato.")
        return config.model_dump(mode="json")

    @router.post("/bots")
    async def create_bot(payload: BotConfigRequest, request: Request) -> dict:
        await require_dashboard_user(request, settings)
        if config_store.get(payload.id):
            raise HTTPException(status_code=409, detail="Esiste gia un bot con questo id.")
        return config_store.upsert(payload).model_dump(mode="json")

    @router.put("/bots/{bot_id}")
    async def update_bot(bot_id: str, payload: BotConfigRequest, request: Request) -> dict:
        await require_dashboard_user(request, settings)
        if payload.id != bot_id:
            raise HTTPException(status_code=400, detail="bot_id nel path e nel payload non coincidono.")
        return config_store.upsert(payload).model_dump(mode="json")

    @router.delete("/bots/{bot_id}")
    async def delete_bot(bot_id: str, request: Request) -> dict:
        await require_dashboard_user(request, settings)
        if config_store.get(bot_id) is None:
            raise HTTPException(status_code=404, detail="Bot non trovato.")
        config_store.delete(bot_id)
        return {"status": "deleted", "bot_id": bot_id}

    @router.post("/send-template")
    async def send_template(payload: TemplateSendRequest, request: Request) -> dict:
        await require_dashboard_user(request, settings)
        response = outbound_service.send_template(
            bot_id=payload.bot_id,
            to=payload.to,
            template_name=payload.template_name,
            language_code=payload.language_code,
            body_parameters=payload.body_parameters,
        )
        return {
            "status": "sent",
            "response": response,
        }

    return router
