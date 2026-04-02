from __future__ import annotations

import json
import sqlite3
from contextlib import contextmanager
from pathlib import Path
from typing import Iterator

from lead_qualifier.models import LeadState, StoredMessage


class SQLiteLeadStore:
    def __init__(self, db_path: Path) -> None:
        self._db_path = db_path
        self._db_path.parent.mkdir(parents=True, exist_ok=True)
        self._initialize()

    @contextmanager
    def _connection(self) -> Iterator[sqlite3.Connection]:
        connection = sqlite3.connect(self._db_path)
        connection.row_factory = sqlite3.Row
        try:
            yield connection
            connection.commit()
        finally:
            connection.close()

    def _initialize(self) -> None:
        with self._connection() as connection:
            connection.executescript(
                """
                CREATE TABLE IF NOT EXISTS conversation_messages (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    wa_id TEXT NOT NULL,
                    role TEXT NOT NULL,
                    display_text TEXT NOT NULL,
                    api_content TEXT NOT NULL,
                    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
                );

                CREATE INDEX IF NOT EXISTS idx_conversation_messages_wa_id_id
                ON conversation_messages (wa_id, id);

                CREATE TABLE IF NOT EXISTS lead_states (
                    wa_id TEXT PRIMARY KEY,
                    zona_lavoro TEXT NOT NULL,
                    tipo_lavoro TEXT NOT NULL,
                    tempistica TEXT NOT NULL,
                    budget_indicativo TEXT NOT NULL,
                    disponibile_chiamata TEXT NOT NULL,
                    disponibile_sopralluogo TEXT NOT NULL,
                    stato_qualifica TEXT NOT NULL,
                    missing_fields_json TEXT NOT NULL,
                    summary TEXT NOT NULL,
                    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
                );

                CREATE TABLE IF NOT EXISTS inbound_messages (
                    message_id TEXT PRIMARY KEY,
                    wa_id TEXT NOT NULL,
                    status TEXT NOT NULL,
                    error TEXT NOT NULL DEFAULT '',
                    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
                );
                """
            )

    def list_messages(self, wa_id: str) -> list[StoredMessage]:
        with self._connection() as connection:
            rows = connection.execute(
                """
                SELECT role, display_text, api_content
                FROM conversation_messages
                WHERE wa_id = ?
                ORDER BY id ASC
                """,
                (wa_id,),
            ).fetchall()

        return [
            StoredMessage(role=row["role"], display=row["display_text"], api_content=row["api_content"])
            for row in rows
        ]

    def save_message(self, wa_id: str, message: StoredMessage) -> None:
        with self._connection() as connection:
            connection.execute(
                """
                INSERT INTO conversation_messages (wa_id, role, display_text, api_content)
                VALUES (?, ?, ?, ?)
                """,
                (wa_id, message.role, message.display, message.api_content),
            )

    def get_lead_state(self, wa_id: str) -> LeadState | None:
        with self._connection() as connection:
            row = connection.execute(
                """
                SELECT
                    zona_lavoro,
                    tipo_lavoro,
                    tempistica,
                    budget_indicativo,
                    disponibile_chiamata,
                    disponibile_sopralluogo,
                    stato_qualifica,
                    missing_fields_json,
                    summary
                FROM lead_states
                WHERE wa_id = ?
                """,
                (wa_id,),
            ).fetchone()

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
        with self._connection() as connection:
            connection.execute(
                """
                INSERT INTO lead_states (
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
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
                ON CONFLICT(wa_id) DO UPDATE SET
                    zona_lavoro = excluded.zona_lavoro,
                    tipo_lavoro = excluded.tipo_lavoro,
                    tempistica = excluded.tempistica,
                    budget_indicativo = excluded.budget_indicativo,
                    disponibile_chiamata = excluded.disponibile_chiamata,
                    disponibile_sopralluogo = excluded.disponibile_sopralluogo,
                    stato_qualifica = excluded.stato_qualifica,
                    missing_fields_json = excluded.missing_fields_json,
                    summary = excluded.summary,
                    updated_at = CURRENT_TIMESTAMP
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
        with self._connection() as connection:
            try:
                connection.execute(
                    """
                    INSERT INTO inbound_messages (message_id, wa_id, status)
                    VALUES (?, ?, 'processing')
                    """,
                    (message_id, wa_id),
                )
                return True
            except sqlite3.IntegrityError:
                return False

    def mark_inbound_message_completed(self, message_id: str) -> None:
        with self._connection() as connection:
            connection.execute(
                """
                UPDATE inbound_messages
                SET status = 'completed', error = '', updated_at = CURRENT_TIMESTAMP
                WHERE message_id = ?
                """,
                (message_id,),
            )

    def mark_inbound_message_failed(self, message_id: str, error: str) -> None:
        with self._connection() as connection:
            connection.execute(
                """
                UPDATE inbound_messages
                SET status = 'failed', error = ?, updated_at = CURRENT_TIMESTAMP
                WHERE message_id = ?
                """,
                (error[:1000], message_id),
            )

    def healthcheck(self) -> None:
        with self._connection() as connection:
            connection.execute("SELECT 1").fetchone()

    def close(self) -> None:
        return None
