from __future__ import annotations

from lead_qualifier.domain.bot_config import BotConfig
from lead_qualifier.services.ghl_payloads import GhlLeadPayload
from lead_qualifier.storage.bot_config_store import BotConfigStore


class GhlBotResolver:
    def __init__(self, config_store: BotConfigStore) -> None:
        self._config_store = config_store

    def resolve(self, payload: GhlLeadPayload) -> tuple[BotConfig, str]:
        if payload.bot_id:
            config = self._config_store.get(payload.bot_id)
            if config is None:
                raise LookupError(f"Bot non trovato per bot_id={payload.bot_id}.")
            if (
                payload.location_id
                and config.ghl_location_id
                and config.ghl_location_id != payload.location_id
            ):
                raise LookupError(
                    "Il bot richiesto non corrisponde alla location GHL ricevuta."
                )
            return config, "bot_id"

        if payload.location_id:
            config = self._config_store.get_by_ghl_location_id(payload.location_id)
            if config is None:
                raise LookupError(
                    f"Nessun bot configurato per ghl_location_id={payload.location_id}."
                )
            return config, "ghl_location_id"

        raise LookupError(
            "Payload GHL senza selector valido. Invia location.id oppure bot_id nel custom data."
        )
