from __future__ import annotations

import logging
from typing import Any

from fastapi import APIRouter, HTTPException, Request

from lead_qualifier.integrations.whatsapp.client import WhatsAppCloudError
from lead_qualifier.services.ghl_bot_resolver import GhlBotResolver
from lead_qualifier.services.ghl_payloads import parse_ghl_lead_payload
from lead_qualifier.services.outbound import OutboundMessageService

LOGGER = logging.getLogger(__name__)


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
            LOGGER.warning("GHL webhook missing phone: location_id=%s", parsed.location_id)
            raise HTTPException(
                status_code=400,
                detail="Telefono lead mancante nel payload GHL.",
            )

        LOGGER.info(
            "GHL qualification-start phone=%s location_id=%s name=%s",
            parsed.phone, parsed.location_id, parsed.full_name,
        )

        try:
            config, matched_by = resolver.resolve(parsed)
            response = outbound_service.start_qualification_for_lead(
                bot_id=config.id,
                phone=parsed.phone,
                full_name=parsed.full_name,
            )
        except LookupError as exc:
            LOGGER.error(
                "GHL bot resolve failed phone=%s location_id=%s: %s",
                parsed.phone, parsed.location_id, exc,
            )
            raise HTTPException(status_code=404, detail=str(exc)) from exc
        except WhatsAppCloudError as exc:
            LOGGER.error(
                "GHL WhatsApp error phone=%s classification=%s: %s",
                parsed.phone, exc.classification, exc,
            )
            status_code = 400 if 400 <= exc.status_code < 500 else 502
            raise HTTPException(status_code=status_code, detail=str(exc)) from exc
        except RuntimeError as exc:
            LOGGER.error(
                "GHL qualification error phone=%s: %s", parsed.phone, exc,
            )
            raise HTTPException(status_code=400, detail=str(exc)) from exc

        LOGGER.info(
            "GHL qualification started bot=%s phone=%s matched_by=%s",
            config.id, parsed.phone, matched_by,
        )
        return {
            "status": "started",
            "bot_id": config.id,
            "matched_by": matched_by,
            "ghl_location_id": parsed.location_id,
            "phone": parsed.phone,
            "response": response,
        }

    return router
