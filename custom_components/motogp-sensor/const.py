"""Constantes pour l'intégration MotoGP."""
from datetime import timedelta

DOMAIN = "motogp"
DOCUMENTATION_URL = "https://github.com/minibn/motogp-sensor"

# Base de l'API "pulselive". Non officielle : vérifiez cette URL de temps
# en temps (elle a existé sous les deux formes api.pulselive.motogp.com
# et api.motogp.pulselive.com selon les périodes).
API_BASE = "https://api.pulselive.motogp.com/motogp/v1"
# Endpoint distinct de /results/, donne les détails "grand public" d'un
# événement (dates réelles, plan du circuit...). Requiert le
# "toad_api_uuid" de l'événement (obtenu via /results/events).
EVENT_DETAIL_BASE = "https://api.pulselive.motogp.com/motogp/v1/events"

ENDPOINT_SEASONS = "/results/seasons"
ENDPOINT_EVENTS = "/results/events"
ENDPOINT_CATEGORIES = "/results/categories"
ENDPOINT_SESSIONS = "/results/sessions"
# Endpoint distinct de /results/ : liste des équipes d'une catégorie pour
# une année donnée, avec leur couleur officielle (color/text_color).
ENDPOINT_TEAMS = "/teams"
# Endpoint "Broadcast" (distinct de /results/categories) : donne l'ID de
# catégorie attendu par /teams, qui n'est PAS le même que celui renvoyé
# par /results/categories pour la même catégorie.
ENDPOINT_BROADCAST_CATEGORIES = "/categories"

# L'API des classements est en v2, contrairement au reste (v1).
STANDINGS_API_BASE = "https://api.pulselive.motogp.com/motogp/v2"
ENDPOINT_WORLD_STANDINGS = "/results/world-standings"

# Nom de la catégorie que l'on veut suivre par défaut.
DEFAULT_CATEGORY_NAME = "MotoGP™"

CONF_CATEGORY = "category_name"

DEFAULT_SCAN_INTERVAL = timedelta(hours=2)

ATTRIBUTION = "Données non officielles fournies par l'API pulselive MotoGP"
