from __future__ import annotations

from contextlib import asynccontextmanager
import logging

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from lead_qualifier.api.admin_router import build_admin_router
from lead_qualifier.api.dashboard_router import build_dashboard_api_router
from lead_qualifier.api.internal_router import build_internal_router
from lead_qualifier.api.webhook_router import build_webhook_router
from lead_qualifier.core.settings import Settings
from lead_qualifier.integrations.anthropic.client import AnthropicLeadQualifier
from lead_qualifier.integrations.lead_manager.client import LeadManagerClient
from lead_qualifier.integrations.whatsapp.client import WhatsAppCloudClient
from lead_qualifier.services.agent_toolbox import LeadQualifierToolbox
from lead_qualifier.services.cloudflare_crawl import CloudflareCrawlClient
from lead_qualifier.services.inbound import InboundMessageService
from lead_qualifier.services.outbound import OutboundMessageService
from lead_qualifier.services.supabase_admin import SupabaseAdminClient
from lead_qualifier.services.meta_integration import MetaIntegrationService
from lead_qualifier.services.knowledge_base import KnowledgeBaseService
from lead_qualifier.services.runtime_credentials import RuntimeCredentialsService
from lead_qualifier.services.website_personalization import WebsitePersonalizationService
from lead_qualifier.storage.bot_config_store import BotConfigStore
from lead_qualifier.storage.factory import create_lead_store


def create_app() -> FastAPI:
    settings = Settings.from_env()
    logging.basicConfig(
        level=getattr(logging, settings.log_level, logging.INFO),
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
    )

    store = create_lead_store(settings)
    config_store = BotConfigStore(
        settings.bot_config_path,
        database_url=settings.database_url,
        schema=settings.database_schema,
        min_size=1,
        max_size=4,
        timeout_seconds=settings.database_pool_timeout_seconds,
    )
    supabase_admin = SupabaseAdminClient(settings)
    meta_integration = MetaIntegrationService(settings, supabase_admin)
    lead_manager_client = LeadManagerClient(settings, meta_integration)
    toolbox = LeadQualifierToolbox(lead_manager_client)
    qualifier = AnthropicLeadQualifier(settings, toolbox)
    whatsapp_client = WhatsAppCloudClient(settings)
    runtime_credentials = RuntimeCredentialsService(settings, meta_integration)
    knowledge_base = KnowledgeBaseService(settings)
    crawl_client = CloudflareCrawlClient(settings)
    website_personalization = WebsitePersonalizationService(
        settings,
        crawl_client,
        knowledge_base,
    )
    message_service = InboundMessageService(
        store,
        config_store,
        qualifier,
        whatsapp_client,
        runtime_credentials,
        website_personalization,
    )
    outbound_service = OutboundMessageService(
        store,
        config_store,
        whatsapp_client,
        runtime_credentials,
    )

    @asynccontextmanager
    async def lifespan(_: FastAPI):
        try:
            yield
        finally:
            store.close()
            config_store.close()
            knowledge_base.close()

    app = FastAPI(
        title="WhatsApp Lead Qualifier",
        version="0.2.0",
        lifespan=lifespan,
    )
    app.include_router(build_webhook_router(settings, message_service))
    app.include_router(build_admin_router(settings, outbound_service))
    app.include_router(build_internal_router(meta_integration, outbound_service))
    app.include_router(
        build_dashboard_api_router(
            settings,
            config_store,
            outbound_service,
            lead_store=store,
            meta_integration=meta_integration,
            website_personalization=website_personalization,
        )
    )

    assets_dir = settings.dashboard_dist_path / "assets"
    if assets_dir.exists():
        app.mount("/assets", StaticFiles(directory=assets_dir), name="dashboard-assets")

    @app.get("/", response_model=None)
    async def root():
        index_file = settings.dashboard_dist_path / "index.html"
        if index_file.exists():
            return FileResponse(index_file)
        return JSONResponse(
            {
                "service": "whatsapp-lead-qualifier",
                "status": "dashboard-build-missing",
            }
        )

    @app.get("/healthz")
    async def healthz() -> dict[str, str]:
        try:
            store.healthcheck()
        except Exception as exc:
            raise HTTPException(status_code=503, detail="Database non raggiungibile.") from exc
        return {"status": "ok"}

    return app
