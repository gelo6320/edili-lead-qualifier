from __future__ import annotations

import base64
import hashlib
import hmac
import json
import re
import time
from datetime import datetime, timedelta, timezone
from typing import Any
from urllib.parse import urlencode

import httpx

from lead_qualifier.core.settings import Settings
from lead_qualifier.services.supabase_admin import SupabaseAdminClient, SupabaseAdminError


STATE_TTL_SECONDS = 900
PLACEHOLDER_PATTERN = re.compile(r"\{\{(\d+)\}\}")


class MetaIntegrationError(RuntimeError):
    pass


def _clean(value: object) -> str:
    return str(value or "").strip()


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _is_schema_missing_error(exc: Exception) -> bool:
    message = str(exc).lower()
    return any(
        snippet in message
        for snippet in (
            "does not exist",
            "schema cache",
            "undefined column",
            "could not find the",
            "relation ",
            "rpc",
            "function ",
        )
    )


class MetaIntegrationService:
    def __init__(self, settings: Settings, admin: SupabaseAdminClient) -> None:
        self._settings = settings
        self._admin = admin

    def build_oauth_authorize_url(self, owner_user_id: str) -> str:
        if not self._settings.meta_app_id or not self._settings.meta_app_secret:
            raise MetaIntegrationError("META_APP_ID o META_APP_SECRET non configurate.")
        if not self._settings.app_base_url:
            raise MetaIntegrationError("APP_BASE_URL non configurata.")

        callback_url = f"{self._settings.app_base_url}/api/dashboard/meta/oauth/callback"
        params = {
            "client_id": self._settings.meta_app_id,
            "redirect_uri": callback_url,
            "response_type": "code",
            "state": self._build_state(owner_user_id),
            "scope": ",".join(
                [
                    "business_management",
                    "whatsapp_business_management",
                    "whatsapp_business_messaging",
                    "pages_show_list",
                    "pages_manage_metadata",
                    "pages_read_engagement",
                    "leads_retrieval",
                ]
            ),
        }
        return f"https://www.facebook.com/{self._settings.meta_api_version}/dialog/oauth?{urlencode(params)}"

    def handle_oauth_callback(self, *, code: str, state: str) -> dict[str, str]:
        owner_user_id = self._parse_state(state)
        token = self._exchange_code_for_token(code)
        long_lived_token = self._exchange_for_long_lived_token(token["access_token"])
        profile = self._graph_get("me", long_lived_token["access_token"], params={"fields": "id,name"})

        expires_at = _utc_now() + timedelta(seconds=int(long_lived_token.get("expires_in") or 0))
        secret_id = self._upsert_secret(
            secret=long_lived_token["access_token"],
            secret_id=self.get_integration(owner_user_id).get("access_token_secret_id"),
            name=f"lead-qualifier:meta:{owner_user_id}:access-token",
            description=f"Meta access token for lead qualifier user {owner_user_id}",
        )

        try:
            self._admin.request(
                "POST",
                "/rest/v1/qualifier_meta_integrations",
                json_body=[
                    {
                        "owner_user_id": owner_user_id,
                        "meta_user_id": _clean(profile.get("id")),
                        "meta_user_name": _clean(profile.get("name")),
                        "access_token_secret_id": secret_id,
                        "token_expires_at": expires_at.isoformat(),
                        "updated_at": _utc_now().isoformat(),
                    }
                ],
                params={"on_conflict": "owner_user_id"},
                prefer="resolution=merge-duplicates",
            )
        except SupabaseAdminError as exc:
            if _is_schema_missing_error(exc):
                raise MetaIntegrationError(self._migration_missing_message()) from exc
            raise MetaIntegrationError(str(exc)) from exc

        return {
            "owner_user_id": owner_user_id,
            "meta_user_id": _clean(profile.get("id")),
            "meta_user_name": _clean(profile.get("name")),
        }

    def get_integration(self, owner_user_id: str) -> dict[str, Any]:
        if not self._admin.is_configured:
            return {}
        try:
            payload = self._admin.request(
                "GET",
                "/rest/v1/qualifier_meta_integrations",
                params={
                    "owner_user_id": f"eq.{owner_user_id}",
                    "select": "owner_user_id,meta_user_id,meta_user_name,access_token_secret_id,token_expires_at",
                    "limit": "1",
                },
            )
        except SupabaseAdminError as exc:
            if _is_schema_missing_error(exc):
                return {}
            raise MetaIntegrationError(str(exc)) from exc
        if isinstance(payload, list) and payload:
            return payload[0]
        return {}

    def get_access_token(self, owner_user_id: str) -> str:
        integration = self.get_integration(owner_user_id)
        secret_id = integration.get("access_token_secret_id")
        if not secret_id:
            raise MetaIntegrationError("Facebook non collegato per questo utente.")
        secret = self._read_secret(secret_id)
        if not secret:
            raise MetaIntegrationError("Token Meta non disponibile in Vault.")
        return secret

    def list_assets(self, owner_user_id: str) -> dict[str, Any]:
        page_options = self.list_page_options(owner_user_id)
        integration = self.get_integration(owner_user_id)
        if not integration:
            return {
                "connected": False,
                "profile": None,
                "page_options": page_options,
                "waba_options": [],
            }

        access_token = self.get_access_token(owner_user_id)
        businesses = self._list_businesses(access_token)
        waba_options: list[dict[str, Any]] = []
        seen_waba_ids: set[str] = set()
        for business in businesses:
            for waba in self._list_business_wabas(access_token, business["id"]):
                waba_id = _clean(waba.get("id"))
                if not waba_id or waba_id in seen_waba_ids:
                    continue
                seen_waba_ids.add(waba_id)
                phone_numbers = self._list_phone_numbers(access_token, waba_id)
                templates = self._list_templates(access_token, waba_id)
                waba_options.append(
                    {
                        "id": waba_id,
                        "name": _clean(waba.get("name")) or waba_id,
                        "business_id": business["id"],
                        "business_name": business["name"],
                        "phone_numbers": phone_numbers,
                        "templates": templates,
                    }
                )

        return {
            "connected": True,
            "profile": {
                "id": _clean(integration.get("meta_user_id")),
                "name": _clean(integration.get("meta_user_name")),
                "token_expires_at": _clean(integration.get("token_expires_at")),
            },
            "page_options": page_options,
            "waba_options": waba_options,
        }

    def list_page_options(self, owner_user_id: str) -> list[dict[str, str]]:
        if self._settings.lead_manager_api_url:
            try:
                return self._list_page_options_via_lead_manager(owner_user_id)
            except MetaIntegrationError:
                if not self._admin.is_configured:
                    raise
        if not self._admin.is_configured:
            return []
        try:
            payload = self._admin.request(
                "GET",
                "/rest/v1/meta_page_subscriptions",
                params={
                    "owner_user_id": f"eq.{owner_user_id}",
                    "select": "page_id,page_name,is_active,qualifier_bot_id,qualifier_bot_name",
                    "order": "page_name.asc",
                },
            )
        except SupabaseAdminError as exc:
            if _is_schema_missing_error(exc):
                try:
                    payload = self._admin.request(
                        "GET",
                        "/rest/v1/meta_page_subscriptions",
                        params={
                            "owner_user_id": f"eq.{owner_user_id}",
                            "select": "page_id,page_name,is_active",
                            "order": "page_name.asc",
                        },
                    )
                except SupabaseAdminError:
                    return []
            else:
                raise MetaIntegrationError(str(exc)) from exc
        options: list[dict[str, str]] = []
        if not isinstance(payload, list):
            return options
        for item in payload:
            if not isinstance(item, dict):
                continue
            page_id = _clean(item.get("page_id"))
            if not page_id:
                continue
            options.append(
                {
                    "id": page_id,
                    "name": _clean(item.get("page_name")) or page_id,
                    "is_active": "true" if bool(item.get("is_active")) else "false",
                    "qualifier_bot_id": _clean(item.get("qualifier_bot_id")),
                    "qualifier_bot_name": _clean(item.get("qualifier_bot_name")),
                }
            )
        return options

    def assign_page_to_bot(self, *, owner_user_id: str, page_id: str, bot_id: str, bot_name: str) -> None:
        if self._settings.lead_manager_api_url:
            self._assign_page_to_bot_via_lead_manager(
                owner_user_id=owner_user_id,
                page_id=page_id,
                bot_id=bot_id,
                bot_name=bot_name,
            )
            return
        try:
            self._admin.rpc(
                "assign_meta_page_qualifier",
                {
                    "p_owner_user_id": owner_user_id,
                    "p_page_id": page_id,
                    "p_bot_id": bot_id,
                    "p_bot_name": bot_name,
                },
            )
        except SupabaseAdminError as exc:
            if _is_schema_missing_error(exc):
                raise MetaIntegrationError(self._migration_missing_message()) from exc
            raise MetaIntegrationError(str(exc)) from exc

    def clear_page_assignment(self, *, owner_user_id: str, page_id: str) -> None:
        if self._settings.lead_manager_api_url:
            self._clear_page_assignment_via_lead_manager(
                owner_user_id=owner_user_id,
                page_id=page_id,
            )
            return
        try:
            self._admin.rpc(
                "clear_meta_page_qualifier",
                {
                    "p_owner_user_id": owner_user_id,
                    "p_page_id": page_id,
                },
            )
        except SupabaseAdminError as exc:
            if _is_schema_missing_error(exc):
                raise MetaIntegrationError(self._migration_missing_message()) from exc
            raise MetaIntegrationError(str(exc)) from exc

    def get_runtime_page_bridge(self, page_id: str) -> dict[str, Any]:
        if self._settings.lead_manager_api_url:
            try:
                return self._get_runtime_page_bridge_via_lead_manager(page_id)
            except MetaIntegrationError:
                if not self._admin.is_configured:
                    raise
        if not self._admin.is_configured:
            return {}
        try:
            payload = self._admin.request(
                "GET",
                "/rest/v1/meta_page_subscriptions",
                params={
                    "page_id": f"eq.{page_id}",
                    "select": "page_id,page_name,owner_user_id,qualifier_bot_id,qualifier_bot_name,qualifier_bridge_secret_id",
                    "limit": "1",
                },
            )
        except SupabaseAdminError as exc:
            if _is_schema_missing_error(exc):
                return {}
            raise MetaIntegrationError(str(exc)) from exc
        if isinstance(payload, list) and payload:
            return payload[0]
        return {}

    def read_bridge_secret(self, secret_id: str) -> str:
        return self._read_secret(secret_id)

    def _lead_manager_request(
        self,
        method: str,
        path: str,
        *,
        params: dict[str, Any] | None = None,
        json_body: Any = None,
    ) -> Any:
        base_url = _lead_manager_base_url(self._settings.lead_manager_api_url)
        if not base_url:
            raise MetaIntegrationError("LEAD_MANAGER_API_URL non configurato.")
        headers = {"Content-Type": "application/json"}
        if self._settings.lead_manager_api_key:
            headers["X-API-Key"] = self._settings.lead_manager_api_key

        url = f"{base_url.rstrip('/')}{path}"
        try:
            response = httpx.request(
                method,
                url,
                headers=headers,
                params=params,
                json=json_body,
                timeout=30.0,
            )
        except httpx.HTTPError as exc:
            raise MetaIntegrationError(str(exc)) from exc

        if response.status_code == 204:
            return None

        try:
            payload: Any = response.json()
        except ValueError:
            payload = {"raw": response.text}

        if not response.is_success:
            raise MetaIntegrationError(str(payload))
        return payload

    def _list_page_options_via_lead_manager(self, owner_user_id: str) -> list[dict[str, str]]:
        payload = self._lead_manager_request(
            "GET",
            "/api/internal/qualifier/pages",
            params={"owner_user_id": owner_user_id},
        )
        if not isinstance(payload, list):
            raise MetaIntegrationError("Risposta lead-manager non valida.")
        return [
            {
                "id": _clean(item.get("id")),
                "name": _clean(item.get("name")) or _clean(item.get("id")),
                "is_active": _clean(item.get("is_active")) or "false",
                "qualifier_bot_id": _clean(item.get("qualifier_bot_id")),
                "qualifier_bot_name": _clean(item.get("qualifier_bot_name")),
            }
            for item in payload
            if isinstance(item, dict) and _clean(item.get("id"))
        ]

    def _assign_page_to_bot_via_lead_manager(
        self,
        *,
        owner_user_id: str,
        page_id: str,
        bot_id: str,
        bot_name: str,
    ) -> None:
        self._lead_manager_request(
            "POST",
            "/api/internal/qualifier/assignment",
            json_body={
                "owner_user_id": owner_user_id,
                "page_id": page_id,
                "bot_id": bot_id,
                "bot_name": bot_name,
            },
        )

    def _clear_page_assignment_via_lead_manager(
        self,
        *,
        owner_user_id: str,
        page_id: str,
    ) -> None:
        self._lead_manager_request(
            "POST",
            "/api/internal/qualifier/assignment",
            json_body={
                "owner_user_id": owner_user_id,
                "page_id": page_id,
            },
        )

    def _get_runtime_page_bridge_via_lead_manager(self, page_id: str) -> dict[str, Any]:
        payload = self._lead_manager_request(
            "GET",
            "/api/internal/qualifier/page-bridge",
            params={"page_id": page_id},
        )
        if isinstance(payload, dict):
            return payload
        raise MetaIntegrationError("Risposta bridge lead-manager non valida.")

    def _exchange_code_for_token(self, code: str) -> dict[str, Any]:
        callback_url = f"{self._settings.app_base_url}/api/dashboard/meta/oauth/callback"
        params = {
            "client_id": self._settings.meta_app_id,
            "client_secret": self._settings.meta_app_secret,
            "redirect_uri": callback_url,
            "code": code,
        }
        return self._direct_request("GET", f"/oauth/access_token", params=params)

    def _exchange_for_long_lived_token(self, short_lived_token: str) -> dict[str, Any]:
        params = {
            "grant_type": "fb_exchange_token",
            "client_id": self._settings.meta_app_id,
            "client_secret": self._settings.meta_app_secret,
            "fb_exchange_token": short_lived_token,
        }
        return self._direct_request("GET", "/oauth/access_token", params=params)

    def _list_businesses(self, access_token: str) -> list[dict[str, str]]:
        payload = self._graph_get("me/businesses", access_token, params={"fields": "id,name"})
        return [
            {"id": _clean(item.get("id")), "name": _clean(item.get("name"))}
            for item in payload.get("data", [])
            if _clean(item.get("id"))
        ]

    def _list_business_wabas(self, access_token: str, business_id: str) -> list[dict[str, str]]:
        results: list[dict[str, str]] = []
        for edge in (
            "owned_whatsapp_business_accounts",
            "client_whatsapp_business_accounts",
        ):
            payload = self._graph_get(f"{business_id}/{edge}", access_token, params={"fields": "id,name"})
            for item in payload.get("data", []):
                waba_id = _clean(item.get("id"))
                if not waba_id:
                    continue
                results.append({"id": waba_id, "name": _clean(item.get("name")) or waba_id})
        return results

    def _list_phone_numbers(self, access_token: str, waba_id: str) -> list[dict[str, str]]:
        payload = self._graph_get(
            f"{waba_id}/phone_numbers",
            access_token,
            params={"fields": "id,display_phone_number,verified_name,name_status"},
        )
        return [
            {
                "id": _clean(item.get("id")),
                "display_phone_number": _clean(item.get("display_phone_number")),
                "verified_name": _clean(item.get("verified_name")),
                "name_status": _clean(item.get("name_status")),
            }
            for item in payload.get("data", [])
            if _clean(item.get("id"))
        ]

    def _list_templates(self, access_token: str, waba_id: str) -> list[dict[str, Any]]:
        url = None
        templates: list[dict[str, Any]] = []
        params = {
            "fields": "id,name,language,status,category,components",
            "limit": 200,
        }
        while True:
            payload = self._graph_get(
                f"{waba_id}/message_templates" if url is None else url,
                access_token,
                params=params if url is None else None,
                absolute=url is not None,
            )
            for item in payload.get("data", []):
                status = _clean(item.get("status")).upper()
                if status and status != "APPROVED":
                    continue
                templates.append(
                    {
                        "id": _clean(item.get("id")),
                        "name": _clean(item.get("name")),
                        "language": _clean(item.get("language")) or "it",
                        "status": status,
                        "category": _clean(item.get("category")),
                        "body_variable_count": _infer_template_variable_count(item.get("components")),
                    }
                )
            url = payload.get("paging", {}).get("next")
            if not url:
                break
            params = None

        templates.sort(key=lambda item: (item["name"], item["language"]))
        return templates

    def _graph_get(
        self,
        endpoint_or_url: str,
        access_token: str,
        *,
        params: dict[str, Any] | None = None,
        absolute: bool = False,
    ) -> dict[str, Any]:
        query_params = dict(params or {})
        query_params["access_token"] = access_token
        return self._direct_request(
            "GET",
            endpoint_or_url if absolute else f"/{self._settings.meta_api_version}/{endpoint_or_url}",
            params=query_params,
            absolute=absolute,
        )

    def _direct_request(
        self,
        method: str,
        path_or_url: str,
        *,
        params: dict[str, Any] | None = None,
        absolute: bool = False,
    ) -> dict[str, Any]:
        url = path_or_url if absolute else f"https://graph.facebook.com{path_or_url}"
        try:
            response = httpx.request(method, url, params=params, timeout=30.0)
        except httpx.HTTPError as exc:
            raise MetaIntegrationError(str(exc)) from exc

        try:
            payload = response.json()
        except ValueError:
            payload = {"raw": response.text}
        if not response.is_success:
            raise MetaIntegrationError(str(payload))
        if not isinstance(payload, dict):
            raise MetaIntegrationError("Risposta Meta non valida.")
        return payload

    def _build_state(self, owner_user_id: str) -> str:
        if not self._settings.oauth_state_secret:
            raise MetaIntegrationError("OAUTH_STATE_SECRET non configurata.")
        payload = {
            "sub": owner_user_id,
            "iat": int(time.time()),
        }
        raw = json.dumps(payload, separators=(",", ":"), sort_keys=True).encode("utf-8")
        signature = hmac.new(
            self._settings.oauth_state_secret.encode("utf-8"),
            raw,
            hashlib.sha256,
        ).hexdigest()
        encoded = base64.urlsafe_b64encode(raw).decode("ascii")
        return f"{encoded}.{signature}"

    def _parse_state(self, state: str) -> str:
        if not self._settings.oauth_state_secret:
            raise MetaIntegrationError("OAUTH_STATE_SECRET non configurata.")
        encoded, separator, signature = state.partition(".")
        if not separator or not encoded or not signature:
            raise MetaIntegrationError("State OAuth non valido.")
        try:
            raw = base64.urlsafe_b64decode(encoded.encode("ascii"))
        except Exception as exc:  # noqa: BLE001
            raise MetaIntegrationError("State OAuth non valido.") from exc

        expected_signature = hmac.new(
            self._settings.oauth_state_secret.encode("utf-8"),
            raw,
            hashlib.sha256,
        ).hexdigest()
        if not hmac.compare_digest(expected_signature, signature):
            raise MetaIntegrationError("Firma state OAuth non valida.")

        payload = json.loads(raw.decode("utf-8"))
        issued_at = int(payload.get("iat") or 0)
        if issued_at <= 0 or (time.time() - issued_at) > STATE_TTL_SECONDS:
            raise MetaIntegrationError("State OAuth scaduto.")
        owner_user_id = _clean(payload.get("sub"))
        if not owner_user_id:
            raise MetaIntegrationError("State OAuth privo di owner.")
        return owner_user_id

    def _upsert_secret(
        self,
        *,
        secret: str,
        secret_id: object = None,
        name: str | None = None,
        description: str | None = None,
    ) -> str:
        try:
            payload = self._admin.rpc(
                "upsert_vault_secret",
                {
                    "p_secret": secret,
                    "p_secret_id": _clean(secret_id) or None,
                    "p_name": name,
                    "p_description": description,
                },
            )
        except SupabaseAdminError as exc:
            if _is_schema_missing_error(exc):
                raise MetaIntegrationError(self._migration_missing_message()) from exc
            raise MetaIntegrationError(str(exc)) from exc
        return _extract_rpc_scalar(payload, "secret_id")

    def _read_secret(self, secret_id: object) -> str:
        try:
            payload = self._admin.rpc(
                "read_vault_secret",
                {"p_secret_id": _clean(secret_id)},
            )
        except SupabaseAdminError as exc:
            if _is_schema_missing_error(exc):
                raise MetaIntegrationError(self._migration_missing_message()) from exc
            raise MetaIntegrationError(str(exc)) from exc
        secret = _extract_rpc_scalar(payload, "secret")
        if not secret:
            raise MetaIntegrationError("Segreto Vault non trovato.")
        return secret

    @staticmethod
    def _migration_missing_message() -> str:
        return (
            "Schema Supabase non aggiornato per integrazione Meta/bridge. "
            "Applica la migration 20260405_180000_add_meta_bridge_and_knowledge.sql."
        )


def _infer_template_variable_count(components: object) -> int:
    if not isinstance(components, list):
        return 0
    max_placeholder = 0
    for component in components:
        if not isinstance(component, dict):
            continue
        if _clean(component.get("type")).upper() != "BODY":
            continue
        for match in PLACEHOLDER_PATTERN.findall(_clean(component.get("text"))):
            max_placeholder = max(max_placeholder, int(match))
    return max_placeholder


def _extract_rpc_scalar(payload: Any, key: str) -> str:
    if isinstance(payload, list) and payload:
        first = payload[0]
        if isinstance(first, dict):
            return _clean(first.get(key))
        return _clean(first)
    if isinstance(payload, dict):
        return _clean(payload.get(key))
    return _clean(payload)


def _lead_manager_base_url(configured_url: str) -> str:
    normalized = _clean(configured_url).rstrip("/")
    if normalized.endswith("/api/leads/custom"):
        return normalized[: -len("/api/leads/custom")]
    return normalized
