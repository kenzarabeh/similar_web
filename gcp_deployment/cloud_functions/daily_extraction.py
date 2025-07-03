"""
Script d'extraction quotidienne des données SimilarWeb
Ce script sera adapté pour Cloud Functions dans la phase de déploiement GCP
"""
import sys
import os
import json
import logging
from datetime import datetime, timedelta
from typing import Dict, List

# Ajouter le chemin parent pour importer les modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import *
from similarweb_api import SimilarWebAPI, save_results_to_json

# Configuration du logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def get_extraction_period(lookback_days: int = 30) -> Dict[str, str]:
    """
    Détermine la période d'extraction basée sur la date actuelle
    
    Args:
        lookback_days: Nombre de jours en arrière pour l'extraction
        
    Returns:
        Dictionnaire avec start_date et end_date au format YYYY-MM
    """
    today = datetime.now()
    
    # Pour une extraction mensuelle, on prend le mois précédent
    if lookback_days >= 30:
        # Dernier jour du mois précédent
        last_day_prev_month = today.replace(day=1) - timedelta(days=1)
        # Premier jour du mois précédent
        first_day_prev_month = last_day_prev_month.replace(day=1)
        
        return {
            'start_date': first_day_prev_month.strftime('%Y-%m'),
            'end_date': last_day_prev_month.strftime('%Y-%m')
        }
    else:
        # Pour une extraction plus courte, on utilise la période spécifiée
        start_date = today - timedelta(days=lookback_days)
        return {
            'start_date': start_date.strftime('%Y-%m'),
            'end_date': today.strftime('%Y-%m')
        }


def extract_and_save_segments(api_client: SimilarWebAPI, period: Dict[str, str], 
                            limit: int = None) -> Dict:
    """
    Extrait et sauvegarde les données des segments
    
    Args:
        api_client: Instance du client API
        period: Dictionnaire avec start_date et end_date
        limit: Nombre maximum de segments à traiter
        
    Returns:
        Statistiques de l'extraction
    """
    logger.info("=== EXTRACTION DES SEGMENTS ===")
    
    # Extraction des données
    segments_data = api_client.extract_all_segments(
        start_date=period['start_date'],
        end_date=period['end_date'],
        limit=limit
    )
    
    # Statistiques
    stats = {
        'total': len(segments_data),
        'success': len([s for s in segments_data if not s.get('error')]),
        'errors': len([s for s in segments_data if s.get('error')])
    }
    
    # Sauvegarde avec timestamp
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    filename = f"segments_extraction_{timestamp}.json"
    save_results_to_json(segments_data, filename)
    
    # Sauvegarder dans BigQuery si on est dans Cloud Functions
    if os.environ.get('FUNCTION_NAME') or os.environ.get('GCP_PROJECT_ID'):
        try:
            from bigquery_utils import save_segments_to_bigquery
            project_id = os.environ.get('GCP_PROJECT_ID', GCP_PROJECT_ID)
            rows_inserted = save_segments_to_bigquery(segments_data, project_id)
            logger.info(f"✅ {rows_inserted} lignes insérées dans BigQuery")
        except Exception as e:
            logger.error(f"❌ Erreur BigQuery: {str(e)}")
    
    logger.info(f"📊 Segments: {stats['success']}/{stats['total']} extraits avec succès")
    
    return stats


def extract_and_save_websites(api_client: SimilarWebAPI, period: Dict[str, str], 
                            domains: List[str] = None) -> Dict:
    """
    Extrait et sauvegarde les données des sites web
    
    Args:
        api_client: Instance du client API
        period: Dictionnaire avec start_date et end_date
        domains: Liste des domaines (utilise TARGET_DOMAINS par défaut)
        
    Returns:
        Statistiques de l'extraction
    """
    logger.info("=== EXTRACTION DES SITES WEB ===")
    
    if domains is None:
        domains = TARGET_DOMAINS
    
    # Extraction des données
    websites_data = api_client.extract_all_websites(
        domains=domains,
        start_date=period['start_date'],
        end_date=period['end_date']
    )
    
    # Statistiques
    stats = {
        'total': len(websites_data),
        'success': len([w for w in websites_data if any(w['metrics'].values())]),
        'errors': len([w for w in websites_data if not any(w['metrics'].values())])
    }
    
    # Sauvegarde avec timestamp
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    filename = f"websites_extraction_{timestamp}.json"
    save_results_to_json(websites_data, filename)
    
    # Sauvegarder dans BigQuery si on est dans Cloud Functions
    if os.environ.get('FUNCTION_NAME') or os.environ.get('GCP_PROJECT_ID'):
        try:
            from bigquery_utils import save_websites_to_bigquery
            project_id = os.environ.get('GCP_PROJECT_ID', GCP_PROJECT_ID)
            rows_inserted = save_websites_to_bigquery(websites_data, project_id)
            logger.info(f"✅ {rows_inserted} lignes insérées dans BigQuery")
        except Exception as e:
            logger.error(f"❌ Erreur BigQuery: {str(e)}")
    
    logger.info(f"🌐 Sites web: {stats['success']}/{stats['total']} extraits avec succès")
    
    return stats


