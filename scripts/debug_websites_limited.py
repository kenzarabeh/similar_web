#!/usr/bin/env python3
"""
Script modifié pour créer 3 tables :
- segments_daily (daily, sans unique_visitors)
- websites_daily (daily, avec unique_visitors)  
- segments_unique_visitors (monthly, seulement unique_visitors)
"""
import sys
import os
import json
import logging
from datetime import datetime
from google.cloud import bigquery

# Ajouter le chemin parent pour importer les modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config.config import *
from scripts.similarweb_api import SimilarWebAPI, save_results_to_json

# Configuration du logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class ThreeTablesTestExtractor:
    """
    Extracteur pour 3 tables distinctes avec granularités adaptées
    """
    
    def __init__(self, project_id=None):
        self.api = SimilarWebAPI()
        self.project_id = project_id or os.environ.get('GCP_PROJECT_ID', 'lec-lco-mkt-acquisition-prd')
        self.client = bigquery.Client(project=self.project_id)
        self.dataset_id = 'similar_web_data'
        
        # Configuration pour les 3 extractions
        self.test_config = {
            'start_date': '2025-09',
            'end_date': '2025-09',
            'daily_granularity': 'daily',
            'monthly_granularity': 'monthly',
            'max_segments': 3,
            'test_domains': ['amazon.fr', 'cdiscount.com', 'fnac.com']
        }
        
        # Endpoints websites (inchangés)
        self.website_endpoints = {
            'visits': '/total-traffic-and-engagement/visits',
            'pages_per_visit': '/total-traffic-and-engagement/pages-per-visit',
            'avg_visit_duration': '/total-traffic-and-engagement/average-visit-duration',
            'bounce_rate': '/total-traffic-and-engagement/bounce-rate',
            'page_views': '/total-traffic-and-engagement/page-views',
            'desktop_mobile_split': '/total-traffic-and-engagement/visits-split',
            'unique_visitors_desktop': '/unique-visitors/desktop_unique_visitors',
            'unique_visitors_mobile': '/unique-visitors/mobileweb_unique_visitors'
        }
        
    def extract_segments_daily(self):
        """
        Extraction segments DAILY sans unique_visitors - avec debug détaillé
        """
        logger.info("EXTRACTION SEGMENTS DAILY (sans unique_visitors)")
        logger.info("=" * 55)
        
        # Récupérer segments
        all_segments = self.api.get_custom_segments(user_only=True)
        if not all_segments:
            logger.error("Aucun segment disponible")
            return []
        
        test_segments = all_segments[:self.test_config['max_segments']]
        logger.info(f"Test avec {len(test_segments)} segments en daily")
        
        segments_data = []
        
        for i, segment in enumerate(test_segments):
            segment_id = segment.get('segment_id')
            segment_name = segment.get('segment_name', 'N/A')
            
            logger.info(f"Extraction segment daily {i+1}/{len(test_segments)}: {segment_name}")
            logger.info(f"  segment_id: {segment_id}")
            
            # Appel daily SANS unique_visitors avec debug
            data = self.api.get_segment_data_daily_no_uv(
                segment_id=segment_id,
                start_date=self.test_config['start_date'],
                end_date=self.test_config['end_date'],
                granularity=self.test_config['daily_granularity']
            )
            
            # DEBUG: Analyser la réponse
            if data:
                logger.info(f"  Données reçues pour {segment_name}")
                if 'segments' in data:
                    segments_count = len(data['segments'])
                    logger.info(f"  Nombre de points dans segments: {segments_count}")
                    
                    if segments_count > 0:
                        first_segment = data['segments'][0]
                        last_segment = data['segments'][-1] if segments_count > 1 else first_segment
                        logger.info(f"  Première date: {first_segment.get('date', 'N/A')}")
                        logger.info(f"  Dernière date: {last_segment.get('date', 'N/A')}")
                        logger.info(f"  Métriques dans premier point: {list(first_segment.keys())}")
                else:
                    logger.warning(f"  Pas de clé 'segments' dans la réponse pour {segment_name}")
                    logger.warning(f"  Clés disponibles: {list(data.keys())}")
            else:
                logger.error(f"  Aucune donnée reçue pour {segment_name}")
            
            segments_data.append({
                'segment_id': segment_id,
                'segment_name': segment_name,
                'data': data,
                'extraction_granularity': self.test_config['daily_granularity'],
                'table_type': 'segments_daily',
                'extraction_date': datetime.now().isoformat()
            })
        
        # Sauvegarder
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f"segments_daily_{timestamp}.json"
        save_results_to_json(segments_data, filename)
        
        logger.info(f"Segments daily sauvegardés dans {filename}")
        
        # DEBUG FINAL: Compter les points totaux attendus
        total_expected_points = 0
        for segment in segments_data:
            if segment['data'] and 'segments' in segment['data']:
                total_expected_points += len(segment['data']['segments'])
        logger.info(f"TOTAL POINTS ATTENDUS dans segments_daily: {total_expected_points}")
        
        return segments_data
    
    def extract_segments_unique_visitors(self):
        """
        Extraction segments MONTHLY uniquement pour unique_visitors
        """
        logger.info("EXTRACTION SEGMENTS UNIQUE_VISITORS (monthly)")
        logger.info("=" * 55)
        
        # Récupérer segments
        all_segments = self.api.get_custom_segments(user_only=True)
        if not all_segments:
            logger.error("Aucun segment disponible")
            return []
        
        test_segments = all_segments[:self.test_config['max_segments']]
        logger.info(f"Test avec {len(test_segments)} segments en monthly pour unique_visitors")
        
        segments_uv_data = []
        
        for i, segment in enumerate(test_segments):
            segment_id = segment.get('segment_id')
            segment_name = segment.get('segment_name', 'N/A')
            
            logger.info(f"Extraction unique_visitors {i+1}/{len(test_segments)}: {segment_name}")
            
            # Appel monthly SEULEMENT pour unique_visitors
            data = self.api.get_segment_unique_visitors_only(
                segment_id=segment_id,
                start_date=self.test_config['start_date'],
                end_date=self.test_config['end_date'],
                granularity=self.test_config['monthly_granularity']
            )
            
            segments_uv_data.append({
                'segment_id': segment_id,
                'segment_name': segment_name,
                'data': data,
                'extraction_granularity': self.test_config['monthly_granularity'],
                'table_type': 'segments_unique_visitors',
                'extraction_date': datetime.now().isoformat()
            })
        
        # Sauvegarder
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f"segments_unique_visitors_{timestamp}.json"
        save_results_to_json(segments_uv_data, filename)
        
        logger.info(f"Segments unique_visitors sauvegardés dans {filename}")
        return segments_uv_data
    
    def extract_websites_daily(self):
        """
        Extraction websites DAILY avec unique_visitors (inchangé)
        """
        logger.info("EXTRACTION WEBSITES DAILY (avec unique_visitors)")
        logger.info("=" * 55)
        
        websites_data = []
        
        for domain in self.test_config['test_domains']:
            logger.info(f"Extraction {domain}")
            
            domain_results = {
                'domain': domain,
                'period': f"{self.test_config['start_date']} to {self.test_config['end_date']}",
                'extraction_date': datetime.now().isoformat(),
                'extraction_granularity': self.test_config['daily_granularity'],
                'table_type': 'websites_daily',
                'metrics': {}
            }
            
            # Extraire toutes les métriques incluant unique_visitors
            for metric_name, endpoint in self.website_endpoints.items():
                logger.info(f"  Extraction {metric_name}...")
                
                data = self.api.get_website_metric(
                    domain=domain,
                    metric_endpoint=endpoint,
                    start_date=self.test_config['start_date'],
                    end_date=self.test_config['end_date'],
                    granularity=self.test_config['daily_granularity']
                )
                
                if data:
                    logger.info(f"    {metric_name} récupéré")
                    domain_results['metrics'][metric_name] = data
                else:
                    logger.error(f"    Échec {metric_name}")
                    domain_results['metrics'][metric_name] = None
            
            websites_data.append(domain_results)
        
        # Sauvegarder
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f"websites_daily_{timestamp}.json"
        save_results_to_json(websites_data, filename)
        
        logger.info(f"Websites daily sauvegardés dans {filename}")
        return websites_data
    
    def create_three_tables(self):
        """Crée les 3 tables avec schémas adaptés"""
        logger.info("Création des 3 tables BigQuery")
        
        # 1. Schéma segments_daily (SANS unique_visitors)
        segments_daily_schema = [
            bigquery.SchemaField("segment_id", "STRING"),
            bigquery.SchemaField("segment_name", "STRING"),
            bigquery.SchemaField("date", "DATE"),
            bigquery.SchemaField("visits", "FLOAT"),
            bigquery.SchemaField("share", "FLOAT"),
            bigquery.SchemaField("bounce_rate", "FLOAT"),
            bigquery.SchemaField("pages_per_visit", "FLOAT"),
            bigquery.SchemaField("visit_duration", "FLOAT"),
            bigquery.SchemaField("page_views", "FLOAT"),
            # PAS de unique_visitors
            bigquery.SchemaField("extraction_date", "DATE"),
            bigquery.SchemaField("confidence", "STRING"),
            bigquery.SchemaField("granularity", "STRING"),
        ]
        
        # 2. Schéma segments_unique_visitors (SEULEMENT unique_visitors + dimensions)
        segments_uv_schema = [
            bigquery.SchemaField("segment_id", "STRING"),
            bigquery.SchemaField("segment_name", "STRING"),
            bigquery.SchemaField("date", "DATE"),
            bigquery.SchemaField("unique_visitors", "FLOAT"),  # SEULEMENT cette métrique
            bigquery.SchemaField("extraction_date", "DATE"),
            bigquery.SchemaField("confidence", "STRING"),
            bigquery.SchemaField("granularity", "STRING"),
        ]
        
        # 3. Schéma websites_daily (AVEC unique_visitors, inchangé)
        websites_daily_schema = [
            bigquery.SchemaField("domain", "STRING"),
            bigquery.SchemaField("date", "DATE"),
            bigquery.SchemaField("visits", "FLOAT"),
            bigquery.SchemaField("bounce_rate", "FLOAT"),
            bigquery.SchemaField("pages_per_visit", "FLOAT"),
            bigquery.SchemaField("avg_visit_duration", "FLOAT"),
            bigquery.SchemaField("page_views", "FLOAT"),
            bigquery.SchemaField("unique_visitors", "FLOAT"),
            bigquery.SchemaField("desktop_share", "FLOAT"),
            bigquery.SchemaField("mobile_share", "FLOAT"),
            bigquery.SchemaField("extraction_date", "DATE"),
            bigquery.SchemaField("confidence", "FLOAT"),
            bigquery.SchemaField("granularity", "STRING"),
        ]
        
        # Créer les 3 tables
        tables_to_create = [
            ("segments_daily", segments_daily_schema),
            ("segments_unique_visitors", segments_uv_schema),
            ("websites_daily", websites_daily_schema)
        ]
        
        for table_name, schema in tables_to_create:
            table_id = f"{self.project_id}.{self.dataset_id}.{table_name}"
            
            try:
                self.client.delete_table(table_id, not_found_ok=True)
                logger.info(f"Table {table_name} supprimée")
                
                table = bigquery.Table(table_id, schema=schema)
                table = self.client.create_table(table)
                logger.info(f"Table {table_name} créée avec {len(schema)} colonnes")
                
            except Exception as e:
                logger.error(f"Erreur création table {table_name}: {e}")
    
    def process_segments_daily(self, segments_data):
        """Traitement segments daily (SANS unique_visitors) - CORRIGÉ"""
        rows = []
        extraction_date = datetime.now().date().isoformat()
        
        logger.info(f"Traitement de {len(segments_data)} segments pour segments_daily")
        
        for segment in segments_data:
            if segment.get('error', False):
                logger.warning(f"Segment avec erreur ignoré: {segment.get('segment_id', 'N/A')}")
                continue
                
            segment_id = segment.get('segment_id', '')
            segment_name = segment.get('segment_name', '')
            extraction_granularity = segment.get('extraction_granularity', 'daily')
            
            segment_data = segment.get('data', {})
            if not segment_data:
                logger.warning(f"Pas de données pour segment {segment_id}")
                continue
                
            if 'segments' not in segment_data:
                logger.warning(f"Clé 'segments' manquante pour {segment_id}")
                logger.debug(f"Clés disponibles: {list(segment_data.keys())}")
                continue
            
            segment_points = segment_data['segments']
            logger.info(f"Segment {segment_name}: {len(segment_points)} points de données trouvés")
            
            points_added = 0
            for data_point in segment_points:
                if not isinstance(data_point, dict):
                    logger.warning(f"Point de données invalide (non dict): {type(data_point)}")
                    continue
                
                date_str = data_point.get('date', '')
                if not date_str:
                    logger.warning(f"Date manquante dans point: {data_point}")
                    continue
                
                # Normalisation de la date
                if len(date_str) == 10:  # YYYY-MM-DD
                    final_date = date_str
                elif len(date_str) == 7:  # YYYY-MM
                    final_date = date_str + '-01'
                else:
                    logger.warning(f"Format de date invalide: {date_str}")
                    continue
                
                row = {
                    'segment_id': segment_id,
                    'segment_name': segment_name,
                    'date': final_date,
                    'visits': float(data_point.get('visits', 0)) if data_point.get('visits') is not None else None,
                    'share': float(data_point.get('share', 0.0)) if data_point.get('share') is not None else None,
                    'bounce_rate': float(data_point.get('bounce_rate')) if data_point.get('bounce_rate') is not None else None,
                    'pages_per_visit': float(data_point.get('pages_per_visit')) if data_point.get('pages_per_visit') is not None else None,
                    'visit_duration': float(data_point.get('visit_duration')) if data_point.get('visit_duration') is not None else None,
                    'page_views': float(data_point.get('page_views')) if data_point.get('page_views') is not None else None,
                    # PAS de unique_visitors
                    'confidence': str(data_point.get('confidence')) if data_point.get('confidence') is not None else None,
                    'granularity': extraction_granularity,
                    'extraction_date': extraction_date
                }
                
                # CONDITION DE VALIDATION ASSOUPLIE
                # Au lieu de vérifier visits > 0, on accepte toute valeur non-nulle
                has_valid_data = (
                    row['visits'] is not None or 
                    row['share'] is not None or 
                    row['page_views'] is not None or
                    row['bounce_rate'] is not None
                )
                
                if has_valid_data:
                    rows.append(row)
                    points_added += 1
                else:
                    logger.warning(f"Point rejeté (pas de données valides): {final_date} - {data_point}")
            
            logger.info(f"Segment {segment_name}: {points_added} lignes ajoutées sur {len(segment_points)} points")
        
        logger.info(f"Total segments_daily: {len(rows)} lignes générées")
        return rows
    
    def process_segments_unique_visitors(self, segments_uv_data):
        """Traitement segments unique_visitors (SEULEMENT unique_visitors) - CORRIGÉ"""
        rows = []
        extraction_date = datetime.now().date().isoformat()
        
        logger.info(f"Traitement de {len(segments_uv_data)} segments pour segments_unique_visitors")
        
        for segment in segments_uv_data:
            if segment.get('error', False):
                logger.warning(f"Segment avec erreur ignoré: {segment.get('segment_id', 'N/A')}")
                continue
                
            segment_id = segment.get('segment_id', '')
            segment_name = segment.get('segment_name', '')
            extraction_granularity = segment.get('extraction_granularity', 'monthly')
            
            segment_data = segment.get('data', {})
            if not segment_data:
                logger.warning(f"Pas de données pour segment {segment_id}")
                continue
                
            if 'segments' not in segment_data:
                logger.warning(f"Clé 'segments' manquante pour {segment_id}")
                logger.debug(f"Clés disponibles: {list(segment_data.keys())}")
                continue
            
            segment_points = segment_data['segments']
            logger.info(f"Segment {segment_name}: {len(segment_points)} points unique_visitors trouvés")
            
            points_added = 0
            for data_point in segment_points:
                if not isinstance(data_point, dict):
                    logger.warning(f"Point de données invalide (non dict): {type(data_point)}")
                    continue
                
                date_str = data_point.get('date', '')
                if not date_str:
                    logger.warning(f"Date manquante dans point: {data_point}")
                    continue
                
                # Normalisation de la date
                if len(date_str) == 10:  # YYYY-MM-DD
                    final_date = date_str
                elif len(date_str) == 7:  # YYYY-MM
                    final_date = date_str + '-01'
                else:
                    logger.warning(f"Format de date invalide: {date_str}")
                    continue
                
                # SEULEMENT unique_visitors et dimensions
                unique_visitors_value = data_point.get('unique_visitors')
                if unique_visitors_value is None:
                    logger.warning(f"unique_visitors manquant pour {final_date}: {data_point}")
                    continue
                
                row = {
                    'segment_id': segment_id,
                    'segment_name': segment_name,
                    'date': final_date,
                    'unique_visitors': float(unique_visitors_value) if unique_visitors_value is not None else None,
                    'confidence': str(data_point.get('confidence')) if data_point.get('confidence') is not None else None,
                    'granularity': extraction_granularity,
                    'extraction_date': extraction_date
                }
                
                if row['unique_visitors'] is not None:
                    rows.append(row)
                    points_added += 1
                else:
                    logger.warning(f"Point rejeté (unique_visitors null): {final_date}")
            
            logger.info(f"Segment {segment_name}: {points_added} lignes unique_visitors ajoutées sur {len(segment_points)} points")
        
        logger.info(f"Total segments_unique_visitors: {len(rows)} lignes générées")
        return rows
    
    def process_websites_daily(self, websites_data):
        """Traitement websites daily (inchangé avec unique_visitors)"""
        rows = []
        extraction_date = datetime.now().date().isoformat()
        
        for website in websites_data:
            domain = website.get('domain', '')
            metrics = website.get('metrics', {})
            extraction_granularity = website.get('extraction_granularity', 'daily')
            
            if not metrics:
                continue
            
            visits_data = metrics.get('visits', {})
            if not visits_data or 'visits' not in visits_data:
                continue
            
            for visit_point in visits_data['visits']:
                date_str = visit_point.get('date', '')
                if not date_str:
                    continue
                
                # Validation de date
                if len(date_str) == 10:  # YYYY-MM-DD
                    final_date = date_str
                elif len(date_str) == 7:  # YYYY-MM
                    final_date = date_str + '-01'
                else:
                    continue
                
                row = {
                    'domain': domain,
                    'date': final_date,
                    'visits': float(visit_point.get('visits', 0)) if visit_point.get('visits') is not None else None,
                    'bounce_rate': None,
                    'pages_per_visit': None,
                    'avg_visit_duration': None,
                    'page_views': None,
                    'unique_visitors': None,  # SERA REMPLI
                    'desktop_share': None,
                    'mobile_share': None,
                    'confidence': float(visit_point.get('confidence')) if visit_point.get('confidence') is not None else None,
                    'granularity': extraction_granularity,
                    'extraction_date': extraction_date
                }
                
                # Ajouter métriques standards
                self._add_metric_corrected(row, metrics, 'bounce_rate', 'bounce_rate', final_date)
                self._add_metric_corrected(row, metrics, 'pages_per_visit', 'pages_per_visit', final_date)
                self._add_metric_corrected(row, metrics, 'avg_visit_duration', 'average_visit_duration', final_date)
                self._add_metric_corrected(row, metrics, 'page_views', 'pages_views', final_date)
                
                # Combiner unique_visitors desktop + mobile
                self._add_unique_visitors_combined(row, metrics, final_date)
                
                # Desktop/mobile split
                self._add_split_metrics_corrected(row, metrics)
                
                rows.append(row)
        
        return rows
    
    def _add_unique_visitors_combined(self, row, metrics, target_date):
        """Combine unique_visitors desktop + mobile"""
        desktop_uv = None
        mobile_uv = None
        
        # Récupérer desktop unique visitors
        desktop_data = metrics.get('unique_visitors_desktop', {})
        if desktop_data and 'unique_visitors' in desktop_data:
            for point in desktop_data['unique_visitors']:
                if point.get('date') == target_date:
                    desktop_uv = point.get('unique_visitors')
                    break
        
        # Récupérer mobile unique visitors
        mobile_data = metrics.get('unique_visitors_mobile', {})
        if mobile_data and 'unique_visitors' in mobile_data:
            for point in mobile_data['unique_visitors']:
                if point.get('date') == target_date:
                    mobile_uv = point.get('unique_visitors')
                    break
        
        # Combiner desktop + mobile
        if desktop_uv is not None and mobile_uv is not None:
            row['unique_visitors'] = float(desktop_uv) + float(mobile_uv)
        elif desktop_uv is not None:
            row['unique_visitors'] = float(desktop_uv)
        elif mobile_uv is not None:
            row['unique_visitors'] = float(mobile_uv)
    
    def _add_metric_corrected(self, row, metrics, row_field, api_field, target_date):
        """Ajoute une métrique avec mapping corrigé"""
        api_key = row_field
        
        if api_key in metrics:
            metric_data = metrics[api_key]
            if isinstance(metric_data, dict) and api_field in metric_data:
                data_points = metric_data[api_field]
                
                if isinstance(data_points, list):
                    for point in data_points:
                        if point.get('date') == target_date:
                            value = point.get(api_field)
                            if value is not None:
                                row[row_field] = float(value)
                                
                                # Confidence seulement depuis les métriques qui l'ont
                                if row.get('confidence') is None and row_field != 'unique_visitors':
                                    confidence = point.get('confidence')
                                    if confidence is not None:
                                        row['confidence'] = float(confidence)
                                break
    
    def _add_split_metrics_corrected(self, row, metrics):
        """Desktop/mobile split corrigé"""
        split_data = metrics.get('desktop_mobile_split', {})
        if isinstance(split_data, dict):
            desktop = split_data.get('desktop_visit_share')
            mobile = split_data.get('mobile_web_visit_share')
            
            if desktop is not None:
                row['desktop_share'] = float(desktop)
            if mobile is not None:
                row['mobile_share'] = float(mobile)
    
    def debug_segments_data_structure(self, segments_data):
        """Méthode de debug pour analyser la structure des données segments"""
        logger.info("=== DEBUG STRUCTURE DONNÉES SEGMENTS ===")
        
        for i, segment in enumerate(segments_data):
            logger.info(f"Segment {i+1}:")
            logger.info(f"  segment_id: {segment.get('segment_id', 'N/A')}")
            logger.info(f"  segment_name: {segment.get('segment_name', 'N/A')}")
            logger.info(f"  error: {segment.get('error', False)}")
            
            segment_data = segment.get('data', {})
            if not segment_data:
                logger.warning(f"  PROBLÈME: Pas de clé 'data'")
                continue
                
            logger.info(f"  Clés dans 'data': {list(segment_data.keys())}")
            
            if 'segments' in segment_data:
                segments_array = segment_data['segments']
                logger.info(f"  Nombre de points dans 'segments': {len(segments_array) if isinstance(segments_array, list) else 'N/A (pas une liste)'}")
                
                if isinstance(segments_array, list) and len(segments_array) > 0:
                    # Analyser le premier point
                    first_point = segments_array[0]
                    logger.info(f"  Premier point - type: {type(first_point)}")
                    if isinstance(first_point, dict):
                        logger.info(f"  Premier point - clés: {list(first_point.keys())}")
                        logger.info(f"  Premier point - date: {first_point.get('date', 'N/A')}")
                        logger.info(f"  Premier point - visits: {first_point.get('visits', 'N/A')}")
                    
                    # Analyser le dernier point
                    if len(segments_array) > 1:
                        last_point = segments_array[-1]
                        if isinstance(last_point, dict):
                            logger.info(f"  Dernier point - date: {last_point.get('date', 'N/A')}")
            else:
                logger.warning(f"  PROBLÈME: Pas de clé 'segments' dans 'data'")
        
        logger.info("=== FIN DEBUG ===")
    
    def upload_to_three_tables(self, segments_daily_data, segments_uv_data, websites_data):
        """Upload vers les 3 tables avec debug amélioré"""
        logger.info("Upload vers les 3 tables")
        
        # DEBUG: Analyser la structure des données avant traitement
        if segments_daily_data:
            logger.info("=== ANALYSE DONNÉES SEGMENTS DAILY ===")
            self.debug_segments_data_structure(segments_daily_data)
        
        upload_stats = {'segments_daily': 0, 'segments_unique_visitors': 0, 'websites_daily': 0}
        
        # 1. Upload segments_daily
        if segments_daily_data:
            logger.info("Traitement segments_daily...")
            segments_rows = self.process_segments_daily(segments_daily_data)
            if segments_rows:
                table_id = f"{self.project_id}.{self.dataset_id}.segments_daily"
                errors = self.client.insert_rows_json(table_id, segments_rows)
                
                if errors:
                    logger.error(f"Erreur upload segments_daily: {errors}")
                else:
                    upload_stats['segments_daily'] = len(segments_rows)
                    logger.info(f"segments_daily: {len(segments_rows)} lignes uploadées")
                    
                    # Statistiques détaillées
                    segments_count = len(set(row['segment_id'] for row in segments_rows))
                    dates_count = len(set(row['date'] for row in segments_rows))
                    logger.info(f"  {segments_count} segments distincts, {dates_count} dates distinctes")
            else:
                logger.error("PROBLÈME: Aucune ligne générée pour segments_daily")
        
        # 2. Upload segments_unique_visitors
        if segments_uv_data:
            logger.info("Traitement segments_unique_visitors...")
            segments_uv_rows = self.process_segments_unique_visitors(segments_uv_data)
            if segments_uv_rows:
                table_id = f"{self.project_id}.{self.dataset_id}.segments_unique_visitors"
                errors = self.client.insert_rows_json(table_id, segments_uv_rows)
                
                if errors:
                    logger.error(f"Erreur upload segments_unique_visitors: {errors}")
                else:
                    upload_stats['segments_unique_visitors'] = len(segments_uv_rows)
                    logger.info(f"segments_unique_visitors: {len(segments_uv_rows)} lignes uploadées")
                    
                    # Validation unique_visitors
                    uv_count = sum(1 for row in segments_uv_rows if row.get('unique_visitors') is not None)
                    logger.info(f"  unique_visitors rempli: {uv_count}/{len(segments_uv_rows)}")
            else:
                logger.error("PROBLÈME: Aucune ligne générée pour segments_unique_visitors")
        
        # 3. Upload websites_daily (inchangé)
        if websites_data:
            logger.info("Traitement websites_daily...")
            websites_rows = self.process_websites_daily(websites_data)
            if websites_rows:
                table_id = f"{self.project_id}.{self.dataset_id}.websites_daily"
                errors = self.client.insert_rows_json(table_id, websites_rows)
                
                if errors:
                    logger.error(f"Erreur upload websites_daily: {errors}")
                else:
                    upload_stats['websites_daily'] = len(websites_rows)
                    logger.info(f"websites_daily: {len(websites_rows)} lignes uploadées")
                    
                    # Validation métriques websites
                    uv_count = sum(1 for row in websites_rows if row.get('unique_visitors') is not None)
                    logger.info(f"  unique_visitors websites: {uv_count}/{len(websites_rows)} remplis")
            else:
                logger.error("PROBLÈME: Aucune ligne générée pour websites_daily")
        
        return upload_stats
    
    def verify_three_tables(self):
        """Vérification des 3 tables"""
        logger.info("Vérification des 3 tables")
        
        tables_to_verify = [
            'segments_daily',
            'segments_unique_visitors', 
            'websites_daily'
        ]
        
        for table_name in tables_to_verify:
            try:
                if table_name == 'segments_unique_visitors':
                    # Vérification spéciale pour unique_visitors
                    query = f"""
                    SELECT 
                        COUNT(*) as total_rows,
                        COUNT(unique_visitors) as uv_filled,
                        AVG(unique_visitors) as avg_uv,
                        granularity
                    FROM `{self.project_id}.{self.dataset_id}.{table_name}`
                    GROUP BY granularity
                    """
                else:
                    # Vérification générale
                    query = f"""
                    SELECT 
                        COUNT(*) as total_rows,
                        granularity,
                        COUNT(CASE WHEN visits > 0 THEN 1 END) as visits_filled
                    FROM `{self.project_id}.{self.dataset_id}.{table_name}`
                    GROUP BY granularity
                    """
                
                results = list(self.client.query(query))
                if results:
                    for result in results:
                        if table_name == 'segments_unique_visitors':
                            logger.info(f"{table_name}: {result['total_rows']} lignes, unique_visitors: {result['uv_filled']}, granularité: {result['granularity']}")
                        else:
                            logger.info(f"{table_name}: {result['total_rows']} lignes, visits rempli: {result['visits_filled']}, granularité: {result['granularity']}")
                        
            except Exception as e:
                logger.error(f"Erreur vérification {table_name}: {e}")


