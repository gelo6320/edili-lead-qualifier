from __future__ import annotations

import json

from psycopg.rows import dict_row
from psycopg_pool import ConnectionPool

from lead_qualifier.models import LeadState, StoredMessage


class PostgresLeadStore:
    def __init__(
        self,
        database_url: str,
        *,
        schema: str,
        min_size: int,
        max_size: int,
        timeout_seconds: float,
    ) -> None:
        self._schema = schema
        self._messages_table = f"{schema}.conversation_messages"
        self._lead_states_table = f"{schema}.lead_states"
        self._inbound_messages_table = f"{schema}.inbound_messages"
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

    def list_messages(self, bot_id: str, wa_id: str) -> list[StoredMessage]:
        with self._pool.connection() as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    f"""
                    SELECT role, display_text, api_content
                    FROM {self._messages_table}
                    WHERE bot_id = %s AND wa_id = %s
                    ORDER BY id ASC
                    """,
                    (bot_id, wa_id),
                )
                rows = cursor.fetchall()

        return [
            StoredMessage(role=row["role"], display=row["display_text"], api_content=row["api_content"])
            for row in rows
        ]

    def save_message(self, bot_id: str, wa_id: str, message: StoredMessage) -> None:
        with self._pool.connection() as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    f"""
                    INSERT INTO {self._messages_table} (bot_id, wa_id, role, display_text, api_content)
                    VALUES (%s, %s, %s, %s, %s)
                    """,
                    (bot_id, wa_id, message.role, message.display, message.api_content),
                )

    def get_lead_state(self, bot_id: str, wa_id: str) -> LeadState | None:
        with self._pool.connection() as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    f"""
                    SELECT
                        field_values_json::text AS field_values_json,
                        qualification_status,
                        missing_fields_json::text AS missing_fields_json,
                        summary
                    FROM {self._lead_states_table}
                    WHERE bot_id = %s AND wa_id = %s
                    """,
                    (bot_id, wa_id),
                )
                row = cursor.fetchone()

        if row is None:
            return None

        return LeadState(
            field_values=json.loads(row["field_values_json"]),
            qualification_status=row["qualification_status"],
            missing_fields=json.loads(row["missing_fields_json"]),
            summary=row["summary"],
        )

    def save_lead_state(self, bot_id: str, wa_id: str, lead_state: LeadState) -> None:
        with self._pool.connection() as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    f"""
                    INSERT INTO {self._lead_states_table} (
                        bot_id,
                        wa_id,
                        field_values_json,
                        qualification_status,
                        missing_fields_json,
                        summary,
                        updated_at
                    )
                    VALUES (%s, %s, %s::jsonb, %s, %s::jsonb, %s, timezone('utc', now()))
                    ON CONFLICT (bot_id, wa_id) DO UPDATE SET
                        field_values_json = excluded.field_values_json,
                        qualification_status = excluded.qualification_status,
                        missing_fields_json = excluded.missing_fields_json,
                        summary = excluded.summary,
                        updated_at = timezone('utc', now())
                    """,
                    (
                        bot_id,
                        wa_id,
                        json.dumps(lead_state.field_values, ensure_ascii=False),
                        lead_state.qualification_status,
                        json.dumps(lead_state.missing_fields, ensure_ascii=False),
                        lead_state.summary,
                    ),
                )

    def reserve_inbound_message(self, message_id: str, bot_id: str, wa_id: str) -> bool:
        with self._pool.connection() as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    f"""
                    INSERT INTO {self._inbound_messages_table} (message_id, bot_id, wa_id, status)
                    VALUES (%s, %s, %s, 'processing')
                    ON CONFLICT (message_id) DO NOTHING
                    RETURNING message_id
                    """,
                    (message_id, bot_id, wa_id),
                )
                return cursor.fetchone() is not None

    def mark_inbound_message_completed(self, message_id: str) -> None:
        with self._pool.connection() as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    f"""
                    UPDATE {self._inbound_messages_table}
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
                    UPDATE {self._inbound_messages_table}
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
