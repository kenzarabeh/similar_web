"""
Script de backfill historique pour récupérer toutes les données 2024 et 2025
Optimisé pour minimiser les appels API et maximiser l'efficacité
"""
import sys
import os
from datetime import datetime
import time
import logging
from typing import List, Dict, Tuple
import argparse

# Ajouter le chemin parent pour importer les modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config.config import *
from scripts.similarweb_api import SimilarWebAPI, save_results_to_json
from scripts.daily_extraction import extract_and_save_segments, extract_and_save_websites

# Configuration du logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def get_historical_periods() -> List[Dict[str, str]]:
    """
    Génère la liste des périodes à extraire pour 2024 et 2025
    
    Returns:
        Liste des périodes avec start_date et end_date
    """
    periods = []
    
    # Année 2024 complète
    for month in range(1, 13):
        period = {
            'start_date': f'2024-{month:02d}',
            'end_date': f'2024-{month:02d}'
        }
        periods.append(period)
    
    # Année 2025 jusqu'à mai
    current_date = datetime.now()
    max_month = min(current_date.month - 1, 5)  # Jusqu'à mai ou le mois précédent
    
    for month in range(1, max_month + 1):
        period = {
            'start_date': f'2025-{month:02d}',
            'end_date': f'2025-{month:02d}'
        }
        periods.append(period)
    
    return periods


def estimate_api_calls(periods: List[Dict], segments_count: int, websites_count: int) -> Dict:
    """
    Estime le nombre d'appels API nécessaires
    
    Args:
        periods: Liste des périodes
        segments_count: Nombre de segments
        websites_count: Nombre de sites web
        
    Returns:
        Estimation des appels API
    """
    # 3 appels par segment (avec les nouvelles métriques)
    segment_calls = len(periods) * segments_count * 3
    
    # 6 appels par site web
    website_calls = len(periods) * websites_count * 6
    
    total_calls = segment_calls + website_calls
    
    # Temps estimé (1 seconde par appel + marges)
    estimated_time_minutes = (total_calls * 1.2) / 60
    
    return {
        'periods': len(periods),
        'segment_calls': segment_calls,
        'website_calls': website_calls,
        'total_calls': total_calls,
        'estimated_time_minutes': round(estimated_time_minutes, 1)
    }


def check_existing_data(period: Dict[str, str]) -> Tuple[bool, bool]:
    """
    Vérifie si les données existent déjà dans BigQuery
    
    Args:
        period: Période à vérifier
        
    Returns:
        Tuple (segments_exist, websites_exist)
    """
    try:
        from google.cloud import bigquery
        client = bigquery.Client(project=GCP_PROJECT_ID)
        
        # Vérifier les segments
        query_segments = f"""
        SELECT COUNT(*) as count
        FROM `{GCP_PROJECT_ID}.{BIGQUERY_DATASET}.segments_data`
        WHERE date = '{period['start_date']}-01'
        """
        
        result_segments = client.query(query_segments).result()
        segments_count = list(result_segments)[0].count
        
        # Vérifier les sites web
        query_websites = f"""
        SELECT COUNT(*) as count
        FROM `{GCP_PROJECT_ID}.{BIGQUERY_DATASET}.websites_data`
        WHERE date = '{period['start_date']}-01'
        """
        
        result_websites = client.query(query_websites).result()
        websites_count = list(result_websites)[0].count
        
        # On considère que les données existent si on a au moins quelques entrées
        return segments_count > 10, websites_count > 0
        
    except Exception as e:
        logger.warning(f"Impossible de vérifier les données existantes: {e}")
        return False, False


