from __future__ import annotations

from typing import Any

from fastapi import APIRouter, HTTPException, Request

from lead_qualifier.integrations.whatsapp.client import WhatsAppCloudError
from lead_qualifier.services.ghl_bot_resolver import GhlBotResolver
from lead_qualifier.services.ghl_payloads import parse_ghl_lead_payload
from lead_qualifier.services.outbound import OutboundMessageService


def build_ghl_webhook_router(
    resolver: GhlBotResolver,
    outbound_service: OutboundMessageService,
) -> APIRouter:
    router = APIRouter(tags=["ghl-webhooks"])

    @router.post("/webhooks/ghl/qualification-start")
    async def receive_ghl_lead(request: Request) -> dict[str, Any]:
        try:
            payload = await request.json()
        except Exception as exc:  # noqa: BLE001
            raise HTTPException(status_code=400, detail="Payload JSON non valido.") from exc
        if not isinstance(payload, dict):
            raise HTTPException(status_code=400, detail="Payload GHL non valido.")

        parsed = parse_ghl_lead_payload(payload)
        if not parsed.phone:
            raise HTTPException(
                status_code=400,
                detail="Telefono lead mancante nel payload GHL.",
            )

        try:
            config, matched_by = resolver.resolve(parsed)
            response = outbound_service.start_qualification_for_lead(
                bot_id=config.id,
                phone=parsed.phone,
                full_name=parsed.full_name,
            )
        except LookupError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc
        except WhatsAppCloudError as exc:
            status_code = 400 if 400 <= exc.status_code < 500 else 502
            raise HTTPException(status_code=status_code, detail=str(exc)) from exc
        except RuntimeError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc

        return {
            "status": "started",
            "bot_id": config.id,
            "matched_by": matched_by,
            "ghl_location_id": parsed.location_id,
            "phone": parsed.phone,
            "response": response,
        }

    return router
