from __future__ import annotations

from fastapi import HTTPException, Request

from lead_qualifier.settings import Settings


def require_admin_api_key(request: Request, settings: Settings) -> None:
    if not settings.admin_api_key:
        raise HTTPException(status_code=500, detail="ADMIN_API_KEY non configurata.")

    authorization = request.headers.get("Authorization", "").strip()
    scheme, _, token = authorization.partition(" ")
    if scheme.lower() != "bearer" or token != settings.admin_api_key:
        raise HTTPException(status_code=401, detail="Token amministrativo non valido.")
