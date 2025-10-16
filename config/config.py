"""
Configuration centralisée pour le projet SimilarWeb Intelligence Platform
"""
import os
from datetime import datetime
from pathlib import Path

# Charger les variables d'environnement depuis .env si disponible
try:
    from dotenv import load_dotenv
    # Chercher le fichier .env dans le répertoire parent
    env_path = Path(__file__).parent.parent / '.env'
    if env_path.exists():
        load_dotenv(env_path)
except ImportError:
    # python-dotenv n'est pas installé, continuer sans
    pass

# === Configuration API SimilarWeb ===
SIMILARWEB_API_KEY = os.environ.get('SIMILARWEB_API_KEY', '865fd28dc61c402396309df6ddfb145d')
SIMILARWEB_BASE_URL = 'https://api.similarweb.com/v1'

# Headers par défaut pour l'API
API_HEADERS = {
    'accept': 'application/json'
}

# === Configuration des domaines à analyser ===
TARGET_DOMAINS = ['amazon.fr', 'joueclub.fr']

# === Configuration des extractions ===
# Granularité par défaut
DEFAULT_GRANULARITY = 'daily'  # Options: 'daily', 'weekly', 'monthly'
DEFAULT_COUNTRY = 'fr'

# Métriques pour les segments - divisées en groupes pour l'API
SEGMENT_METRICS_GROUPS = [
    'visits,share',
    'bounce-rate,pages-per-visit,visit-duration',
    'page-views'
    # ,unique-visitors'
]

# Endpoints pour les sites web
WEBSITE_METRICS_ENDPOINTS = {
    'visits': '/total-traffic-and-engagement/visits',
    'pages_per_visit': '/total-traffic-and-engagement/pages-per-visit',
    'avg_visit_duration': '/total-traffic-and-engagement/average-visit-duration',
    'bounce_rate': '/total-traffic-and-engagement/bounce-rate',
    'page_views': '/total-traffic-and-engagement/page-views',
    'desktop_mobile_split': '/total-traffic-and-engagement/visits-split'
}

# === Configuration GCP (pour phase de déploiement) ===
GCP_PROJECT_ID = os.environ.get('GCP_PROJECT_ID', 'similarweb-intelligence-dev')
BIGQUERY_DATASET = os.environ.get('BIGQUERY_DATASET', 'similarweb_data')
CLOUD_STORAGE_BUCKET = os.environ.get('GCS_BUCKET', 'similarweb-data-bucket')

# Tables BigQuery
BIGQUERY_TABLES = {
    'segments': 'segments_data',
    'websites': 'websites_data'
}

# === Configuration des limites et retry ===
API_RATE_LIMIT_DELAY = 1  # Délai en secondes entre les appels API
MAX_RETRIES = 3
RETRY_DELAY = 5  # Délai en secondes entre les tentatives

# === Configuration des notifications (pour phases ultérieures) ===
SLACK_WEBHOOK_URL = os.environ.get('SLACK_WEBHOOK_URL', '')
WHATSAPP_API_URL = os.environ.get('WHATSAPP_API_URL', '')

# === Configuration des chemins locaux ===
DATA_PATH = 'data'
LOGS_PATH = 'logs'
SCRIPTS_PATH = 'scripts'

# === Configuration des formats de date ===
def get_current_month():
    """Retourne le mois actuel au format YYYY-MM"""
    return datetime.now().strftime('%Y-%m')

def get_current_date():
    """Retourne la date actuelle au format YYYY-MM-DD"""
    return datetime.now().strftime('%Y-%m-%d')

# === Configuration des seuils d'alerte (pour Vertex AI) ===
ALERT_THRESHOLDS = {
    'visits_drop_percentage': 20,  # Alerte si baisse > 20%
    'bounce_rate_increase': 10,    # Alerte si augmentation > 10%
    'segment_share_change': 15     # Alerte si changement > 15%
} 