from __future__ import annotations

from fastapi import APIRouter, Header, HTTPException, Request

from lead_qualifier.api.schemas import BridgeQualificationRequest
from lead_qualifier.services.bridge_security import verify_bridge_signature
from lead_qualifier.services.meta_integration import MetaIntegrationError, MetaIntegrationService
from lead_qualifier.services.outbound import OutboundMessageService


def build_internal_router(
    meta_integration: MetaIntegrationService,
    outbound_service: OutboundMessageService,
) -> APIRouter:
    router = APIRouter(prefix="/api/internal", tags=["internal"])

    @router.post("/qualification/start")
    async def start_qualification(
        payload: BridgeQualificationRequest,
        request: Request,
        x_gelo_bridge_timestamp: str | None = Header(default=None),
        x_gelo_bridge_signature: str | None = Header(default=None),
    ) -> dict:
        bridge = meta_integration.get_runtime_page_bridge(payload.page_id)
        if not bridge:
            raise HTTPException(status_code=404, detail="Bridge pagina non trovato.")
        expected_bot_id = str(bridge.get("qualifier_bot_id") or "").strip()
        if not expected_bot_id or expected_bot_id != payload.bot_id:
            raise HTTPException(status_code=403, detail="Configurazione bot non autorizzata per questa pagina.")

        secret_id = str(bridge.get("qualifier_bridge_secret_id") or "").strip()
        if not secret_id:
            raise HTTPException(status_code=403, detail="Bridge secret non configurato.")
        try:
            secret = meta_integration.read_bridge_secret(secret_id)
        except MetaIntegrationError as exc:
            raise HTTPException(status_code=500, detail=str(exc)) from exc

        raw_body = (await request.body()).decode("utf-8")
        if not x_gelo_bridge_timestamp or not x_gelo_bridge_signature:
            raise HTTPException(status_code=401, detail="Firma bridge mancante.")
        if not verify_bridge_signature(
            secret=secret,
            timestamp=x_gelo_bridge_timestamp,
            body=raw_body,
            provided_signature=x_gelo_bridge_signature,
        ):
            raise HTTPException(status_code=401, detail="Firma bridge non valida.")

        try:
            response = outbound_service.start_qualification_from_bridge(
                bot_id=payload.bot_id,
                phone=payload.phone,
                full_name=payload.full_name or "",
            )
        except Exception as exc:  # noqa: BLE001
            raise HTTPException(status_code=502, detail=str(exc)) from exc

        return {
            "status": "started",
            "bot_id": payload.bot_id,
            "page_id": payload.page_id,
            "phone": payload.phone,
            "response": response,
        }

    return router
