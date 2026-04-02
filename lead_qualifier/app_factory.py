from __future__ import annotations

from contextlib import asynccontextmanager
import logging

from fastapi import FastAPI, HTTPException

from lead_qualifier.admin_router import build_admin_router
from lead_qualifier.anthropic_client import AnthropicLeadQualifier
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
    qualifier = AnthropicLeadQualifier(settings)
    whatsapp_client = WhatsAppCloudClient(settings)
    message_service = InboundMessageService(store, qualifier, whatsapp_client)
    outbound_service = OutboundMessageService(whatsapp_client)

    @asynccontextmanager
    async def lifespan(_: FastAPI):
        try:
            yield
        finally:
            store.close()

    app = FastAPI(
        title="WhatsApp Lead Qualifier",
        version="0.1.0",
        lifespan=lifespan,
    )
    app.include_router(build_webhook_router(settings, message_service))
    app.include_router(build_admin_router(settings, outbound_service))

    @app.get("/")
    async def root() -> dict[str, str]:
        return {
            "service": "whatsapp-lead-qualifier",
            "status": "ok",
        }

    @app.get("/healthz")
    async def healthz() -> dict[str, str]:
        try:
            store.healthcheck()
        except Exception as exc:
            raise HTTPException(status_code=503, detail="Database non raggiungibile.") from exc
        return {"status": "ok"}

    return app
