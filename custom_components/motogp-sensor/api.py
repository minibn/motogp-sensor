"""Client léger pour l'API (non officielle) pulselive MotoGP."""
from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any

from aiohttp import ClientSession, ClientTimeout

from .const import (
    API_BASE,
    ENDPOINT_BROADCAST_CATEGORIES,
    ENDPOINT_CATEGORIES,
    ENDPOINT_EVENTS,
    ENDPOINT_SEASONS,
    ENDPOINT_SESSIONS,
    ENDPOINT_TEAMS,
    ENDPOINT_WORLD_STANDINGS,
    EVENT_DETAIL_BASE,
    STANDINGS_API_BASE,
)

_LOGGER = logging.getLogger(__name__)

_TIMEOUT = ClientTimeout(total=15)

# Codes de session observés sur l'API Results (FP1/FP2/FP3, Q1/Q2, Warm-up,
# Course...). Le champ "type" est un code court, combiné à "number" pour
# distinguer par exemple FP1 de FP2.
_SESSION_TYPE_LABELS = {
    "FP": "EL",   # Essais Libres
    "Q": "Q",
    "WUP": "Warm-up",
    "RAC": "Course",
    "EP": "EL",
    "QP": "Q",
    "SPR": "Sprint",
    "TTS": "Essai TT",
    "PR": "Essais",
}


def session_label(session: dict[str, Any]) -> str:
    """Construit un libellé court ('EL1', 'Q2', 'Course'...) pour une session."""
    raw_type = str(session.get("type") or "").upper()
    number = session.get("number")
    base = _SESSION_TYPE_LABELS.get(raw_type, raw_type or "?")
    if number and base not in ("Warm-up", "Course", "Sprint", "Essai TT", "Essais"):
        return f"{base}{number}"
    return base


def _parse_session_date(session: dict[str, Any]) -> datetime | None:
    raw = session.get("date")
    if not raw:
        return None
    try:
        parsed = datetime.fromisoformat(raw)
    except ValueError:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed


