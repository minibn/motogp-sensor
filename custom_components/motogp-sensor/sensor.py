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
    def _event(self) -> dict[str, Any]:
        return self.coordinator.data.get("next_event", {})

    @property
    def native_value(self) -> str | None:
        # Adaptez le champ selon le JSON réel (ex: "name" ou "short_name").
        return self._event.get("name") or self._event.get("short_name")

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        event = self._event
        circuit = event.get("circuit", {}) if isinstance(event.get("circuit"), dict) else {}

        date_start_raw = event.get("date_start") or event.get("date")
        date_start = None
        days_remaining = None
        if date_start_raw:
            try:
                date_start = datetime.fromisoformat(date_start_raw.replace("Z", "+00:00"))
                days_remaining = (date_start.date() - datetime.now(timezone.utc).date()).days
            except ValueError:
                pass

        sessions = []
        for session in event.get("_sessions", []):
            sessions.append(
                {
                    "type": session.get("type") or session.get("name"),
                    "date_start": session.get("date_start"),
                }
            )

        return {
            "circuit": circuit.get("name"),
            "pays": event.get("country"),
            "date_debut": date_start.isoformat() if date_start else None,
            "jours_restants": days_remaining,
            "sessions": sessions,
        }
