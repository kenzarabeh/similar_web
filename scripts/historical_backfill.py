"""
Script de backfill historique pour récupérer toutes les données 2024 et 2025
VERSION CORRIGÉE - Compatible avec daily_extraction.py actuel
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
            'end_date': f'2024-{month:02d}-31'
        }
        periods.append(period)
    
    # Année 2025 jusqu'à août (mois actuel)
    current_date = datetime.now()
    max_month = min(current_date.month, 8)  # Jusqu'au mois actuel max
    
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
            'end_date': f'2025-{month:02d}-{last_day:02d}'
        }
        periods.append(period)
    
    return periods


def extract_and_save_segments(api_client: SimilarWebAPI, period: Dict[str, str], 
                             limit: int = None) -> Dict:
    """
    Extrait et sauvegarde les segments pour une période donnée
    
    Args:
        api_client: Instance du client API
        period: Dictionnaire avec start_date et end_date
        limit: Limite du nombre de segments
        
    Returns:
        Statistiques de l'extraction
    """
    logger.info(f"Extraction segments pour {period['start_date'][:7]}")
    
    # Convertir les dates au format YYYY-MM pour l'API
    start_month = period['start_date'][:7]  # YYYY-MM
    end_month = period['end_date'][:7]      # YYYY-MM
    
    # Extraction des segments
    segments_data = api_client.extract_all_segments(
        start_date=start_month,
        end_date=end_month,
        limit=limit,
        user_only=True  # Utiliser seulement les segments utilisateur
    )
    
    # Statistiques
    stats = {
        'total': len(segments_data),
        'success': len([s for s in segments_data if not s.get('error')]),
        'errors': len([s for s in segments_data if s.get('error')])
    }
    
    # Sauvegarde avec timestamp
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    filename = f"segments_extraction_{start_month.replace('-', '')}_{timestamp}.json"
    save_results_to_json(segments_data, filename)
    
    logger.info(f"Segments {period['start_date'][:7]}: {stats['success']}/{stats['total']} extraits")
    
    return stats


def extract_and_save_websites(api_client: SimilarWebAPI, period: Dict[str, str]) -> Dict:
    """
    Extrait et sauvegarde les sites web pour une période donnée
    
    Args:
        api_client: Instance du client API  
        period: Dictionnaire avec start_date et end_date
        
    Returns:
        Statistiques de l'extraction
    """
    logger.info(f"Extraction websites pour {period['start_date'][:7]}")
    
    # Convertir les dates au format YYYY-MM pour l'API
    start_month = period['start_date'][:7]  # YYYY-MM
    end_month = period['end_date'][:7]      # YYYY-MM
    
    # Charger la liste des sites web
    try:
        from scripts.manage_websites import load_websites
        domains = load_websites()
        logger.info(f"{len(domains)} sites web chargés")
    except:
        domains = TARGET_DOMAINS
        logger.warning(f"Utilisation de la liste par défaut: {len(domains)} sites")
    
    # Extraction des sites web
    websites_data = api_client.extract_all_websites(
        domains=domains,
        start_date=start_month,
        end_date=end_month
    )
    
    # Statistiques
    stats = {
        'total': len(websites_data),
        'success': len([w for w in websites_data if any(w.get('metrics', {}).values())]),
        'errors': len([w for w in websites_data if not any(w.get('metrics', {}).values())])
    }
    
    # Sauvegarde avec timestamp
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    filename = f"websites_extraction_{start_month.replace('-', '')}_{timestamp}.json"
    save_results_to_json(websites_data, filename)
    
    logger.info(f"Websites {period['start_date'][:7]}: {stats['success']}/{stats['total']} extraits")
    
    return stats


def estimate_api_calls(periods: List[Dict], segments_count: int, websites_count: int) -> Dict:
    """
    Estime le nombre d'appels API nécessaires
    """
    # 3 appels par segment (avec les nouvelles métriques)
    segment_calls = len(periods) * segments_count * 3
    
    # 6 appels par site web
    website_calls = len(periods) * websites_count * 6
    
    total_calls = segment_calls + website_calls
    
    # Temps estimé (1.5 seconde par appel + marges)
    estimated_time_minutes = (total_calls * 1.5) / 60
    
    return {
        'periods': len(periods),
        'segment_calls': segment_calls,
        'website_calls': website_calls,
        'total_calls': total_calls,
        'estimated_time_minutes': round(estimated_time_minutes, 1)
    }


def run_backfill(start_year: int = 2024, end_month: str = None, 
                 limit_segments: int = None, batch_size: int = 3):
    """
    Exécute le backfill historique
    
    Args:
        start_year: Année de début (2024 par défaut)
        end_month: Mois de fin au format YYYY-MM (automatique si None)
        limit_segments: Limiter le nombre de segments (None = tous)
        batch_size: Nombre de mois à traiter par batch
    """
    logger.info("Démarrage du backfill historique")
    
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
        periods = [p for p in periods if p['start_date'].startswith('2025')]
    elif start_year == 2024:
        periods = [p for p in periods if p['start_date'].startswith('2024')]
    
    if end_month:
        periods = [p for p in periods if p['start_date'][:7] <= end_month]
    
    # Estimation
    estimation = estimate_api_calls(periods, segments_count, websites_count)
    
    logger.info(f"ESTIMATION DU BACKFILL:")
    logger.info(f"   - Périodes: {estimation['periods']} mois")
    logger.info(f"   - Segments: {segments_count}")
    logger.info(f"   - Sites web: {websites_count}")
    logger.info(f"   - Appels API totaux: {estimation['total_calls']:,}")
    logger.info(f"   - Temps estimé: {estimation['estimated_time_minutes']} minutes")
    
    logger.info(f"\nPériodes à extraire:")
    for period in periods:
        logger.info(f"   - {period['start_date'][:7]}")
    
    # Confirmation
    response = input(f"\nVoulez-vous continuer avec {len(periods)} mois? (y/n): ")
    if response.lower() != 'y':
        logger.info("Backfill annulé")
        return
    
    # Statistiques globales
    stats = {
        'periods_processed': 0,
        'segments_extracted': 0,
        'websites_extracted': 0,
        'errors': 0,
        'start_time': datetime.now()
    }
    
    # Traiter par batch
    for i in range(0, len(periods), batch_size):
        batch = periods[i:i + batch_size]
        logger.info(f"\nBATCH {i//batch_size + 1}/{(len(periods) + batch_size - 1)//batch_size}")
        
        for period in batch:
            try:
                logger.info(f"\nPériode: {period['start_date'][:7]}")
                
                # Extraction des segments
                segment_stats = extract_and_save_segments(
                    api_client=api_client,
                    period=period,
                    limit=limit_segments
                )
                stats['segments_extracted'] += segment_stats['success']
                
                # Extraction des sites web
                website_stats = extract_and_save_websites(
                    api_client=api_client,
                    period=period
                )
                stats['websites_extracted'] += website_stats['success']
                
                stats['periods_processed'] += 1
                
                # Pause entre les périodes
                logger.info(f"   Pause de 5 secondes...")
                time.sleep(5)
                
            except Exception as e:
                logger.error(f"Erreur pour la période {period['start_date'][:7]}: {e}")
                stats['errors'] += 1
                continue
        
        # Pause plus longue entre les batchs
        if i + batch_size < len(periods):
            logger.info(f"\nPause de 30 secondes entre les batchs...")
            time.sleep(30)
    
    # Résumé final
    duration = (datetime.now() - stats['start_time']).total_seconds() / 60
    
    logger.info("\n" + "="*50)
    logger.info("BACKFILL TERMINÉ")
    logger.info(f"   - Durée: {duration:.1f} minutes")
    logger.info(f"   - Périodes traitées: {stats['periods_processed']}")
    logger.info(f"   - Segments extraits: {stats['segments_extracted']}")
    logger.info(f"   - Sites web extraits: {stats['websites_extracted']}")
    logger.info(f"   - Erreurs: {stats['errors']}")
    
    logger.info(f"\nFichiers créés dans le dossier 'data/'")
    logger.info(f"   - Utilisez: python scripts/upload_to_bigquery.py --type all")
    
    return stats


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Backfill historique des données SimilarWeb')
    parser.add_argument('--year', type=int, default=2024, 
                        help='Année de début (2024 ou 2025)')
    parser.add_argument('--end-month', type=str, 
                        help='Mois de fin au format YYYY-MM')
    parser.add_argument('--limit-segments', type=int, 
                        help='Limiter le nombre de segments')
    parser.add_argument('--batch-size', type=int, default=3,
                        help='Nombre de mois par batch')
    
    args = parser.parse_args()
    
    run_backfill(
        start_year=args.year,
        end_month=args.end_month,
        limit_segments=args.limit_segments,
        batch_size=args.batch_size
    )