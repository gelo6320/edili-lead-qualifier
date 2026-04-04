from __future__ import annotations

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import RedirectResponse

from dataclasses import asdict

from lead_qualifier.api.dashboard_auth import require_dashboard_user
from lead_qualifier.api.schemas import (
    BotConfigRequest,
    SiteCrawlRequest,
    TemplateSendRequest,
    TemplateTestRequest,
)
from lead_qualifier.core.settings import Settings
from lead_qualifier.domain.bot_config import BotConfig
from lead_qualifier.services.outbound import OutboundMessageService
from lead_qualifier.services.meta_integration import MetaIntegrationError, MetaIntegrationService
from lead_qualifier.services.website_personalization import (
    WebsitePersonalizationError,
    WebsitePersonalizationService,
)
from lead_qualifier.storage.bot_config_store import BotConfigStore
from lead_qualifier.storage.protocol import LeadStore


def build_dashboard_api_router(
    settings: Settings,
    config_store: BotConfigStore,
    outbound_service: OutboundMessageService,
    lead_store: LeadStore | None = None,
    meta_integration: MetaIntegrationService | None = None,
    website_personalization: WebsitePersonalizationService | None = None,
) -> APIRouter:
    router = APIRouter(prefix="/api/dashboard", tags=["dashboard"])

    @router.get("/app-config")
    async def get_app_config() -> dict:
        return {
            "supabase_url": settings.supabase_url,
            "supabase_publishable_key": settings.supabase_publishable_key,
            "meta_oauth_enabled": bool(
                settings.meta_app_id
                and settings.meta_app_secret
                and settings.app_base_url
                and settings.supabase_service_role_key
            ),
            "cloudflare_crawl_enabled": bool(settings.cloudflare_account_id and settings.cloudflare_api_token),
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
        user = await require_dashboard_user(request, settings)
        return [
            config.model_dump(mode="json")
            for config in config_store.list_configs()
            if not config.owner_user_id or config.owner_user_id == user.id
        ]

    @router.get("/bots/{bot_id}")
    async def get_bot(bot_id: str, request: Request) -> dict:
        user = await require_dashboard_user(request, settings)
        config = config_store.get(bot_id)
        if config is None or (config.owner_user_id and config.owner_user_id != user.id):
            raise HTTPException(status_code=404, detail="Bot non trovato.")
        return config.model_dump(mode="json")

    @router.post("/bots")
    async def create_bot(payload: BotConfigRequest, request: Request) -> dict:
        user = await require_dashboard_user(request, settings)
        if config_store.get(payload.id):
            raise HTTPException(status_code=409, detail="Esiste gia un bot con questo id.")
        prepared_payload = BotConfigRequest.model_validate(
            {
                **payload.model_dump(mode="json"),
                "owner_user_id": user.id,
            }
        )
        saved = config_store.upsert(prepared_payload)
        _sync_page_assignment(meta_integration, user.id, saved, previous_config=None)
        return saved.model_dump(mode="json")

    @router.put("/bots/{bot_id}")
    async def update_bot(bot_id: str, payload: BotConfigRequest, request: Request) -> dict:
        user = await require_dashboard_user(request, settings)
        if payload.id != bot_id:
            raise HTTPException(status_code=400, detail="bot_id nel path e nel payload non coincidono.")
        previous_config = config_store.get(bot_id)
        if previous_config is None or (previous_config.owner_user_id and previous_config.owner_user_id != user.id):
            raise HTTPException(status_code=404, detail="Bot non trovato.")
        prepared_payload = BotConfigRequest.model_validate(
            {
                **payload.model_dump(mode="json"),
                "owner_user_id": user.id,
            }
        )
        saved = config_store.upsert(prepared_payload)
        _sync_page_assignment(meta_integration, user.id, saved, previous_config=previous_config)
        return saved.model_dump(mode="json")

    @router.delete("/bots/{bot_id}")
    async def delete_bot(bot_id: str, request: Request) -> dict:
        user = await require_dashboard_user(request, settings)
        existing = config_store.get(bot_id)
        if existing is None or (existing.owner_user_id and existing.owner_user_id != user.id):
            raise HTTPException(status_code=404, detail="Bot non trovato.")
        if meta_integration and existing.lead_manager_page_id:
            try:
                meta_integration.clear_page_assignment(
                    owner_user_id=user.id,
                    page_id=existing.lead_manager_page_id,
                )
            except MetaIntegrationError as exc:
                raise HTTPException(status_code=502, detail=str(exc)) from exc
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

    @router.post("/bots/{bot_id}/test-template")
    async def send_test_template(bot_id: str, payload: TemplateTestRequest, request: Request) -> dict:
        await require_dashboard_user(request, settings)
        if config_store.get(bot_id) is None:
            raise HTTPException(status_code=404, detail="Bot non trovato.")
        response = outbound_service.send_test_template(
            bot_id=bot_id,
            to=payload.to,
            template_name=payload.template_name,
            language_code=payload.language_code,
            body_parameters=payload.body_parameters,
        )
        return {
            "status": "sent",
            "response": response,
        }

    @router.get("/bots/{bot_id}/leads")
    async def list_leads(bot_id: str, request: Request) -> list[dict]:
        await require_dashboard_user(request, settings)
        if lead_store is None:
            raise HTTPException(status_code=501, detail="Lead store non disponibile.")
        if config_store.get(bot_id) is None:
            raise HTTPException(status_code=404, detail="Bot non trovato.")
        return [asdict(lead) for lead in lead_store.list_leads(bot_id)]

    @router.get("/bots/{bot_id}/leads/{wa_id}/messages")
    async def list_lead_messages(bot_id: str, wa_id: str, request: Request) -> list[dict]:
        await require_dashboard_user(request, settings)
        if lead_store is None:
            raise HTTPException(status_code=501, detail="Lead store non disponibile.")
        if config_store.get(bot_id) is None:
            raise HTTPException(status_code=404, detail="Bot non trovato.")
        messages = lead_store.list_messages(bot_id, wa_id)
        return [{"role": m.role, "display": m.display} for m in messages]

    @router.get("/meta/oauth/start")
    async def start_meta_oauth(request: Request) -> dict:
        if meta_integration is None:
            raise HTTPException(status_code=503, detail="Integrazione Meta non disponibile.")
        user = await require_dashboard_user(request, settings)
        try:
            return {
                "authorize_url": meta_integration.build_oauth_authorize_url(user.id),
            }
        except MetaIntegrationError as exc:
            raise HTTPException(status_code=500, detail=str(exc)) from exc

    @router.get("/meta/oauth/callback")
    async def meta_oauth_callback(code: str | None = None, state: str | None = None, error: str | None = None):
        if meta_integration is None:
            raise HTTPException(status_code=503, detail="Integrazione Meta non disponibile.")
        redirect_base = settings.app_base_url or ""
        if not redirect_base:
            raise HTTPException(status_code=500, detail="APP_BASE_URL non configurata.")
        if error:
            return RedirectResponse(url=f"{redirect_base}/?meta_oauth=error&message={error}")
        if not code or not state:
            return RedirectResponse(url=f"{redirect_base}/?meta_oauth=error&message=missing_code")
        try:
            meta_integration.handle_oauth_callback(code=code, state=state)
        except MetaIntegrationError as exc:
            return RedirectResponse(url=f"{redirect_base}/?meta_oauth=error&message={str(exc)}")
        return RedirectResponse(url=f"{redirect_base}/?meta_oauth=success")

    @router.get("/meta/assets")
    async def get_meta_assets(request: Request) -> dict:
        if meta_integration is None:
            raise HTTPException(status_code=503, detail="Integrazione Meta non disponibile.")
        user = await require_dashboard_user(request, settings)
        try:
            return meta_integration.list_assets(user.id)
        except Exception as exc:
            raise HTTPException(status_code=502, detail=str(exc)) from exc

    @router.post("/bots/{bot_id}/crawl-site")
    async def crawl_site_for_bot(bot_id: str, payload: SiteCrawlRequest, request: Request) -> dict:
        if website_personalization is None:
            raise HTTPException(status_code=503, detail="Knowledge base non disponibile.")
        user = await require_dashboard_user(request, settings)
        config = config_store.get(bot_id)
        if config is None or (config.owner_user_id and config.owner_user_id != user.id):
            raise HTTPException(status_code=404, detail="Bot non trovato.")
        try:
            result = website_personalization.personalize_bot_from_site(
                bot=config,
                owner_user_id=user.id,
                site_url=payload.site_url,
            )
        except WebsitePersonalizationError as exc:
            raise HTTPException(status_code=502, detail=str(exc)) from exc
        saved = config_store.upsert(result["bot"])
        return {
            "bot": saved.model_dump(mode="json"),
            "pages_crawled": result["pages_crawled"],
            "chunks_stored": result["chunks_stored"],
            "summary": result["summary"],
        }

    return router


def _sync_page_assignment(
    meta_integration: MetaIntegrationService | None,
    owner_user_id: str,
    config: BotConfig,
    *,
    previous_config: BotConfig | None,
) -> None:
    if meta_integration is None:
        return

    previous_page_id = previous_config.lead_manager_page_id if previous_config else ""
    next_page_id = config.lead_manager_page_id

    if previous_page_id and previous_page_id != next_page_id:
        meta_integration.clear_page_assignment(
            owner_user_id=owner_user_id,
            page_id=previous_page_id,
        )

    if next_page_id:
        meta_integration.assign_page_to_bot(
            owner_user_id=owner_user_id,
            page_id=next_page_id,
            bot_id=config.id,
            bot_name=config.name,
        )
