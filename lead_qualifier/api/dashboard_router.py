from __future__ import annotations

import json
from functools import partial

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import RedirectResponse
from starlette.concurrency import run_in_threadpool

from dataclasses import asdict

from lead_qualifier.api.dashboard_auth import require_dashboard_user
from lead_qualifier.api.schemas import (
    SiteCrawlRequest,
    TemplateSendRequest,
    TemplateTestRequest,
)
from lead_qualifier.core.settings import Settings
from lead_qualifier.domain.bot_config import BotConfig
from lead_qualifier.integrations.whatsapp.client import WhatsAppCloudError
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
        configs = await run_in_threadpool(
            partial(
                config_store.list_configs_filtered,
                [user.id],
                include_unowned=True,
            )
        )
        return [
            config.model_dump(mode="json")
            for config in configs
        ]

    @router.get("/bots/{bot_id}")
    async def get_bot(bot_id: str, request: Request) -> dict:
        user = await require_dashboard_user(request, settings)
        config = config_store.get(bot_id)
        if config is None or (config.owner_user_id and config.owner_user_id != user.id):
            raise HTTPException(status_code=404, detail="Bot non trovato.")
        return config.model_dump(mode="json")

    @router.post("/bots")
    async def create_bot(payload: BotConfig, request: Request) -> dict:
        user = await require_dashboard_user(request, settings)
        if config_store.get(payload.id):
            raise HTTPException(status_code=409, detail="Esiste gia un bot con questo id.")
        prepared_payload = BotConfig.model_validate(
            {
                **payload.model_dump(mode="json"),
                "owner_user_id": user.id,
            }
        )
        saved = config_store.upsert(prepared_payload)
        return saved.model_dump(mode="json")

    @router.put("/bots/{bot_id}")
    async def update_bot(bot_id: str, payload: BotConfig, request: Request) -> dict:
        user = await require_dashboard_user(request, settings)
        if payload.id != bot_id:
            raise HTTPException(status_code=400, detail="bot_id nel path e nel payload non coincidono.")
        previous_config = config_store.get(bot_id)
        if previous_config is None or (previous_config.owner_user_id and previous_config.owner_user_id != user.id):
            raise HTTPException(status_code=404, detail="Bot non trovato.")
        prepared_payload = BotConfig.model_validate(
            {
                **payload.model_dump(mode="json"),
                "owner_user_id": user.id,
            }
        )
        saved = config_store.upsert(prepared_payload)
        return saved.model_dump(mode="json")

    @router.delete("/bots/{bot_id}")
    async def delete_bot(bot_id: str, request: Request) -> dict:
        user = await require_dashboard_user(request, settings)
        existing = config_store.get(bot_id)
        if existing is None or (existing.owner_user_id and existing.owner_user_id != user.id):
            raise HTTPException(status_code=404, detail="Bot non trovato.")
        config_store.delete(bot_id)
        return {"status": "deleted", "bot_id": bot_id}

    @router.post("/send-template")
    async def send_template(payload: TemplateSendRequest, request: Request) -> dict:
        await require_dashboard_user(request, settings)
        try:
            response = outbound_service.send_template(
                bot_id=payload.bot_id,
                to=payload.to,
                template_name=payload.template_name,
                language_code=payload.language_code,
                body_parameters=payload.body_parameters,
            )
        except FileNotFoundError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc
        except WhatsAppCloudError as exc:
            status_code = 400 if 400 <= exc.status_code < 500 else 502
            raise HTTPException(status_code=status_code, detail=str(exc)) from exc
        except RuntimeError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        return {
            "status": "sent",
            "response": response,
        }

    @router.post("/bots/{bot_id}/test-template")
    async def send_test_template(bot_id: str, payload: TemplateTestRequest, request: Request) -> dict:
        await require_dashboard_user(request, settings)
        if config_store.get(bot_id) is None:
            raise HTTPException(status_code=404, detail="Bot non trovato.")
        try:
            response = outbound_service.send_test_template(
                bot_id=bot_id,
                to=payload.to,
                template_name=payload.template_name,
                language_code=payload.language_code,
                body_parameters=payload.body_parameters,
            )
        except WhatsAppCloudError as exc:
            status_code = 400 if 400 <= exc.status_code < 500 else 502
            raise HTTPException(status_code=status_code, detail=str(exc)) from exc
        except RuntimeError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
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
        lead_state = lead_store.get_lead_state(bot_id, wa_id)
        fallback_image_urls = lead_state.metadata.image_public_urls if lead_state else []
        fallback_index = 0
        response: list[dict] = []
        for message in messages:
            image_urls, image_block_count = _extract_message_images(message.api_content)
            if image_block_count:
                if not image_urls:
                    image_urls = fallback_image_urls[fallback_index : fallback_index + image_block_count]
                fallback_index += image_block_count
            response.append(
                {
                    "role": message.role,
                    "display": _resolve_message_display(message.display, message.api_content),
                    "images": image_urls,
                }
            )
        return response

    @router.delete("/bots/{bot_id}/leads/{wa_id}")
    async def delete_lead_conversation(bot_id: str, wa_id: str, request: Request) -> dict:
        await require_dashboard_user(request, settings)
        if lead_store is None:
            raise HTTPException(status_code=501, detail="Lead store non disponibile.")
        if config_store.get(bot_id) is None:
            raise HTTPException(status_code=404, detail="Bot non trovato.")
        lead_store.delete_lead_conversation(bot_id, wa_id)
        return {"status": "deleted", "bot_id": bot_id, "wa_id": wa_id}

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
            return await run_in_threadpool(
                partial(
                    meta_integration.list_assets,
                    user.id,
                    owner_email=user.email,
                )
            )
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
            result = await run_in_threadpool(
                partial(
                    website_personalization.personalize_bot_from_site,
                    bot=config,
                    owner_user_id=user.id,
                    site_url=payload.site_url,
                )
            )
        except WebsitePersonalizationError as exc:
            raise HTTPException(status_code=502, detail=str(exc)) from exc
        saved = await run_in_threadpool(config_store.upsert, result["bot"])
        return {
            "bot": saved.model_dump(mode="json"),
            "pages_crawled": result["pages_crawled"],
            "chunks_stored": result["chunks_stored"],
            "summary": result["summary"],
        }

    return router


