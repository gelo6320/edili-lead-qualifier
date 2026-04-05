from __future__ import annotations

import time
from typing import Any

import httpx

from lead_qualifier.core.settings import Settings


class CloudflareCrawlError(RuntimeError):
    pass


def _clean(value: object) -> str:
    return str(value or "").strip()


class CloudflareCrawlClient:
    def __init__(self, settings: Settings) -> None:
        self._settings = settings

    @property
    def is_configured(self) -> bool:
        return bool(self._settings.cloudflare_account_id and self._settings.cloudflare_api_token)

    def crawl_markdown_site(self, site_url: str) -> list[dict[str, str]]:
        if not self.is_configured:
            raise CloudflareCrawlError("Cloudflare Browser Rendering non configurato.")

        normalized_url = _clean(site_url)
        if not normalized_url:
            raise CloudflareCrawlError("URL sito mancante.")

        job_id = self._create_job(normalized_url)
        deadline = time.time() + self._settings.cloudflare_crawl_timeout_seconds
        last_status = "queued"

        while time.time() < deadline:
            result = self._get_job(job_id)
            status = _clean(result.get("status")).lower() or last_status
            last_status = status
            if status == "completed":
                records = result.get("records")
                if not isinstance(records, list):
                    raise CloudflareCrawlError("Cloudflare /crawl non ha restituito record.")
                pages: list[dict[str, str]] = []
                for record in records:
                    if not isinstance(record, dict):
                        continue
                    markdown = _clean(record.get("markdown"))
                    if not markdown:
                        continue
                    pages.append(
                        {
                            "url": _clean(record.get("url")),
                            "title": _clean(record.get("title")),
                            "markdown": markdown,
                        }
                    )
                return pages

            if status in {"errored", "cancelled", "disallowed"}:
                raise CloudflareCrawlError(f"Crawl Cloudflare terminato con stato {status}.")

            time.sleep(2)

        raise CloudflareCrawlError(f"Crawl Cloudflare non completato entro il timeout. Stato: {last_status}.")

    def _create_job(self, site_url: str) -> str:
        payload = self._request(
            "POST",
            f"/accounts/{self._settings.cloudflare_account_id}/browser-rendering/crawl",
            json_body={
                "url": site_url,
                "limit": 25,
                "depth": 3,
                "source": "all",
                "formats": ["markdown"],
                "render": True,
                "options": {
                    "includeSubdomains": False,
                },
                "crawlPurposes": ["ai-input"],
            },
        )
        result = payload.get("result")
        if isinstance(result, dict):
            job_id = _clean(result.get("id"))
            if job_id:
                return job_id
        if isinstance(result, str) and _clean(result):
            return _clean(result)
        raise CloudflareCrawlError("Cloudflare /crawl non ha restituito un job id.")

    def _get_job(self, job_id: str) -> dict[str, Any]:
        payload = self._request(
            "GET",
            f"/accounts/{self._settings.cloudflare_account_id}/browser-rendering/crawl/{job_id}",
            params={"status": "completed"},
        )
        result = payload.get("result")
        if isinstance(result, dict):
            return result
        raise CloudflareCrawlError("Risposta Cloudflare /crawl job non valida.")

    def _request(
        self,
        method: str,
        path: str,
        *,
        json_body: Any = None,
        params: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        url = f"https://api.cloudflare.com/client/v4{path}"
        try:
            response = httpx.request(
                method,
                url,
                headers={
                    "Authorization": f"Bearer {self._settings.cloudflare_api_token}",
                    "Content-Type": "application/json",
                },
                json=json_body,
                params=params,
                timeout=45.0,
            )
        except httpx.HTTPError as exc:
            raise CloudflareCrawlError(str(exc)) from exc

        try:
            payload: dict[str, Any] = response.json()
        except ValueError:
            payload = {"success": False, "errors": [response.text]}

        if not response.is_success or payload.get("success") is False:
            errors = payload.get("errors") or payload
            if response.status_code in {401, 403}:
                raise CloudflareCrawlError(
                    "Autenticazione Cloudflare Browser Rendering fallita. "
                    "Verifica che CLOUDFLARE_API_TOKEN appartenga allo stesso account di "
                    "CLOUDFLARE_ACCOUNT_ID e abbia il permesso 'Browser Rendering - Edit'."
                )
            raise CloudflareCrawlError(str(errors))
        return payload
