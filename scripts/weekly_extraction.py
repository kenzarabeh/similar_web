#!/usr/bin/env python3
"""
Script d'extraction hebdomadaire (WEEKLY) CORRIGÉ pour architecture 3 tables SimilarWeb
Utilise les méthodes existantes de similarweb_api.py
"""
import sys
import os
import json
import logging
import time
from datetime import datetime, timedelta
from typing import Dict, List, Optional
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


def get_date_range_for_extraction(start_date: str, end_date: str, granularity: str) -> List[Dict]:
    """
    Génère les périodes d'extraction selon la granularité - Format API YYYY-MM
    
    Args:
        start_date: Date de début (YYYY-MM-DD)
        end_date: Date de fin (YYYY-MM-DD) 
        granularity: 'weekly' ou 'monthly'
        
    Returns:
        Liste des périodes à extraire
    """
    periods = []
    
    if granularity == 'weekly':
        # Pour weekly, l'API attend le format YYYY-MM
        # On extrait par mois, l'API retournera les semaines automatiquement
        current = datetime.strptime(start_date, '%Y-%m-%d')
        end = datetime.strptime(end_date, '%Y-%m-%d')
        
        # Extraire tous les mois couverts par la période
        months_set = set()
        temp_date = current
        while temp_date <= end:
            months_set.add(temp_date.strftime('%Y-%m'))
            # Passer au mois suivant
            if temp_date.month == 12:
                temp_date = temp_date.replace(year=temp_date.year + 1, month=1, day=1)
            else:
                temp_date = temp_date.replace(month=temp_date.month + 1, day=1)
        
        # Créer une période par mois
        for month_str in sorted(months_set):
            year_month = datetime.strptime(month_str, '%Y-%m')
            
            periods.append({
                'start_date': month_str,  # Format YYYY-MM pour l'API
                'end_date': month_str,    # Format YYYY-MM pour l'API
                'api_format': month_str,
                'granularity': 'weekly',
                'month': month_str
            })
            
    else:  # monthly
        # Extraction mois par mois
        current = datetime.strptime(start_date, '%Y-%m-%d')
        end = datetime.strptime(end_date, '%Y-%m-%d')
        
        while current <= end:
            month_str = current.strftime('%Y-%m')
            
            periods.append({
                'start_date': month_str,
                'end_date': month_str,
                'api_format': month_str,
                'granularity': 'monthly',
                'month': month_str
            })
            
            # Passer au mois suivant
            if current.month == 12:
                current = current.replace(year=current.year + 1, month=1)
            else:
                current = current.replace(month=current.month + 1)
    
    return periods


