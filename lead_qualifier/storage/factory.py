from __future__ import annotations

from lead_qualifier.core.settings import Settings
from lead_qualifier.storage.postgres import PostgresLeadStore
from lead_qualifier.storage.protocol import LeadStore
from lead_qualifier.storage.sqlite import SQLiteLeadStore


def create_lead_store(settings: Settings) -> LeadStore:
    if settings.database_url:
        return PostgresLeadStore(
            settings.database_url,
            schema=settings.database_schema,
            min_size=settings.database_pool_min_size,
            max_size=settings.database_pool_max_size,
            timeout_seconds=settings.database_pool_timeout_seconds,
        )

    return SQLiteLeadStore(settings.sqlite_file)
