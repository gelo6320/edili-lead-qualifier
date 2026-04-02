from __future__ import annotations

from fastapi import APIRouter, HTTPException, Request

from lead_qualifier.admin_auth import require_admin_api_key
from lead_qualifier.api_models import TemplateSendRequest
from lead_qualifier.outbound_service import OutboundMessageService
from lead_qualifier.settings import Settings


def build_admin_router(settings: Settings, service: OutboundMessageService) -> APIRouter:
    router = APIRouter(prefix="/admin", tags=["admin"])

    @router.post("/whatsapp/template")
    async def send_whatsapp_template(payload: TemplateSendRequest, request: Request) -> dict:
        require_admin_api_key(request, settings)
        try:
            response = service.send_template(
                bot_id=payload.bot_id,
                to=payload.to,
                template_name=payload.template_name,
                language_code=payload.language_code,
                body_parameters=payload.body_parameters,
            )
        except FileNotFoundError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc
        except RuntimeError as exc:
            raise HTTPException(status_code=500, detail=str(exc)) from exc

        return {
            "status": "sent",
            "bot_id": payload.bot_id,
            "to": payload.to,
            "template_name": payload.template_name,
            "response": response,
        }

    return router
