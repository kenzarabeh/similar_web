"""
Script d'extraction corrigé pour SimilarWeb - Gère les dates correctement
"""
import sys
import os
import json
import logging
from datetime import datetime, timedelta
from typing import Dict, List

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


def convert_date_range_to_months(start_date_str: str, end_date_str: str) -> List[str]:
    """
    Convertit une plage de dates en liste de mois
    
    Args:
        start_date_str: Date de début (YYYY-MM-DD)
        end_date_str: Date de fin (YYYY-MM-DD)
        
    Returns:
        Liste des mois au format YYYY-MM
    """
    start_date = datetime.strptime(start_date_str, '%Y-%m-%d')
    end_date = datetime.strptime(end_date_str, '%Y-%m-%d')
    
    months = []
    current = start_date.replace(day=1)  # Premier jour du mois
    
    while current <= end_date:
        months.append(current.strftime('%Y-%m'))
        
        # Passer au mois suivant
        if current.month == 12:
            current = current.replace(year=current.year + 1, month=1)
        else:
            current = current.replace(month=current.month + 1)
    
    return list(set(months))  # Éliminer les doublons


def extract_segments_for_period(api_client: SimilarWebAPI, start_date_str: str, 
                               end_date_str: str, granularity: str = 'monthly', 
                               limit: int = None) -> List[Dict]:
    """
    Extrait les segments pour une période donnée
    
    Args:
        api_client: Client API
        start_date_str: Date de début (YYYY-MM-DD)
        end_date_str: Date de fin (YYYY-MM-DD)
        granularity: 'monthly' ou 'daily'
        limit: Limite du nombre de segments
        
    Returns:
        Liste des données extraites
    """
    logger.info("=== EXTRACTION DES SEGMENTS ===")
    
    # Convertir les dates en mois
    months = convert_date_range_to_months(start_date_str, end_date_str)
    logger.info(f"Mois à extraire: {months}")
    
    all_results = []
    
    for month in months:
        logger.info(f"Extraction pour {month}")
        
        # Utiliser le format correct pour l'API
        segments_data = api_client.extract_all_segments(
            start_date=month,  # Format YYYY-MM
            end_date=month,    # Format YYYY-MM
            limit=limit,
            user_only=True
        )
        
        # Modifier la granularité si nécessaire
        if granularity == 'daily':
            # Pour chaque segment, refaire l'appel avec granularité quotidienne
            for segment in segments_data:
                if not segment.get('error'):
                    try:
                        daily_data = api_client.get_segment_data(
                            segment_id=segment['segment_id'],
                            start_date=month,
                            end_date=month,
                            granularity='daily'
                        )
                        if daily_data:
                            segment['data'] = daily_data
                    except Exception as e:
                        logger.warning(f"Granularité quotidienne non disponible pour {segment['segment_name']}: {e}")
        
        all_results.extend(segments_data)
    
    # Statistiques
    stats = {
        'total': len(all_results),
        'success': len([s for s in all_results if not s.get('error')]),
        'errors': len([s for s in all_results if s.get('error')])
    }
    
    logger.info(f"Segments: {stats['success']}/{stats['total']} extraits avec succès")
    
    # Sauvegarde
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    filename = f"segments_extraction_{timestamp}.json"
    save_results_to_json(all_results, filename)
    
    return all_results