def extract_segments_weekly_three_tables(api_client: SimilarWebAPI, weekly_periods: List[Dict], 
                                        monthly_periods: List[Dict], limit: int = None) -> Dict:
    """
    Extraction segments selon l'architecture 3 tables avec granularité WEEKLY
    Utilise les méthodes existantes de similarweb_api.py
    
    Args:
        api_client: Client API SimilarWeb
        weekly_periods: Périodes weekly pour segments_weekly (SANS unique_visitors)
        monthly_periods: Périodes monthly pour segments_unique_visitors (AVEC unique_visitors)
        limit: Limite de segments à traiter
        
    Returns:
        Dictionnaire avec les 2 types de données segments
    """
    logger.info(f"=== EXTRACTION SEGMENTS - ARCHITECTURE 3 TABLES (WEEKLY) ===")
    logger.info("Note: unique_visitors disponible uniquement en granularité monthly")
    
    results = {
        'segments_weekly': [],
        'segments_unique_visitors': []
    }
    
    # 1. Extraction segments_weekly (weekly, SANS unique_visitors)
    logger.info(f"1. SEGMENTS WEEKLY ({len(weekly_periods)} périodes)")
    logger.info("Métriques: visits, bounce-rate, pages-per-visit, visit-duration, page-views, traffic-share")
    
    for i, period in enumerate(weekly_periods):
        logger.info(f"Période {i+1}/{len(weekly_periods)}: Mois {period['month']} (granularité weekly)")
        
        # Utiliser extract_segments_daily_architecture avec granularity='weekly'
        segments_weekly_data = api_client.extract_segments_daily_architecture(
            start_date=period['api_format'],  # Format YYYY-MM
            end_date=period['api_format'],    # Format YYYY-MM
            limit=limit,
            user_only=True,
            granularity='weekly'  # Granularité weekly
        )
        
        # Ajouter l'information de période à chaque segment
        for segment in segments_weekly_data:
            segment['extraction_period'] = period
            segment['table_type'] = 'segments_weekly'  # Override
        
        results['segments_weekly'].extend(segments_weekly_data)
        
        # Pause entre les périodes
        if i < len(weekly_periods) - 1:
            time.sleep(2)
    
    # 2. Extraction segments_unique_visitors (monthly, SEULEMENT unique_visitors)
    logger.info(f"2. SEGMENTS UNIQUE_VISITORS ({len(monthly_periods)} mois)")
    logger.info("Métrique: unique-visitors uniquement (granularité monthly)")
    
    for i, period in enumerate(monthly_periods):
        logger.info(f"Mois {i+1}/{len(monthly_periods)}: {period['month']}")
        
        # Utiliser extract_segments_unique_visitors_architecture
        segments_uv_data = api_client.extract_segments_unique_visitors_architecture(
            start_date=period['api_format'],  # Format YYYY-MM
            end_date=period['api_format'],    # Format YYYY-MM
            limit=limit,
            user_only=True
        )
        
        # Ajouter l'information de période à chaque segment
        for segment in segments_uv_data:
            segment['extraction_period'] = period
        
        results['segments_unique_visitors'].extend(segments_uv_data)
        
        # Pause entre les périodes
        if i < len(monthly_periods) - 1:
            time.sleep(2)
    
    # Statistiques
    weekly_stats = {
        'total': len(results['segments_weekly']),
        'success': len([s for s in results['segments_weekly'] if not s.get('error')]),
        'errors': len([s for s in results['segments_weekly'] if s.get('error')])
    }
    
    uv_stats = {
        'total': len(results['segments_unique_visitors']),
        'success': len([s for s in results['segments_unique_visitors'] if not s.get('error')]),
        'errors': len([s for s in results['segments_unique_visitors'] if s.get('error')])
    }
    
    logger.info(f"Segments weekly: {weekly_stats['success']}/{weekly_stats['total']} extraits")
    logger.info(f"Segments unique_visitors: {uv_stats['success']}/{uv_stats['total']} extraits")
    
    return results


def extract_websites_weekly_three_tables(api_client: SimilarWebAPI, weekly_periods: List[Dict],
                                        domains: List[str] = None) -> List[Dict]:
    """
    Extraction websites weekly AVEC unique_visitors - Architecture 3 tables
    Utilise extract_websites_daily_architecture avec granularity='weekly'
    
    Args:
        api_client: Client API SimilarWeb
        weekly_periods: Périodes weekly
        domains: Liste des domaines
        
    Returns:
        Liste des websites weekly
    """
    logger.info(f"=== EXTRACTION WEBSITES WEEKLY ({len(weekly_periods)} périodes) ===")
    
    # Charger les domaines
    if domains is None:
        try:
            from scripts.manage_websites import load_websites
            domains = load_websites()
            logger.info(f"{len(domains)} sites web chargés")
        except Exception as e:
            logger.warning(f"Erreur chargement websites: {e}")
            domains = TARGET_DOMAINS
            logger.warning(f"Utilisation de la liste par défaut: {len(domains)} sites")
    
    all_results = []
    
    for i, period in enumerate(weekly_periods):
        logger.info(f"Période {i+1}/{len(weekly_periods)}: Mois {period['month']} (granularité weekly)")
        
        # Utiliser extract_websites_daily_architecture avec granularity='weekly'
        websites_data = api_client.extract_websites_daily_architecture(
            domains=domains,
            start_date=period['api_format'],  # Format YYYY-MM
            end_date=period['api_format'],    # Format YYYY-MM
            granularity='weekly'  # Granularité weekly
        )
        
        # Ajouter l'information de période et override table_type
        for website in websites_data:
            website['extraction_period'] = period
            website['table_type'] = 'websites_weekly'  # Override
        
        all_results.extend(websites_data)
        
        # Pause entre les périodes
        if i < len(weekly_periods) - 1:
            time.sleep(2)
    
    # Statistiques
    stats = {
        'total': len(all_results),
        'success': len([w for w in all_results if any(w.get('metrics', {}).values())]),
        'errors': len([w for w in all_results if not any(w.get('metrics', {}).values())])
    }
    
    logger.info(f"Websites: {stats['success']}/{stats['total']} extraits avec succès")
    
    return all_results


