from __future__ import annotations

import json
from typing import Any

from fastapi import APIRouter, BackgroundTasks, HTTPException, Query, Request
from fastapi.responses import JSONResponse, PlainTextResponse

from lead_qualifier.message_service import InboundMessageService
from lead_qualifier.settings import Settings
from lead_qualifier.whatsapp_security import is_valid_meta_signature


def build_webhook_router(settings: Settings, service: InboundMessageService) -> APIRouter:
    router = APIRouter()

    @router.get("/webhooks/whatsapp")
    async def verify_webhook(
        hub_mode: str | None = Query(default=None, alias="hub.mode"),
        hub_challenge: str | None = Query(default=None, alias="hub.challenge"),
        hub_verify_token: str | None = Query(default=None, alias="hub.verify_token"),
    ) -> PlainTextResponse:
        if not settings.whatsapp_verify_token:
            raise HTTPException(status_code=500, detail="WHATSAPP_VERIFY_TOKEN non configurato.")
        if hub_mode != "subscribe":
            raise HTTPException(status_code=400, detail="hub.mode non valido.")
        if hub_verify_token != settings.whatsapp_verify_token:
            raise HTTPException(status_code=403, detail="Verify token non valido.")
        return PlainTextResponse(content=hub_challenge or "", status_code=200)

    @router.post("/webhooks/whatsapp")
    async def receive_webhook(request: Request, background_tasks: BackgroundTasks) -> JSONResponse:
        raw_body = await request.body()
        signature_header = request.headers.get("X-Hub-Signature-256")

        if settings.meta_enforce_signature:
            if not is_valid_meta_signature(settings.meta_app_secret, raw_body, signature_header):
                raise HTTPException(status_code=403, detail="Firma webhook non valida.")

        try:
            payload: dict[str, Any] = json.loads(raw_body.decode("utf-8"))
        except json.JSONDecodeError as exc:
            raise HTTPException(status_code=400, detail="Payload JSON non valido.") from exc

        background_tasks.add_task(service.process_payload, payload)
        return JSONResponse(content={"status": "accepted"})

    return router
