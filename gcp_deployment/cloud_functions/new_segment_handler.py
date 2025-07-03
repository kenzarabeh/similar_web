"""
Gestion automatique des nouveaux segments avec récupération de l'historique
Cette fonction sera intégrée dans la Cloud Function
"""
from datetime import datetime, date
from dateutil.relativedelta import relativedelta
import logging

logger = logging.getLogger(__name__)

class NewSegmentHandler:
    """Gère l'ajout de nouveaux segments avec récupération automatique de l'historique"""
    
    def __init__(self, api_client, bigquery_client):
        self.api = api_client
        self.bq = bigquery_client
        self.historical_months = 12  # Récupérer 12 mois d'historique par défaut
        
    def check_for_new_segments(self):
        """
        Vérifie s'il y a de nouveaux segments et récupère leur historique
        Appelé quotidiennement par la Cloud Function
        """
        logger.info("🔍 Vérification des nouveaux segments...")
        
        # 1. Récupérer la liste actuelle des segments
        current_segments = self.api.get_custom_segments(user_only=True)
        current_ids = {s['segment_id'] for s in current_segments}
        
        # 2. Récupérer les segments déjà dans BigQuery
        known_ids = self.get_known_segments_from_bq()
        
        # 3. Identifier les nouveaux segments
        new_segment_ids = current_ids - known_ids
        
        if not new_segment_ids:
            logger.info("✅ Aucun nouveau segment détecté")
            return []
        
        logger.info(f"🆕 {len(new_segment_ids)} nouveaux segments détectés!")
        
        # 4. Pour chaque nouveau segment, récupérer l'historique
        new_segments = [s for s in current_segments if s['segment_id'] in new_segment_ids]
        
        for segment in new_segments:
            logger.info(f"\n📊 Nouveau segment: {segment['segment_name']}")
            self.extract_segment_history(segment)
        
        return new_segments
    
    def get_known_segments_from_bq(self):
        """Récupère la liste des segments déjà présents dans BigQuery"""
        query = """
        SELECT DISTINCT segment_id 
        FROM `similarweb-intel-dev.similarweb_data.segments_data`
        """
        
        known_ids = set()
        for row in self.bq.query(query).result():
            known_ids.add(row.segment_id)
        
        return known_ids
    
    def extract_segment_history(self, segment):
        """
        Extrait l'historique complet d'un segment
        Récupère l'année en cours + année précédente
        """
        segment_id = segment['segment_id']
        segment_name = segment['segment_name']
        
        logger.info(f"📅 Récupération de l'historique pour {segment_name}...")
        
        # Déterminer les périodes à extraire
        current_date = date.today()
        periods_to_extract = []
        
        # Année en cours (jusqu'à J-3)
        for month_offset in range(0, 12):
            target_date = current_date - relativedelta(months=month_offset)
            if target_date >= date(current_date.year, 1, 1):
                periods_to_extract.append({
                    'year': target_date.year,
                    'month': target_date.month,
                    'date_str': target_date.strftime('%Y-%m')
                })
        
        # Année précédente complète
        previous_year = current_date.year - 1
        for month in range(1, 13):
            periods_to_extract.append({
                'year': previous_year,
                'month': month,
                'date_str': f"{previous_year}-{month:02d}"
            })
        
        logger.info(f"   📊 Extraction de {len(periods_to_extract)} mois d'historique")
        
        # Extraire mois par mois
        extracted_count = 0
        for period in periods_to_extract:
            try:
                # Vérifier si déjà présent
                if self.data_exists_for_segment(segment_id, period['date_str']):
                    continue
                
                # Extraire les données
                data = self.api.get_segment_data(
                    segment_id=segment_id,
                    start_date=period['date_str'],
                    end_date=period['date_str'],
                    granularity='monthly'
                )
                
                if data:
                    # Sauvegarder dans BigQuery
                    self.save_segment_data(segment, data, period['date_str'])
                    extracted_count += 1
                    
            except Exception as e:
                logger.error(f"❌ Erreur pour {period['date_str']}: {e}")
        
        logger.info(f"✅ {extracted_count} mois extraits pour {segment_name}")
    
    def data_exists_for_segment(self, segment_id, date_str):
        """Vérifie si les données existent déjà pour un segment à une date donnée"""
        query = f"""
        SELECT COUNT(*) as count
        FROM `similarweb-intel-dev.similarweb_data.segments_data`
        WHERE segment_id = '{segment_id}'
        AND DATE_TRUNC(date, MONTH) = DATE('{date_str}-01')
        """
        
        result = list(self.bq.query(query).result())
        return result[0].count > 0
    
    def save_segment_data(self, segment, data, date_str):
        """Sauvegarde les données d'un segment dans BigQuery"""
        # Transformer les données pour BigQuery
        rows_to_insert = []
        
        if 'segments' in data:
            for segment_data in data['segments']:
                row = {
                    'date': f"{date_str}-01",  # Premier jour du mois
                    'segment_id': segment['segment_id'],
                    'segment_name': segment['segment_name'],
                    'extraction_date': datetime.now().strftime('%Y-%m-%d'),
                    'visits': segment_data.get('visits'),
                    'share': segment_data.get('share'),
                    'bounce_rate': segment_data.get('bounce_rate'),
                    'pages_per_visit': segment_data.get('pages_per_visit'),
                    'visit_duration': segment_data.get('visit_duration'),
                    'page_views': segment_data.get('page_views')
                }
                rows_to_insert.append(row)
        
        # Insérer dans BigQuery
        if rows_to_insert:
            table_id = 'similarweb-intel-dev.similarweb_data.segments_data'
            errors = self.bq.insert_rows_json(table_id, rows_to_insert)
            
            if not errors:
                logger.info(f"   ✅ Données sauvegardées pour {date_str}")
            else:
                logger.error(f"   ❌ Erreur BigQuery: {errors}")


# Exemple d'intégration dans la Cloud Function principale
def enhanced_daily_handler(request):
    """
    Version améliorée du handler quotidien qui gère aussi les nouveaux segments
    """
    # 1. Extraction quotidienne normale
    daily_extraction_handler(request)
    
    # 2. Vérifier et gérer les nouveaux segments
    handler = NewSegmentHandler(api_client, bq_client)
    new_segments = handler.check_for_new_segments()
    
    if new_segments:
        # 3. Notifier (optionnel)
        send_notification(f"🆕 {len(new_segments)} nouveaux segments ajoutés avec historique")
    
    return {
        'status': 'success',
        'new_segments': len(new_segments)
    } 