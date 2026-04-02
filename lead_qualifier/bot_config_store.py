from __future__ import annotations

import json
from pathlib import Path

from psycopg.rows import dict_row
from psycopg_pool import ConnectionPool

from lead_qualifier.bot_config_models import BotConfig


class BotConfigStore:
    def __init__(
        self,
        config_dir: Path,
        *,
        database_url: str = "",
        schema: str = "public",
        min_size: int = 1,
        max_size: int = 4,
        timeout_seconds: float = 10.0,
    ) -> None:
        self._config_dir = config_dir
        self._config_dir.mkdir(parents=True, exist_ok=True)
        self._table = f"{schema}.bot_configs"
        self._pool: ConnectionPool | None = None

        if database_url:
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
            self._bootstrap_from_files_if_needed()

    def list_configs(self) -> list[BotConfig]:
        if self._pool is None:
            return self._list_file_configs()

        with self._pool.connection() as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    f"""
                    SELECT
                        bot_id,
                        name,
                        company_name,
                        agent_name,
                        phone_number_id,
                        default_template_name,
                        template_language,
                        booking_url,
                        prompt_preamble,
                        qualification_statuses_json::text AS qualification_statuses_json,
                        fields_json::text AS fields_json
                    FROM {self._table}
                    ORDER BY name ASC, bot_id ASC
                    """
                )
                rows = cursor.fetchall()

        return [self._row_to_config(row) for row in rows]

    def get(self, bot_id: str) -> BotConfig | None:
        if self._pool is None:
            return self._get_file(bot_id)

        with self._pool.connection() as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    f"""
                    SELECT
                        bot_id,
                        name,
                        company_name,
                        agent_name,
                        phone_number_id,
                        default_template_name,
                        template_language,
                        booking_url,
                        prompt_preamble,
                        qualification_statuses_json::text AS qualification_statuses_json,
                        fields_json::text AS fields_json
                    FROM {self._table}
                    WHERE bot_id = %s
                    """,
                    (bot_id.strip().lower(),),
                )
                row = cursor.fetchone()

        if row is None:
            return None
        return self._row_to_config(row)

    def require(self, bot_id: str) -> BotConfig:
        config = self.get(bot_id)
        if config is None:
            raise FileNotFoundError(f"Configurazione bot non trovata: {bot_id}")
        return config

    def get_by_phone_number_id(self, phone_number_id: str) -> BotConfig | None:
        normalized = phone_number_id.strip()
        if not normalized:
            return None

        if self._pool is None:
            for config in self._list_file_configs():
                if config.phone_number_id == normalized:
                    return config
            return None

        with self._pool.connection() as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    f"""
                    SELECT
                        bot_id,
                        name,
                        company_name,
                        agent_name,
                        phone_number_id,
                        default_template_name,
                        template_language,
                        booking_url,
                        prompt_preamble,
                        qualification_statuses_json::text AS qualification_statuses_json,
                        fields_json::text AS fields_json
                    FROM {self._table}
                    WHERE phone_number_id = %s
                    LIMIT 1
                    """,
                    (normalized,),
                )
                row = cursor.fetchone()

        if row is None:
            return None
        return self._row_to_config(row)

    def upsert(self, config: BotConfig) -> BotConfig:
        if self._pool is None:
            return self._upsert_file(config)

        normalized = self._normalize_config(config)
        with self._pool.connection() as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    f"""
                    INSERT INTO {self._table} (
                        bot_id,
                        name,
                        company_name,
                        agent_name,
                        phone_number_id,
                        default_template_name,
                        template_language,
                        booking_url,
                        prompt_preamble,
                        qualification_statuses_json,
                        fields_json,
                        updated_at
                    )
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s::jsonb, %s::jsonb, timezone('utc', now()))
                    ON CONFLICT (bot_id) DO UPDATE SET
                        name = excluded.name,
                        company_name = excluded.company_name,
                        agent_name = excluded.agent_name,
                        phone_number_id = excluded.phone_number_id,
                        default_template_name = excluded.default_template_name,
                        template_language = excluded.template_language,
                        booking_url = excluded.booking_url,
                        prompt_preamble = excluded.prompt_preamble,
                        qualification_statuses_json = excluded.qualification_statuses_json,
                        fields_json = excluded.fields_json,
                        updated_at = timezone('utc', now())
                    """,
                    (
                        normalized.id,
                        normalized.name,
                        normalized.company_name,
                        normalized.agent_name,
                        normalized.phone_number_id,
                        normalized.default_template_name,
                        normalized.template_language,
                        normalized.booking_url,
                        normalized.prompt_preamble,
                        json.dumps(normalized.qualification_statuses, ensure_ascii=False),
                        json.dumps(
                            [field.model_dump(mode="json") for field in normalized.fields],
                            ensure_ascii=False,
                        ),
                    ),
                )
        return normalized

    def delete(self, bot_id: str) -> None:
        if self._pool is None:
            self._delete_file(bot_id)
            return

        with self._pool.connection() as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    f"DELETE FROM {self._table} WHERE bot_id = %s",
                    (bot_id.strip().lower(),),
                )

    def healthcheck(self) -> None:
        if self._pool is None:
            return None
        with self._pool.connection() as connection:
            with connection.cursor() as cursor:
                cursor.execute("SELECT 1")
                cursor.fetchone()

    def close(self) -> None:
        if self._pool is not None:
            self._pool.close()

    def _bootstrap_from_files_if_needed(self) -> None:
        if self._pool is None:
            return

        with self._pool.connection() as connection:
            with connection.cursor() as cursor:
                cursor.execute(f"SELECT COUNT(*) AS count FROM {self._table}")
                row = cursor.fetchone()
        if not row or int(row["count"] or 0) > 0:
            return

        for config in self._list_file_configs():
            self.upsert(config)

    def _list_file_configs(self) -> list[BotConfig]:
        configs: list[BotConfig] = []
        for path in sorted(self._config_dir.glob("*.json")):
            configs.append(self._load_path(path))
        return configs

    def _get_file(self, bot_id: str) -> BotConfig | None:
        path = self._path_for(bot_id)
        if not path.exists():
            return None
        return self._load_path(path)

    def _upsert_file(self, config: BotConfig) -> BotConfig:
        normalized = self._normalize_config(config)
        path = self._path_for(normalized.id)
        path.write_text(
            json.dumps(normalized.model_dump(mode="json"), ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
        return normalized

    def _delete_file(self, bot_id: str) -> None:
        path = self._path_for(bot_id)
        if path.exists():
            path.unlink()

    @staticmethod
    def _normalize_config(config: BotConfig) -> BotConfig:
        payload = config.model_dump(mode="json")
        payload["id"] = str(payload.get("id", "")).strip().lower()
        return BotConfig.model_validate(payload)

    @staticmethod
    def _row_to_config(row: dict) -> BotConfig:
        return BotConfig.model_validate(
            {
                "id": row["bot_id"],
                "name": row["name"],
                "company_name": row["company_name"],
                "agent_name": row["agent_name"],
                "phone_number_id": row["phone_number_id"],
                "default_template_name": row["default_template_name"],
                "template_language": row["template_language"],
                "booking_url": row["booking_url"],
                "prompt_preamble": row["prompt_preamble"],
                "qualification_statuses": json.loads(row["qualification_statuses_json"]),
                "fields": json.loads(row["fields_json"]),
            }
        )

    def _load_path(self, path: Path) -> BotConfig:
        payload = json.loads(path.read_text(encoding="utf-8"))
        return self._normalize_config(BotConfig.model_validate(payload))

    def _path_for(self, bot_id: str) -> Path:
        normalized = bot_id.strip().lower()
        if not normalized:
            raise ValueError("bot_id non valido.")
        return self._config_dir / f"{normalized}.json"