def _extract_message_images(api_content: str) -> tuple[list[str], int]:
    try:
        payload = json.loads(api_content)
    except json.JSONDecodeError:
        return [], 0

    blocks: list[dict] = []
    image_urls: list[str] = []

    if isinstance(payload, list):
        blocks = [block for block in payload if isinstance(block, dict)]
    elif isinstance(payload, dict):
        content = payload.get("content")
        if isinstance(content, list):
            blocks = [block for block in content if isinstance(block, dict)]
        images = payload.get("images")
        if isinstance(images, list):
            for image in images:
                if isinstance(image, str) and image.strip():
                    image_urls.append(image.strip())
                elif isinstance(image, dict):
                    url = str(image.get("url", "")).strip()
                    if url:
                        image_urls.append(url)

    image_block_count = sum(
        1
        for block in blocks
        if str(block.get("type", "")).strip() == "image"
    )
    if not image_urls:
        image_urls = _extract_image_urls_from_blocks(blocks)
    return image_urls, image_block_count


def _resolve_message_display(display: str, api_content: str) -> str:
    try:
        payload = json.loads(api_content)
    except json.JSONDecodeError:
        return display

    if not isinstance(payload, dict):
        return display
    if payload.get("kind") != "outbound_template":
        return display

    rendered_text = str(payload.get("rendered_text", "")).strip()
    if rendered_text:
        return rendered_text

    template_body = str(payload.get("template_body", "")).strip()
    if not template_body:
        return display

    body_parameters = [
        str(value).strip()
        for value in payload.get("body_parameters", [])
        if str(value).strip()
    ] if isinstance(payload.get("body_parameters"), list) else []
    return _render_template_text(template_body, body_parameters) or display


def _render_template_text(template_body: str, body_parameters: list[str]) -> str:
    rendered = template_body
    for index, value in enumerate(body_parameters, start=1):
        rendered = rendered.replace(f"{{{{{index}}}}}", value)
    return rendered.strip()


def _extract_image_urls_from_blocks(blocks: list[dict]) -> list[str]:
    image_urls: list[str] = []
    for block in blocks:
        if str(block.get("type", "")).strip() != "image":
            continue
        source = block.get("source")
        if not isinstance(source, dict):
            continue
        source_type = str(source.get("type", "")).strip()
        if source_type == "url":
            url = str(source.get("url", "")).strip()
            if url:
                image_urls.append(url)
            continue
        if source_type == "base64":
            media_type = str(source.get("media_type", "")).strip() or "image/jpeg"
            data = str(source.get("data", "")).strip()
            if data:
                image_urls.append(f"data:{media_type};base64,{data}")
    return image_urls
