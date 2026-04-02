from __future__ import annotations

import json

from psycopg.rows import dict_row
from psycopg_pool import ConnectionPool

from lead_qualifier.models import LeadState, StoredMessage

SCHEMA_NAME = "lead_qualifier"
MESSAGES_TABLE = f"{SCHEMA_NAME}.conversation_messages"
LEAD_STATES_TABLE = f"{SCHEMA_NAME}.lead_states"
INBOUND_MESSAGES_TABLE = f"{SCHEMA_NAME}.inbound_messages"


class PostgresLeadStore:
    def __init__(
        self,
        database_url: str,
        *,
        min_size: int,
        max_size: int,
        timeout_seconds: float,
    ) -> None:
        self._pool = ConnectionPool(
            conninfo=database_url,
            min_size=min_size,
            max_size=max_size,
            timeout=timeout_seconds,
            open=True,
            kwargs={
                "autocommit": False,
                "row_factory": dict_row,
            },
        )
        self._pool.wait()

    def list_messages(self, wa_id: str) -> list[StoredMessage]:
        with self._pool.connection() as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    f"""
                    SELECT role, display_text, api_content
                    FROM {MESSAGES_TABLE}
                    WHERE wa_id = %s
                    ORDER BY id ASC
                    """,
                    (wa_id,),
                )
                rows = cursor.fetchall()

        return [
            StoredMessage(role=row["role"], display=row["display_text"], api_content=row["api_content"])
            for row in rows
        ]

    def save_message(self, wa_id: str, message: StoredMessage) -> None:
        with self._pool.connection() as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    f"""
                    INSERT INTO {MESSAGES_TABLE} (wa_id, role, display_text, api_content)
                    VALUES (%s, %s, %s, %s)
                    """,
                    (wa_id, message.role, message.display, message.api_content),
                )

    def get_lead_state(self, wa_id: str) -> LeadState | None:
        with self._pool.connection() as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    f"""
                    SELECT
                        zona_lavoro,
                        tipo_lavoro,
                        tempistica,
                        budget_indicativo,
                        disponibile_chiamata,
                        disponibile_sopralluogo,
                        stato_qualifica,
                        missing_fields_json::text AS missing_fields_json,
                        summary
                    FROM {LEAD_STATES_TABLE}
                    WHERE wa_id = %s
                    """,
                    (wa_id,),
                )
                row = cursor.fetchone()

        if row is None:
            return None

        return LeadState(
            zona_lavoro=row["zona_lavoro"],
            tipo_lavoro=row["tipo_lavoro"],
            tempistica=row["tempistica"],
            budget_indicativo=row["budget_indicativo"],
            disponibile_chiamata=row["disponibile_chiamata"],
            disponibile_sopralluogo=row["disponibile_sopralluogo"],
            stato_qualifica=row["stato_qualifica"],
            missing_fields=json.loads(row["missing_fields_json"]),
            summary=row["summary"],
        )

    def save_lead_state(self, wa_id: str, lead_state: LeadState) -> None:
        with self._pool.connection() as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    f"""
                    INSERT INTO {LEAD_STATES_TABLE} (
                        wa_id,
                        zona_lavoro,
                        tipo_lavoro,
                        tempistica,
                        budget_indicativo,
                        disponibile_chiamata,
                        disponibile_sopralluogo,
                        stato_qualifica,
                        missing_fields_json,
                        summary,
                        updated_at
                    )
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s::jsonb, %s, timezone('utc', now()))
                    ON CONFLICT (wa_id) DO UPDATE SET
                        zona_lavoro = excluded.zona_lavoro,
                        tipo_lavoro = excluded.tipo_lavoro,
                        tempistica = excluded.tempistica,
                        budget_indicativo = excluded.budget_indicativo,
                        disponibile_chiamata = excluded.disponibile_chiamata,
                        disponibile_sopralluogo = excluded.disponibile_sopralluogo,
                        stato_qualifica = excluded.stato_qualifica,
                        missing_fields_json = excluded.missing_fields_json,
                        summary = excluded.summary,
                        updated_at = timezone('utc', now())
                    """,
                    (
                        wa_id,
                        lead_state.zona_lavoro,
                        lead_state.tipo_lavoro,
                        lead_state.tempistica,
                        lead_state.budget_indicativo,
                        lead_state.disponibile_chiamata,
                        lead_state.disponibile_sopralluogo,
                        lead_state.stato_qualifica,
                        json.dumps(lead_state.missing_fields, ensure_ascii=False),
                        lead_state.summary,
                    ),
                )

    def reserve_inbound_message(self, message_id: str, wa_id: str) -> bool:
        with self._pool.connection() as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    f"""
                    INSERT INTO {INBOUND_MESSAGES_TABLE} (message_id, wa_id, status)
                    VALUES (%s, %s, 'processing')
                    ON CONFLICT (message_id) DO NOTHING
                    RETURNING message_id
                    """,
                    (message_id, wa_id),
                )
                return cursor.fetchone() is not None

    def mark_inbound_message_completed(self, message_id: str) -> None:
        with self._pool.connection() as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    f"""
                    UPDATE {INBOUND_MESSAGES_TABLE}
                    SET status = 'completed', error = '', updated_at = timezone('utc', now())
                    WHERE message_id = %s
                    """,
                    (message_id,),
                )

    def mark_inbound_message_failed(self, message_id: str, error: str) -> None:
        with self._pool.connection() as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    f"""
                    UPDATE {INBOUND_MESSAGES_TABLE}
                    SET status = 'failed', error = %s, updated_at = timezone('utc', now())
                    WHERE message_id = %s
                    """,
                    (error[:1000], message_id),
                )

    def healthcheck(self) -> None:
        with self._pool.connection() as connection:
            with connection.cursor() as cursor:
                cursor.execute("SELECT 1")
                cursor.fetchone()

    def close(self) -> None:
        self._pool.close()
