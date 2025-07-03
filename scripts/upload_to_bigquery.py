#!/usr/bin/env python3
"""
Script consolidé pour uploader les données vers BigQuery
Remplace les multiples scripts d'upload
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

class BigQueryUploader:
    def __init__(self, project_id='similarweb-intel-dev'):
        """Initialise le client BigQuery"""
        self.client = bigquery.Client(project=project_id)
        self.project_id = project_id
        self.dataset_id = 'similarweb_data'
        
    def upload_segments(self, file_pattern='data/segments_extraction_*.json'):
        """Upload les fichiers de segments vers BigQuery"""
        files = glob.glob(file_pattern)
        logger.info(f"📊 {len(files)} fichiers segments trouvés")
        
        total_rows = 0
        table_id = f"{self.project_id}.{self.dataset_id}.segments_data"
        
        for file_path in sorted(files):
            try:
                rows = self._process_segments_file(file_path)
                if rows:
                    errors = self.client.insert_rows_json(table_id, rows)
                    if errors:
                        logger.error(f"❌ Erreur pour {file_path}: {errors}")
                    else:
                        total_rows += len(rows)
                        logger.info(f"✅ {file_path}: {len(rows)} lignes")
            except Exception as e:
                logger.error(f"❌ Erreur {file_path}: {str(e)}")
                
        logger.info(f"✅ Total segments: {total_rows} lignes uploadées")
        return total_rows
    
    def upload_websites(self, file_pattern='data/websites_extraction_*.json'):
        """Upload les fichiers de websites vers BigQuery"""
        files = glob.glob(file_pattern)
        logger.info(f"🌐 {len(files)} fichiers websites trouvés")
        
        total_rows = 0
        table_id = f"{self.project_id}.{self.dataset_id}.websites_data"
        
        for file_path in sorted(files):
            try:
                rows = self._process_websites_file(file_path)
                if rows:
                    errors = self.client.insert_rows_json(table_id, rows)
                    if errors:
                        logger.error(f"❌ Erreur pour {file_path}: {errors}")
                    else:
                        total_rows += len(rows)
                        logger.info(f"✅ {file_path}: {len(rows)} lignes")
            except Exception as e:
                logger.error(f"❌ Erreur {file_path}: {str(e)}")
                
        logger.info(f"✅ Total websites: {total_rows} lignes uploadées")
        return total_rows
    
    def _process_segments_file(self, file_path):
        """Traite un fichier de segments"""
        with open(file_path, 'r') as f:
            data = json.load(f)
        
        # Extraire la date du filename
        filename = os.path.basename(file_path)
        date_str = filename.split('_')[2][:8]  # 20250620
        extraction_date = datetime.strptime(date_str, '%Y%m%d').strftime('%Y-%m-%d')
        
        rows = []
        for segment in data:
            if 'data' in segment:
                for date, metrics in segment['data'].items():
                    if metrics and isinstance(metrics, dict):
                        rows.append({
                            'segment_id': segment.get('segment_id', segment.get('id', '')),
                            'segment_name': segment.get('segment_name', segment.get('name', '')),
                            'date': date,
                            'visits': metrics.get('visits', 0),
                            'share': metrics.get('share', 0),
                            'bounce_rate': metrics.get('bounce_rate'),
                            'pages_per_visit': metrics.get('pages_per_visit'),
                            'visit_duration': metrics.get('visit_duration'),
                            'page_views': metrics.get('page_views'),
                            'unique_visitors': metrics.get('unique_visitors'),
                            'extraction_timestamp': datetime.now().isoformat()
                        })
        return rows
    
    def _process_websites_file(self, file_path):
        """Traite un fichier de websites"""
        with open(file_path, 'r') as f:
            data = json.load(f)
        
        rows = []
        for website in data:
            if 'data' in website:
                domain = website.get('domain', '')
                for date, metrics in website['data'].items():
                    if metrics and isinstance(metrics, dict):
                        rows.append({
                            'domain': domain,
                            'date': date,
                            'visits': metrics.get('visits', 0),
                            'bounce_rate': metrics.get('bounce_rate'),
                            'pages_per_visit': metrics.get('pages_per_visit'),
                            'visit_duration': metrics.get('avg_visit_duration'),
                            'page_views': metrics.get('page_views'),
                            'unique_visitors': metrics.get('unique_visitors'),
                            'desktop_share': metrics.get('desktop_share'),
                            'mobile_share': metrics.get('mobile_share'),
                            'extraction_timestamp': datetime.now().isoformat()
                        })
        return rows
    
    def verify_data(self):
        """Vérifie les données dans BigQuery"""
        logger.info("\n📊 VÉRIFICATION BIGQUERY")
        
        # Vérifier segments
        query = f"""
        SELECT 
            COUNT(*) as total,
            COUNT(DISTINCT date) as nb_dates,
            MIN(date) as min_date,
            MAX(date) as max_date
        FROM `{self.project_id}.{self.dataset_id}.segments_data`
        """
        result = list(self.client.query(query))[0]
        logger.info(f"Segments: {result['total']} lignes, {result['nb_dates']} dates ({result['min_date']} → {result['max_date']})")
        
        # Vérifier websites
        query = f"""
        SELECT 
            COUNT(*) as total,
            COUNT(DISTINCT date) as nb_dates,
            MIN(date) as min_date,
            MAX(date) as max_date
        FROM `{self.project_id}.{self.dataset_id}.websites_data`
        """
        result = list(self.client.query(query))[0]
        logger.info(f"Websites: {result['total']} lignes, {result['nb_dates']} dates ({result['min_date']} → {result['max_date']})")


def main():
    """Fonction principale"""
    parser = argparse.ArgumentParser(description='Upload des données vers BigQuery')
    parser.add_argument('--type', choices=['all', 'segments', 'websites'], 
                       default='all', help='Type de données à uploader')
    parser.add_argument('--pattern', help='Pattern des fichiers à uploader')
    parser.add_argument('--verify-only', action='store_true', 
                       help='Vérifier seulement les données dans BigQuery')
    
    args = parser.parse_args()
    
    uploader = BigQueryUploader()
    
    if args.verify_only:
        uploader.verify_data()
        return
    
    logger.info("🚀 UPLOAD VERS BIGQUERY")
    logger.info("=" * 60)
    
    if args.type in ['all', 'segments']:
        pattern = args.pattern or 'data/segments_extraction_*.json'
        uploader.upload_segments(pattern)
    
    if args.type in ['all', 'websites']:
        pattern = args.pattern or 'data/websites_extraction_*.json'
        uploader.upload_websites(pattern)
    
    # Vérification finale
    uploader.verify_data()


if __name__ == "__main__":
    main() 