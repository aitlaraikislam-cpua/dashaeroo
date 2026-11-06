# AERONEX — Aircraft Maintenance Intelligence

Application analytique Streamlit pour explorer les ordres de travail, la flotte, la fiabilité, les systèmes ATA, les coûts et l’impact opérationnel.

## Démarrage

```bash
python -m venv .venv
# Windows : .venv\\Scripts\\activate
# macOS / Linux : source .venv/bin/activate
pip install -r requirements.txt
streamlit run app.py
```

Le fichier source est `data/ait_laraik_islam.csv`. Remplace-le par un CSV compatible si nécessaire : les noms de colonnes attendus sont utilisés dans `utils/data_loader.py`, `utils/calculations.py` et `app.py`.

## Connexion

Pour un environnement local de démonstration, les identifiants par défaut sont `admin` / `demo-Aviation-2026`. **Ils ne doivent pas être utilisés en production.**

Configure tes identifiants dans `.streamlit/secrets.toml` :

```toml
[auth]
username = "ton_utilisateur"
password = "un_mot_de_passe_long_et_unique"
```

Ou via les variables d’environnement `AMA_USERNAME` et `AMA_PASSWORD`. Ne publie jamais `secrets.toml` et ne versionne aucun secret.

## Séparation des informations

AERONEX distingue explicitement trois catégories :

1. **Données réelles** — enregistrements et champs chargés du CSV fourni (ordres de travail, immatriculations, escales, coûts, dates, défauts, statuts, etc.).
2. **Indicateurs et alertes calculés** — KPI, agrégations, classements et listes AOG / High / MEL / défauts répétitifs construites à partir des champs source et des filtres actifs. Les règles sont visibles dans le code Python.
3. **Éléments décoratifs** — photographie de hangar, images illustratives d’avion / moteur / maintenance, silhouette d’avion, logo, effets CSS et textes de présentation. Les images illustratives ne sont pas reliées à une immatriculation, un WO ou un événement du CSV et ne sont jamais utilisées dans les calculs.

Les alertes sont des signaux analytiques dérivés des données disponibles. Elles ne sont pas temps réel et ne constituent ni un diagnostic technique, ni une décision de dispatch, ni une déclaration de navigabilité.

## Fonctionnalités conservées

- Authentification de démonstration et déconnexion
- Thème sombre / clair
- Navigation par modules et filtres globaux
- KPI et analyses Plotly
- Analyses flotte, fiabilité, ATA, coûts, immobilisation et retards
- Centre d’alertes analytiques
- Exploration, recherche et export CSV
- Contrôle qualité des données sans suppression silencieuse des lignes

## Personnalisation

- `config.py` : titre, sous-titre et navigation
- `assets/styles.css` : design, responsive, animations et thèmes
- `assets/` : photographie de couverture et visuels illustratifs locaux (aucun chargement d’image externe à l’exécution)
- `components/charts.py` : palette et style Plotly
- `components/login.py` : écran de connexion
- `utils/data_loader.py` : chargement et qualité des données
- `utils/calculations.py` : règles de calcul des KPI
- `app.py` : pages, filtres et visualisations

## Limites à connaître

Les résultats dépendent de la qualité et de la couverture du CSV. Une donnée absente n’est pas assimilée à zéro lorsque le champ reste manquant. Vérifie les règles métier et la signification des champs avec les responsables maintenance avant toute utilisation opérationnelle.


## Module Activité quotidienne
Le module **Activité quotidienne** regroupe les ordres de travail par date d'ouverture et affiche des cartes avion avec immatriculation, type, escale, système ATA, priorité, statut et horaires d'intervention. Il propose aussi un export CSV par journée.

**Limite de la source :** le CSV contient des données de maintenance, pas des horaires de vols ni une télémétrie de suivi aérien. Les cartes décrivent donc l'activité de maintenance réellement présente dans le fichier et ne doivent pas être interprétées comme un suivi de vols en temps réel.


## Version visuelle multilingue
- Choix de langue dès l'écran de connexion : français, anglais ou espagnol.
- Navigation traduite et possibilité de changer la langue depuis la barre latérale.
- Profils visuels par type de flotte et fiche avion individuelle avec historique récent.
- Cartes quotidiennes enrichies de photographies d'illustration.
- Vues visuelles pour les systèmes ATA, les coûts, les alertes et les ordres de travail afin de réduire l'usage des tableaux.
- Les photographies sont des illustrations d'aéronefs/environnements et ne prétendent pas représenter l'immatriculation exacte.


## Mise à jour de l'interface dashboard
- Le sélecteur de langue est disponible dès l'écran de connexion (français, anglais, espagnol).
- La page d'accueil comprend une bannière photo et des raccourcis visuels vers les modules principaux.
- Les pages Fiabilité, Analyse ATA et Rapports disposent de bannières photographiques thématiques.
- Les photographies restent illustratives ; les chiffres, alertes et fiches sont calculés à partir du CSV.
- Le journal quotidien décrit les interventions de maintenance, et ne simule pas des vols ni un suivi GPS.


## Interface AERONEX — cockpit visuel

La page « Vue d’ensemble » utilise une disposition cockpit : suivi de flotte, réseau des escales du jeu de données, alertes calculées, comparaison des types d’avions, journal récent et actions rapides. La carte représente les aéroports associés aux ordres de maintenance du CSV ; elle ne prétend pas afficher des positions avion ou des trajectoires en temps réel.


