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
            self._migrate_legacy_schema(connection)
            connection.executescript(
                """
                CREATE TABLE IF NOT EXISTS conversation_messages (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    bot_id TEXT NOT NULL,
                    wa_id TEXT NOT NULL,
                    role TEXT NOT NULL,
                    display_text TEXT NOT NULL,
                    api_content TEXT NOT NULL,
                    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
                );

                CREATE INDEX IF NOT EXISTS idx_conversation_messages_bot_wa_id_id
                ON conversation_messages (bot_id, wa_id, id);

                CREATE TABLE IF NOT EXISTS lead_states (
                    bot_id TEXT NOT NULL,
                    wa_id TEXT NOT NULL,
                    field_values_json TEXT NOT NULL,
                    qualification_status TEXT NOT NULL,
                    missing_fields_json TEXT NOT NULL,
                    summary TEXT NOT NULL,
                    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    PRIMARY KEY (bot_id, wa_id)
                );

                CREATE TABLE IF NOT EXISTS inbound_messages (
                    message_id TEXT PRIMARY KEY,
                    bot_id TEXT NOT NULL,
                    wa_id TEXT NOT NULL,
                    status TEXT NOT NULL,
                    error TEXT NOT NULL DEFAULT '',
                    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
                );
                """
            )

            self._backfill_legacy_rows(connection)

    @staticmethod
    def _table_columns(connection: sqlite3.Connection, table_name: str) -> set[str]:
        rows = connection.execute(f"PRAGMA table_info({table_name})").fetchall()
        return {str(row["name"]) for row in rows}

    def _migrate_legacy_schema(self, connection: sqlite3.Connection) -> None:
        legacy_migrations = {
            "conversation_messages": "bot_id",
            "lead_states": "bot_id",
            "inbound_messages": "bot_id",
        }

        for table_name, required_column in legacy_migrations.items():
            columns = self._table_columns(connection, table_name)
            if not columns or required_column in columns:
                continue

            legacy_table_name = f"legacy_{table_name}"
            connection.execute(f"DROP TABLE IF EXISTS {legacy_table_name}")
            connection.execute(f"ALTER TABLE {table_name} RENAME TO {legacy_table_name}")

    def _backfill_legacy_rows(self, connection: sqlite3.Connection) -> None:
        legacy_conversation_columns = self._table_columns(connection, "legacy_conversation_messages")
        if legacy_conversation_columns:
            row = connection.execute(
                "SELECT COUNT(*) AS count FROM conversation_messages WHERE bot_id = 'default'"
            ).fetchone()
            if row and int(row["count"] or 0) == 0:
                connection.execute(
                    """
                    INSERT INTO conversation_messages (
                        bot_id,
                        wa_id,
                        role,
                        display_text,
                        api_content,
                        created_at
                    )
                    SELECT
                        'default',
                        wa_id,
                        role,
                        display_text,
                        api_content,
                        created_at
                    FROM legacy_conversation_messages
                    """
                )

        legacy_lead_state_columns = self._table_columns(connection, "legacy_lead_states")
        if legacy_lead_state_columns:
            row = connection.execute(
                "SELECT COUNT(*) AS count FROM lead_states WHERE bot_id = 'default'"
            ).fetchone()
            if row and int(row["count"] or 0) == 0:
                connection.execute(
                    """
                    INSERT INTO lead_states (
                        bot_id,
                        wa_id,
                        field_values_json,
                        qualification_status,
                        missing_fields_json,
                        summary,
                        updated_at
                    )
                    SELECT
                        'default',
                        wa_id,
                        json_object(
                            'zona_lavoro', zona_lavoro,
                            'tipo_lavoro', tipo_lavoro,
                            'tempistica', tempistica,
                            'budget_indicativo', budget_indicativo,
                            'disponibile_chiamata',
                                CASE
                                    WHEN disponibile_chiamata = 'sconosciuto' THEN ''
                                    ELSE disponibile_chiamata
                                END
                        ),
                        CASE stato_qualifica
                            WHEN 'nuovo' THEN 'new'
                            WHEN 'in_qualifica' THEN 'in_progress'
                            WHEN 'qualificato' THEN 'qualified'
                            WHEN 'da_richiamare' THEN 'follow_up'
                            ELSE 'new'
                        END,
                        COALESCE(missing_fields_json, '[]'),
                        summary,
                        updated_at
                    FROM legacy_lead_states
                    """
                )

        legacy_inbound_columns = self._table_columns(connection, "legacy_inbound_messages")
        if legacy_inbound_columns:
            row = connection.execute(
                "SELECT COUNT(*) AS count FROM inbound_messages WHERE bot_id = 'default'"
            ).fetchone()
            if row and int(row["count"] or 0) == 0:
                connection.execute(
                    """
                    INSERT INTO inbound_messages (
                        message_id,
                        bot_id,
                        wa_id,
                        status,
                        error,
                        created_at,
                        updated_at
                    )
                    SELECT
                        message_id,
                        'default',
                        wa_id,
                        status,
                        error,
                        created_at,
                        updated_at
                    FROM legacy_inbound_messages
                    """
                )

    def list_messages(self, bot_id: str, wa_id: str) -> list[StoredMessage]:
        with self._connection() as connection:
            rows = connection.execute(
                """
                SELECT role, display_text, api_content
                FROM conversation_messages
                WHERE bot_id = ? AND wa_id = ?
                ORDER BY id ASC
                """,
                (bot_id, wa_id),
            ).fetchall()

        return [
            StoredMessage(role=row["role"], display=row["display_text"], api_content=row["api_content"])
            for row in rows
        ]

    def save_message(self, bot_id: str, wa_id: str, message: StoredMessage) -> None:
        with self._connection() as connection:
            connection.execute(
                """
                INSERT INTO conversation_messages (bot_id, wa_id, role, display_text, api_content)
                VALUES (?, ?, ?, ?, ?)
                """,
                (bot_id, wa_id, message.role, message.display, message.api_content),
            )

    def get_lead_state(self, bot_id: str, wa_id: str) -> LeadState | None:
        with self._connection() as connection:
            row = connection.execute(
                """
                SELECT field_values_json, qualification_status, missing_fields_json, summary
                FROM lead_states
                WHERE bot_id = ? AND wa_id = ?
                """,
                (bot_id, wa_id),
            ).fetchone()

        if row is None:
            return None

        return LeadState(
            field_values=json.loads(row["field_values_json"]),
            qualification_status=row["qualification_status"],
            missing_fields=json.loads(row["missing_fields_json"]),
            summary=row["summary"],
        )

    def save_lead_state(self, bot_id: str, wa_id: str, lead_state: LeadState) -> None:
        with self._connection() as connection:
            connection.execute(
                """
                INSERT INTO lead_states (
                    bot_id,
                    wa_id,
                    field_values_json,
                    qualification_status,
                    missing_fields_json,
                    summary,
                    updated_at
                )
                VALUES (?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
                ON CONFLICT(bot_id, wa_id) DO UPDATE SET
                    field_values_json = excluded.field_values_json,
                    qualification_status = excluded.qualification_status,
                    missing_fields_json = excluded.missing_fields_json,
                    summary = excluded.summary,
                    updated_at = CURRENT_TIMESTAMP
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
        with self._connection() as connection:
            try:
                connection.execute(
                    """
                    INSERT INTO inbound_messages (message_id, bot_id, wa_id, status)
                    VALUES (?, ?, ?, 'processing')
                    """,
                    (message_id, bot_id, wa_id),
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