def extract_websites_for_period(api_client: SimilarWebAPI, start_date_str: str, 
                                end_date_str: str, granularity: str = 'monthly',
                                domains: List[str] = None) -> List[Dict]:
    """
    Extrait les websites pour une période donnée
    
    Args:
        api_client: Client API
        start_date_str: Date de début (YYYY-MM-DD)
        end_date_str: Date de fin (YYYY-MM-DD)
        granularity: 'monthly' ou 'daily'
        domains: Liste des domaines
        
    Returns:
        Liste des données extraites
    """
    logger.info("Extraction des sites webs")
    
    # Charger les domaines
    if domains is None:
        try:
            from scripts.manage_websites import load_websites
            domains = load_websites()
            logger.info(f"{len(domains)} sites web chargés")
        except:
            domains = TARGET_DOMAINS
            logger.warning(f"Utilisation de la liste par défaut: {len(domains)} sites")
    
    # Convertir les dates en mois
    months = convert_date_range_to_months(start_date_str, end_date_str)
    
    all_results = []
    
    for month in months:
        logger.info(f"Extraction websites pour {month}")
        
        # Extraire avec le format correct
        websites_data = api_client.extract_all_websites(
            domains=domains,
            start_date=month,  # Format YYYY-MM
            end_date=month     # Format YYYY-MM
        )
        
        # Modifier la granularité si nécessaire
        if granularity == 'daily':
            for website in websites_data:
                domain = website['domain']
                try:
                    # Refaire les appels avec granularité quotidienne
                    for metric_name, endpoint in WEBSITE_METRICS_ENDPOINTS.items():
                        daily_data = api_client.get_website_metric(
                            domain=domain,
                            metric_endpoint=endpoint,
                            start_date=month,
                            end_date=month,
                            granularity='daily'
                        )
                        if daily_data:
                            website['metrics'][metric_name] = daily_data
                except Exception as e:
                    logger.warning(f"Granularité quotidienne non disponible pour {domain}: {e}")
        
        all_results.extend(websites_data)
    
    # Statistiques
    stats = {
        'total': len(all_results),
        'success': len([w for w in all_results if any(w['metrics'].values())]),
        'errors': len([w for w in all_results if not any(w['metrics'].values())])
    }
    
    logger.info(f"Sites web: {stats['success']}/{stats['total']} extraits avec succès")
    
    # Sauvegarde
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    filename = f"websites_extraction_{timestamp}.json"
    save_results_to_json(all_results, filename)
    
    return all_results


def main():
    """Fonction principale corrigée"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Extraction SimilarWeb avec dates corrigées')
    parser.add_argument('--start-date', required=True, help='Date de début (YYYY-MM-DD)')
    parser.add_argument('--end-date', required=True, help='Date de fin (YYYY-MM-DD)')
    parser.add_argument('--granularity', choices=['monthly', 'daily'], default='monthly',
                       help='Granularité des données')
    parser.add_argument('--test', action='store_true', help='Mode test (limite à 1 segment)')
    parser.add_argument('--segments-only', action='store_true', help='Extraire seulement les segments')
    parser.add_argument('--websites-only', action='store_true', help='Extraire seulement les websites')
    
    args = parser.parse_args()
    
    logger.info(f"Extraction SimilarWeb")
    logger.info(f"Période: {args.start_date} à {args.end_date}")
    logger.info(f"Granularité: {args.granularity}")
    
    try:
        # Initialiser le client API
        api_client = SimilarWebAPI()
        
        results = {}
        
        # Extraction des segments
        if not args.websites_only:
            segments_data = extract_segments_for_period(
                api_client=api_client,
                start_date_str=args.start_date,
                end_date_str=args.end_date,
                granularity=args.granularity,
                limit=1 if args.test else None
            )
            results['segments'] = len(segments_data)
        
        # Extraction des websites
        if not args.segments_only:
            websites_data = extract_websites_for_period(
                api_client=api_client,
                start_date_str=args.start_date,
                end_date_str=args.end_date,
                granularity=args.granularity
            )
            results['websites'] = len(websites_data)
        
        # Résumé
        summary = {
            'extraction_timestamp': datetime.now().isoformat(),
            'period': f"{args.start_date} to {args.end_date}",
            'granularity': args.granularity,
            'results': results,
            'status': 'success'
        }
        
        save_results_to_json(summary, 'extraction_summary_latest.json')
        
        logger.info("Extraction terminée avec succès")
        print(json.dumps(summary, indent=2))
        
        return summary
        
    except Exception as e:
        logger.error(f"Erreur lors de l'extraction: {str(e)}")
        error_summary = {
            'extraction_timestamp': datetime.now().isoformat(),
            'status': 'error',
            'error': str(e)
        }
        print(json.dumps(error_summary, indent=2))
        raise


if __name__ == "__main__":
    main()