from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()


def _env_flag(name: str, default: bool) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


@dataclass(frozen=True)
class Settings:
    anthropic_api_key: str
    anthropic_model: str
    company_name: str
    agent_name: str
    call_booking_url: str
    admin_api_key: str
    database_url: str
    database_pool_min_size: int
    database_pool_max_size: int
    database_pool_timeout_seconds: float
    whatsapp_api_base_url: str
    whatsapp_graph_version: str
    whatsapp_access_token: str
    whatsapp_phone_number_id: str
    whatsapp_business_account_id: str
    whatsapp_verify_token: str
    whatsapp_template_language: str
    meta_app_secret: str
    meta_enforce_signature: bool
    sqlite_path: str
    log_level: str

    @property
    def sqlite_file(self) -> Path:
        return Path(self.sqlite_path)

    @classmethod
    def from_env(cls) -> "Settings":
        database_pool_min_size = max(int(os.getenv("DATABASE_POOL_MIN_SIZE", "1")), 1)
        database_pool_max_size = max(int(os.getenv("DATABASE_POOL_MAX_SIZE", "10")), database_pool_min_size)

        return cls(
            anthropic_api_key=os.getenv("ANTHROPIC_API_KEY", "").strip(),
            anthropic_model=os.getenv("ANTHROPIC_MODEL", "claude-sonnet-4-6").strip() or "claude-sonnet-4-6",
            company_name=os.getenv("COMPANY_NAME", "Impresa Edile Demo").strip() or "Impresa Edile Demo",
            agent_name=os.getenv("AGENT_NAME", "Giulia").strip() or "Giulia",
            call_booking_url=os.getenv("CALL_BOOKING_URL", "").strip(),
            admin_api_key=os.getenv("ADMIN_API_KEY", "").strip(),
            database_url=os.getenv("DATABASE_URL", "").strip(),
            database_pool_min_size=database_pool_min_size,
            database_pool_max_size=database_pool_max_size,
            database_pool_timeout_seconds=max(float(os.getenv("DATABASE_POOL_TIMEOUT_SECONDS", "10")), 1.0),
            whatsapp_api_base_url=os.getenv("WHATSAPP_API_BASE_URL", "https://graph.facebook.com").rstrip("/"),
            whatsapp_graph_version=os.getenv("WHATSAPP_GRAPH_VERSION", "v23.0").strip() or "v23.0",
            whatsapp_access_token=os.getenv("WHATSAPP_ACCESS_TOKEN", "").strip(),
            whatsapp_phone_number_id=os.getenv("WHATSAPP_PHONE_NUMBER_ID", "").strip(),
            whatsapp_business_account_id=os.getenv("WHATSAPP_BUSINESS_ACCOUNT_ID", "").strip(),
            whatsapp_verify_token=os.getenv("WHATSAPP_VERIFY_TOKEN", "").strip(),
            whatsapp_template_language=os.getenv("WHATSAPP_TEMPLATE_LANGUAGE", "it").strip() or "it",
            meta_app_secret=os.getenv("META_APP_SECRET", "").strip(),
            meta_enforce_signature=_env_flag("META_ENFORCE_SIGNATURE", True),
            sqlite_path=os.getenv("SQLITE_PATH", "data/lead_qualifier.sqlite3").strip() or "data/lead_qualifier.sqlite3",
            log_level=os.getenv("LOG_LEVEL", "INFO").upper().strip() or "INFO",
        )