def extract_for_automation_three_tables(weeks_back: int = 4) -> Dict:
    """
    Fonction pour l'automatisation hebdomadaire - Architecture 3 tables
    Extrait segments weekly + segments monthly + websites weekly
    
    Args:
        weeks_back: Nombre de semaines en arrière à extraire
        
    Returns:
        Résumé de l'extraction
    """
    logger.info(f"=== EXTRACTION AUTOMATISÉE 3 TABLES WEEKLY ({weeks_back} semaines en arrière) ===")
    
    # Calculer les dates
    end_date = datetime.now().date()
    start_date = end_date - timedelta(weeks=weeks_back)
    
    # SimilarWeb a un délai, donc exclure les 2-3 derniers jours
    end_date = end_date - timedelta(days=3)
    
    logger.info(f"Période: {start_date} → {end_date}")
    
    # Générer les périodes weekly et monthly
    weekly_periods = get_date_range_for_extraction(
        start_date.strftime('%Y-%m-%d'),
        end_date.strftime('%Y-%m-%d'),
        'weekly'
    )
    
    # Pour monthly, prendre seulement les mois concernés
    monthly_periods = get_date_range_for_extraction(
        start_date.strftime('%Y-%m-%d'),
        end_date.strftime('%Y-%m-%d'),
        'monthly'
    )
    
    if not weekly_periods:
        logger.warning("Aucune période weekly à extraire")
        return {'status': 'no_data', 'periods': 0}
    
    logger.info(f"{len(weekly_periods)} périodes weekly à extraire")
    logger.info(f"{len(monthly_periods)} mois monthly à extraire")
    
    api_client = SimilarWebAPI()
    results = {}
    
    try:
        # 1. Extraction segments (weekly + unique_visitors)
        segments_results = extract_segments_weekly_three_tables(
            api_client, weekly_periods, monthly_periods
        )
        
        # Sauvegarder segments_weekly
        if segments_results['segments_weekly']:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            filename = f"segments_weekly_auto_{timestamp}.json"
            save_results_to_json(segments_results['segments_weekly'], filename)
            results['segments_weekly'] = {
                'count': len(segments_results['segments_weekly']),
                'success': len([s for s in segments_results['segments_weekly'] if not s.get('error')]),
                'file': filename
            }
        
        # Sauvegarder segments_unique_visitors
        if segments_results['segments_unique_visitors']:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            filename = f"segments_unique_visitors_auto_{timestamp}.json"
            save_results_to_json(segments_results['segments_unique_visitors'], filename)
            results['segments_unique_visitors'] = {
                'count': len(segments_results['segments_unique_visitors']),
                'success': len([s for s in segments_results['segments_unique_visitors'] if not s.get('error')]),
                'file': filename
            }
        
        # 2. Extraction websites weekly
        websites_data = extract_websites_weekly_three_tables(api_client, weekly_periods)
        if websites_data:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            filename = f"websites_weekly_auto_{timestamp}.json"
            save_results_to_json(websites_data, filename)
            results['websites_weekly'] = {
                'count': len(websites_data),
                'success': len([w for w in websites_data if any(w.get('metrics', {}).values())]),
                'file': filename
            }
        
        # Résumé
        summary = {
            'status': 'success',
            'extraction_date': datetime.now().isoformat(),
            'period_start': start_date.isoformat(),
            'period_end': end_date.isoformat(),
            'weekly_periods_count': len(weekly_periods),
            'monthly_periods_count': len(monthly_periods),
            'architecture': '3_tables',
            'granularity': 'weekly',
            'results': results
        }
        
        save_results_to_json(summary, 'weekly_extraction_summary_latest.json')
        
        logger.info("=== EXTRACTION AUTOMATISÉE 3 TABLES WEEKLY TERMINÉE ===")
        logger.info(f"Segments weekly: {results.get('segments_weekly', {}).get('success', 0)} extraits")
        logger.info(f"Segments unique_visitors: {results.get('segments_unique_visitors', {}).get('success', 0)} extraits")
        logger.info(f"Websites weekly: {results.get('websites_weekly', {}).get('success', 0)} extraits")
        
        return summary
        
    except Exception as e:
        logger.error(f"Erreur lors de l'extraction automatisée: {e}")
        error_summary = {
            'status': 'error',
            'extraction_date': datetime.now().isoformat(),
            'architecture': '3_tables',
            'granularity': 'weekly',
            'error': str(e)
        }
        save_results_to_json(error_summary, 'weekly_extraction_error.json')
        return error_summary


