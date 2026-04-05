from __future__ import annotations

import json
import time
from pathlib import Path

from psycopg.rows import dict_row
from psycopg_pool import ConnectionPool

from lead_qualifier.domain.bot_config import BotConfig, DEFAULT_QUALIFICATION_STATUSES


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
        self._schema = schema
        self._table_name = "bot_configs"
        self._table = f"{schema}.bot_configs"
        self._pool: ConnectionPool | None = None
        self._db_columns: set[str] = set()
        self._db_columns_loaded_at = 0.0

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
            self._ensure_runtime_columns()
            self._refresh_db_columns()
            self._bootstrap_from_files_if_needed()

    def list_configs(self) -> list[BotConfig]:
        if self._pool is None:
            return self._list_file_configs()
        self._refresh_db_columns_if_stale()

        with self._pool.connection() as connection:
            with connection.cursor() as cursor:
                cursor.execute(self._build_select_sql(order_by="ORDER BY name ASC, bot_id ASC"))
                rows = cursor.fetchall()

        return [self._row_to_config(row) for row in rows]

    def get(self, bot_id: str) -> BotConfig | None:
        if self._pool is None:
            return self._get_file(bot_id)
        self._refresh_db_columns_if_stale()

        with self._pool.connection() as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    self._build_select_sql(where_clause="WHERE bot_id = %s"),
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
        self._refresh_db_columns_if_stale()

        with self._pool.connection() as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    self._build_select_sql(
                        where_clause="WHERE phone_number_id = %s",
                        limit_clause="LIMIT 1",
                    ),
                    (normalized,),
                )
                row = cursor.fetchone()

        if row is None:
            return None
        return self._row_to_config(row)

    def upsert(self, config: BotConfig) -> BotConfig:
        if self._pool is None:
            return self._upsert_file(config)
        self._refresh_db_columns_if_stale()

        normalized = self._normalize_config(config)
        with self._pool.connection() as connection:
            with connection.cursor() as cursor:
                statement, params = self._build_upsert_sql(normalized)
                cursor.execute(statement, params)
        return normalized

    def delete(self, bot_id: str) -> None:
        if self._pool is None:
            self._delete_file(bot_id)
            return
        self._refresh_db_columns_if_stale()

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

    def _refresh_db_columns(self) -> None:
        if self._pool is None:
            self._db_columns = set()
            self._db_columns_loaded_at = time.time()
            return

        with self._pool.connection() as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    """
                    SELECT column_name
                    FROM information_schema.columns
                    WHERE table_schema = %s
                      AND table_name = %s
                    """,
                    (self._schema, self._table_name),
                )
                rows = cursor.fetchall()
        self._db_columns = {
            str(row.get("column_name") or "").strip()
            for row in rows
            if str(row.get("column_name") or "").strip()
        }
        self._db_columns_loaded_at = time.time()

    def _refresh_db_columns_if_stale(self, *, max_age_seconds: float = 60.0) -> None:
        if self._pool is None:
            return
        if self._db_columns and (time.time() - self._db_columns_loaded_at) < max_age_seconds:
            return
        self._refresh_db_columns()

    def _ensure_runtime_columns(self) -> None:
        if self._pool is None:
            return

        with self._pool.connection() as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    f"""
                    ALTER TABLE IF EXISTS {self._table}
                        ADD COLUMN IF NOT EXISTS default_template_id text NOT NULL DEFAULT ''
                    """
                )
                cursor.execute(
                    f"""
                    ALTER TABLE IF EXISTS {self._table}
                        ADD COLUMN IF NOT EXISTS default_template_body_text text NOT NULL DEFAULT ''
                    """
                )
                cursor.execute(
                    f"""
                    UPDATE {self._table}
                    SET
                        default_template_id = COALESCE(default_template_id, ''),
                        default_template_body_text = COALESCE(default_template_body_text, '')
                    WHERE default_template_id IS NULL
                       OR default_template_body_text IS NULL
                    """
                )

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

    def _has_column(self, name: str) -> bool:
        return name in self._db_columns

    def _build_select_sql(
        self,
        *,
        where_clause: str = "",
        order_by: str = "",
        limit_clause: str = "",
    ) -> str:
        json_list_default = "'[]'"
        statuses_default = json.dumps(DEFAULT_QUALIFICATION_STATUSES, ensure_ascii=True)
        select_parts = [
            self._select_expr("bot_id"),
            self._select_expr("owner_user_id", fallback_sql="''"),
            self._select_expr("name"),
            self._select_expr("company_name"),
            self._select_expr("company_description"),
            self._select_expr("service_area"),
            self._select_expr("company_services_json", cast="::text", fallback_sql=json_list_default),
            self._select_expr("website_url", fallback_sql="''"),
            self._select_expr("agent_name"),
            self._select_expr("phone_number_id"),
            self._select_expr("whatsapp_display_phone_number", fallback_sql="''"),
            self._select_expr("meta_business_id", fallback_sql="''"),
            self._select_expr("meta_business_name", fallback_sql="''"),
            self._select_expr("meta_waba_id", fallback_sql="''"),
            self._select_expr("meta_waba_name", fallback_sql="''"),
            self._select_expr("default_template_id", fallback_sql="''"),
            self._select_expr("default_template_name"),
            self._select_expr("default_template_body_text", fallback_sql="''"),
            self._select_expr("default_template_variable_count", fallback_sql="0"),
            self._select_expr("template_language"),
            self._select_expr("booking_url"),
            self._select_expr("lead_manager_page_id"),
            self._select_expr("lead_manager_page_name", fallback_sql="''"),
            self._select_expr(
                "qualification_statuses_json",
                cast="::text",
                fallback_sql=f"'{statuses_default}'",
            ),
            self._select_expr("fields_json", cast="::text", fallback_sql=json_list_default),
        ]
        return (
            f"""
            SELECT
                {",\n                ".join(select_parts)}
            FROM {self._table}
            {where_clause}
            {order_by}
            {limit_clause}
            """
        )

    def _select_expr(self, column_name: str, *, cast: str = "", fallback_sql: str | None = None) -> str:
        if self._has_column(column_name):
            return f"{column_name}{cast} AS {column_name}"
        fallback = fallback_sql or "NULL"
        return f"{fallback} AS {column_name}"

    def _build_upsert_sql(self, normalized: BotConfig) -> tuple[str, tuple[object, ...]]:
        field_specs: list[tuple[str, object, str | None, bool]] = [
            ("bot_id", normalized.id, None, False),
            ("owner_user_id", normalized.owner_user_id, None, False),
            ("name", normalized.name, None, False),
            ("company_name", normalized.company_name, None, False),
            ("company_description", normalized.company_description, None, False),
            ("service_area", normalized.service_area, None, False),
            (
                "company_services_json",
                json.dumps(normalized.company_services, ensure_ascii=False),
                "::jsonb",
                False,
            ),
            ("website_url", normalized.website_url, None, False),
            ("agent_name", normalized.agent_name, None, False),
            ("phone_number_id", normalized.phone_number_id, None, False),
            ("whatsapp_display_phone_number", normalized.whatsapp_display_phone_number, None, False),
            ("meta_business_id", normalized.meta_business_id, None, False),
            ("meta_business_name", normalized.meta_business_name, None, False),
            ("meta_waba_id", normalized.meta_waba_id, None, False),
            ("meta_waba_name", normalized.meta_waba_name, None, False),
            ("default_template_id", normalized.default_template_id, None, False),
            ("default_template_name", normalized.default_template_name, None, False),
            ("default_template_body_text", normalized.default_template_body_text, None, False),
            ("default_template_variable_count", normalized.default_template_variable_count, None, False),
            ("template_language", normalized.template_language, None, False),
            ("booking_url", normalized.booking_url, None, False),
            ("lead_manager_page_id", normalized.lead_manager_page_id, None, False),
            ("lead_manager_page_name", normalized.lead_manager_page_name, None, False),
            (
                "qualification_statuses_json",
                json.dumps(normalized.qualification_statuses, ensure_ascii=False),
                "::jsonb",
                False,
            ),
            (
                "fields_json",
                json.dumps(
                    [field.model_dump(mode="json") for field in normalized.fields],
                    ensure_ascii=False,
                ),
                "::jsonb",
                False,
            ),
            ("updated_at", "timezone('utc', now())", None, True),
        ]

        insert_columns: list[str] = []
        insert_values_sql: list[str] = []
        update_assignments: list[str] = []
        params: list[object] = []

        for column_name, value, cast, is_raw_sql in field_specs:
            if not self._has_column(column_name):
                continue
            insert_columns.append(column_name)
            if is_raw_sql:
                insert_values_sql.append(str(value))
            else:
                insert_values_sql.append(f"%s{cast or ''}")
                params.append(value)

            if column_name == "bot_id":
                continue
            if column_name == "updated_at":
                update_assignments.append("updated_at = timezone('utc', now())")
            else:
                update_assignments.append(f"{column_name} = excluded.{column_name}")

        statement = (
            f"""
            INSERT INTO {self._table} (
                {", ".join(insert_columns)}
            )
            VALUES ({", ".join(insert_values_sql)})
            ON CONFLICT (bot_id) DO UPDATE SET
                {", ".join(update_assignments)}
            """
        )
        return statement, tuple(params)

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
                "owner_user_id": row.get("owner_user_id", ""),
                "name": row["name"],
                "company_name": row["company_name"],
                "company_description": row["company_description"],
                "service_area": row["service_area"],
                "company_services": json.loads(row["company_services_json"]),
                "website_url": row.get("website_url", ""),
                "agent_name": row["agent_name"],
                "phone_number_id": row["phone_number_id"],
                "whatsapp_display_phone_number": row.get("whatsapp_display_phone_number", ""),
                "meta_business_id": row.get("meta_business_id", ""),
                "meta_business_name": row.get("meta_business_name", ""),
                "meta_waba_id": row.get("meta_waba_id", ""),
                "meta_waba_name": row.get("meta_waba_name", ""),
                "default_template_id": row.get("default_template_id", ""),
                "default_template_name": row["default_template_name"],
                "default_template_body_text": row.get("default_template_body_text", ""),
                "default_template_variable_count": row.get("default_template_variable_count", 0),
                "template_language": row["template_language"],
                "booking_url": row["booking_url"],
                "lead_manager_page_id": row["lead_manager_page_id"],
                "lead_manager_page_name": row.get("lead_manager_page_name", ""),
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
