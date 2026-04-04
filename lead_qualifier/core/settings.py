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


def _env_list(name: str) -> list[str]:
    raw = os.getenv(name, "")
    return [item.strip().lower() for item in raw.split(",") if item.strip()]


@dataclass(frozen=True)
class Settings:
    anthropic_api_key: str
    anthropic_model: str
    admin_api_key: str
    database_url: str
    database_schema: str
    database_pool_min_size: int
    database_pool_max_size: int
    database_pool_timeout_seconds: float
    supabase_url: str
    supabase_publishable_key: str
    dashboard_allowed_emails: list[str]
    bot_config_dir: str
    dashboard_dist_dir: str
    whatsapp_api_base_url: str
    whatsapp_graph_version: str
    whatsapp_access_token: str
    whatsapp_business_account_id: str
    whatsapp_verify_token: str
    meta_app_secret: str
    meta_enforce_signature: bool
    lead_manager_api_url: str
    lead_manager_api_key: str
    sqlite_path: str
    log_level: str

    @property
    def sqlite_file(self) -> Path:
        return Path(self.sqlite_path)

    @property
    def bot_config_path(self) -> Path:
        return Path(self.bot_config_dir)

    @property
    def dashboard_dist_path(self) -> Path:
        return Path(self.dashboard_dist_dir)

    @classmethod
    def from_env(cls) -> "Settings":
        database_pool_min_size = max(int(os.getenv("DATABASE_POOL_MIN_SIZE", "1")), 1)
        database_pool_max_size = max(int(os.getenv("DATABASE_POOL_MAX_SIZE", "10")), database_pool_min_size)

        return cls(
            anthropic_api_key=os.getenv("ANTHROPIC_API_KEY", "").strip(),
            anthropic_model=os.getenv("ANTHROPIC_MODEL", "claude-sonnet-4-6").strip() or "claude-sonnet-4-6",
            admin_api_key=os.getenv("ADMIN_API_KEY", "").strip(),
            database_url=os.getenv("DATABASE_URL", "").strip(),
            database_schema=os.getenv("DATABASE_SCHEMA", "public").strip() or "public",
            database_pool_min_size=database_pool_min_size,
            database_pool_max_size=database_pool_max_size,
            database_pool_timeout_seconds=max(float(os.getenv("DATABASE_POOL_TIMEOUT_SECONDS", "10")), 1.0),
            supabase_url=os.getenv("SUPABASE_URL", "").rstrip("/"),
            supabase_publishable_key=os.getenv("SUPABASE_PUBLISHABLE_KEY", "").strip(),
            dashboard_allowed_emails=_env_list("DASHBOARD_ALLOWED_EMAILS"),
            bot_config_dir=os.getenv("BOT_CONFIG_DIR", "bot_configs").strip() or "bot_configs",
            dashboard_dist_dir=os.getenv("DASHBOARD_DIST_DIR", "web/dist").strip() or "web/dist",
            whatsapp_api_base_url=os.getenv("WHATSAPP_API_BASE_URL", "https://graph.facebook.com").rstrip("/"),
            whatsapp_graph_version=os.getenv("WHATSAPP_GRAPH_VERSION", "v23.0").strip() or "v23.0",
            whatsapp_access_token=os.getenv("WHATSAPP_ACCESS_TOKEN", "").strip(),
            whatsapp_business_account_id=os.getenv("WHATSAPP_BUSINESS_ACCOUNT_ID", "").strip(),
            whatsapp_verify_token=os.getenv("WHATSAPP_VERIFY_TOKEN", "").strip(),
            meta_app_secret=os.getenv("META_APP_SECRET", "").strip(),
            meta_enforce_signature=_env_flag("META_ENFORCE_SIGNATURE", True),
            lead_manager_api_url=os.getenv("LEAD_MANAGER_API_URL", "").rstrip("/"),
            lead_manager_api_key=os.getenv("LEAD_MANAGER_API_KEY", "").strip(),
            sqlite_path=os.getenv("SQLITE_PATH", "data/lead_qualifier.sqlite3").strip() or "data/lead_qualifier.sqlite3",
            log_level=os.getenv("LOG_LEVEL", "INFO").upper().strip() or "INFO",
        )
