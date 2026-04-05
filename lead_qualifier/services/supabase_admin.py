from __future__ import annotations

from typing import Any

import httpx

from lead_qualifier.core.settings import Settings


class SupabaseAdminError(RuntimeError):
    pass


class SupabaseAdminClient:
    def __init__(self, settings: Settings) -> None:
        self._settings = settings

    @property
    def is_configured(self) -> bool:
        return bool(self._settings.supabase_url and self._settings.supabase_service_role_key)

    def _require_config(self) -> tuple[str, str]:
        if not self.is_configured:
            raise SupabaseAdminError("SUPABASE_URL o SUPABASE_SERVICE_ROLE_KEY non configurate.")
        return self._settings.supabase_url.rstrip("/"), self._settings.supabase_service_role_key

    def request(
        self,
        method: str,
        path: str,
        *,
        json_body: Any = None,
        params: dict[str, Any] | None = None,
        prefer: str | None = None,
    ) -> Any:
        base_url, service_role_key = self._require_config()
        headers = {
            "apikey": service_role_key,
            "Authorization": f"Bearer {service_role_key}",
            "Content-Type": "application/json",
        }
        if prefer:
            headers["Prefer"] = prefer

        url = f"{base_url}{path}"
        try:
            response = httpx.request(
                method,
                url,
                headers=headers,
                json=json_body,
                params=params,
                timeout=self._settings.http_timeout_seconds,
            )
        except httpx.HTTPError as exc:
            raise SupabaseAdminError(str(exc)) from exc

        if response.status_code == 204:
            return None

        try:
            payload: Any = response.json()
        except ValueError:
            payload = {"raw": response.text}

        if not response.is_success:
            raise SupabaseAdminError(str(payload))
        return payload

    def rpc(self, fn_name: str, params: dict[str, Any] | None = None) -> Any:
        return self.request(
            "POST",
            f"/rest/v1/rpc/{fn_name}",
            json_body=params or {},
        )
