from __future__ import annotations

import json
from typing import Any

from anthropic import Anthropic

from lead_qualifier.core.settings import Settings
from lead_qualifier.domain.bot_config import BotConfig
from lead_qualifier.services.cloudflare_crawl import CloudflareCrawlClient
from lead_qualifier.services.knowledge_base import KnowledgeBaseService


class WebsitePersonalizationError(RuntimeError):
    pass


def _clean(value: object) -> str:
    return str(value or "").strip()


class WebsitePersonalizationService:
    def __init__(
        self,
        settings: Settings,
        crawl_client: CloudflareCrawlClient,
        knowledge_base: KnowledgeBaseService,
    ) -> None:
        self._settings = settings
        self._crawl_client = crawl_client
        self._knowledge_base = knowledge_base
        self._anthropic = Anthropic(api_key=settings.anthropic_api_key) if settings.anthropic_api_key else None

    def personalize_bot_from_site(
        self,
        *,
        bot: BotConfig,
        owner_user_id: str,
        site_url: str,
    ) -> dict[str, Any]:
        pages = self._crawl_client.crawl_markdown_site(site_url)
        if not pages:
            raise WebsitePersonalizationError("Il crawl non ha prodotto contenuti utili.")

        chunk_count = self._knowledge_base.replace_site_content(
            owner_user_id=owner_user_id,
            bot_id=bot.id,
            source_url=site_url,
            pages=pages,
        )

        summary = self._summarize_pages(bot=bot, site_url=site_url, pages=pages)
        updated_bot = BotConfig.model_validate(
            {
                **bot.model_dump(mode="json"),
                "website_url": site_url,
                "company_description": summary.get("company_description") or bot.company_description,
                "service_area": summary.get("service_area") or bot.service_area,
                "company_services": summary.get("company_services") or bot.company_services,
            }
        )

        return {
            "bot": updated_bot,
            "pages_crawled": len(pages),
            "chunks_stored": chunk_count,
            "summary": summary,
        }

    def search_context(self, *, bot_id: str, query: str, limit: int = 4) -> str:
        chunks = self._knowledge_base.search(bot_id=bot_id, query=query, limit=limit)
        if not chunks:
            return ""
        lines: list[str] = []
        for chunk in chunks:
            title = _clean(chunk.get("page_title")) or _clean(chunk.get("page_url")) or "Fonte"
            body = _clean(chunk.get("chunk_text"))
            if not body:
                continue
            lines.append(f"- {title}: {body[:700]}")
        return "\n".join(lines)

    def close(self) -> None:
        self._knowledge_base.close()

    def _summarize_pages(self, *, bot: BotConfig, site_url: str, pages: list[dict[str, str]]) -> dict[str, Any]:
        if self._anthropic is None:
            return {
                "company_description": bot.company_description,
                "service_area": bot.service_area,
                "company_services": bot.company_services,
            }

        context_parts: list[str] = []
        for page in pages[:8]:
            title = _clean(page.get("title")) or _clean(page.get("url"))
            markdown = _clean(page.get("markdown"))
            if not markdown:
                continue
            context_parts.append(f"# {title}\n{markdown[:5000]}")
        context = "\n\n".join(context_parts)[:30000]
        if not context:
            raise WebsitePersonalizationError("Contenuto sito insufficiente per personalizzare il bot.")

        schema = {
            "type": "object",
            "properties": {
                "company_description": {"type": "string"},
                "service_area": {"type": "string"},
                "company_services": {
                    "type": "array",
                    "items": {"type": "string"},
                },
            },
            "required": ["company_description", "service_area", "company_services"],
            "additionalProperties": False,
        }
        response = self._anthropic.messages.create(
            model=self._settings.anthropic_model,
            max_tokens=900,
            temperature=0.1,
            system=(
                "Analizza il contenuto di un sito aziendale e restituisci solo JSON valido. "
                "Non inventare nulla: usa stringa vuota o lista vuota quando un dato non e chiaro."
            ),
            messages=[
                {
                    "role": "user",
                    "content": (
                        f"Sito: {site_url}\n"
                        f"Bot corrente: {bot.name}\n"
                        "Estrai una descrizione breve dell'azienda, l'area geografica servita e i servizi principali.\n\n"
                        f"{context}"
                    ),
                }
            ],
            output_config={"format": {"type": "json_schema", "schema": schema}},
        )
        text = "".join(
            getattr(block, "text", "")
            for block in response.content
            if getattr(block, "type", None) == "text"
        )
        payload = json.loads(text or "{}")
        services = payload.get("company_services")
        if not isinstance(services, list):
            services = []
        payload["company_services"] = [_clean(item) for item in services if _clean(item)]
        payload["company_description"] = _clean(payload.get("company_description"))
        payload["service_area"] = _clean(payload.get("service_area"))
        return payload
