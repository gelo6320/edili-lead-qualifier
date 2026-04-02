from __future__ import annotations

from lead_qualifier.postgres_store import PostgresLeadStore
from lead_qualifier.settings import Settings
from lead_qualifier.sqlite_store import SQLiteLeadStore
from lead_qualifier.store_protocol import LeadStore


def create_lead_store(settings: Settings) -> LeadStore:
    if settings.database_url:
        return PostgresLeadStore(
            settings.database_url,
            min_size=settings.database_pool_min_size,
            max_size=settings.database_pool_max_size,
            timeout_seconds=settings.database_pool_timeout_seconds,
        )

    return SQLiteLeadStore(settings.sqlite_file)
