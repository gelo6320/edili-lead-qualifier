from __future__ import annotations

from dataclasses import dataclass

import httpx
from fastapi import HTTPException, Request

from lead_qualifier.core.settings import Settings


@dataclass(frozen=True)
class DashboardUser:
    id: str
    email: str


async def require_dashboard_user(request: Request, settings: Settings) -> DashboardUser:
    if not settings.supabase_url or not settings.supabase_publishable_key:
        raise HTTPException(status_code=500, detail="Supabase Auth non configurato.")

    authorization = request.headers.get("Authorization", "").strip()
    scheme, _, token = authorization.partition(" ")
    if scheme.lower() != "bearer" or not token:
        raise HTTPException(status_code=401, detail="Sessione dashboard non valida.")

    async with httpx.AsyncClient(timeout=15.0) as client:
        response = await client.get(
            f"{settings.supabase_url}/auth/v1/user",
            headers={
                "apikey": settings.supabase_publishable_key,
                "Authorization": f"Bearer {token}",
            },
        )
    if response.status_code != 200:
        raise HTTPException(status_code=401, detail="Sessione dashboard non valida.")

    payload = response.json()
    email = str(payload.get("email", "")).strip().lower()
    if settings.dashboard_allowed_emails and email not in settings.dashboard_allowed_emails:
        raise HTTPException(status_code=403, detail="Utente non autorizzato.")

    return DashboardUser(
        id=str(payload.get("id", "")).strip(),
        email=email,
    )
