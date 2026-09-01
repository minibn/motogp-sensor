"""Capteur exposant les infos de la prochaine course MotoGP."""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from homeassistant.components.sensor import SensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import ATTRIBUTION, DOMAIN
from .coordinator import MotoGPDataUpdateCoordinator


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    coordinator: MotoGPDataUpdateCoordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities([MotoGPNextRaceSensor(coordinator, entry)])


class MotoGPNextRaceSensor(CoordinatorEntity[MotoGPDataUpdateCoordinator], SensorEntity):
    """État = nom du Grand Prix, attributs = tout le détail utile au dashboard."""

    _attr_has_entity_name = True
    _attr_name = "Prochaine course"
    _attr_icon = "mdi:motorbike"
    _attr_attribution = ATTRIBUTION

    def __init__(self, coordinator: MotoGPDataUpdateCoordinator, entry: ConfigEntry) -> None:
        super().__init__(coordinator)
        self._attr_unique_id = f"{entry.entry_id}_next_race"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, entry.entry_id)},
            name="MotoGP",
            manufacturer="Dorna Sports (données non officielles)",
        )

    @property
    def _data(self) -> dict[str, Any]:
        return self.coordinator.data or {}

    @property
    def _event(self) -> dict[str, Any]:
        return self._data.get("event", {})

    @property
    def native_value(self) -> str | None:
        return self._event.get("name") or self._event.get("sponsored_name")

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        event = self._event
        data = self._data

        circuit = event.get("circuit")
        circuit_name = circuit.get("name") if isinstance(circuit, dict) else circuit

        country = event.get("country")
        if isinstance(country, dict):
            country_name = country.get("name")
            country_iso = country.get("iso")
        else:
            # Filet de sécurité si l'API renvoie un jour directement une
            # chaîne (observé sur d'autres endpoints de cette même API).
            country_name = country
            country_iso = None

        weekend_start = data.get("weekend_start")
        jours_restants = None
        if weekend_start:
            try:
                start_dt = datetime.fromisoformat(weekend_start)
                jours_restants = (start_dt.date() - datetime.now(timezone.utc).date()).days
            except ValueError:
                pass

        return {
            "circuit": circuit_name,
            "pays": country_name,
            "pays_iso": country_iso,
            "manche": data.get("round"),
            "manche_total": data.get("total_rounds"),
            "saison": data.get("season_year"),
            "debut_weekend": weekend_start,
            "debut_course": data.get("race_start"),
            "prochaine_session": data.get("next_session"),
            "jours_restants": jours_restants,
            "sessions": data.get("sessions", []),
            "circuit_plan_svg": data.get("circuit_map_svg"),
            "circuit_plan_png": data.get("circuit_map_png"),
            "circuit_virages_gauche": data.get("circuit_left_corners"),
            "circuit_virages_droite": data.get("circuit_right_corners"),
        }
