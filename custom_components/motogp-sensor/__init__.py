"""Intégration MotoGP pour Home Assistant."""
from __future__ import annotations

import logging

from homeassistant.components.frontend import add_extra_js_url
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

from .const import CONF_CATEGORY, DEFAULT_CATEGORY_NAME, DOMAIN
from .coordinator import MotoGPDataUpdateCoordinator, MotoGPStandingsCoordinator

_LOGGER = logging.getLogger(__name__)

PLATFORMS = ["sensor"]

CARD_VERSION = "4"
CARD_URL_PREFIX = "/motogp_card"
CARD_DIR_RELATIVE = "www"
CARD_FILES = [
    "motogp-next-race-card.js",
    "motogp-standings-card.js",
]
_RESOURCE_REGISTERED_KEY = f"{DOMAIN}_resource_registered"


async def _async_register_card(hass: HomeAssistant) -> None:
    """Sert le dossier www/ de l'intégration et enregistre les cartes.

    Ne fait le travail qu'une seule fois par démarrage de Home Assistant,
    même si plusieurs config entries sont configurées.
    """
    if hass.data.get(_RESOURCE_REGISTERED_KEY):
        return

    www_path = hass.config.path(f"custom_components/{DOMAIN}/{CARD_DIR_RELATIVE}")

    try:
        # API récente (HA >= 2024.7)
        from homeassistant.components.http import StaticPathConfig

        await hass.http.async_register_static_paths(
            [StaticPathConfig(CARD_URL_PREFIX, www_path, cache_headers=False)]
        )
    except ImportError:
        # Fallback pour les versions plus anciennes de Home Assistant.
        hass.http.register_static_path(CARD_URL_PREFIX, www_path, cache_headers=False)

    for filename in CARD_FILES:
        add_extra_js_url(hass, f"{CARD_URL_PREFIX}/{filename}?v={CARD_VERSION}")

    hass.data[_RESOURCE_REGISTERED_KEY] = True
    _LOGGER.debug("Cartes MotoGP enregistrées en tant que ressources frontend")


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    # On enregistre les ressources cartes en tout premier : même si l'appel
    # à l'API MotoGP échoue juste après (première synchro), les cartes
    # doivent rester disponibles pour le dashboard. On isole les erreurs
    # pour ne pas bloquer la création des capteurs si le service statique
    # a un souci.
    try:
        await _async_register_card(hass)
    except Exception:  # noqa: BLE001
        _LOGGER.exception("Impossible d'enregistrer les cartes MotoGP")

    category_name = entry.data.get(CONF_CATEGORY, DEFAULT_CATEGORY_NAME)

    next_race_coordinator = MotoGPDataUpdateCoordinator(hass, category_name)
    await next_race_coordinator.async_config_entry_first_refresh()

    standings_coordinator = MotoGPStandingsCoordinator(hass, category_name)
    await standings_coordinator.async_config_entry_first_refresh()

    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = {
        "next_race": next_race_coordinator,
        "standings": standings_coordinator,
    }

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    unloaded = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unloaded:
        hass.data[DOMAIN].pop(entry.entry_id)
    return unloaded
