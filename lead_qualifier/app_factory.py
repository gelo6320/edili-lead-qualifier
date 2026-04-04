from __future__ import annotations

from contextlib import asynccontextmanager
import logging

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from lead_qualifier.admin_router import build_admin_router
from lead_qualifier.anthropic_client import AnthropicLeadQualifier
from lead_qualifier.bot_config_store import BotConfigStore
from lead_qualifier.dashboard_api_router import build_dashboard_api_router
from lead_qualifier.message_service import InboundMessageService
from lead_qualifier.outbound_service import OutboundMessageService
from lead_qualifier.settings import Settings
from lead_qualifier.store_factory import create_lead_store
from lead_qualifier.webhook_router import build_webhook_router
from lead_qualifier.whatsapp_client import WhatsAppCloudClient


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
    qualifier = AnthropicLeadQualifier(settings)
    whatsapp_client = WhatsAppCloudClient(settings)
    message_service = InboundMessageService(store, config_store, qualifier, whatsapp_client)
    outbound_service = OutboundMessageService(store, config_store, whatsapp_client)

    @asynccontextmanager
    async def lifespan(_: FastAPI):
        try:
            yield
        finally:
            store.close()
            config_store.close()

    app = FastAPI(
        title="WhatsApp Lead Qualifier",
        version="0.2.0",
        lifespan=lifespan,
    )
    app.include_router(build_webhook_router(settings, message_service))
    app.include_router(build_admin_router(settings, outbound_service))
    app.include_router(build_dashboard_api_router(settings, config_store, outbound_service, lead_store=store))

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