def run_backfill(start_year: int = 2024, end_month: str = None, 
                 skip_existing: bool = True, limit_segments: int = None,
                 batch_size: int = 3):
    """
    Exécute le backfill historique
    
    Args:
        start_year: Année de début (2024 par défaut)
        end_month: Mois de fin au format YYYY-MM (automatique si None)
        skip_existing: Ignorer les périodes déjà présentes dans BigQuery
        limit_segments: Limiter le nombre de segments (None = tous)
        batch_size: Nombre de mois à traiter par batch
    """
    logger.info("🚀 Démarrage du backfill historique")
    
    # Initialiser le client API
    api_client = SimilarWebAPI()
    
    # Récupérer le nombre de segments
    segments = api_client.get_custom_segments()
    if not segments:
        logger.error("Impossible de récupérer les segments")
        return
    
    segments_count = len(segments) if not limit_segments else min(limit_segments, len(segments))
    
    # Charger la liste dynamique des sites web
    try:
        from scripts.manage_websites import load_websites
        domains = load_websites()
        websites_count = len(domains)
        logger.info(f"📋 {websites_count} sites web chargés depuis la configuration")
    except:
        websites_count = len(TARGET_DOMAINS)
        logger.warning(f"⚠️  Utilisation de la liste par défaut: {websites_count} sites")
    
    # Générer les périodes
    periods = get_historical_periods()
    
    # Filtrer selon les paramètres
    if start_year == 2025:
        periods = [p for p in periods if p['start_date'].startswith('2025')]
    
    if end_month:
        periods = [p for p in periods if p['start_date'] <= end_month]
    
    # Estimation
    estimation = estimate_api_calls(periods, segments_count, websites_count)
    
    logger.info(f"📊 Estimation du backfill:")
    logger.info(f"   - Périodes: {estimation['periods']} mois")
    logger.info(f"   - Segments: {segments_count}")
    logger.info(f"   - Sites web: {websites_count}")
    logger.info(f"   - Appels API totaux: {estimation['total_calls']:,}")
    logger.info(f"   - Temps estimé: {estimation['estimated_time_minutes']} minutes")
    
    # Confirmation
    response = input("\n⚠️  Voulez-vous continuer? (y/n): ")
    if response.lower() != 'y':
        logger.info("Backfill annulé")
        return
    
    # Statistiques globales
    stats = {
        'periods_processed': 0,
        'periods_skipped': 0,
        'segments_extracted': 0,
        'websites_extracted': 0,
        'errors': 0
    }
    
    # Traiter par batch
    for i in range(0, len(periods), batch_size):
        batch = periods[i:i + batch_size]
        logger.info(f"\n📦 Traitement du batch {i//batch_size + 1}/{(len(periods) + batch_size - 1)//batch_size}")
        
        for period in batch:
            try:
                logger.info(f"\n🗓️  Période: {period['start_date']}")
                
                # Vérifier si les données existent déjà
                if skip_existing:
                    segments_exist, websites_exist = check_existing_data(period)
                    if segments_exist and websites_exist:
                        logger.info(f"   ⏭️  Données déjà présentes, passage au mois suivant")
                        stats['periods_skipped'] += 1
                        continue
                
                # Extraction des segments
                if not skip_existing or not segments_exist:
                    segment_stats = extract_and_save_segments(
                        api_client=api_client,
                        period=period,
                        limit=limit_segments
                    )
                    stats['segments_extracted'] += segment_stats['success']
                
                # Extraction des sites web
                if not skip_existing or not websites_exist:
                    website_stats = extract_and_save_websites(
                        api_client=api_client,
                        period=period
                    )
                    stats['websites_extracted'] += website_stats['success']
                
                stats['periods_processed'] += 1
                
                # Pause entre les périodes
                logger.info(f"   ⏸️  Pause de 5 secondes...")
                time.sleep(5)
                
            except Exception as e:
                logger.error(f"❌ Erreur pour la période {period['start_date']}: {e}")
                stats['errors'] += 1
                continue
        
        # Pause plus longue entre les batchs
        if i + batch_size < len(periods):
            logger.info(f"\n⏸️  Pause de 30 secondes entre les batchs...")
            time.sleep(30)
    
    # Résumé final
    logger.info("\n" + "="*50)
    logger.info("✅ BACKFILL TERMINÉ")
    logger.info(f"   - Périodes traitées: {stats['periods_processed']}")
    logger.info(f"   - Périodes ignorées: {stats['periods_skipped']}")
    logger.info(f"   - Segments extraits: {stats['segments_extracted']}")
    logger.info(f"   - Sites web extraits: {stats['websites_extracted']}")
    logger.info(f"   - Erreurs: {stats['errors']}")
    
    return stats


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Backfill historique des données SimilarWeb')
    parser.add_argument('--year', type=int, default=2024, 
                        help='Année de début (2024 ou 2025)')
    parser.add_argument('--end-month', type=str, 
                        help='Mois de fin au format YYYY-MM')
    parser.add_argument('--no-skip-existing', action='store_true',
                        help='Ne pas ignorer les données existantes')
    parser.add_argument('--limit-segments', type=int, 
                        help='Limiter le nombre de segments')
    parser.add_argument('--batch-size', type=int, default=3,
                        help='Nombre de mois par batch')
    
    args = parser.parse_args()
    
    run_backfill(
        start_year=args.year,
        end_month=args.end_month,
        skip_existing=not args.no_skip_existing,
        limit_segments=args.limit_segments,
        batch_size=args.batch_size
    ) 