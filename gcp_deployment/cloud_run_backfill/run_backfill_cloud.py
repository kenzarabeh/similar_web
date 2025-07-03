"""
Script de backfill pour Cloud Run
Upload automatiquement les données vers BigQuery après extraction
"""
import os
import sys
import logging
from datetime import datetime

# Ajouter le chemin pour les imports
sys.path.append('/app')

from scripts.historical_backfill import run_backfill
from gcp_deployment.cloud_functions.bigquery_utils import insert_segments_data, insert_websites_data
from scripts.similarweb_api import SimilarWebAPI
import json

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def upload_to_bigquery(data_file: str, data_type: str):
    """Upload les données extraites vers BigQuery"""
    try:
        with open(data_file, 'r') as f:
            data = json.load(f)
        
        if data_type == 'segments':
            # Formater pour BigQuery
            formatted_data = []
            for segment in data.get('segments', []):
                if segment['data'] and 'segments' in segment['data']:
                    for seg_data in segment['data']['segments']:
                        for date_str, metrics in seg_data.get('data', {}).items():
                            if isinstance(metrics, dict):
                                formatted_data.append({
                                    'date': date_str,
                                    'segment_id': segment['segment_id'],
                                    'segment_name': segment['segment_name'],
                                    **metrics
                                })
            
            if formatted_data:
                insert_segments_data(formatted_data)
                logger.info(f"✅ {len(formatted_data)} lignes de segments uploadées vers BigQuery")
        
        elif data_type == 'websites':
            # Formater pour BigQuery
            formatted_data = []
            for site in data.get('websites', []):
                metrics = site.get('metrics', {})
                
                # Extraire les données de chaque métrique
                visits_data = metrics.get('visits', {}).get('visits', [])
                for visit in visits_data:
                    date_str = visit.get('date')
                    if date_str:
                        row = {
                            'date': date_str,
                            'domain': site['domain'],
                            'visits': visit.get('visits')
                        }
                        
                        # Ajouter les autres métriques
                        for metric_name, metric_data in metrics.items():
                            if metric_name != 'visits' and metric_data:
                                metric_values = metric_data.get(list(metric_data.keys())[0], [])
                                for mv in metric_values:
                                    if mv.get('date') == date_str:
                                        if metric_name == 'pages_per_visit':
                                            row['pages_per_visit'] = mv.get('pages_per_visit')
                                        elif metric_name == 'avg_visit_duration':
                                            row['avg_visit_duration'] = mv.get('average_visit_duration')
                                        elif metric_name == 'bounce_rate':
                                            row['bounce_rate'] = mv.get('bounce_rate')
                                        elif metric_name == 'page_views':
                                            row['page_views'] = mv.get('page_views')
                                        elif metric_name == 'desktop_mobile_split':
                                            row['desktop_share'] = mv.get('desktop_share')
                                            row['mobile_share'] = mv.get('mobile_share')
                        
                        formatted_data.append(row)
            
            if formatted_data:
                insert_websites_data(formatted_data)
                logger.info(f"✅ {len(formatted_data)} lignes de sites web uploadées vers BigQuery")
                
    except Exception as e:
        logger.error(f"Erreur lors de l'upload vers BigQuery: {e}")

def main():
    """Fonction principale"""
    logger.info("🚀 Démarrage du backfill Cloud Run")
    
    # Récupérer les paramètres depuis les variables d'environnement
    limit_segments = int(os.environ.get('LIMIT_SEGMENTS', '0')) or None
    batch_size = int(os.environ.get('BATCH_SIZE', '3'))
    
    try:
        # Lancer le backfill
        stats = run_backfill(
            start_year=2024,
            skip_existing=True,
            limit_segments=limit_segments,
            batch_size=batch_size
        )
        
        logger.info("📤 Upload des données vers BigQuery...")
        
        # Chercher les fichiers de données générés
        import glob
        
        # Upload des segments
        segment_files = glob.glob('/app/data/segments_extraction_*.json')
        for file in segment_files:
            logger.info(f"Upload du fichier: {file}")
            upload_to_bigquery(file, 'segments')
        
        # Upload des sites web
        website_files = glob.glob('/app/data/websites_extraction_*.json')
        for file in website_files:
            logger.info(f"Upload du fichier: {file}")
            upload_to_bigquery(file, 'websites')
        
        logger.info("✅ Backfill Cloud Run terminé avec succès!")
        logger.info(f"Statistiques: {stats}")
        
    except Exception as e:
        logger.error(f"❌ Erreur lors du backfill: {e}")
        raise

if __name__ == "__main__":
    main() 