## AERONEX V2 Premium — modules additionnels

- Fiches avions individuelles avec historique des ordres issus du CSV.
- Planning de maintenance avec saisie persistante dans `data/aeronex.db`.
- Carte des escales avec agrégats de maintenance (pas de tracking GPS).
- AERONEX AI : analyses descriptives explicables, sans diagnostic prédictif.
- Stocks de pièces et seuils minimum (saisie manuelle).
- Répertoire des techniciens (compétences et disponibilités déclaratives).
- Notifications calculées à partir des signaux du dataset.
- Rapports PDF téléchargeables.

### Installation / lancement

```bash
pip install -r requirements.txt
streamlit run app.py
```

La base SQLite est créée automatiquement au premier lancement. Sauvegarder `data/aeronex.db` pour conserver les données saisies.

### Langues
Le sélecteur propose français, anglais et arabe. La navigation et la direction RTL sont adaptées en arabe ; certains libellés analytiques historiques des modules existants restent en français.

### Limites opérationnelles
Les données source ne contiennent pas de calendrier réglementaire, de données capteurs, de GPS, ni de référentiel de pièces ou d'habilitations. Les alertes et analyses sont des aides descriptives à vérifier par le personnel habilité. Elles ne remplacent ni AMM/MPD, ni les procédures approuvées, ni les décisions de navigabilité.


## AERONEX V3 — amélioration visuelle

Cette version conserve l'application Streamlit, les données CSV, les calculs KPI,
les graphiques, les modules de maintenance et la base SQLite existants.

Améliorations :
- Bannières photographiques locales adaptées aux familles de pages (flotte,
  hangar, moteurs, inspection et techniciens).
- Photographie réelle intégrée à l'écran de connexion.
- Sélecteur de langue étendu à Français, English, العربية et Español sur
  l'écran de connexion et dans la navigation.
- Mise en page RTL activée pour l'arabe.
- Images embarquées dans le projet : aucun téléchargement externe requis
  pour afficher les visuels.

Note : les photographies illustrent l'environnement aéronautique ; elles ne
constituent pas des preuves d'inspection ni des données opérationnelles.
Le son d'ambiance n'est pas activé par défaut : l'autoplay audio est bloqué
par plusieurs navigateurs et aucun fichier audio validé n'était fourni.

## Correctifs de navigation et de lisibilité — V3.1
- Les raccourcis du tableau de bord ouvrent maintenant les bons modules : Ordres de travail, Planning de maintenance, Carte mondiale des escales et Rapports PDF professionnels.
- Le choix du module dans la barre latérale est synchronisé avec les raccourcis, y compris après un changement de langue.
- Un bouton « Retour au Dashboard » est disponible depuis les pages secondaires.
- Les boutons d'action, de téléchargement et de formulaire utilisent maintenant des couleurs de texte et de fond liées au thème actif pour éviter les libellés blancs illisibles.
- Vérification de compilation Python et chargement des 30 000 lignes du CSV source (24 colonnes).


## AERONEX V3.2 — Fleet Intelligence
La page **Flotte** a été restructurée en cockpit analytique :
- Vue d'ensemble avec flotte, ordres, coûts, immobilisation et âge moyen.
- Galerie de modèles avec cinq visuels locaux distincts (aucune photo répétée dans la galerie).
- Comparaison des modèles, distribution du parc et classements dynamiques.
- Profil d'une immatriculation avec historique récent.
- Toutes les métriques sont agrégées depuis les données CSV et les filtres actifs ; aucun chiffre de démonstration n'est ajouté.


## Fleet Intelligence update (V3.3)

The Fleet module now includes:
- Consolidated fleet KPIs and aircraft-model cards with distinct, real Wikimedia Commons photographs.
- Interactive model comparison with both total and per-aircraft metrics.
- Cost, maintenance workload, and downtime visual analytics.
- Fleet Intelligence rankings that normalize costs, work orders, and downtime by fleet size.
- A dedicated model/aircraft profile view with registration-level history, costs, ATA distribution, and monthly activity.
- An expanded aircraft, engine, maintenance, and cockpit gallery.

Image sources, creators, and license information are documented in `assets/image_sources.md`. Model photographs are loaded from Wikimedia Commons at runtime, so internet access is needed to display them. The existing login, filters, data loading, database-backed planning and inventory, notifications, reports, and other modules remain in place.

## AERONEX V3.5 — Neon Aviation refresh

This release applies a unified dark-cockpit / neon-aviation visual system across the existing Streamlit modules and upgrades the maintenance network page with a Morocco network overview, KPI strip, centre list, and connected geographic map.

Included fleet capabilities: fleet KPIs, aircraft-model cards, model comparison, cost and downtime analytics, per-model/per-registration profiles, fleet-intelligence rankings, and an aircraft/engine/cabin gallery. Existing modules for operations, reliability, ATA analysis, workshop costs, downtime, alerts, work orders, maintenance planning, AI helper, inventory, technician management, notifications, and reports remain in the application.

The maintenance map uses fixed airport coordinates from the dataset and is not live GPS or flight tracking. External model/gallery photographs require an internet connection; local maintenance imagery is bundled in `assets/`.

### Validation
- Python syntax compilation: passed for all application Python files.
- Dataset schema check: passed for the expected aircraft, maintenance, cost, and downtime fields.
- Full interactive browser smoke test: not run in this build environment because Streamlit is not installed here. Install `requirements.txt` and launch with `streamlit run app.py` to perform the final runtime check.