def create_extraction_summary(segments_stats: Dict, websites_stats: Dict, 
                            period: Dict[str, str]) -> Dict:
    """
    Crée un résumé de l'extraction pour logging et monitoring
    
    Args:
        segments_stats: Statistiques des segments
        websites_stats: Statistiques des sites web
        period: Période d'extraction
        
    Returns:
        Résumé complet de l'extraction
    """
    return {
        'extraction_timestamp': datetime.now().isoformat(),
        'period': period,
        'segments': segments_stats,
        'websites': websites_stats,
        'total_api_calls': segments_stats['total'] * 2 + websites_stats['total'] * 6,
        'status': 'success' if segments_stats['errors'] == 0 and websites_stats['errors'] == 0 else 'partial_success'
    }


def main(event=None, context=None):
    """
    Fonction principale d'extraction
    Compatible avec Cloud Functions (event, context) et exécution locale
    
    Args:
        event: Event Cloud Functions (optionnel)
        context: Context Cloud Functions (optionnel)
        
    Returns:
        Résumé de l'extraction
    """
    logger.info("🚀 Démarrage de l'extraction quotidienne SimilarWeb")
    
    try:
        # Déterminer la période d'extraction
        period = get_extraction_period()
        logger.info(f"📅 Période d'extraction: {period['start_date']} à {period['end_date']}")
        
        # Initialiser le client API
        api_client = SimilarWebAPI()
        
        # Extraction des segments (limite à 10 pour les tests)
        segments_stats = extract_and_save_segments(
            api_client=api_client,
            period=period,
            limit=10 if event and event.get('test_mode') else None
        )
        
        # Extraction des sites web
        websites_stats = extract_and_save_websites(
            api_client=api_client,
            period=period
        )
        
        # Créer le résumé
        summary = create_extraction_summary(segments_stats, websites_stats, period)
        
        # Sauvegarder le résumé
        save_results_to_json(summary, 'extraction_summary_latest.json')
        
        logger.info("✅ Extraction terminée avec succès!")
        logger.info(f"📊 Total API calls: {summary['total_api_calls']}")
        
        return summary
        
    except Exception as e:
        logger.error(f"❌ Erreur lors de l'extraction: {str(e)}")
        
        error_summary = {
            'extraction_timestamp': datetime.now().isoformat(),
            'status': 'error',
            'error': str(e)
        }
        
        save_results_to_json(error_summary, 'extraction_error_latest.json')
        
        # Re-lancer l'exception pour Cloud Functions
        raise


if __name__ == "__main__":
    # Pour les tests locaux
    import argparse
    
    parser = argparse.ArgumentParser(description='Extraction quotidienne SimilarWeb')
    parser.add_argument('--test', action='store_true', help='Mode test (limite à 10 segments)')
    parser.add_argument('--start-date', help='Date de début (YYYY-MM)')
    parser.add_argument('--end-date', help='Date de fin (YYYY-MM)')
    
    args = parser.parse_args()
    
    # Créer un event fictif pour les tests
    event = {'test_mode': args.test} if args.test else None
    
    # Modifier la période si spécifiée
    if args.start_date and args.end_date:
        # Monkey patch pour tester avec des dates spécifiques
        original_get_period = get_extraction_period
        def custom_get_period(lookback_days=30):
            return {
                'start_date': args.start_date,
                'end_date': args.end_date
            }
        get_extraction_period = custom_get_period
    
    # Exécuter l'extraction
    result = main(event)
    
    print(json.dumps(result, indent=2)) 