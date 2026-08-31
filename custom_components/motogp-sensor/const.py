"""Constantes pour l'intégration MotoGP."""
from datetime import timedelta

DOMAIN = "motogp"

# Base de l'API "pulselive". Non officielle : vérifiez cette URL de temps
# en temps (elle a existé sous les deux formes api.pulselive.motogp.com
# et api.motogp.pulselive.com selon les périodes).
API_BASE = "https://api.pulselive.motogp.com/motogp/v1"

ENDPOINT_SEASONS = "/results/seasons"
ENDPOINT_EVENTS = "/results/events"
ENDPOINT_CATEGORIES = "/results/categories"
ENDPOINT_SESSIONS = "/results/sessions"

# Nom de la catégorie que l'on veut suivre par défaut.
DEFAULT_CATEGORY_NAME = "MotoGP™"

CONF_CATEGORY = "category_name"

DEFAULT_SCAN_INTERVAL = timedelta(hours=2)

ATTRIBUTION = "Données non officielles fournies par l'API pulselive MotoGP"
