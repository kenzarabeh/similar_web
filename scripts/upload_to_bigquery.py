#!/usr/bin/env python3
"""
Script d'upload BigQuery pour architecture 3 tables SimilarWeb - UNIFIED
- segments_daily : données daily ET weekly sans unique_visitors (colonne granularity)
- segments_unique_visitors : données monthly avec seulement unique_visitors
- websites_daily : données daily ET weekly avec unique_visitors (colonne granularity)
"""
import os
import json
import glob
import argparse
from datetime import datetime
from google.cloud import bigquery
import logging
from typing import Set, Tuple, List, Dict

# Configuration du logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class BigQueryThreeTablesUploader:
    def __init__(self, project_id=None):
        """Initialise le client BigQuery pour architecture 3 tables UNIFIED"""
        self.project_id = project_id or os.environ.get('GCP_PROJECT_ID', 'lec-lco-mkt-acquisition-prd')
        self.client = bigquery.Client(project=self.project_id)
        self.dataset_id = 'similar_web_data'
        
        # Cache pour les données existantes des 3 tables
        self._existing_segments_daily = None
        self._existing_segments_uv = None
        self._existing_websites_daily = None
        
        # Mapping API CORRIGÉ
        self.api_field_mapping = {
            'avg_visit_duration': ('average_visit_duration', 'average_visit_duration'),
            'page_views': ('pages_views', 'pages_views'),
            'bounce_rate': ('bounce_rate', 'bounce_rate'),
            'pages_per_visit': ('pages_per_visit', 'pages_per_visit'),
        }
        
        # Mapping pour desktop/mobile split
        self.split_field_mapping = {
            'desktop_share': 'desktop_visit_share',
            'mobile_share': 'mobile_web_visit_share'
        }
        
        logger.info(f"Configuration: Projet {self.project_id}, Dataset {self.dataset_id}")
        logger.info("Architecture: 3 tables UNIFIED (segments_daily, segments_unique_visitors, websites_daily)")

    def create_three_tables_if_needed(self):
        """Crée les 3 tables avec schémas adaptés si elles n'existent pas"""
        logger.info("Vérification/création des 3 tables BigQuery UNIFIED")
        
        # 1. Schéma segments_daily (SANS unique_visitors, granularity = daily/weekly)
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
            bigquery.SchemaField("extraction_date", "DATE"),
            bigquery.SchemaField("confidence", "STRING"),
            bigquery.SchemaField("granularity", "STRING"),  # daily ou weekly
        ]
        
        # 2. Schéma segments_unique_visitors (SEULEMENT unique_visitors, granularity = monthly)
        segments_uv_schema = [
            bigquery.SchemaField("segment_id", "STRING"),
            bigquery.SchemaField("segment_name", "STRING"),
            bigquery.SchemaField("date", "DATE"),
            bigquery.SchemaField("unique_visitors", "FLOAT"),
            bigquery.SchemaField("extraction_date", "DATE"),
            bigquery.SchemaField("confidence", "STRING"),
            bigquery.SchemaField("granularity", "STRING"),  # monthly
        ]
        
        # 3. Schéma websites_daily (AVEC unique_visitors, granularity = daily/weekly)
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
            bigquery.SchemaField("granularity", "STRING"),  # daily ou weekly
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
                self.client.get_table(table_id)
                logger.info(f"Table {table_name} existe déjà")
                
            except Exception:
                table = bigquery.Table(table_id, schema=schema)
                table = self.client.create_table(table)
                logger.info(f"Table {table_name} créée avec {len(schema)} colonnes")

    def get_existing_segments_daily_keys(self) -> Set[Tuple[str, str, str]]:
        """Récupère les clés (segment_id, date, granularity) existantes pour segments_daily"""
        if self._existing_segments_daily is not None:
            return self._existing_segments_daily
        
        logger.info("Récupération des segments_daily existants...")
        
        query = f"""
        SELECT DISTINCT segment_id, date, granularity
        FROM `{self.project_id}.{self.dataset_id}.segments_daily`
        """
        
        try:
            results = self.client.query(query).result()
            existing_keys = set((row.segment_id, str(row.date), row.granularity) for row in results)
            self._existing_segments_daily = existing_keys
            logger.info(f"{len(existing_keys)} segments_daily existants trouvés")
            return existing_keys
        except Exception as e:
            logger.warning(f"Erreur récupération segments_daily: {e}")
            return set()

    def get_existing_segments_uv_keys(self) -> Set[Tuple[str, str]]:
        """Récupère les clés (segment_id, date) existantes pour segments_unique_visitors"""
        if self._existing_segments_uv is not None:
            return self._existing_segments_uv
        
        logger.info("Récupération des segments_unique_visitors existants...")
        
        query = f"""
        SELECT DISTINCT segment_id, date
        FROM `{self.project_id}.{self.dataset_id}.segments_unique_visitors`
        """
        
        try:
            results = self.client.query(query).result()
            existing_keys = set((row.segment_id, str(row.date)) for row in results)
            self._existing_segments_uv = existing_keys
            logger.info(f"{len(existing_keys)} segments_unique_visitors existants trouvés")
            return existing_keys
        except Exception as e:
            logger.warning(f"Erreur récupération segments_unique_visitors: {e}")
            return set()

    def get_existing_websites_daily_keys(self) -> Set[Tuple[str, str, str]]:
        """Récupère les clés (domain, date, granularity) existantes pour websites_daily"""
        if self._existing_websites_daily is not None:
            return self._existing_websites_daily
        
        logger.info("Récupération des websites_daily existants...")
        
        query = f"""
        SELECT DISTINCT domain, date, granularity
        FROM `{self.project_id}.{self.dataset_id}.websites_daily`
        """
        
        try:
            results = self.client.query(query).result()
            existing_keys = set((row.domain, str(row.date), row.granularity) for row in results)
            self._existing_websites_daily = existing_keys
            logger.info(f"{len(existing_keys)} websites_daily existants trouvés")
            return existing_keys
        except Exception as e:
            logger.warning(f"Erreur récupération websites_daily: {e}")
            return set()

    def _process_segments_daily_file(self, file_path):
        """Traite un fichier segments_daily - SANS unique_visitors (daily ou weekly)"""
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        if not isinstance(data, list):
            logger.warning(f"Format inattendu dans {file_path}")
            return []
        
        rows = []
        extraction_date = datetime.now().date().isoformat()
        
        for segment in data:
            if segment.get('error', False):
                continue
                
            segment_id = segment.get('segment_id', '')
            segment_name = segment.get('segment_name', '')
            extraction_granularity = segment.get('extraction_granularity', 'daily')
            
            segment_data = segment.get('data', {})
            if not segment_data or 'segments' not in segment_data:
                continue
            
            for data_point in segment_data['segments']:
                if not isinstance(data_point, dict):
                    continue
                
                date_str = data_point.get('date', '')
                if not date_str:
                    continue
                
                # Normalisation de la date
                if len(date_str) == 10:  # YYYY-MM-DD
                    final_date = date_str
                elif len(date_str) == 7:  # YYYY-MM
                    final_date = date_str + '-01'
                else:
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
                    'confidence': str(data_point.get('confidence')) if data_point.get('confidence') is not None else None,
                    'granularity': extraction_granularity,  # daily ou weekly
                    'extraction_date': extraction_date
                }
                
                has_valid_data = (
                    row['visits'] is not None or 
                    row['share'] is not None or 
                    row['page_views'] is not None or
                    row['bounce_rate'] is not None
                )
                
                if has_valid_data:
                    rows.append(row)
        
        return rows

    def _process_segments_uv_file(self, file_path):
        """Traite un fichier segments_unique_visitors - SEULEMENT unique_visitors"""
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        if not isinstance(data, list):
            logger.warning(f"Format inattendu dans {file_path}")
            return []
        
        rows = []
        extraction_date = datetime.now().date().isoformat()
        
        for segment in data:
            if segment.get('error', False):
                continue
                
            segment_id = segment.get('segment_id', '')
            segment_name = segment.get('segment_name', '')
            extraction_granularity = segment.get('extraction_granularity', 'monthly')
            
            segment_data = segment.get('data', {})
            if not segment_data or 'segments' not in segment_data:
                continue
            
            for data_point in segment_data['segments']:
                if not isinstance(data_point, dict):
                    continue
                
                date_str = data_point.get('date', '')
                if not date_str:
                    continue
                
                if len(date_str) == 10:
                    final_date = date_str
                elif len(date_str) == 7:
                    final_date = date_str + '-01'
                else:
                    continue
                
                unique_visitors_value = data_point.get('unique_visitors')
                if unique_visitors_value is None:
                    continue
                
                row = {
                    'segment_id': segment_id,
                    'segment_name': segment_name,
                    'date': final_date,
                    'unique_visitors': float(unique_visitors_value) if unique_visitors_value is not None else None,
                    'confidence': str(data_point.get('confidence')) if data_point.get('confidence') is not None else None,
                    'granularity': extraction_granularity,  # monthly
                    'extraction_date': extraction_date
                }
                
                if row['unique_visitors'] is not None:
                    rows.append(row)
        
        return rows

    def _process_websites_daily_file(self, file_path):
        """Traite un fichier websites_daily - AVEC unique_visitors (daily ou weekly)"""
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        if not isinstance(data, list):
            logger.warning(f"Format inattendu dans {file_path}")
            return []
        
        rows = []
        extraction_date = datetime.now().date().isoformat()
        
        for website in data:
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
                
                if len(date_str) == 10:
                    final_date = date_str
                elif len(date_str) == 7:
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
                    'unique_visitors': None,
                    'desktop_share': None,
                    'mobile_share': None,
                    'confidence': float(visit_point.get('confidence')) if visit_point.get('confidence') is not None else None,
                    'granularity': extraction_granularity,  # daily ou weekly
                    'extraction_date': extraction_date
                }
                
                self._add_metric_corrected(row, metrics, 'bounce_rate', 'bounce_rate', final_date)
                self._add_metric_corrected(row, metrics, 'pages_per_visit', 'pages_per_visit', final_date)
                self._add_metric_corrected(row, metrics, 'avg_visit_duration', 'average_visit_duration', final_date)
                self._add_metric_corrected(row, metrics, 'page_views', 'pages_views', final_date)
                self._add_unique_visitors_combined(row, metrics, final_date)
                self._add_split_metrics_corrected(row, metrics)
                
                rows.append(row)
        
        return rows

    def _add_unique_visitors_combined(self, row, metrics, target_date):
        """Combine unique_visitors desktop + mobile"""
        desktop_uv = None
        mobile_uv = None
        
        desktop_data = metrics.get('unique_visitors_desktop', {})
        if desktop_data and isinstance(desktop_data, dict) and 'unique_visitors' in desktop_data:
            desktop_points = desktop_data['unique_visitors']
            if isinstance(desktop_points, list):
                for point in desktop_points:
                    if point.get('date', '') == target_date:
                        desktop_uv = point.get('unique_visitors')
                        break
        
        mobile_data = metrics.get('unique_visitors_mobile', {})
        if mobile_data and isinstance(mobile_data, dict) and 'unique_visitors' in mobile_data:
            mobile_points = mobile_data['unique_visitors']
            if isinstance(mobile_points, list):
                for point in mobile_points:
                    if point.get('date', '') == target_date:
                        mobile_uv = point.get('unique_visitors')
                        break
        
        if desktop_uv is not None and mobile_uv is not None:
            row['unique_visitors'] = float(desktop_uv) + float(mobile_uv)
        elif desktop_uv is not None:
            row['unique_visitors'] = float(desktop_uv)
        elif mobile_uv is not None:
            row['unique_visitors'] = float(mobile_uv)

    def _add_metric_corrected(self, row, metrics, row_field, api_field, target_date):
        """Ajoute une métrique avec mapping corrigé"""
        if row_field in metrics:
            metric_data = metrics[row_field]
            if isinstance(metric_data, dict) and api_field in metric_data:
                data_points = metric_data[api_field]
                
                if isinstance(data_points, list):
                    for point in data_points:
                        if point.get('date') == target_date:
                            value = point.get(api_field)
                            if value is not None:
                                row[row_field] = float(value)
                                
                                if row.get('confidence') is None:
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

    def upload_segments_daily(self, file_pattern='data/segments_*_*.json'):
        """Upload segments_daily vers BigQuery (accepte daily ET weekly)"""
        # Chercher tous les fichiers segments (daily et weekly)
        daily_files = glob.glob('data/segments_daily_*.json')
        weekly_files = glob.glob('data/segments_weekly_*.json')
        files = daily_files + weekly_files
        
        logger.info(f"{len(files)} fichiers segments trouvés ({len(daily_files)} daily, {len(weekly_files)} weekly)")
        
        if not files:
            logger.warning("Aucun fichier segments trouvé")
            return 0
        
        existing_keys = self.get_existing_segments_daily_keys()
        total_rows_uploaded = 0
        table_id = f"{self.project_id}.{self.dataset_id}.segments_daily"
        
        for file_path in sorted(files):
            try:
                logger.info(f"Traitement: {os.path.basename(file_path)}")
                rows = self._process_segments_daily_file(file_path)
                
                if not rows:
                    continue
                
                # Filtrer les doublons (segment_id, date, granularity)
                new_rows = []
                for row in rows:
                    key = (row['segment_id'], row['date'], row['granularity'])
                    if key not in existing_keys:
                        new_rows.append(row)
                        existing_keys.add(key)
                
                if new_rows:
                    errors = self.client.insert_rows_json(table_id, new_rows)
                    if errors:
                        logger.error(f"Erreur pour {file_path}: {errors}")
                    else:
                        total_rows_uploaded += len(new_rows)
                        logger.info(f"{os.path.basename(file_path)}: {len(new_rows)} lignes uploadées")
                        
            except Exception as e:
                logger.error(f"Erreur {file_path}: {str(e)}")
        
        logger.info(f"SEGMENTS_DAILY: {total_rows_uploaded} nouvelles lignes uploadées")
        return total_rows_uploaded

    def upload_segments_unique_visitors(self, file_pattern='data/segments_unique_visitors_*.json'):
        """Upload segments_unique_visitors vers BigQuery"""
        files = glob.glob(file_pattern)
        logger.info(f"{len(files)} fichiers segments_unique_visitors trouvés")
        
        if not files:
            logger.warning("Aucun fichier segments_unique_visitors trouvé")
            return 0
        
        existing_keys = self.get_existing_segments_uv_keys()
        total_rows_uploaded = 0
        table_id = f"{self.project_id}.{self.dataset_id}.segments_unique_visitors"
        
        for file_path in sorted(files):
            try:
                logger.info(f"Traitement: {os.path.basename(file_path)}")
                rows = self._process_segments_uv_file(file_path)
                
                if not rows:
                    continue
                
                # Filtrer les doublons (segment_id, date)
                new_rows = []
                for row in rows:
                    key = (row['segment_id'], row['date'])
                    if key not in existing_keys:
                        new_rows.append(row)
                        existing_keys.add(key)
                
                if new_rows:
                    errors = self.client.insert_rows_json(table_id, new_rows)
                    if errors:
                        logger.error(f"Erreur pour {file_path}: {errors}")
                    else:
                        total_rows_uploaded += len(new_rows)
                        logger.info(f"{os.path.basename(file_path)}: {len(new_rows)} lignes uploadées")
                        
            except Exception as e:
                logger.error(f"Erreur {file_path}: {str(e)}")
        
        logger.info(f"SEGMENTS_UNIQUE_VISITORS: {total_rows_uploaded} nouvelles lignes uploadées")
        return total_rows_uploaded

    def upload_websites_daily(self, file_pattern='data/websites_*_*.json'):
        """Upload websites_daily vers BigQuery (accepte daily ET weekly)"""
        # Chercher tous les fichiers websites (daily et weekly)
        daily_files = glob.glob('data/websites_daily_*.json')
        weekly_files = glob.glob('data/websites_weekly_*.json')
        files = daily_files + weekly_files
        
        logger.info(f"{len(files)} fichiers websites trouvés ({len(daily_files)} daily, {len(weekly_files)} weekly)")
        
        if not files:
            logger.warning("Aucun fichier websites trouvé")
            return 0
        
        existing_keys = self.get_existing_websites_daily_keys()
        total_rows_uploaded = 0
        table_id = f"{self.project_id}.{self.dataset_id}.websites_daily"
        
        for file_path in sorted(files):
            try:
                logger.info(f"Traitement: {os.path.basename(file_path)}")
                rows = self._process_websites_daily_file(file_path)
                
                if not rows:
                    continue
                
                # Filtrer les doublons (domain, date, granularity)
                new_rows = []
                for row in rows:
                    key = (row['domain'], row['date'], row['granularity'])
                    if key not in existing_keys:
                        new_rows.append(row)
                        existing_keys.add(key)
                
                if new_rows:
                    errors = self.client.insert_rows_json(table_id, new_rows)
                    if errors:
                        logger.error(f"Erreur pour {file_path}: {errors}")
                    else:
                        total_rows_uploaded += len(new_rows)
                        logger.info(f"{os.path.basename(file_path)}: {len(new_rows)} lignes uploadées")
                        
            except Exception as e:
                logger.error(f"Erreur {file_path}: {str(e)}")
        
        logger.info(f"WEBSITES_DAILY: {total_rows_uploaded} nouvelles lignes uploadées")
        return total_rows_uploaded

    def verify_three_tables(self):
        """Vérifie les 3 tables BigQuery"""
        logger.info("VÉRIFICATION DES 3 TABLES BIGQUERY (UNIFIED)")
        
        tables_to_verify = [
            ('segments_daily', 'segment_id'),
            ('segments_unique_visitors', 'segment_id'), 
            ('websites_daily', 'domain')
        ]
        
        for table_name, id_field in tables_to_verify:
            try:
                if table_name == 'segments_unique_visitors':
                    query = f"""
                    SELECT 
                        COUNT(*) as total_rows,
                        COUNT(unique_visitors) as uv_filled,
                        AVG(unique_visitors) as avg_uv,
                        granularity,
                        COUNT(DISTINCT {id_field}) as distinct_ids
                    FROM `{self.project_id}.{self.dataset_id}.{table_name}`
                    GROUP BY granularity
                    """
                elif table_name == 'segments_daily':
                    query = f"""
                    SELECT 
                        COUNT(*) as total_rows,
                        granularity,
                        COUNT(CASE WHEN visits > 0 THEN 1 END) as visits_filled,
                        COUNT(DISTINCT {id_field}) as distinct_ids
                    FROM `{self.project_id}.{self.dataset_id}.{table_name}`
                    GROUP BY granularity
                    """
                else:  # websites_daily
                    query = f"""
                    SELECT 
                        COUNT(*) as total_rows,
                        granularity,
                        COUNT(CASE WHEN visits > 0 THEN 1 END) as visits_filled,
                        COUNT(unique_visitors) as uv_filled,
                        COUNT(DISTINCT {id_field}) as distinct_ids
                    FROM `{self.project_id}.{self.dataset_id}.{table_name}`
                    GROUP BY granularity
                    """
                
                results = list(self.client.query(query))
                if results:
                    for result in results:
                        if table_name == 'segments_unique_visitors':
                            logger.info(f"{table_name}: {result['total_rows']} lignes, UV: {result['uv_filled']}, {result['distinct_ids']} IDs, granularité: {result['granularity']}")
                        elif table_name == 'segments_daily':
                            logger.info(f"{table_name}: {result['total_rows']} lignes, visits: {result['visits_filled']}, {result['distinct_ids']} IDs, granularité: {result['granularity']}")
                        else:
                            logger.info(f"{table_name}: {result['total_rows']} lignes, visits: {result['visits_filled']}, UV: {result['uv_filled']}, {result['distinct_ids']} IDs, granularité: {result['granularity']}")
                else:
                    logger.info(f"{table_name}: aucune donnée trouvée")
                        
            except Exception as e:
                logger.error(f"Erreur vérification {table_name}: {e}")

    def clear_cache(self):
        """Vide le cache des 3 tables"""
        self._existing_segments_daily = None
        self._existing_segments_uv = None
        self._existing_websites_daily = None
        logger.info("Cache vidé")