def main():
    """Fonction principale pour architecture 3 tables avec granularité WEEKLY"""
    parser = argparse.ArgumentParser(
        description='Extraction SimilarWeb - Architecture 3 tables (WEEKLY)',
        epilog='Note: utilise les méthodes existantes avec granularity=weekly'
    )
    parser.add_argument('--start-date', help='Date de début (YYYY-MM-DD)')
    parser.add_argument('--end-date', help='Date de fin (YYYY-MM-DD)')
    parser.add_argument('--auto', action='store_true', 
                       help='Mode automatisation (4 dernières semaines)')
    parser.add_argument('--weeks-back', type=int, default=4,
                       help='Nombre de semaines en arrière pour mode auto')
    parser.add_argument('--test', action='store_true', 
                       help='Mode test (limite à 1 segment)')
    parser.add_argument('--segments-only', action='store_true', 
                       help='Extraire seulement les segments')
    parser.add_argument('--websites-only', action='store_true', 
                       help='Extraire seulement les websites')
    
    args = parser.parse_args()
    
    # Mode automatisation pour Cloud Run
    if args.auto:
        result = extract_for_automation_three_tables(args.weeks_back)
        print(json.dumps(result, indent=2))
        return result
    
    # Mode manuel avec dates spécifiques
    if not args.start_date or not args.end_date:
        logger.error("--start-date et --end-date requis en mode manuel")
        return
    
    logger.info(f"Extraction SimilarWeb - Architecture 3 tables (WEEKLY)")
    logger.info(f"Période: {args.start_date} → {args.end_date}")
    
    try:
        # Générer les périodes weekly et monthly
        weekly_periods = get_date_range_for_extraction(
            args.start_date, 
            args.end_date, 
            'weekly'
        )
        
        monthly_periods = get_date_range_for_extraction(
            args.start_date, 
            args.end_date, 
            'monthly'
        )
        
        logger.info(f"{len(weekly_periods)} périodes weekly à extraire")
        logger.info(f"{len(monthly_periods)} périodes monthly à extraire")
        
        api_client = SimilarWebAPI()
        results = {}
        
        # Extraction des segments (2 types)
        if not args.websites_only:
            segments_results = extract_segments_weekly_three_tables(
                api_client=api_client,
                weekly_periods=weekly_periods,
                monthly_periods=monthly_periods,
                limit=1 if args.test else None
            )
            
            # Sauvegarder segments_weekly
            if segments_results['segments_weekly']:
                timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                filename = f"segments_weekly_{timestamp}.json"
                save_results_to_json(segments_results['segments_weekly'], filename)
                results['segments_weekly'] = len(segments_results['segments_weekly'])
            
            # Sauvegarder segments_unique_visitors
            if segments_results['segments_unique_visitors']:
                timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                filename = f"segments_unique_visitors_{timestamp}.json"
                save_results_to_json(segments_results['segments_unique_visitors'], filename)
                results['segments_unique_visitors'] = len(segments_results['segments_unique_visitors'])
        
        # Extraction des websites (weekly)
        if not args.segments_only:
            websites_data = extract_websites_weekly_three_tables(
                api_client=api_client,
                weekly_periods=weekly_periods
            )
            
            if websites_data:
                timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                filename = f"websites_weekly_{timestamp}.json"
                save_results_to_json(websites_data, filename)
                results['websites_weekly'] = len(websites_data)
        
        # Résumé
        summary = {
            'extraction_timestamp': datetime.now().isoformat(),
            'period': f"{args.start_date} to {args.end_date}",
            'architecture': '3_tables',
            'granularity': 'weekly',
            'weekly_periods_processed': len(weekly_periods),
            'monthly_periods_processed': len(monthly_periods),
            'results': results,
            'status': 'success'
        }
        
        save_results_to_json(summary, 'extraction_summary_latest.json')
        
        logger.info("Extraction terminée avec succès - Architecture 3 tables (WEEKLY)")
        print(json.dumps(summary, indent=2))
        
        return summary
        
    except Exception as e:
        logger.error(f"Erreur lors de l'extraction: {str(e)}")
        error_summary = {
            'extraction_timestamp': datetime.now().isoformat(),
            'architecture': '3_tables',
            'granularity': 'weekly',
            'status': 'error',
            'error': str(e)
        }
        print(json.dumps(error_summary, indent=2))
        raise


if __name__ == "__main__":
    main()