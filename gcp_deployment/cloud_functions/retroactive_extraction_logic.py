"""
Logique de récupération rétroactive des données SimilarWeb
Gère les cas où les données ne sont pas immédiatement disponibles
"""
from datetime import datetime, timedelta
from typing import List, Tuple, Dict
import logging

logger = logging.getLogger(__name__)

class RetroactiveDataExtractor:
    def __init__(self, api_client, bigquery_client):
        self.api = api_client
        self.bq = bigquery_client
        self.max_lookback_days = 7  # Chercher jusqu'à 7 jours en arrière
        self.data_availability_delay = 2  # Les données sont généralement disponibles après 2-3 jours
        
    def daily_extraction_handler(self, event=None, context=None):
        """
        Fonction principale appelée quotidiennement par Cloud Scheduler
        Exemple: Exécutée le mercredi 3 janvier à 2h du matin
        """
        current_date = datetime.now().date()
        logger.info(f"🚀 Extraction quotidienne démarrée le {current_date}")
        
        # 1. Identifier toutes les dates à vérifier
        dates_to_check = self.get_dates_to_check(current_date)
        logger.info(f"📅 Dates à vérifier: {[d.strftime('%Y-%m-%d') for d in dates_to_check]}")
        
        # 2. Pour chaque date, vérifier et extraire si nécessaire
        extraction_summary = {
            'already_extracted': [],
            'newly_extracted': [],
            'not_available': [],
            'errors': []
        }
        
        for check_date in dates_to_check:
            result = self.process_date(check_date)
            extraction_summary[result['status']].append(check_date)
        
        # 3. Rapport final
        self.generate_report(extraction_summary)
        
        return extraction_summary
    
    def get_dates_to_check(self, current_date) -> List[datetime.date]:
        """
        Retourne la liste des dates à vérifier
        Exemple: Le mercredi 3, on vérifie:
        - Lundi 1er (J-2)
        - Dimanche 31 (J-3)
        - Samedi 30 (J-4)
        - ... jusqu'à J-7
        """
        dates = []
        for days_back in range(self.data_availability_delay, self.max_lookback_days + 1):
            dates.append(current_date - timedelta(days=days_back))
        return dates
    
    def process_date(self, target_date) -> Dict:
        """
        Traite une date spécifique
        """
        logger.info(f"\n🔍 Vérification pour {target_date}...")
        
        # Étape 1: Vérifier si déjà dans BigQuery
        if self.data_exists_in_bigquery(target_date):
            logger.info(f"✅ Données déjà extraites pour {target_date}")
            return {'status': 'already_extracted', 'date': target_date}
        
        # Étape 2: Tester la disponibilité dans l'API
        is_available = self.check_api_availability(target_date)
        
        if not is_available:
            logger.info(f"⏳ Données pas encore disponibles pour {target_date}")
            return {'status': 'not_available', 'date': target_date}
        
        # Étape 3: Extraire les données
        try:
            logger.info(f"🚀 Extraction des données pour {target_date}...")
            self.extract_data_for_date(target_date)
            logger.info(f"✅ Extraction réussie pour {target_date}")
            return {'status': 'newly_extracted', 'date': target_date}
        except Exception as e:
            logger.error(f"❌ Erreur lors de l'extraction pour {target_date}: {e}")
            return {'status': 'errors', 'date': target_date, 'error': str(e)}
    
    def data_exists_in_bigquery(self, target_date) -> bool:
        """
        Vérifie si les données existent déjà dans BigQuery
        """
        query = f"""
        SELECT COUNT(*) as count
        FROM `similarweb-intel-dev.similarweb_data.segments_data`
        WHERE DATE(date) = '{target_date}'
        """
        
        result = list(self.bq.query(query).result())
        return result[0].count > 0
    
    def check_api_availability(self, target_date) -> bool:
        """
        Teste si les données sont disponibles dans l'API
        Utilise un seul segment pour tester (économise les crédits API)
        """
        # Utiliser le premier segment comme test
        test_segment_id = "00d0e096-5b68-46cb-a570-3edf5849623a"  # Feuvert par exemple
        
        try:
            response = self.api.get_segment_data(
                segment_id=test_segment_id,
                start_date=target_date.strftime('%Y-%m'),
                end_date=target_date.strftime('%Y-%m'),
                granularity='daily'
            )
            
            # Vérifier si on a des données pour cette date spécifique
            if response and 'segments' in response:
                for segment in response['segments']:
                    if segment.get('date') == target_date.strftime('%Y-%m-%d'):
                        return True
            return False
            
        except Exception:
            return False
    
    def extract_data_for_date(self, target_date):
        """
        Extrait toutes les données pour une date donnée
        """
        # Formater les dates pour l'API (format mensuel)
        month_str = target_date.strftime('%Y-%m')
        
        # 1. Extraire les 88 segments personnels
        segments_data = self.api.extract_all_segments(
            start_date=month_str,
            end_date=month_str,
            user_only=True,
            granularity='daily'  # Important pour avoir le détail quotidien
        )
        
        # 2. Filtrer uniquement les données de la date cible
        filtered_segments = []
        for segment in segments_data:
            if segment.get('data') and segment['data'].get('segments'):
                for seg_data in segment['data']['segments']:
                    if seg_data.get('date') == target_date.strftime('%Y-%m-%d'):
                        filtered_segments.append({
                            'segment_id': segment['segment_id'],
                            'segment_name': segment['segment_name'],
                            'data': {'segments': [seg_data]},
                            'extraction_date': datetime.now().strftime('%Y-%m-%d')
                        })
        
        # 3. Upload vers BigQuery
        if filtered_segments:
            self.upload_to_bigquery(filtered_segments)
    
    def generate_report(self, summary: Dict):
        """
        Génère un rapport de l'extraction
        """
        logger.info("\n📊 RAPPORT D'EXTRACTION RÉTROACTIVE")
        logger.info("=" * 50)
        
        if summary['newly_extracted']:
            logger.info(f"✅ Nouvelles données extraites ({len(summary['newly_extracted'])}):")
            for date in summary['newly_extracted']:
                logger.info(f"   - {date}")
        
        if summary['already_extracted']:
            logger.info(f"✓ Déjà extraites ({len(summary['already_extracted'])}):")
            for date in summary['already_extracted']:
                logger.info(f"   - {date}")
        
        if summary['not_available']:
            logger.info(f"⏳ Pas encore disponibles ({len(summary['not_available'])}):")
            for date in summary['not_available']:
                days_old = (datetime.now().date() - date).days
                logger.info(f"   - {date} (J-{days_old})")
        
        if summary['errors']:
            logger.info(f"❌ Erreurs ({len(summary['errors'])}):")
            for date in summary['errors']:
                logger.info(f"   - {date}")


# Exemple d'utilisation
if __name__ == "__main__":
    # Simulation pour le mercredi 3 janvier 2025
    print("\n🔄 EXEMPLE DE RÉCUPÉRATION RÉTROACTIVE")
    print("Scenario: Nous sommes le mercredi 3 janvier 2025")
    print("La Cloud Function vérifie les 7 derniers jours...")
    print("\nDates vérifiées:")
    print("- Lundi 1er janvier (J-2) - Peut-être disponible")
    print("- Dimanche 31 décembre (J-3) - Probablement disponible")
    print("- Samedi 30 décembre (J-4) - Disponible")
    print("- ... jusqu'à J-7")
    print("\nRésultat possible:")
    print("✅ 30 & 31 décembre: Données extraites")
    print("⏳ 1er janvier: Pas encore disponible (sera récupéré demain)")
    print("✓ 29, 28, 27 décembre: Déjà dans BigQuery") 