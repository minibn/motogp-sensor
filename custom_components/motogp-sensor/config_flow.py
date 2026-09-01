"""Config flow pour l'intégration MotoGP."""
from __future__ import annotations

import voluptuous as vol

from homeassistant import config_entries
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .api import MotoGPApiClient, MotoGPApiError
from .const import CONF_CATEGORY, DEFAULT_CATEGORY_NAME, DOMAIN, DOCUMENTATION_URL

CATEGORY_CHOICES = ["MotoGP™", "Moto2™", "Moto3™"]


class MotoGPConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Un seul écran : choix de la catégorie à suivre."""

    VERSION = 1

    async def async_step_user(self, user_input: dict | None = None):
        errors: dict[str, str] = {}

        if user_input is not None:
            # On vérifie que l'API répond avant de valider la config.
            session = async_get_clientsession(self.hass)
            client = MotoGPApiClient(session)
            try:
                await client.async_get_current_season()
            except MotoGPApiError:
                errors["base"] = "cannot_connect"
            else:
                await self.async_set_unique_id(
                    f"{DOMAIN}_{user_input[CONF_CATEGORY]}"
                )
                self._abort_if_unique_id_configured()
                return self.async_create_entry(
                    title=f"MotoGP ({user_input[CONF_CATEGORY]})",
                    data=user_input,
                )

        schema = vol.Schema(
            {
                vol.Required(
                    CONF_CATEGORY, default=DEFAULT_CATEGORY_NAME
                ): vol.In(CATEGORY_CHOICES)
            }
        )
        return self.async_show_form(
            step_id="user",
            data_schema=schema,
            errors=errors,
            # Certaines versions de Home Assistant retombent sur un texte
            # générique interne ("...have a look here: {documentation_url}")
            # si la description personnalisée ne se charge pas pour une
            # langue donnée. Ce texte générique attend une variable
            # 'documentation_url' : on la fournit toujours pour que
            # l'affichage ne casse jamais, quelle que soit la cause exacte
            # du fallback.
            description_placeholders={"documentation_url": DOCUMENTATION_URL},
        )