def main():
    """Fonction principale pour upload architecture 3 tables UNIFIED"""
    parser = argparse.ArgumentParser(description='Upload BigQuery - Architecture 3 tables UNIFIED (noms existants)')
    parser.add_argument('--type', choices=['all', 'segments_daily', 'segments_uv', 'websites_daily'], 
                       default='all', help='Type de données à uploader')
    parser.add_argument('--verify-only', action='store_true', 
                       help='Vérifier seulement les données')
    parser.add_argument('--clear-cache', action='store_true',
                       help='Vider le cache avant upload')
    parser.add_argument('--create-tables', action='store_true',
                       help='Créer les tables si nécessaire')
    
    args = parser.parse_args()
    
    uploader = BigQueryThreeTablesUploader()
    
    if args.create_tables:
        uploader.create_three_tables_if_needed()
    
    if args.verify_only:
        uploader.verify_three_tables()
        return
    
    if args.clear_cache:
        uploader.clear_cache()
    
    logger.info("UPLOAD BIGQUERY - ARCHITECTURE 3 TABLES UNIFIED (noms existants)")
    logger.info("=" * 70)
    
    total_uploaded = 0
    
    if args.type in ['all', 'segments_daily']:
        uploaded = uploader.upload_segments_daily()
        total_uploaded += uploaded
    
    if args.type in ['all', 'segments_uv']:
        uploaded = uploader.upload_segments_unique_visitors()
        total_uploaded += uploaded
    
    if args.type in ['all', 'websites_daily']:
        uploaded = uploader.upload_websites_daily()
        total_uploaded += uploaded
    
    # Vérification finale
    uploader.verify_three_tables()
    
    logger.info(f"\nUPLOAD TERMINÉ - {total_uploaded} nouvelles lignes ajoutées (3 tables unified)")


if __name__ == "__main__":
    main()