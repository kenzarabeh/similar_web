#!/usr/bin/env python3
"""
Script d'upload vers BigQuery avec gestion automatique des doublons
Ne charge que les données qui n'existent pas déjà dans BigQuery
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

class BigQueryUploaderWithDeduplication:
    def __init__(self, project_id=None):
        """Initialise le client BigQuery avec gestion des doublons"""
        self.project_id = project_id or os.environ.get('GCP_PROJECT_ID', 'lec-lco-mkt-acquisition-prd')
        self.client = bigquery.Client(project=self.project_id)
        self.dataset_id = 'similar_web_data'
        
        # Cache pour les données existantes
        self._existing_segments = None
        self._existing_websites = None
        
        logger.info(f"Configuration: Projet {self.project_id}, Dataset {self.dataset_id}")
    
    def get_existing_segments_keys(self) -> Set[Tuple[str, str]]:
        """
        Récupère les clés (segment_id, date) existantes dans BigQuery pour éviter les doublons
        
        Returns:
            Set de tuples (segment_id, date)
        """
        if self._existing_segments is not None:
            return self._existing_segments
        
        logger.info("Récupération des segments existants dans BigQuery...")
        
        query = f"""
        SELECT DISTINCT 
            segment_id,
            DATE(date) as date
        FROM `{self.project_id}.{self.dataset_id}.segments_data`
        """
        
        try:
            results = self.client.query(query).result()
            existing_keys = set()
            
            for row in results:
                key = (row.segment_id, str(row.date))
                existing_keys.add(key)
            
            self._existing_segments = existing_keys
            logger.info(f"{len(existing_keys)} segments existants trouvés")
            return existing_keys
            
        except Exception as e:
            logger.warning(f"Erreur lors de la récupération des segments existants: {e}")
            return set()
    
    def get_existing_websites_keys(self) -> Set[Tuple[str, str]]:
        """
        Récupère les clés (domain, date) existantes dans BigQuery pour éviter les doublons
        
        Returns:
            Set de tuples (domain, date)
        """
        if self._existing_websites is not None:
            return self._existing_websites
        
        logger.info("Récupération des websites existants dans BigQuery...")
        
        query = f"""
        SELECT DISTINCT 
            domain,
            DATE(date) as date
        FROM `{self.project_id}.{self.dataset_id}.websites_data`
        """
        
        try:
            results = self.client.query(query).result()
            existing_keys = set()
            
            for row in results:
                key = (row.domain, str(row.date))
                existing_keys.add(key)
            
            self._existing_websites = existing_keys
            logger.info(f"{len(existing_keys)} websites existants trouvés")
            return existing_keys
            
        except Exception as e:
            logger.warning(f"Erreur lors de la récupération des websites existants: {e}")
            return set()
    
    def upload_segments(self, file_pattern='data/segments_extraction_*.json'):
        """Upload les fichiers de segments vers BigQuery en évitant les doublons"""
        files = glob.glob(file_pattern)
        logger.info(f"{len(files)} fichiers segments trouvés")
        
        if not files:
            logger.warning("Aucun fichier segments trouvé")
            return 0
        
        # Récupérer les données existantes
        existing_keys = self.get_existing_segments_keys()
        
        total_rows_processed = 0
        total_rows_uploaded = 0
        total_rows_skipped = 0
        
        table_id = f"{self.project_id}.{self.dataset_id}.segments_data"
        
        for file_path in sorted(files):
            try:
                logger.info(f"Traitement: {os.path.basename(file_path)}")
                rows = self._process_segments_file(file_path)
                
                if not rows:
                    logger.warning(f"{file_path}: Aucune donnée trouvée")
                    continue
                
                # Filtrer les doublons
                new_rows = []
                skipped_count = 0
                
                for row in rows:
                    key = (row['segment_id'], row['date'])
                    if key not in existing_keys:
                        new_rows.append(row)
                        # Ajouter au cache pour éviter les doublons dans le même batch
                        existing_keys.add(key)
                    else:
                        skipped_count += 1
                
                total_rows_processed += len(rows)
                total_rows_skipped += skipped_count
                
                if new_rows:
                    # Upload vers BigQuery
                    errors = self.client.insert_rows_json(table_id, new_rows)
                    if errors:
                        logger.error(f"Erreur pour {file_path}: {errors}")
                    else:
                        total_rows_uploaded += len(new_rows)
                        logger.info(f"{os.path.basename(file_path)}: {len(new_rows)} nouvelles lignes uploadées ({skipped_count} doublons ignorés)")
                else:
                    logger.info(f" {os.path.basename(file_path)}: Toutes les données existent déjà ({skipped_count} doublons)")
                    
            except Exception as e:
                logger.error(f"Erreur {file_path}: {str(e)}")
        
        logger.info(f"RÉSUMÉ SEGMENTS:")
        logger.info(f"   - Lignes traitées: {total_rows_processed}")
        logger.info(f"   - Nouvelles lignes uploadées: {total_rows_uploaded}")
        logger.info(f"   - Doublons ignorés: {total_rows_skipped}")
        
        return total_rows_uploaded
    
    def upload_websites(self, file_pattern='data/websites_extraction_*.json'):
        """Upload les fichiers de websites vers BigQuery en évitant les doublons"""
        files = glob.glob(file_pattern)
        logger.info(f"{len(files)} fichiers websites trouvés")
        
        if not files:
            logger.warning("Aucun fichier websites trouvé")
            return 0
        
        # Récupérer les données existantes
        existing_keys = self.get_existing_websites_keys()
        
        total_rows_processed = 0
        total_rows_uploaded = 0
        total_rows_skipped = 0
        
        table_id = f"{self.project_id}.{self.dataset_id}.websites_data"
        
        for file_path in sorted(files):
            try:
                logger.info(f"Traitement: {os.path.basename(file_path)}")
                rows = self._process_websites_file(file_path)
                
                if not rows:
                    logger.warning(f"{file_path}: Aucune donnée trouvée")
                    continue
                
                # Filtrer les doublons
                new_rows = []
                skipped_count = 0
                
                for row in rows:
                    key = (row['domain'], row['date'])
                    if key not in existing_keys:
                        new_rows.append(row)
                        # Ajouter au cache pour éviter les doublons dans le même batch
                        existing_keys.add(key)
                    else:
                        skipped_count += 1
                
                total_rows_processed += len(rows)
                total_rows_skipped += skipped_count
                
                if new_rows:
                    # Upload vers BigQuery
                    errors = self.client.insert_rows_json(table_id, new_rows)
                    if errors:
                        logger.error(f"Erreur pour {file_path}: {errors}")
                    else:
                        total_rows_uploaded += len(new_rows)
                        logger.info(f"{os.path.basename(file_path)}: {len(new_rows)} nouvelles lignes uploadées ({skipped_count} doublons ignorés)")
                else:
                    logger.info(f"{os.path.basename(file_path)}: Toutes les données existent déjà ({skipped_count} doublons)")
                    
            except Exception as e:
                logger.error(f"Erreur {file_path}: {str(e)}")
        
        logger.info(f"RÉSUMÉ WEBSITES:")
        logger.info(f"   - Lignes traitées: {total_rows_processed}")
        logger.info(f"   - Nouvelles lignes uploadées: {total_rows_uploaded}")
        logger.info(f"   - Doublons ignorés: {total_rows_skipped}")
        
        return total_rows_uploaded
    
    def _process_segments_file(self, file_path):
        """Traite un fichier de segments - Format SimilarWeb"""
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        if not isinstance(data, list):
            logger.warning(f"Format inattendu dans {file_path}: attendu une liste")
            return []
        
        rows = []
        extraction_date = datetime.now().date().isoformat()
        
        for segment in data:
            # Ignorer les segments avec erreur
            if segment.get('error', False):
                continue
                
            segment_id = segment.get('segment_id', '')
            segment_name = segment.get('segment_name', '')
            
            # Vérifier la structure des données
            segment_data = segment.get('data', {})
            if not segment_data or 'segments' not in segment_data:
                continue
            
            # Traiter chaque point de données
            for data_point in segment_data['segments']:
                if not isinstance(data_point, dict):
                    continue
                
                # Normaliser le format de date (enlever le jour si présent)
                date_str = data_point.get('date', '')
                if len(date_str) > 7:  # Format YYYY-MM-DD -> YYYY-MM-01
                    date_str = date_str[:7] + '-01'
                elif len(date_str) == 7:  # Format YYYY-MM -> YYYY-MM-01
                    date_str = date_str + '-01'
                    
                row = {
                    'segment_id': segment_id,
                    'segment_name': segment_name,
                    'date': date_str,
                    'visits': float(data_point.get('visits', 0)) if data_point.get('visits') is not None else None,
                    'share': float(data_point.get('share', 0.0)) if data_point.get('share') is not None else None,
                    'bounce_rate': float(data_point.get('bounce_rate')) if data_point.get('bounce_rate') is not None else None,
                    'pages_per_visit': float(data_point.get('pages_per_visit')) if data_point.get('pages_per_visit') is not None else None,
                    'visit_duration': float(data_point.get('visit_duration')) if data_point.get('visit_duration') is not None else None,
                    'page_views': float(data_point.get('page_views')) if data_point.get('page_views') is not None else None,
                    'unique_visitors': float(data_point.get('unique_visitors')) if data_point.get('unique_visitors') is not None else None,
                    'extraction_date': extraction_date
                }
                
                # Ne garder que les lignes avec au moins visits ou share
                if (row['visits'] is not None and row['visits'] > 0) or (row['share'] is not None and row['share'] > 0):
                    rows.append(row)
        
        return rows
    
    def _process_websites_file(self, file_path):
        """Traite un fichier de websites - Format SimilarWeb"""
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        if not isinstance(data, list):
            logger.warning(f"Format inattendu dans {file_path}: attendu une liste")
            return []
        
        rows = []
        extraction_date = datetime.now().date().isoformat()
        
        for website in data:
            domain = website.get('domain', '')
            metrics = website.get('metrics', {})
            
            if not metrics:
                continue
            
            # Extraire les visites comme référence de dates
            visits_data = metrics.get('visits', {})
            if not visits_data or 'visits' not in visits_data:
                continue
            
            # Pour chaque point de date dans les visites
            for visit_point in visits_data['visits']:
                date_str = visit_point.get('date', '')
                if not date_str:
                    continue
                
                # Normaliser le format de date
                if len(date_str) > 7:  # Format YYYY-MM-DD -> YYYY-MM-01
                    date_str = date_str[:7] + '-01'
                elif len(date_str) == 7:  # Format YYYY-MM -> YYYY-MM-01
                    date_str = date_str + '-01'
                
                row = {
                    'domain': domain,
                    'date': date_str,
                    'visits': float(visit_point.get('visits', 0)) if visit_point.get('visits') is not None else None,
                    'bounce_rate': None,
                    'pages_per_visit': None,
                    'avg_visit_duration': None,
                    'page_views': None,
                    'unique_visitors': None,
                    'desktop_share': None,
                    'mobile_share': None,
                    'extraction_date': extraction_date
                }
                
                # Ajouter les autres métriques si disponibles
                self._add_metric_to_row(row, metrics, 'bounce_rate', 'bounce_rate', date_str)
                self._add_metric_to_row(row, metrics, 'pages_per_visit', 'pages_per_visit', date_str)
                self._add_metric_to_row(row, metrics, 'avg_visit_duration', 'average_visit_duration', date_str)
                self._add_metric_to_row(row, metrics, 'page_views', 'page_views', date_str)
                
                # Desktop/Mobile split
                self._add_split_metrics(row, metrics, date_str)
                
                rows.append(row)
        
        return rows
    
    def _add_metric_to_row(self, row, metrics, metric_name, field_name, target_date):
        """Ajoute une métrique à la ligne si elle existe pour la date"""
        metric_data = metrics.get(metric_name, {})
        if metric_data and metric_name in metric_data:
            for point in metric_data[metric_name]:
                point_date = point.get('date', '')
                # Normaliser la date pour comparaison
                if len(point_date) > 7:
                    point_date = point_date[:7] + '-01'
                elif len(point_date) == 7:
                    point_date = point_date + '-01'
                
                if point_date == target_date:
                    value = point.get(field_name)
                    if value is not None:
                        row[metric_name] = float(value)
                    break
    
    def _add_split_metrics(self, row, metrics, target_date):
        """Ajoute les métriques desktop/mobile split"""
        split_data = metrics.get('desktop_mobile_split', {})
        if split_data and 'data' in split_data:
            for split_point in split_data['data']:
                point_date = split_point.get('date', '')
                # Normaliser la date
                if len(point_date) > 7:
                    point_date = point_date[:7] + '-01'
                elif len(point_date) == 7:
                    point_date = point_date + '-01'
                
                if point_date == target_date:
                    for device_data in split_point.get('data', []):
                        device = device_data.get('device', '')
                        value = device_data.get('value', 0)
                        if device == 'desktop':
                            row['desktop_share'] = float(value) if value is not None else None
                        elif device == 'mobile':
                            row['mobile_share'] = float(value) if value is not None else None
                    break
    
    def verify_data(self):
        """Vérifie les données dans BigQuery"""
        logger.info("\nVÉRIFICATION BIGQUERY")
        
        try:
            # Vérifier segments
            query = f"""
            SELECT 
                COUNT(*) as total,
                COUNT(DISTINCT date) as nb_dates,
                MIN(date) as min_date,
                MAX(date) as max_date,
                COUNT(DISTINCT segment_id) as nb_segments
            FROM `{self.project_id}.{self.dataset_id}.segments_data`
            """
            result = list(self.client.query(query))[0]
            logger.info(f"Segments: {result['total']} lignes, {result['nb_segments']} segments, {result['nb_dates']} dates ({result['min_date']} → {result['max_date']})")
        except Exception as e:
            logger.error(f"Erreur vérification segments: {e}")
        
        try:
            # Vérifier websites
            query = f"""
            SELECT 
                COUNT(*) as total,
                COUNT(DISTINCT date) as nb_dates,
                MIN(date) as min_date,
                MAX(date) as max_date,
                COUNT(DISTINCT domain) as nb_domains
            FROM `{self.project_id}.{self.dataset_id}.websites_data`
            """
            result = list(self.client.query(query))[0]
            logger.info(f"Websites: {result['total']} lignes, {result['nb_domains']} domaines, {result['nb_dates']} dates ({result['min_date']} → {result['max_date']})")
        except Exception as e:
            logger.error(f"Erreur vérification websites: {e}")
    
    def clear_cache(self):
        """Vide le cache des données existantes (à utiliser si les données ont changé)"""
        self._existing_segments = None
        self._existing_websites = None
        logger.info("Cache des données existantes vidé")


def main():
    """Fonction principale avec gestion des doublons"""
    parser = argparse.ArgumentParser(description='Upload vers BigQuery avec gestion automatique des doublons')
    parser.add_argument('--type', choices=['all', 'segments', 'websites'], 
                       default='all', help='Type de données à uploader')
    parser.add_argument('--verify-only', action='store_true', 
                       help='Vérifier seulement les données dans BigQuery')
    parser.add_argument('--clear-cache', action='store_true',
                       help='Vider le cache des données existantes avant upload')
    
    args = parser.parse_args()
    
    uploader = BigQueryUploaderWithDeduplication()
    
    if args.verify_only:
        uploader.verify_data()
        return
    
    if args.clear_cache:
        uploader.clear_cache()
    
    logger.info("UPLOAD VERS BIGQUERY (AVEC GESTION DES DOUBLONS)")
    logger.info("=" * 60)
    
    total_uploaded = 0
    
    if args.type in ['all', 'segments']:
        uploaded = uploader.upload_segments()
        total_uploaded += uploaded
    
    if args.type in ['all', 'websites']:
        uploaded = uploader.upload_websites()
        total_uploaded += uploaded
    
    # Vérification finale
    uploader.verify_data()
    
    logger.info(f"\nUPLOAD TERMINÉ - {total_uploaded} nouvelles lignes ajoutées")


if __name__ == "__main__":
    main()