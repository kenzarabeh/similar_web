"""
Utilitaires pour sauvegarder les données dans BigQuery
"""
import logging
from google.cloud import bigquery
from datetime import datetime
from typing import Dict, List, Any

logger = logging.getLogger(__name__)


def save_segments_to_bigquery(segments_data: List[Dict], project_id: str, dataset_id: str = 'similarweb_data'):
    """
    Sauvegarde les données des segments dans BigQuery
    
    Args:
        segments_data: Liste des données de segments
        project_id: ID du projet GCP
        dataset_id: ID du dataset BigQuery
    """
    client = bigquery.Client(project=project_id)
    table_id = f"{project_id}.{dataset_id}.segments_data"
    
    rows_to_insert = []
    extraction_date = datetime.now().date().isoformat()
    
    for segment in segments_data:
        if segment.get('error'):
            continue
            
        segment_id = segment['segment_id']
        segment_name = segment['segment_name']
        
        # Parser les données de trafic
        if segment.get('data') and 'segments' in segment['data']:
            for item in segment['data']['segments']:
                row = {
                    'extraction_date': extraction_date,
                    'segment_id': segment_id,
                    'segment_name': segment_name,
                    'date': item.get('date', ''),
                    'visits': item.get('visits', 0),
                    'share': item.get('share', 0),
                    'confidence': item.get('confidence', ''),
                    # Nouvelles métriques
                    'bounce_rate': item.get('bounce_rate', None),
                    'pages_per_visit': item.get('pages_per_visit', None),
                    'visit_duration': item.get('visit_duration', None),
                    'page_views': item.get('page_views', None),
                    'unique_visitors': item.get('unique_visitors', None)
                }
                rows_to_insert.append(row)
    
    if rows_to_insert:
        errors = client.insert_rows_json(table_id, rows_to_insert)
        if errors:
            logger.error(f"Erreurs lors de l'insertion dans BigQuery: {errors}")
        else:
            logger.info(f"✅ {len(rows_to_insert)} lignes insérées dans {table_id}")
    
    return len(rows_to_insert)


def save_websites_to_bigquery(websites_data: List[Dict], project_id: str, dataset_id: str = 'similarweb_data'):
    """
    Sauvegarde les données des sites web dans BigQuery
    
    Args:
        websites_data: Liste des données de sites web
        project_id: ID du projet GCP
        dataset_id: ID du dataset BigQuery
    """
    client = bigquery.Client(project=project_id)
    table_id = f"{project_id}.{dataset_id}.websites_data"
    
    rows_to_insert = []
    extraction_date = datetime.now().date().isoformat()
    
    for website in websites_data:
        domain = website['domain']
        metrics = website.get('metrics', {})
        
        # Extraire les métriques
        visits_data = metrics.get('visits', {})
        pages_data = metrics.get('pages_per_visit', {})
        duration_data = metrics.get('avg_visit_duration', {})
        bounce_data = metrics.get('bounce_rate', {})
        pageviews_data = metrics.get('page_views', {})
        split_data = metrics.get('desktop_mobile_split', {})
        
        # Créer une ligne par période
        if visits_data and 'visits' in visits_data:
            for item in visits_data['visits']:
                date = item.get('date', '')
                
                # Récupérer les valeurs pour cette date
                visits = item.get('visits', 0)
                
                # Chercher les autres métriques pour la même date
                pages_per_visit = next((x.get('pages_per_visit', 0) for x in pages_data.get('pages_per_visit', []) if x.get('date') == date), 0)
                avg_duration = next((x.get('average_visit_duration', 0) for x in duration_data.get('average_visit_duration', []) if x.get('date') == date), 0)
                bounce_rate = next((x.get('bounce_rate', 0) for x in bounce_data.get('bounce_rate', []) if x.get('date') == date), 0)
                page_views = next((x.get('page_views', 0) for x in pageviews_data.get('page_views', []) if x.get('date') == date), 0)
                
                # Desktop/Mobile split
                desktop_share = 0
                mobile_share = 0
                if split_data and 'data' in split_data:
                    for split_item in split_data['data']:
                        if split_item.get('date') == date:
                            for device in split_item.get('data', []):
                                if device.get('device') == 'desktop':
                                    desktop_share = device.get('value', 0)
                                elif device.get('device') == 'mobile':
                                    mobile_share = device.get('value', 0)
                
                row = {
                    'extraction_date': extraction_date,
                    'domain': domain,
                    'date': date,
                    'visits': visits,
                    'pages_per_visit': pages_per_visit,
                    'avg_visit_duration': avg_duration,
                    'bounce_rate': bounce_rate,
                    'page_views': page_views,
                    'desktop_share': desktop_share,
                    'mobile_share': mobile_share
                }
                rows_to_insert.append(row)
    
    if rows_to_insert:
        errors = client.insert_rows_json(table_id, rows_to_insert)
        if errors:
            logger.error(f"Erreurs lors de l'insertion dans BigQuery: {errors}")
        else:
            logger.info(f"✅ {len(rows_to_insert)} lignes insérées dans {table_id}")
    
    return len(rows_to_insert) 