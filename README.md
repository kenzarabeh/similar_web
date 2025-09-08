#  Guide SimilarWeb Data Pipeline

## Vue d'ensemble

Ce projet permet d'extraire automatiquement des données SimilarWeb pour :
- **88 segments personnalisés** (concurrents par secteur)
- **21 sites web** majeurs
- **Métriques clés** : visites, durée, pages/visite, taux de rebond
- **Historique** : données mensuelles depuis 2024

## Ce que vous pouvez faire

1. **Extraire des données** via l'API SimilarWeb
2. **Automatiser** l'extraction quotidienne sur Google Cloud Platform
3. **Stocker** les données dans BigQuery

## Installation rapide

### 1. Prérequis
- Python 3.11+
- Clé API SimilarWeb (demander à votre équipe)
- Compte Google Cloud Platform (optionnel pour l'automatisation)

### 2. Configuration locale

```bash
# 1. Créer l'environnement virtuel
python3 -m venv venv
source venv/bin/activate  # Sur Mac/Linux
# ou
venv\Scripts\activate  # Sur Windows

# 2. Installer les dépendances
pip install -r requirements.txt

# 3. Configurer vos clés API
cp config/env.example config/.env
# Éditer config/.env et ajouter votre clé API SimilarWeb
```

### 3. Structure du fichier `.env`
```env
# OBLIGATOIRE : Votre clé API SimilarWeb
SIMILARWEB_API_KEY=votre_cle_api_ici

# Configuration GCP
GCP_PROJECT_ID=votre-projet-gcp
BIGQUERY_DATASET=similar_web_data
```

## Extraction de données

### Extraction simple (mois en cours)
```bash
python scripts/daily_extraction.py
```

### Extraction d'un mois spécifique
```bash
python scripts/daily_extraction.py --year 2025 --month 6
```

### Extraction historique (backfill)
```bash
# Récupérer les 12 derniers mois
python scripts/historical_backfill.py
```

### Extraction des segments uniquement
```bash
python scripts/extract_user_segments_only.py
```

## Où trouver les données

Les données extraites sont sauvegardées dans :
- `data/segments/` - Données des segments (JSON)
- `data/websites/` - Données des sites web (JSON)

Format des fichiers : `segments_YYYY-MM.json`

## Structure des données

### Segments
```json
{
  "segment_id": "abc123",
  "segment_name": "E.Leclerc - Parapharmacie",
  "date": "2025-06-01",
  "visits": 1234567,
  "share": 0.0234,
  "bounce_rate": 0.456,
  "pages_per_visit": 3.2,
  "visit_duration": 180.5
}
```

### Sites web
```json
{
  "domain": "amazon.fr",
  "date": "2025-06-01",
  "visits": 98765432,
  "bounce_rate": 0.345,
  "pages_per_visit": 8.9,
  "visit_duration": 420.3
}
```

## Scripts principaux

### `scripts/similarweb_api.py`
Wrapper Python pour l'API SimilarWeb. Utilisez la classe `SimilarWebAPI` :

```python
from scripts.similarweb_api import SimilarWebAPI

api = SimilarWebAPI()
segments = api.get_custom_segments(user_only=True)
```

### `scripts/daily_extraction.py`
Script principal d'extraction. Peut être lancé :
- Manuellement pour un mois spécifique
- Automatiquement via Cloud Scheduler

### `scripts/upload_to_bigquery.py`
Upload les données JSON vers BigQuery (nécessite configuration GCP).

## Déploiement sur GCP

Si vous souhaitez automatiser l'extraction quotidienne :

### 1. Préparer votre projet GCP
```bash
# Configurer gcloud
gcloud auth login
gcloud config set project VOTRE_PROJET_ID
```

### 2. Créer les tables BigQuery

### 3. Déployer la Cloud Function

### 4. Configurer l'automatisation

### Problèmes fréquents

**1. Données manquantes**
- SimilarWeb a un délai de 7 jours (les données de juin sont disponibles après le 7 juillet)
- Utilisez le script `check_missing_data.py` pour identifier les trous

**2. Rate limit atteint**
- Le script gère automatiquement les rate limits
- Si persistant, augmentez le délai dans `config/config.py`

## Notes importantes

1. **Segments personnalisés** : Le paramètre `userOnlySegments=true` réduit de 159 à 88 segments
2. **Limite API** : Vérifiez votre quota mensuel (généralement 10k appels)
3. **Historique** : Les données sont disponibles jusqu'à 37 mois en arrière

## Prochaines étapes recommandées

1. **Tester l'extraction** sur un mois récent
2. **Configurer BQ** 
3. **Automatiser** via GCP pour des mises à jour quotidiennes
 