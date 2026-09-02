# HA MotoGP (intégration HACS non officielle)

Squelette d'intégration Home Assistant pour afficher la prochaine course du
championnat MotoGP, sur le même principe que
[F1 Sensor](https://github.com/Nicxe/f1_sensor) pour la F1.

⚠️ Utilise l'API non documentée `pulselive` de MotoGP/Dorna. Ni stable ni
garantie dans le temps : vérifiez la forme réelle des réponses JSON avant de
faire confiance aux noms de champs utilisés dans le code (voir commentaires
dans `api.py` et `sensor.py`).

## Installation

1. Publiez ce dossier tel quel dans un dépôt GitHub public
   (`custom_components/motogp/` + `hacs.json` à la racine).
2. Dans HACS : Intégrations → menu ⋮ → Dépôts personnalisés → ajoutez l'URL
   de votre dépôt, type "Intégration".
3. Installez "MotoGP", redémarrez Home Assistant.
4. Paramètres → Appareils et services → Ajouter une intégration → "MotoGP",
   choisissez la catégorie (MotoGP / Moto2 / Moto3).

Cela crée deux capteurs :
- `sensor.motogp_prochaine_course` : état = nom du Grand Prix, attributs =
  `circuit`, `pays`, `date_debut`, `jours_restants`, `sessions`, plan du
  circuit...
- `sensor.motogp_classement_pilotes` : état = nom du pilote en tête du
  championnat, attribut `classement` = liste ordonnée (position, numéro,
  nom, points, équipe, position_change...).

## Avant de coder : valider l'API vous-même

Avant même d'ouvrir `api.py`, testez ces appels dans un navigateur (ou
`curl`) pour confirmer la structure réelle des champs :

```
GET https://api.pulselive.motogp.com/motogp/v1/results/seasons
GET https://api.pulselive.motogp.com/motogp/v1/results/events?seasonUuid=<id>&isFinished=false
GET https://api.pulselive.motogp.com/motogp/v1/results/categories?seasonUuid=<id>
GET https://api.pulselive.motogp.com/motogp/v1/results/sessions?eventUuid=<id>&categoryUuid=<id>
```

Ajustez ensuite les clés (`date_start`, `circuit.name`, etc.) dans `api.py`
et `sensor.py` selon ce que vous observez réellement — c'est l'étape la plus
importante, plus que le code lui-même.

## Carte Lovelace custom "MotoGP - Classement pilotes"

Le fichier `custom_components/motogp/www/motogp-standings-card.js` affiche
le classement du championnat sous forme de tableau (position, drapeau,
numéro, pilote, équipe, points, évolution de position). Enregistrée
automatiquement, au même titre que la carte "Prochaine course".

```yaml
type: custom:motogp-standings-card
entity: sensor.motogp_classement_pilotes
title: Classement MotoGP    # optionnel
limit: 10                   # optionnel, 0/absent = tout afficher
```

## Carte Lovelace custom "MotoGP - Prochaine course"

Le fichier `custom_components/motogp/www/motogp-next-race-card.js` est une
carte Lovelace custom (Web Component, sans étape de build) qui affiche :
- catégorie + nom du Grand Prix
- circuit et pays
- un countdown live (jours / heures / min / sec) jusqu'au début de l'event
- une frise des sessions (EL1, EL2, EL3, Q1, Q2, Course...), la course étant
  mise en valeur par un motif à damier

L'intégration l'enregistre **automatiquement** comme ressource frontend au
démarrage (voir `_async_register_card` dans `__init__.py`), exactement
comme le fait F1 Sensor pour ses cartes bundlées : pas besoin de l'ajouter
manuellement dans Paramètres → Tableaux de bord → Ressources.

Si jamais elle n'apparaît pas après une mise à jour, videz le cache du
navigateur (la ressource est versionnée via `?v=CARD_VERSION` pour éviter
ce problème dans la plupart des cas).

Utilisation dans un tableau de bord (mode YAML de la carte) :

```yaml
type: custom:motogp-next-race-card
entity: sensor.motogp_prochaine_course
title: MotoGP
show_sessions: true       # optionnel, true par défaut — false masque le programme du week-end
show_circuit_map: true    # optionnel, true par défaut — false masque le plan du circuit
circuit_map_zoom: 1.35    # optionnel, 1.35 par défaut — niveau de zoom du plan du circuit
show_info_grid: true      # optionnel, true par défaut — false masque le bloc Prochaine session / Début course / Manche
```

### Plan du circuit

Le capteur appelle un second endpoint (`/events/{toad_api_uuid}`, distinct
de `/results/events`) pour récupérer le tracé du circuit fourni par
l'API : `circuit.tracks[].assets.info.path` (SVG avec virages) et
`assets.simple.path` (PNG, utilisé en repli si le SVG est absent). Cet
appel est fait en "best effort" : s'il échoue, le reste du capteur
continue de fonctionner normalement, seul le plan ne s'affiche pas.

Ou via l'éditeur visuel : "Ajouter une carte" → cherchez
"MotoGP - Prochaine course" dans la liste des cartes custom.

## Alternative rapide sans carte custom

Une carte Markdown fonctionne aussi si vous préférez ne pas dépendre de JS
custom :

```yaml
type: markdown
content: >
  ## 🏍️ {{ state_attr('sensor.motogp_prochaine_course', 'circuit') }}

  **{{ states('sensor.motogp_prochaine_course') }}**

  📅 {{ as_timestamp(state_attr('sensor.motogp_prochaine_course', 'date_debut')) | timestamp_custom('%d %B %Y') }}
  — dans {{ state_attr('sensor.motogp_prochaine_course', 'jours_restants') }} jours

  {% for s in state_attr('sensor.motogp_prochaine_course', 'sessions') %}
  - {{ s.type }} : {{ s.date_start }}
  {% endfor %}
```