# PATCH pour similarweb_api.py : ajouter les nouvelles méthodes
def patch_similarweb_api_three_tables():
    """Ajoute les méthodes pour 3 tables à SimilarWebAPI"""
    
    def get_segment_data_daily_no_uv(self, segment_id: str, start_date: str, end_date: str, 
                                   country: str = DEFAULT_COUNTRY, 
                                   granularity: str = DEFAULT_GRANULARITY):
        """Extraction segments daily SANS unique-visitors - CORRIGÉ"""
        
        # Groupes de métriques SANS unique-visitors
        metrics_groups = [
            'visits,share',
            'bounce-rate,pages-per-visit,visit-duration',
            'page-views'  # SANS unique-visitors
        ]
        
        combined_data = None
        all_api_results = []
        
        for metrics_group in metrics_groups:
            params = {
                'start_date': start_date,
                'end_date': end_date,
                'country': country,
                'granularity': granularity,
                'metrics': metrics_group
            }
            
            endpoint = f'/segment/{segment_id}/total-traffic-and-engagement/query'
            result = self._make_request(endpoint, params)
            
            if result and 'segments' in result:
                all_api_results.append(result)
        
        # CORRECTION: Combiner correctement tous les points de données
        if all_api_results:
            # Prendre le premier résultat comme base (contient tous les points de dates)
            base_result = all_api_results[0]
            combined_segments = []
            
            # Pour chaque point de données (date)
            for i, base_segment in enumerate(base_result['segments']):
                combined_segment = base_segment.copy()
                
                # Ajouter les métriques des autres appels API pour le même point (même index)
                for other_result in all_api_results[1:]:
                    if i < len(other_result['segments']):
                        other_segment = other_result['segments'][i]
                        
                        # Vérifier que c'est la même date
                        if other_segment.get('date') == combined_segment.get('date'):
                            # Ajouter les métriques manquantes
                            for key, value in other_segment.items():
                                if key not in combined_segment and key != 'date':
                                    combined_segment[key] = value
                
                combined_segments.append(combined_segment)
            
            combined_data = {
                'meta': base_result.get('meta', {}),
                'segments': combined_segments
            }
        
        return combined_data
    
    def get_segment_unique_visitors_only(self, segment_id: str, start_date: str, end_date: str, 
                                       country: str = DEFAULT_COUNTRY, 
                                       granularity: str = 'monthly'):
        """Extraction segments monthly SEULEMENT pour unique-visitors - CORRIGÉ"""
        
        params = {
            'start_date': start_date,
            'end_date': end_date,
            'country': country,
            'granularity': granularity,
            'metrics': 'unique-visitors'  # SEULEMENT unique-visitors
        }
        
        endpoint = f'/segment/{segment_id}/total-traffic-and-engagement/query'
        result = self._make_request(endpoint, params)
        
        return result
    
    # Ajouter les méthodes à la classe
    SimilarWebAPI.get_segment_data_daily_no_uv = get_segment_data_daily_no_uv
    SimilarWebAPI.get_segment_unique_visitors_only = get_segment_unique_visitors_only


