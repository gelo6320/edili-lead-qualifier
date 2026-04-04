from __future__ import annotations

import re
from typing import Any

from psycopg.rows import dict_row
from psycopg_pool import ConnectionPool

from lead_qualifier.core.settings import Settings


MAX_CHUNK_LENGTH = 1400


class KnowledgeBaseError(RuntimeError):
    pass


def _clean(value: object) -> str:
    return str(value or "").strip()


def _normalize_markdown(markdown: str) -> str:
    text = markdown.replace("\r\n", "\n")
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def _split_markdown(markdown: str) -> list[str]:
    text = _normalize_markdown(markdown)
    if not text:
        return []

    paragraphs = [chunk.strip() for chunk in text.split("\n\n") if chunk.strip()]
    chunks: list[str] = []
    current = ""
    for paragraph in paragraphs:
        candidate = paragraph if not current else f"{current}\n\n{paragraph}"
        if len(candidate) <= MAX_CHUNK_LENGTH:
            current = candidate
            continue
        if current:
            chunks.append(current)
        if len(paragraph) <= MAX_CHUNK_LENGTH:
            current = paragraph
            continue
        start = 0
        while start < len(paragraph):
            end = min(start + MAX_CHUNK_LENGTH, len(paragraph))
            chunks.append(paragraph[start:end].strip())
            start = end
        current = ""

    if current:
        chunks.append(current)
    return chunks


class KnowledgeBaseService:
    def __init__(self, settings: Settings) -> None:
        self._pool: ConnectionPool | None = None
        if settings.database_url:
            self._pool = ConnectionPool(
                conninfo=settings.database_url,
                min_size=1,
                max_size=2,
                timeout=settings.database_pool_timeout_seconds,
                open=True,
                kwargs={
                    "autocommit": False,
                    "row_factory": dict_row,
                },
            )
            self._pool.wait()

    @property
    def is_available(self) -> bool:
        return self._pool is not None

    def close(self) -> None:
        if self._pool is not None:
            self._pool.close()

    def replace_site_content(
        self,
        *,
        owner_user_id: str,
        bot_id: str,
        source_url: str,
        pages: list[dict[str, str]],
    ) -> int:
        if self._pool is None:
            raise KnowledgeBaseError("Knowledge base non disponibile senza DATABASE_URL.")

        total_chunks = 0
        with self._pool.connection() as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    """
                    DELETE FROM public.bot_knowledge_chunks
                    WHERE bot_id = %s
                    """,
                    (bot_id,),
                )
                for page in pages:
                    page_url = _clean(page.get("url"))
                    page_title = _clean(page.get("title"))
                    markdown = _clean(page.get("markdown"))
                    for index, chunk in enumerate(_split_markdown(markdown)):
                        cursor.execute(
                            """
                            INSERT INTO public.bot_knowledge_chunks (
                                owner_user_id,
                                bot_id,
                                source_url,
                                page_url,
                                page_title,
                                chunk_index,
                                chunk_text
                            )
                            VALUES (%s, %s, %s, %s, %s, %s, %s)
                            """,
                            (
                                owner_user_id,
                                bot_id,
                                source_url,
                                page_url,
                                page_title,
                                index,
                                chunk,
                            ),
                        )
                        total_chunks += 1
        return total_chunks

    def search(self, *, bot_id: str, query: str, limit: int = 4) -> list[dict[str, Any]]:
        if self._pool is None:
            return []
        cleaned_query = _clean(query)
        if not cleaned_query:
            return []

        with self._pool.connection() as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    """
                    SELECT
                        page_url,
                        page_title,
                        chunk_text,
                        ts_rank_cd(
                            search_vector,
                            websearch_to_tsquery('simple', %s)
                        ) AS rank
                    FROM public.bot_knowledge_chunks
                    WHERE bot_id = %s
                      AND search_vector @@ websearch_to_tsquery('simple', %s)
                    ORDER BY rank DESC, id ASC
                    LIMIT %s
                    """,
                    (cleaned_query, bot_id, cleaned_query, max(limit, 1)),
                )
                rows = cursor.fetchall()
        return rows or []
