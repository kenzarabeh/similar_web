# 📚 Documentation API - SimilarWeb Intelligence Platform

## Architecture des Scripts

### 🔧 `scripts/similarweb_api.py`
Module principal pour interagir avec l'API SimilarWeb.

**Classe principale :** `SimilarWebAPI`

#### Méthodes principales :
```python
# Initialisation
api = SimilarWebAPI(api_key, user_only_segments=True)

# Récupérer les segments
segments = api.get_segments()

# Extraire les données d'un segment
data = api.get_segment_data(
    segment_id="abc123",
    domain="domain.com",
    start_date="2024-01", 
    end_date="2024-12",
    time_granularity="monthly"
)

# Extraire les données d'un site web
website_data = api.get_website_data(
    domain="amazon.fr",
    start_date="2024-01",
    end_date="2024-12"
)
```

### 📅 `scripts/daily_extraction.py`
Script d'extraction quotidienne/mensuelle.

**Fonction principale :** `main(event=None)`

#### Paramètres d'event :
```python
event = {
    'year': 2025,      # Année spécifique
    'month': 6,        # Mois spécifique
    'test_mode': True  # Mode test (limite à 2 segments)
}
```

### 🌐 `scripts/website_manager.py`
Gestion des 21 domaines analysés.

**Domaines inclus :**
- E-commerce : amazon.fr, cdiscount.com, fnac.com
- Parapharmacie : (via segments uniquement)
- Jouets : joueclub.fr, cultura.com
- Bricolage : leroymerlin.fr
- Alimentaire : leclerc.com, carrefour.fr, auchan.fr

### 📊 `scripts/create_dashboard.py`
Génération du dashboard HTML interactif.

**Fonction principale :** `create_comparison_dashboard()`

## Structures de données

### Format Segment
```json
{
    "segment_id": "abc123-def456",
    "segment_name": "E.Leclerc - Parapharmacie",
    "date": "2024-05-01",
    "visits": 1234567,
    "share": 0.0234,
    "extraction_date": "2025-06-20"
}
```

### Format Website
```json
{
    "domain": "amazon.fr",
    "date": "2024-05-01",
    "visits": 123456789,
    "pages_per_visit": 5.67,
    "avg_visit_duration": 234.56,
    "bounce_rate": 0.345,
    "extraction_date": "2025-06-20"
}
```

## Tables BigQuery

### `segments_data`
```sql
-- Schéma
segment_id: STRING
segment_name: STRING
date: DATE
visits: INTEGER
share: FLOAT
extraction_date: TIMESTAMP
```

### `websites_data`
```sql
-- Schéma
domain: STRING
date: DATE
visits: INTEGER
pages_per_visit: FLOAT
avg_visit_duration: FLOAT
bounce_rate: FLOAT
extraction_date: TIMESTAMP
```

## Endpoints API SimilarWeb utilisés

### Segments
- `GET /v1/segment/traffic-and-engagement/describe/` - Liste des segments
- `POST /v3/segment/{segment_id}/total-traffic-and-engagement/query` - Données segment

### Websites
- `POST /v1/website/{domain}/total-traffic-and-engagement/visits` - Visites
- `GET /v1/website/{domain}/total-traffic-and-engagement/pages-per-visit` - Pages/visite
- `GET /v1/website/{domain}/total-traffic-and-engagement/average-visit-duration` - Durée
- `GET /v1/website/{domain}/total-traffic-and-engagement/bounce-rate` - Taux rebond

## Gestion des erreurs

### Codes d'erreur API
- `400` : Paramètres invalides
- `401` : Clé API invalide
- `402` : Quota dépassé
- `429` : Rate limit atteint (attendre 2 secondes)

### Retry Logic
```python
MAX_RETRIES = 3
for attempt in range(MAX_RETRIES):
    try:
        response = api_call()
        if response.status_code == 429:
            time.sleep(2)
            continue
    except Exception as e:
        if attempt == MAX_RETRIES - 1:
            raise
```

## Optimisations

### Paramètre userOnlySegments
Réduit de 159 à 88 segments (économie de 44% des appels API).

### Batch Processing
Les extractions sont groupées par mois pour optimiser l'utilisation mémoire.

### Délai J-7
Les données sont extraites avec 7 jours de décalage pour garantir leur disponibilité complète. 