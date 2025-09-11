#!/usr/bin/env python3
"""
Script d'extraction quotidienne CORRIGÉ pour SimilarWeb
Permet une vraie extraction journalière avec granularité daily
"""
import sys
import os
import json
import logging
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
    Génère les périodes d'extraction selon la granularité
    
    Args:
        start_date: Date de début (YYYY-MM-DD)
        end_date: Date de fin (YYYY-MM-DD) 
        granularity: 'daily' ou 'monthly'
        
    Returns:
        Liste des périodes à extraire
    """
    periods = []
    
    if granularity == 'daily':
        # Extraction jour par jour
        current = datetime.strptime(start_date, '%Y-%m-%d')
        end = datetime.strptime(end_date, '%Y-%m-%d')
        
        while current <= end:
            periods.append({
                'start_date': current.strftime('%Y-%m-%d'),
                'end_date': current.strftime('%Y-%m-%d'),
                'api_format': current.strftime('%Y-%m-%d')  # Format complet pour l'API
            })
            current += timedelta(days=1)
            
    else:  # monthly
        # Extraction mois par mois
        current = datetime.strptime(start_date, '%Y-%m-%d')
        end = datetime.strptime(end_date, '%Y-%m-%d')
        
        while current <= end:
            # Premier et dernier jour du mois
            first_day = current.replace(day=1)
            if current.month == 12:
                last_day = current.replace(year=current.year + 1, month=1, day=1) - timedelta(days=1)
            else:
                last_day = current.replace(month=current.month + 1, day=1) - timedelta(days=1)
            
            periods.append({
                'start_date': first_day.strftime('%Y-%m-%d'),
                'end_date': min(last_day, end).strftime('%Y-%m-%d'),
                'api_format': current.strftime('%Y-%m')  # Format YYYY-MM pour API
            })
            
            # Passer au mois suivant
            if current.month == 12:
                current = current.replace(year=current.year + 1, month=1)
            else:
                current = current.replace(month=current.month + 1)
    
    return periods


def extract_segments_daily(api_client: SimilarWebAPI, periods: List[Dict], 
                          limit: int = None) -> List[Dict]:
    """
    Extrait les segments avec la granularité correcte
    """
    logger.info(f"=== EXTRACTION SEGMENTS ({len(periods)} périodes) ===")
    
    all_results = []
    
    for i, period in enumerate(periods):
        logger.info(f"Période {i+1}/{len(periods)}: {period['start_date']} → {period['end_date']}")
        
        # Utiliser le format API approprié
        segments_data = api_client.extract_all_segments(
            start_date=period['api_format'],
            end_date=period['api_format'], 
            limit=limit,
            user_only=True
        )
        
        # Ajouter l'information de période à chaque segment
        for segment in segments_data:
            segment['extraction_period'] = period
            segment['extraction_granularity'] = 'daily' if '-' in period['api_format'] and len(period['api_format']) > 7 else 'monthly'
        
        all_results.extend(segments_data)
        
        # Pause entre les périodes
        if i < len(periods) - 1:
            time.sleep(2)
    
    # Statistiques
    stats = {
        'total': len(all_results),
        'success': len([s for s in all_results if not s.get('error')]),
        'errors': len([s for s in all_results if s.get('error')])
    }
    
    logger.info(f"Segments: {stats['success']}/{stats['total']} extraits avec succès")
    
    return all_results


def extract_websites_daily(api_client: SimilarWebAPI, periods: List[Dict],
                          domains: List[str] = None) -> List[Dict]:
    """
    Extrait les websites avec la granularité correcte
    """
    logger.info(f"=== EXTRACTION WEBSITES ({len(periods)} périodes) ===")
    
    # Charger les domaines
    if domains is None:
        try:
            from scripts.manage_websites import load_websites
            domains = load_websites()
            logger.info(f"{len(domains)} sites web chargés")
        except:
            domains = TARGET_DOMAINS
            logger.warning(f"Utilisation de la liste par défaut: {len(domains)} sites")
    
    all_results = []
    
    for i, period in enumerate(periods):
        logger.info(f"Période {i+1}/{len(periods)}: {period['start_date']} → {period['end_date']}")
        
        # Utiliser le format API approprié
        websites_data = api_client.extract_all_websites(
            domains=domains,
            start_date=period['api_format'],
            end_date=period['api_format']
        )
        
        # Ajouter l'information de période à chaque website
        for website in websites_data:
            website['extraction_period'] = period
            website['extraction_granularity'] = 'daily' if '-' in period['api_format'] and len(period['api_format']) > 7 else 'monthly'
        
        all_results.extend(websites_data)
        
        # Pause entre les périodes
        if i < len(periods) - 1:
            time.sleep(2)
    
    # Statistiques
    stats = {
        'total': len(all_results),
        'success': len([w for w in all_results if any(w.get('metrics', {}).values())]),
        'errors': len([w for w in all_results if not any(w.get('metrics', {}).values())])
    }
    
    logger.info(f"Websites: {stats['success']}/{stats['total']} extraits avec succès")
    
    return all_results


def extract_for_automation(days_back: int = 7) -> Dict:
    """
    Fonction spécifique pour l'automatisation quotidienne
    Extrait les N derniers jours pour rattraper les données manquantes
    
    Args:
        days_back: Nombre de jours en arrière à extraire
        
    Returns:
        Résumé de l'extraction
    """
    logger.info(f"=== EXTRACTION AUTOMATISÉE (J-{days_back} à aujourd'hui) ===")
    
    # Calculer les dates
    end_date = datetime.now().date()
    start_date = end_date - timedelta(days=days_back)
    
    # SimilarWeb a un délai, donc exclure les 2 derniers jours
    end_date = end_date - timedelta(days=2)
    
    logger.info(f"Période: {start_date} → {end_date}")
    
    # Générer les périodes (toujours daily pour l'automation)
    periods = get_date_range_for_extraction(
        start_date.strftime('%Y-%m-%d'),
        end_date.strftime('%Y-%m-%d'),
        'daily'
    )
    
    if not periods:
        logger.warning("Aucune période à extraire")
        return {'status': 'no_data', 'periods': 0}
    
    logger.info(f"{len(periods)} jours à extraire")
    
    api_client = SimilarWebAPI()
    results = {}
    
    try:
        # Extraction segments
        segments_data = extract_segments_daily(api_client, periods)
        if segments_data:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            filename = f"segments_daily_auto_{timestamp}.json"
            save_results_to_json(segments_data, filename)
            results['segments'] = {
                'count': len(segments_data),
                'success': len([s for s in segments_data if not s.get('error')]),
                'file': filename
            }
        
        # Extraction websites
        websites_data = extract_websites_daily(api_client, periods)
        if websites_data:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            filename = f"websites_daily_auto_{timestamp}.json"
            save_results_to_json(websites_data, filename)
            results['websites'] = {
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
            'periods_count': len(periods),
            'granularity': 'daily',
            'results': results
        }
        
        save_results_to_json(summary, 'daily_extraction_summary_latest.json')
        
        logger.info("=== EXTRACTION AUTOMATISÉE TERMINÉE ===")
        logger.info(f"Segments: {results.get('segments', {}).get('success', 0)} extraits")
        logger.info(f"Websites: {results.get('websites', {}).get('success', 0)} extraits")
        
        return summary
        
    except Exception as e:
        logger.error(f"Erreur lors de l'extraction automatisée: {e}")
        error_summary = {
            'status': 'error',
            'extraction_date': datetime.now().isoformat(),
            'error': str(e)
        }
        save_results_to_json(error_summary, 'daily_extraction_error.json')
        return error_summary


import time

def main():
    """Fonction principale corrigée"""
    parser = argparse.ArgumentParser(description='Extraction SimilarWeb avec vraie granularité quotidienne')
    parser.add_argument('--start-date', help='Date de début (YYYY-MM-DD)')
    parser.add_argument('--end-date', help='Date de fin (YYYY-MM-DD)')
    parser.add_argument('--granularity', choices=['daily', 'monthly'], default='daily',
                       help='Granularité des données')
    parser.add_argument('--auto', action='store_true', 
                       help='Mode automatisation (7 derniers jours)')
    parser.add_argument('--days-back', type=int, default=7,
                       help='Nombre de jours en arrière pour mode auto')
    parser.add_argument('--test', action='store_true', 
                       help='Mode test (limite à 1 segment)')
    parser.add_argument('--segments-only', action='store_true', 
                       help='Extraire seulement les segments')
    parser.add_argument('--websites-only', action='store_true', 
                       help='Extraire seulement les websites')
    
    args = parser.parse_args()
    
    # Mode automatisation pour Cloud Run
    if args.auto:
        result = extract_for_automation(args.days_back)
        print(json.dumps(result, indent=2))
        return result
    
    # Mode manuel avec dates spécifiques
    if not args.start_date or not args.end_date:
        logger.error("--start-date et --end-date requis en mode manuel")
        return
    
    logger.info(f"Extraction SimilarWeb")
    logger.info(f"Période: {args.start_date} → {args.end_date}")
    logger.info(f"Granularité: {args.granularity}")
    
    try:
        # Générer les périodes selon la granularité
        periods = get_date_range_for_extraction(
            args.start_date, 
            args.end_date, 
            args.granularity
        )
        
        logger.info(f"{len(periods)} périodes à extraire")
        
        api_client = SimilarWebAPI()
        results = {}
        
        # Extraction des segments
        if not args.websites_only:
            segments_data = extract_segments_daily(
                api_client=api_client,
                periods=periods,
                limit=1 if args.test else None
            )
            
            if segments_data:
                timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                filename = f"segments_{args.granularity}_{timestamp}.json"
                save_results_to_json(segments_data, filename)
                results['segments'] = len(segments_data)
        
        # Extraction des websites
        if not args.segments_only:
            websites_data = extract_websites_daily(
                api_client=api_client,
                periods=periods
            )
            
            if websites_data:
                timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                filename = f"websites_{args.granularity}_{timestamp}.json"
                save_results_to_json(websites_data, filename)
                results['websites'] = len(websites_data)
        
        # Résumé
        summary = {
            'extraction_timestamp': datetime.now().isoformat(),
            'period': f"{args.start_date} to {args.end_date}",
            'granularity': args.granularity,
            'periods_processed': len(periods),
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