def _normalize_category_name(name: str | None) -> str:
    """'MotoGP™' et 'MotoGP' doivent être reconnus comme identiques : les
    deux API n'utilisent pas la même convention de nommage (avec ou sans
    le symbole ™)."""
    return (name or "").replace("™", "").strip().casefold()


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
        return max(seasons, key=lambda s: s.get("year", 0))

    async def async_get_categories(self, season_uuid: str) -> list[dict[str, Any]]:
        return await self._get(ENDPOINT_CATEGORIES, {"seasonUuid": season_uuid})

    async def async_get_world_standings(
        self, season_uuid: str, category_uuid: str, standing_type: str = "rider"
    ) -> dict[str, Any]:
        """Appelle l'API v2 des classements (base différente du reste)."""
        url = f"{STANDINGS_API_BASE}{ENDPOINT_WORLD_STANDINGS}"
        params = {"type": standing_type, "season": season_uuid, "category": category_uuid}
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

    async def async_get_broadcast_category_id(
        self, category_name: str, season_year: int
    ) -> str | None:
        """Trouve l'ID de catégorie attendu par /teams (API "Broadcast"),
        DIFFÉRENT de celui renvoyé par /results/categories pour la même
        catégorie. category_name utilise la convention /results/ (avec
        ™) ; on normalise pour matcher la convention broadcast (sans ™).
        """
        categories = await self._get(
            ENDPOINT_BROADCAST_CATEGORIES, {"seasonYear": season_year}
        )
        target = _normalize_category_name(category_name)
        match = next(
            (
                c
                for c in categories or []
                if _normalize_category_name(c.get("name")) == target
            ),
            None,
        )
        return match["id"] if match else None

    async def async_get_team_colors(
        self, category_uuid: str, season_year: int
    ) -> dict[str, dict[str, str]]:
        """Couleurs officielles par équipe : {team_name: {color, text_color}}.

        Endpoint distinct de /results/ (base v1 mais chemin /teams direct),
        paramétré par categoryUuid + seasonYear (et non seasonUuid).
        """
        teams = await self._get(
            ENDPOINT_TEAMS, {"categoryUuid": category_uuid, "seasonYear": season_year}
        )
        colors: dict[str, dict[str, str]] = {}
        for team in teams or []:
            name = team.get("name")
            if not name:
                continue
            colors[name] = {
                "color": team.get("color"),
                "text_color": team.get("text_color"),
            }
        return colors

    async def async_get_standings(
        self, category_name: str, standing_type: str = "rider"
    ) -> dict[str, Any]:
        """Classement simplifié pour le tableau de bord.

        Retourne {"season_year", "category", "standings": [...]}, chaque
        élément de "standings" ayant : position, number, name, points,
        team, constructor, country_iso, position_change, team_color,
        team_text_color.
        """
        season = await self.async_get_current_season()
        season_uuid = season["id"]

        categories = await self.async_get_categories(season_uuid)
        category = next(
            (c for c in categories if c.get("name") == category_name), None
        )
        if category is None:
            raise MotoGPApiError(f"Catégorie introuvable : {category_name}")

        raw = await self.async_get_world_standings(season_uuid, category["id"], standing_type)
        entries = (raw.get("classification") or {}).get(standing_type) or []

        team_colors: dict[str, dict[str, str]] = {}
        try:
            broadcast_category_id = await self.async_get_broadcast_category_id(
                category_name, season.get("year")
            )
            if broadcast_category_id:
                team_colors = await self.async_get_team_colors(
                    broadcast_category_id, season.get("year")
                )
        except MotoGPApiError as err:
            # Les couleurs sont un "bonus" visuel : une panne sur cet appel
            # ne doit pas empêcher le classement de s'afficher.
            _LOGGER.debug("Impossible de récupérer les couleurs d'équipe: %s", err)

        standings = []
        for entry in entries:
            rider = entry.get("rider") or {}
            constructor = entry.get("constructor") or {}
            country = rider.get("country") or {}
            team_name = entry.get("team_name")
            colors = team_colors.get(team_name, {})
            standings.append(
                {
                    "position": entry.get("position"),
                    "number": rider.get("number"),
                    "name": rider.get("full_name"),
                    "points": entry.get("points"),
                    "team": team_name,
                    "constructor": constructor.get("name"),
                    "country_iso": country.get("iso"),
                    "position_change": entry.get("position_change"),
                    "team_color": colors.get("color"),
                    "team_text_color": colors.get("text_color"),
                }
            )

        return {
            "season_year": season.get("year"),
            "category": category_name,
            "standings": standings,
        }

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

    async def async_get_event_detail(self, toad_api_uuid: str) -> dict[str, Any]:
        """Appelle GET /events/{toad_api_uuid} (endpoint distinct de /results/).

        Contient notamment le plan du circuit (SVG) sous
        circuit.tracks[].assets.info.path.
        """
        url = f"{EVENT_DETAIL_BASE}/{toad_api_uuid}"
        try:
            async with self._session.get(url, timeout=_TIMEOUT) as resp:
                if resp.status != 200:
                    raise MotoGPApiError(f"Réponse HTTP {resp.status} pour {url}")
                return await resp.json(content_type=None)
        except MotoGPApiError:
            raise
        except Exception as err:  # noqa: BLE001
            raise MotoGPApiError(f"Erreur réseau sur {url}: {err}") from err

    @staticmethod
    def extract_circuit_map(event_detail: dict[str, Any]) -> dict[str, Any]:
        """Extrait les URLs du plan de circuit depuis la réponse /events/{id}.

        On privilégie le tracé marqué "is_active": true ; à défaut, le
        premier tracé disponible dans la liste.
        """
        circuit = event_detail.get("circuit") or {}
        tracks = circuit.get("tracks") or []
        if not tracks:
            return {}

        track = next((t for t in tracks if t.get("is_active")), tracks[0])
        assets = track.get("assets")
        if not isinstance(assets, dict):
            # Certains tracés inactifs ont "assets": [] (liste vide) au
            # lieu d'un objet {simple, info} : rien à en tirer.
            return {}

        info = assets.get("info") or {}
        simple = assets.get("simple") or {}

        return {
            "circuit_map_svg": info.get("path"),
            "circuit_map_png": simple.get("path"),
            "circuit_left_corners": track.get("left_corners"),
            "circuit_right_corners": track.get("right_corners"),
        }

    async def async_get_next_event(self, category_name: str) -> dict[str, Any] | None:
        """Construit toutes les infos du prochain Grand Prix pour une catégorie.

        On ne se fie à aucun champ de date au niveau de l'événement lui-même
        (sa forme exacte n'est pas documentée de façon fiable) : les dates
        affichées (week-end, prochaine session, départ course) sont toutes
        dérivées des sessions, dont le schéma est confirmé par la doc de
        l'API Results.
        """
        season = await self.async_get_current_season()
        season_uuid = season["id"]

        finished_events = await self.async_get_events(season_uuid, is_finished=True)
        upcoming_events = await self.async_get_events(season_uuid, is_finished=False)
        if not upcoming_events:
            return None

        # On ignore les séances de tests pour la numérotation "manche X/Y"
        # et pour le choix du prochain évènement, quand l'info est présente.
        finished_real = [e for e in finished_events if not e.get("test")]
        upcoming_real = [e for e in upcoming_events if not e.get("test")] or upcoming_events

        next_event = upcoming_real[0]
        round_number = len(finished_real) + 1
        total_rounds = len(finished_real) + len(upcoming_real)

        categories = await self.async_get_categories(season_uuid)
        category = next(
            (c for c in categories if c.get("name") == category_name), None
        )

        sessions: list[dict[str, Any]] = []
        if category:
            try:
                sessions = await self.async_get_sessions(next_event["id"], category["id"])
            except MotoGPApiError as err:
                _LOGGER.debug("Impossible de récupérer les sessions: %s", err)

        # Sessions triées chronologiquement, avec leur date déjà parsée.
        dated_sessions = sorted(
            (
                (s, d)
                for s in sessions
                if (d := _parse_session_date(s)) is not None
            ),
            key=lambda item: item[1],
        )

        now = datetime.now(timezone.utc)
        next_session = next((s for s, d in dated_sessions if d >= now), None)
        race_entry = next(
            (s for s, _ in dated_sessions if str(s.get("type", "")).upper() == "RAC"),
            None,
        )

        weekend_start = dated_sessions[0][1] if dated_sessions else None
        race_start = None
        if race_entry is not None:
            race_start = _parse_session_date(race_entry)

        circuit_map: dict[str, Any] = {}
        toad_api_uuid = next_event.get("toad_api_uuid")
        if toad_api_uuid:
            try:
                event_detail = await self.async_get_event_detail(toad_api_uuid)
                circuit_map = self.extract_circuit_map(event_detail)
            except MotoGPApiError as err:
                # Ne doit jamais faire échouer tout le capteur : le plan du
                # circuit est un "bonus", pas une donnée critique.
                _LOGGER.debug("Impossible de récupérer le plan du circuit: %s", err)

        return {
            "event": next_event,
            "season_year": season.get("year"),
            "round": round_number,
            "total_rounds": total_rounds,
            "sessions": [
                {"label": session_label(s), "type": s.get("type"), "date": d.isoformat()}
                for s, d in dated_sessions
            ],
            "weekend_start": weekend_start.isoformat() if weekend_start else None,
            "race_start": race_start.isoformat() if race_start else None,
            "next_session": (
                {"label": session_label(next_session), "date": _parse_session_date(next_session).isoformat()}
                if next_session is not None
                else None
            ),
            **circuit_map,
        }
