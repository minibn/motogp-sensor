"""Intégration MotoGP pour Home Assistant."""
from __future__ import annotations

import logging

from homeassistant.components.frontend import add_extra_js_url
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

from .const import CONF_CATEGORY, DEFAULT_CATEGORY_NAME, DOMAIN
from .coordinator import MotoGPDataUpdateCoordinator

_LOGGER = logging.getLogger(__name__)

PLATFORMS = ["sensor"]

CARD_VERSION = "1"
CARD_URL_PATH = "/motogp_card/motogp-next-race-card.js"
CARD_FILE_RELATIVE = "www/motogp-next-race-card.js"
_RESOURCE_REGISTERED_KEY = f"{DOMAIN}_resource_registered"


async def _async_register_card(hass: HomeAssistant) -> None:
    """Sert le fichier JS de la carte et l'enregistre comme ressource frontend.

    Ne fait le travail qu'une seule fois par démarrage de Home Assistant,
    même si plusieurs config entries sont configurées.
    """
    if hass.data.get(_RESOURCE_REGISTERED_KEY):
        return

    card_path = hass.config.path(f"custom_components/{DOMAIN}/{CARD_FILE_RELATIVE}")

    try:
        # API récente (HA >= 2024.7)
        from homeassistant.components.http import StaticPathConfig

        await hass.http.async_register_static_paths(
            [StaticPathConfig(CARD_URL_PATH, card_path, cache_headers=False)]
        )
    except ImportError:
        # Fallback pour les versions plus anciennes de Home Assistant.
        hass.http.register_static_path(CARD_URL_PATH, card_path, cache_headers=False)

    add_extra_js_url(hass, f"{CARD_URL_PATH}?v={CARD_VERSION}")
    hass.data[_RESOURCE_REGISTERED_KEY] = True
    _LOGGER.debug("Carte MotoGP enregistrée en tant que ressource frontend")


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    category_name = entry.data.get(CONF_CATEGORY, DEFAULT_CATEGORY_NAME)

    coordinator = MotoGPDataUpdateCoordinator(hass, category_name)
    await coordinator.async_config_entry_first_refresh()

    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = coordinator

    await _async_register_card(hass)

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    unloaded = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unloaded:
        hass.data[DOMAIN].pop(entry.entry_id)
    return unloaded
