from __future__ import annotations

from lead_qualifier.core.settings import Settings
from lead_qualifier.domain.bot_config import BotConfig
from lead_qualifier.services.meta_integration import MetaIntegrationError, MetaIntegrationService


class RuntimeCredentialsService:
    def __init__(self, settings: Settings, meta_integration: MetaIntegrationService) -> None:
        self._settings = settings
        self._meta_integration = meta_integration

    def get_whatsapp_access_token(self, config: BotConfig) -> str:
        if config.owner_user_id:
            try:
                return self._meta_integration.get_access_token(config.owner_user_id)
            except MetaIntegrationError:
                pass
        if self._settings.whatsapp_access_token:
            return self._settings.whatsapp_access_token
        raise RuntimeError("Nessun token WhatsApp disponibile per questo bot.")
