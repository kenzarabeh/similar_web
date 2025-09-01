#!/usr/bin/env python3
"""
Script d'upload corrigé pour BigQuery - Compatible avec le format SimilarWeb
"""
import os
import json
import glob
import argparse
from datetime import datetime
from google.cloud import bigquery
import logging

# Configuration du logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class BigQueryUploaderFixed:
    def __init__(self, project_id=None):
        """Initialise le client BigQuery"""
        # Utiliser la variable d'environnement ou le projet par défaut
        self.project_id = project_id or os.environ.get('GCP_PROJECT_ID', 'lec-lco-mkt-acquisition-prd')
        self.client = bigquery.Client(project=self.project_id)
        self.dataset_id = 'similar_web_data'
        logger.info(f"📊 Configuration: Projet {self.project_id}, Dataset {self.dataset_id}")
        
    def upload_segments(self, file_pattern='data/segments_extraction_*.json'):
        """Upload les fichiers de segments vers BigQuery"""
        files = glob.glob(file_pattern)
        logger.info(f"📊 {len(files)} fichiers segments trouvés")
        
        if not files:
            logger.warning("⚠️ Aucun fichier segments trouvé")
            return 0
        
        total_rows = 0
        table_id = f"{self.project_id}.{self.dataset_id}.segments_data"
        
        for file_path in sorted(files):
            try:
                logger.info(f"📁 Traitement: {file_path}")
                rows = self._process_segments_file(file_path)
                
                if rows:
                    errors = self.client.insert_rows_json(table_id, rows)
                    if errors:
                        logger.error(f"❌ Erreur pour {file_path}: {errors}")
                    else:
                        total_rows += len(rows)
                        logger.info(f"✅ {file_path}: {len(rows)} lignes uploadées")
                else:
                    logger.warning(f"⚠️ {file_path}: Aucune donnée trouvée")
                    
            except Exception as e:
                logger.error(f"❌ Erreur {file_path}: {str(e)}")
                
        logger.info(f"✅ Total segments: {total_rows} lignes uploadées")
        return total_rows
    
    def upload_websites(self, file_pattern='data/websites_extraction_*.json'):
        """Upload les fichiers de websites vers BigQuery"""
        files = glob.glob(file_pattern)
        logger.info(f"🌐 {len(files)} fichiers websites trouvés")
        
        if not files:
            logger.warning("⚠️ Aucun fichier websites trouvé")
            return 0
        
        total_rows = 0
        table_id = f"{self.project_id}.{self.dataset_id}.websites_data"
        
        for file_path in sorted(files):
            try:
                logger.info(f"📁 Traitement: {file_path}")
                rows = self._process_websites_file(file_path)
                
                if rows:
                    errors = self.client.insert_rows_json(table_id, rows)
                    if errors:
                        logger.error(f"❌ Erreur pour {file_path}: {errors}")
                    else:
                        total_rows += len(rows)
                        logger.info(f"✅ {file_path}: {len(rows)} lignes uploadées")
                else:
                    logger.warning(f"⚠️ {file_path}: Aucune donnée trouvée")
                    
            except Exception as e:
                logger.error(f"❌ Erreur {file_path}: {str(e)}")
                
        logger.info(f"✅ Total websites: {total_rows} lignes uploadées")
        return total_rows
    
    def _process_segments_file(self, file_path):
        """Traite un fichier de segments - Format SimilarWeb"""
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        if not isinstance(data, list):
            logger.warning(f"⚠️ Format inattendu dans {file_path}: attendu une liste")
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
                logger.debug(f"🔍 Pas de données pour {segment_name}")
                continue
            
            # Traiter chaque point de données
            for data_point in segment_data['segments']:
                if not isinstance(data_point, dict):
                    continue
                    
                row = {
                    'segment_id': segment_id,
                    'segment_name': segment_name,
                    'date': data_point.get('date', ''),
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
        
        logger.info(f"📊 {len(rows)} lignes extraites de {os.path.basename(file_path)}")
        return rows
    
    def _process_websites_file(self, file_path):
        """Traite un fichier de websites - Format SimilarWeb"""
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        if not isinstance(data, list):
            logger.warning(f"⚠️ Format inattendu dans {file_path}: attendu une liste")
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
        
        logger.info(f"🌐 {len(rows)} lignes extraites de {os.path.basename(file_path)}")
        return rows
    
    def _add_metric_to_row(self, row, metrics, metric_name, field_name, target_date):
        """Ajoute une métrique à la ligne si elle existe pour la date"""
        metric_data = metrics.get(metric_name, {})
        if metric_data and metric_name in metric_data:
            for point in metric_data[metric_name]:
                if point.get('date') == target_date:
                    value = point.get(field_name)
                    if value is not None:
                        row[metric_name] = float(value)
                    break
    
    def _add_split_metrics(self, row, metrics, target_date):
        """Ajoute les métriques desktop/mobile split"""
        split_data = metrics.get('desktop_mobile_split', {})
        if split_data and 'data' in split_data:
            for split_point in split_data['data']:
                if split_point.get('date') == target_date:
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
        logger.info("\n📊 VÉRIFICATION BIGQUERY")
        
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
            logger.error(f"❌ Erreur vérification segments: {e}")
        
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
            logger.error(f"❌ Erreur vérification websites: {e}")
    
    def debug_file_structure(self, file_pattern='data/*extraction*.json'):
        """Debug la structure des fichiers JSON"""
        files = glob.glob(file_pattern)
        logger.info(f"🔍 DEBUG: Analyse de {len(files)} fichiers")
        
        for file_path in files[:2]:  # Analyser seulement les 2 premiers
            logger.info(f"\n📁 Analyse: {file_path}")
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                
                logger.info(f"   Type: {type(data)}")
                if isinstance(data, list):
                    logger.info(f"   Nombre d'éléments: {len(data)}")
                    if data:
                        first_item = data[0]
                        logger.info(f"   Premier élément - clés: {list(first_item.keys())}")
                        if 'data' in first_item:
                            logger.info(f"   Structure data: {list(first_item['data'].keys())}")
                elif isinstance(data, dict):
                    logger.info(f"   Clés: {list(data.keys())}")
                    
            except Exception as e:
                logger.error(f"❌ Erreur lecture {file_path}: {e}")


def main():
    """Fonction principale"""
    parser = argparse.ArgumentParser(description='Upload corrigé des données vers BigQuery')
    parser.add_argument('--type', choices=['all', 'segments', 'websites'], 
                       default='all', help='Type de données à uploader')
    parser.add_argument('--debug', action='store_true', 
                       help='Analyser la structure des fichiers')
    parser.add_argument('--verify-only', action='store_true', 
                       help='Vérifier seulement les données dans BigQuery')
    
    args = parser.parse_args()
    
    uploader = BigQueryUploaderFixed()
    
    if args.debug:
        uploader.debug_file_structure()
        return
    
    if args.verify_only:
        uploader.verify_data()
        return
    
    logger.info("🚀 UPLOAD VERS BIGQUERY (VERSION CORRIGÉE)")
    logger.info("=" * 60)
    
    if args.type in ['all', 'segments']:
        uploader.upload_segments()
    
    if args.type in ['all', 'websites']:
        uploader.upload_websites()
    
    # Vérification finale
    uploader.verify_data()


if __name__ == "__main__":
    main()