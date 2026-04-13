from __future__ import annotations

from contextlib import asynccontextmanager
import logging

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from lead_qualifier.api.admin_router import build_admin_router
from lead_qualifier.api.dashboard_router import build_dashboard_api_router
from lead_qualifier.api.ghl_webhook_router import build_ghl_webhook_router
from lead_qualifier.api.webhook_router import build_webhook_router
from lead_qualifier.core.settings import Settings
from lead_qualifier.integrations.anthropic.client import AnthropicLeadQualifier
from lead_qualifier.integrations.qualified_lead_webhook.client import QualifiedLeadWebhookClient
from lead_qualifier.integrations.whatsapp.client import WhatsAppCloudClient
from lead_qualifier.services.agent_toolbox import LeadQualifierToolbox
from lead_qualifier.services.cloudflare_crawl import CloudflareCrawlClient
from lead_qualifier.services.ghl_bot_resolver import GhlBotResolver
from lead_qualifier.services.inbound import InboundMessageService
from lead_qualifier.services.lead_media import LeadMediaService
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
    logger = logging.getLogger(__name__)

    logger.info(
        "Starting lead-qualifier model=%s db=%s graph=%s signature_enforcement=%s",
        settings.anthropic_model,
        "postgres" if settings.database_url else "sqlite",
        settings.whatsapp_graph_version,
        settings.meta_enforce_signature,
    )
    if not settings.anthropic_api_key:
        logger.warning("ANTHROPIC_API_KEY not set - agent replies will fail")
    if not settings.whatsapp_access_token and not settings.supabase_service_role_key:
        logger.warning("No WhatsApp token source configured (env or Vault)")
    if not settings.meta_app_secret and settings.meta_enforce_signature:
        logger.warning("META_APP_SECRET not set but signature enforcement is ON - webhooks will be rejected")

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
    qualified_lead_client = QualifiedLeadWebhookClient(settings)
    toolbox = LeadQualifierToolbox(qualified_lead_client)
    qualifier = AnthropicLeadQualifier(settings, toolbox)
    whatsapp_client = WhatsAppCloudClient(settings)
    lead_media = LeadMediaService(settings, whatsapp_client)
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
        lead_media,
        runtime_credentials,
        website_personalization,
    )
    outbound_service = OutboundMessageService(
        store,
        config_store,
        whatsapp_client,
        runtime_credentials,
    )
    ghl_bot_resolver = GhlBotResolver(config_store)

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
    app.include_router(build_ghl_webhook_router(ghl_bot_resolver, outbound_service))
    app.include_router(build_admin_router(settings, outbound_service))
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

    @app.get("/{asset_name}", response_model=None)
    async def dashboard_root_asset(asset_name: str):
        if "." not in asset_name:
            raise HTTPException(status_code=404, detail="Not found.")
        asset_file = settings.dashboard_dist_path / asset_name
        if asset_file.exists() and asset_file.is_file():
            return FileResponse(asset_file)
        raise HTTPException(status_code=404, detail="Not found.")

    return app
