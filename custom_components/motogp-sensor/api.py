"""Client léger pour l'API (non officielle) pulselive MotoGP."""
from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any

from aiohttp import ClientSession, ClientTimeout

from .const import (
    API_BASE,
    ENDPOINT_CATEGORIES,
    ENDPOINT_EVENTS,
    ENDPOINT_SEASONS,
    ENDPOINT_SESSIONS,
)

_LOGGER = logging.getLogger(__name__)

_TIMEOUT = ClientTimeout(total=15)


class MotoGPApiError(Exception):
    """Erreur générique de l'API MotoGP."""


class MotoGPApiClient:
    """Petit wrapper au-dessus de l'API pulselive."""

    def __init__(self, session: ClientSession) -> None:
        self._session = session

    async def _get(self, path: str, params: dict[str, Any] | None = None) -> Any:
        url = f"{API_BASE}{path}"
        try:
            async with self._session.get(url, params=params, timeout=_TIMEOUT) as resp:
                if resp.status != 200:
                    raise MotoGPApiError(
                        f"Réponse HTTP {resp.status} pour {url} (params={params})"
                    )
                return await resp.json(content_type=None)
        except MotoGPApiError:
            raise
        except Exception as err:  # noqa: BLE001
            raise MotoGPApiError(f"Erreur réseau sur {url}: {err}") from err

    async def async_get_current_season(self) -> dict[str, Any]:
        """Retourne la saison marquée 'current': true (sinon la plus récente)."""
        seasons = await self._get(ENDPOINT_SEASONS)
        for season in seasons:
            if season.get("current"):
                return season
        # Filet de sécurité : on prend l'année la plus élevée.
        return max(seasons, key=lambda s: s.get("year", 0))

    async def async_get_categories(self, season_uuid: str) -> list[dict[str, Any]]:
        return await self._get(ENDPOINT_CATEGORIES, {"seasonUuid": season_uuid})

    async def async_get_events(
        self, season_uuid: str, is_finished: bool | None = None
    ) -> list[dict[str, Any]]:
        params: dict[str, Any] = {"seasonUuid": season_uuid}
        if is_finished is not None:
            params["isFinished"] = str(is_finished).lower()
        return await self._get(ENDPOINT_EVENTS, params)

    async def async_get_sessions(
        self, event_uuid: str, category_uuid: str
    ) -> list[dict[str, Any]]:
        return await self._get(
            ENDPOINT_SESSIONS,
            {"eventUuid": event_uuid, "categoryUuid": category_uuid},
        )

    async def async_get_next_event(
        self, category_name: str
    ) -> dict[str, Any] | None:
        """Renvoie le prochain événement (non terminé) le plus proche."""
        season = await self.async_get_current_season()
        season_uuid = season["id"]

        events = await self.async_get_events(season_uuid, is_finished=False)
        if not events:
            return None

        now = datetime.now(timezone.utc)

        def event_start(event: dict[str, Any]) -> datetime:
            # Le champ exact dépend de la réponse réelle de l'API :
            # certains dumps utilisent "date_start", d'autres un objet
            # imbriqué "circuit"/"date". Adaptez ici après vérification.
            raw = event.get("date_start") or event.get("date")
            if not raw:
                return datetime.max.replace(tzinfo=timezone.utc)
            parsed = datetime.fromisoformat(raw.replace("Z", "+00:00"))
            if parsed.tzinfo is None:
                # Certaines réponses de l'API omettent le fuseau : on
                # suppose UTC plutôt que de comparer un datetime naïf
                # à un datetime "aware" (ce qui lève TypeError).
                parsed = parsed.replace(tzinfo=timezone.utc)
            return parsed

        upcoming = [e for e in events if event_start(e) >= now]
        candidates = upcoming or events
        next_event = min(candidates, key=event_start)

        # On récupère aussi les sessions (essais, qualifs, course) pour la
        # catégorie demandée (MotoGP / Moto2 / Moto3), si on la retrouve.
        categories = await self.async_get_categories(season_uuid)
        category = next(
            (c for c in categories if c.get("name") == category_name), None
        )
        sessions: list[dict[str, Any]] = []
        if category:
            try:
                sessions = await self.async_get_sessions(
                    next_event["id"], category["id"]
                )
            except MotoGPApiError as err:
                _LOGGER.debug("Impossible de récupérer les sessions: %s", err)

        next_event["_sessions"] = sessions
        return next_event
