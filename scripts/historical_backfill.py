"""
Script de backfill historique pour récupérer toutes les données 2024 et 2025
VERSION CORRIGÉE - Architecture 3 tables SimilarWeb
- segments_daily : données daily sans unique_visitors
- segments_unique_visitors : données monthly avec seulement unique_visitors  
- websites_daily : données daily avec unique_visitors
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
            'start_date': f'2024-{month:02d}-01',
            'end_date': f'2024-{month:02d}-31',
            'monthly_format': f'2024-{month:02d}',
            'year': 2024,
            'month': month
        }
        periods.append(period)
    
    # Année 2025 jusqu'à septembre (mois actuel)
    current_date = datetime.now()
    max_month = min(current_date.month, 9)  # Jusqu'au mois actuel max
    
    for month in range(1, max_month + 1):
        # Calculer le dernier jour du mois
        if month == 2:
            last_day = 28  # Février (simplifié)
        elif month in [4, 6, 9, 11]:
            last_day = 30
        else:
            last_day = 31
            
        period = {
            'start_date': f'2025-{month:02d}-01',
            'end_date': f'2025-{month:02d}-{last_day:02d}',
            'monthly_format': f'2025-{month:02d}',
            'year': 2025,
            'month': month
        }
        periods.append(period)
    
    return periods


def extract_and_save_segments_three_tables(api_client: SimilarWebAPI, period: Dict[str, str], 
                                          limit: int = None) -> Dict:
    """
    Extrait et sauvegarde les segments pour une période - Architecture 3 tables
    Fait 2 extractions : segments_daily ET segments_unique_visitors
    
    Args:
        api_client: Instance du client API
        period: Dictionnaire avec start_date, end_date, monthly_format
        limit: Limite du nombre de segments
        
    Returns:
        Statistiques de l'extraction
    """
    logger.info(f"Extraction segments 3 tables pour {period['monthly_format']}")
    
    results = {
        'segments_daily': [],
        'segments_unique_visitors': [],
        'stats': {
            'segments_daily': {'total': 0, 'success': 0, 'errors': 0},
            'segments_unique_visitors': {'total': 0, 'success': 0, 'errors': 0}
        }
    }
    
    # 1. Extraction segments_daily (prendre le 15 du mois comme représentatif daily)
    mid_month_date = f"{period['year']}-{period['month']:02d}-15"
    logger.info(f"  1. Segments daily pour {mid_month_date}")
    
    segments_daily_data = api_client.extract_segments_daily_architecture(
        start_date=mid_month_date,
        end_date=mid_month_date,
        limit=limit,
        user_only=True,
        granularity='daily'
    )
    
    results['segments_daily'] = segments_daily_data
    results['stats']['segments_daily'] = {
        'total': len(segments_daily_data),
        'success': len([s for s in segments_daily_data if not s.get('error')]),
        'errors': len([s for s in segments_daily_data if s.get('error')])
    }
    
    # 2. Extraction segments_unique_visitors (monthly)
    logger.info(f"  2. Segments unique_visitors pour {period['monthly_format']}")
    
    segments_uv_data = api_client.extract_segments_unique_visitors_architecture(
        start_date=period['monthly_format'],
        end_date=period['monthly_format'],
        limit=limit,
        user_only=True
    )
    
    results['segments_unique_visitors'] = segments_uv_data
    results['stats']['segments_unique_visitors'] = {
        'total': len(segments_uv_data),
        'success': len([s for s in segments_uv_data if not s.get('error')]),
        'errors': len([s for s in segments_uv_data if s.get('error')])
    }
    
    # Sauvegardes séparées avec timestamp
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    
    # Sauvegarder segments_daily
    if segments_daily_data:
        filename_daily = f"segments_daily_extraction_{period['monthly_format'].replace('-', '')}_{timestamp}.json"
        save_results_to_json(segments_daily_data, filename_daily)
        logger.info(f"  Segments daily sauvegardés: {filename_daily}")
    
    # Sauvegarder segments_unique_visitors
    if segments_uv_data:
        filename_uv = f"segments_unique_visitors_extraction_{period['monthly_format'].replace('-', '')}_{timestamp}.json"
        save_results_to_json(segments_uv_data, filename_uv)
        logger.info(f"  Segments unique_visitors sauvegardés: {filename_uv}")
    
    # Log des stats
    daily_stats = results['stats']['segments_daily']
    uv_stats = results['stats']['segments_unique_visitors']
    
    logger.info(f"Segments {period['monthly_format']}:")
    logger.info(f"  - Daily: {daily_stats['success']}/{daily_stats['total']} extraits")
    logger.info(f"  - Unique_visitors: {uv_stats['success']}/{uv_stats['total']} extraits")
    
    return results['stats']


def extract_and_save_websites_three_tables(api_client: SimilarWebAPI, period: Dict[str, str]) -> Dict:
    """
    Extrait et sauvegarde les sites web pour une période - Architecture 3 tables (inchangé)
    
    Args:
        api_client: Instance du client API  
        period: Dictionnaire avec start_date, end_date
        
    Returns:
        Statistiques de l'extraction
    """
    logger.info(f"Extraction websites pour {period['monthly_format']}")
    
    # Charger la liste des sites web
    try:
        from scripts.manage_websites import load_websites
        domains = load_websites()
        logger.info(f"  {len(domains)} sites web chargés")
    except:
        domains = TARGET_DOMAINS
        logger.warning(f"  Utilisation de la liste par défaut: {len(domains)} sites")
    
    # Extraction websites daily (prendre le 15 du mois comme représentatif)
    mid_month_date = f"{period['year']}-{period['month']:02d}-15"
    
    websites_data = api_client.extract_websites_daily_architecture(
        domains=domains,
        start_date=mid_month_date,
        end_date=mid_month_date,
        granularity='daily'
    )
    
    # Statistiques
    stats = {
        'total': len(websites_data),
        'success': len([w for w in websites_data if any(w.get('metrics', {}).values())]),
        'errors': len([w for w in websites_data if not any(w.get('metrics', {}).values())])
    }
    
    # Sauvegarde avec timestamp
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    filename = f"websites_daily_extraction_{period['monthly_format'].replace('-', '')}_{timestamp}.json"
    save_results_to_json(websites_data, filename)
    
    logger.info(f"Websites {period['monthly_format']}: {stats['success']}/{stats['total']} extraits")
    logger.info(f"  Sauvegardés: {filename}")
    
    return stats


def estimate_api_calls_three_tables(periods: List[Dict], segments_count: int, websites_count: int) -> Dict:
    """
    Estime le nombre d'appels API nécessaires pour l'architecture 3 tables
    """
    # Pour chaque mois :
    # - segments_daily : 3 appels par segment (daily, sans unique_visitors)
    # - segments_unique_visitors : 1 appel par segment (monthly, seulement unique_visitors)
    # - websites_daily : 6 appels par site web (daily, avec unique_visitors)
    
    segments_daily_calls = len(periods) * segments_count * 3
    segments_uv_calls = len(periods) * segments_count * 1 
    website_calls = len(periods) * websites_count * 6
    
    total_calls = segments_daily_calls + segments_uv_calls + website_calls
    
    # Temps estimé (1.5 seconde par appel + marges)
    estimated_time_minutes = (total_calls * 1.5) / 60
    
    return {
        'periods': len(periods),
        'segments_daily_calls': segments_daily_calls,
        'segments_uv_calls': segments_uv_calls,
        'website_calls': website_calls,
        'total_calls': total_calls,
        'estimated_time_minutes': round(estimated_time_minutes, 1),
        'architecture': '3_tables'
    }


def run_backfill_three_tables(start_year: int = 2024, end_month: str = None, 
                             limit_segments: int = None, batch_size: int = 3):
    """
    Exécute le backfill historique - Architecture 3 tables
    
    Args:
        start_year: Année de début (2024 par défaut)
        end_month: Mois de fin au format YYYY-MM (automatique si None)
        limit_segments: Limiter le nombre de segments (None = tous)
        batch_size: Nombre de mois à traiter par batch
    """
    logger.info("Démarrage du backfill historique - Architecture 3 tables")
    
    # Initialiser le client API
    api_client = SimilarWebAPI()
    
    # Récupérer le nombre de segments
    segments = api_client.get_custom_segments(user_only=True)
    if not segments:
        logger.error("Impossible de récupérer les segments")
        return
    
    segments_count = len(segments) if not limit_segments else min(limit_segments, len(segments))
    
    # Charger la liste dynamique des sites web
    try:
        from scripts.manage_websites import load_websites
        domains = load_websites()
        websites_count = len(domains)
        logger.info(f"{websites_count} sites web chargés depuis la configuration")
    except:
        websites_count = len(TARGET_DOMAINS)
        logger.warning(f"Utilisation de la liste par défaut: {websites_count} sites")
    
    # Générer les périodes
    periods = get_historical_periods()
    
    # Filtrer selon les paramètres
    if start_year == 2025:
        periods = [p for p in periods if p['year'] == 2025]
    elif start_year == 2024:
        periods = [p for p in periods if p['year'] == 2024]
    
    if end_month:
        periods = [p for p in periods if p['monthly_format'] <= end_month]
    
    # Estimation avec architecture 3 tables
    estimation = estimate_api_calls_three_tables(periods, segments_count, websites_count)
    
    logger.info(f"ESTIMATION DU BACKFILL - ARCHITECTURE 3 TABLES:")
    logger.info(f"   - Périodes: {estimation['periods']} mois")
    logger.info(f"   - Segments: {segments_count}")
    logger.info(f"   - Sites web: {websites_count}")
    logger.info(f"   - Appels API segments_daily: {estimation['segments_daily_calls']:,}")
    logger.info(f"   - Appels API segments_unique_visitors: {estimation['segments_uv_calls']:,}")
    logger.info(f"   - Appels API websites_daily: {estimation['website_calls']:,}")
    logger.info(f"   - Appels API totaux: {estimation['total_calls']:,}")
    logger.info(f"   - Temps estimé: {estimation['estimated_time_minutes']} minutes")
    
    logger.info(f"\nPériodes à extraire:")
    for period in periods:
        logger.info(f"   - {period['monthly_format']}")
    
    # Confirmation
    response = input(f"\nVoulez-vous continuer avec {len(periods)} mois? (y/n): ")
    if response.lower() != 'y':
        logger.info("Backfill annulé")
        return
    
    # Statistiques globales
    stats = {
        'periods_processed': 0,
        'segments_daily_extracted': 0,
        'segments_uv_extracted': 0,
        'websites_extracted': 0,
        'errors': 0,
        'start_time': datetime.now(),
        'architecture': '3_tables'
    }
    
    # Traiter par batch
    for i in range(0, len(periods), batch_size):
        batch = periods[i:i + batch_size]
        logger.info(f"\nBATCH {i//batch_size + 1}/{(len(periods) + batch_size - 1)//batch_size}")
        
        for period in batch:
            try:
                logger.info(f"\nPériode: {period['monthly_format']}")
                
                # Extraction des segments (2 types)
                segments_stats = extract_and_save_segments_three_tables(
                    api_client=api_client,
                    period=period,
                    limit=limit_segments
                )
                stats['segments_daily_extracted'] += segments_stats['segments_daily']['success']
                stats['segments_uv_extracted'] += segments_stats['segments_unique_visitors']['success']
                
                # Extraction des sites web
                website_stats = extract_and_save_websites_three_tables(
                    api_client=api_client,
                    period=period
                )
                stats['websites_extracted'] += website_stats['success']
                
                stats['periods_processed'] += 1
                
                # Pause entre les périodes
                logger.info(f"   Pause de 5 secondes...")
                time.sleep(5)
                
            except Exception as e:
                logger.error(f"Erreur pour la période {period['monthly_format']}: {e}")
                stats['errors'] += 1
                continue
        
        # Pause plus longue entre les batchs
        if i + batch_size < len(periods):
            logger.info(f"\nPause de 30 secondes entre les batchs...")
            time.sleep(30)
    
    # Résumé final
    duration = (datetime.now() - stats['start_time']).total_seconds() / 60
    
    logger.info("\n" + "="*50)
    logger.info("BACKFILL TERMINÉ - ARCHITECTURE 3 TABLES")
    logger.info(f"   - Durée: {duration:.1f} minutes")
    logger.info(f"   - Périodes traitées: {stats['periods_processed']}")
    logger.info(f"   - Segments daily extraits: {stats['segments_daily_extracted']}")
    logger.info(f"   - Segments unique_visitors extraits: {stats['segments_uv_extracted']}")
    logger.info(f"   - Sites web extraits: {stats['websites_extracted']}")
    logger.info(f"   - Erreurs: {stats['errors']}")
    
    logger.info(f"\nFichiers créés dans le dossier 'data/':")
    logger.info(f"   - segments_daily_extraction_*.json")
    logger.info(f"   - segments_unique_visitors_extraction_*.json")
    logger.info(f"   - websites_daily_extraction_*.json")
    logger.info(f"\nUtilisez: python scripts/upload_to_bigquery.py --type all")
    
    # Sauvegarder le résumé
    summary = {
        'backfill_date': datetime.now().isoformat(),
        'architecture': '3_tables',
        'periods_processed': stats['periods_processed'],
        'duration_minutes': duration,
        'segments_daily_extracted': stats['segments_daily_extracted'],
        'segments_uv_extracted': stats['segments_uv_extracted'],
        'websites_extracted': stats['websites_extracted'],
        'errors': stats['errors'],
        'estimation': estimation
    }
    
    save_results_to_json(summary, 'backfill_summary_3_tables.json')
    
    return stats


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Backfill historique - Architecture 3 tables')
    parser.add_argument('--year', type=int, default=2024, 
                        help='Année de début (2024 ou 2025)')
    parser.add_argument('--end-month', type=str, 
                        help='Mois de fin au format YYYY-MM')
    parser.add_argument('--limit-segments', type=int, 
                        help='Limiter le nombre de segments')
    parser.add_argument('--batch-size', type=int, default=3,
                        help='Nombre de mois par batch')
    
    args = parser.parse_args()
    
    run_backfill_three_tables(
        start_year=args.year,
        end_month=args.end_month,
        limit_segments=args.limit_segments,
        batch_size=args.batch_size
    )