"""Coordinator centralisant les appels à l'API MotoGP."""
from __future__ import annotations

import logging
from typing import Any

from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .api import MotoGPApiClient, MotoGPApiError
from .const import DEFAULT_SCAN_INTERVAL, DOMAIN

_LOGGER = logging.getLogger(__name__)


class MotoGPDataUpdateCoordinator(DataUpdateCoordinator[dict[str, Any]]):
    """Récupère et met en cache les données du prochain Grand Prix."""

    def __init__(self, hass: HomeAssistant, category_name: str) -> None:
        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_interval=DEFAULT_SCAN_INTERVAL,
        )
        self._category_name = category_name
        self.client = MotoGPApiClient(async_get_clientsession(hass))

    async def _async_update_data(self) -> dict[str, Any]:
        try:
            data = await self.client.async_get_next_event(self._category_name)
        except MotoGPApiError as err:
            raise UpdateFailed(str(err)) from err

        if data is None:
            raise UpdateFailed("Aucun événement à venir trouvé")

        return data


class MotoGPStandingsCoordinator(DataUpdateCoordinator[dict[str, Any]]):
    """Récupère et met en cache le classement pilotes/constructeurs."""

    def __init__(self, hass: HomeAssistant, category_name: str) -> None:
        super().__init__(
            hass,
            _LOGGER,
            name=f"{DOMAIN}_standings",
            update_interval=DEFAULT_SCAN_INTERVAL,
        )
        self._category_name = category_name
        self.client = MotoGPApiClient(async_get_clientsession(hass))

    async def _async_update_data(self) -> dict[str, Any]:
        try:
            return await self.client.async_get_standings(self._category_name)
        except MotoGPApiError as err:
            raise UpdateFailed(str(err)) from err