def main():
    """Test avec 3 tables distinctes"""
    print("TEST 3 TABLES DISTINCTES")
    print("=" * 60)
    print("STRUCTURE:")
    print("1. segments_daily (daily, sans unique_visitors)")
    print("2. segments_unique_visitors (monthly, seulement unique_visitors)")
    print("3. websites_daily (daily, avec unique_visitors)")
    
    # Patcher l'API
    patch_similarweb_api_three_tables()
    
    extractor = ThreeTablesTestExtractor()
    
    try:
        # 1. Créer les 3 tables
        print("\n1. Création des 3 tables...")
        extractor.create_three_tables()
        
        # 2. Extraction segments daily (sans unique_visitors)
        print("\n2. Extraction segments daily...")
        segments_daily_data = extractor.extract_segments_daily()
        
        # 3. Extraction segments unique_visitors (monthly)
        print("\n3. Extraction segments unique_visitors...")
        segments_uv_data = extractor.extract_segments_unique_visitors()
        
        # 4. Extraction websites daily (avec unique_visitors)
        print("\n4. Extraction websites daily...")
        websites_data = extractor.extract_websites_daily()
        
        # 5. Upload vers les 3 tables
        print("\n5. Upload vers les 3 tables...")
        upload_stats = extractor.upload_to_three_tables(segments_daily_data, segments_uv_data, websites_data)
        
        # 6. Vérification
        print("\n6. Vérification des 3 tables...")
        extractor.verify_three_tables()
        
        # 7. Résumé
        print(f"\nTEST 3 TABLES TERMINÉ")
        print("=" * 40)
        print(f"segments_daily: {upload_stats['segments_daily']} lignes (sans unique_visitors)")
        print(f"segments_unique_visitors: {upload_stats['segments_unique_visitors']} lignes (seulement unique_visitors)")
        print(f"websites_daily: {upload_stats['websites_daily']} lignes (avec unique_visitors)")
        print(f"ARCHITECTURE OPTIMISÉE SELON CONTRAINTES API")
        
    except Exception as e:
        logger.error(f"Erreur durant le test: {str(e)}")
        raise


if __name__ == "__main__":
    main()