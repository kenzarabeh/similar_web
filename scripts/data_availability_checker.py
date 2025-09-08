"""
Script de vérification de la disponibilité des données
Vérifie les données manquantes et propose de les récupérer
"""
import sys
import os
from datetime import datetime, timedelta
import logging
from typing import List, Dict, Tuple
import argparse
from google.cloud import bigquery

# Ajouter le chemin parent pour importer les modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config.config import *
from scripts.similarweb_api import SimilarWebAPI
from scripts.daily_extraction import extract_and_save_segments, extract_and_save_websites
from scripts.manage_websites import load_websites

# Configuration du logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class DataAvailabilityChecker:
    """Classe pour vérifier la disponibilité des données"""
    
    def __init__(self, project_id: str = None):
        """
        Initialise le checker
        
        Args:
            project_id: ID du projet GCP
        """
        self.project_id = project_id or GCP_PROJECT_ID
        self.client = bigquery.Client(project=self.project_id)
        self.api_client = SimilarWebAPI()
    
    def check_data_completeness(self, start_date: str, end_date: str, 
                               check_type: str = 'both') -> Dict:
        """
        Vérifie la complétude des données pour une période
        
        Args:
            start_date: Date de début (YYYY-MM-DD)
            end_date: Date de fin (YYYY-MM-DD)
            check_type: 'segments', 'websites', or 'both'
            
        Returns:
            Rapport de complétude
        """
        report = {
            'period': f"{start_date} to {end_date}",
            'segments': {},
            'websites': {},
            'missing_dates': [],
            'summary': {}
        }
        
        # Générer la liste des dates attendues
        expected_dates = self._generate_expected_dates(start_date, end_date)
        
        if check_type in ['segments', 'both']:
            segments_data = self._check_segments_data(expected_dates)
            report['segments'] = segments_data
        
        if check_type in ['websites', 'both']:
            websites_data = self._check_websites_data(expected_dates)
            report['websites'] = websites_data
        
        # Identifier les dates manquantes
        missing_segments = set(expected_dates) - set(report['segments'].get('found_dates', []))
        missing_websites = set(expected_dates) - set(report['websites'].get('found_dates', []))
        
        report['missing_dates'] = {
            'segments': sorted(list(missing_segments)),
            'websites': sorted(list(missing_websites)),
            'both': sorted(list(missing_segments.union(missing_websites)))
        }
        
        # Résumé
        report['summary'] = {
            'expected_dates': len(expected_dates),
            'segments_complete': len(report['segments'].get('found_dates', [])),
            'websites_complete': len(report['websites'].get('found_dates', [])),
            'segments_missing': len(missing_segments),
            'websites_missing': len(missing_websites),
            'completeness_rate': {
                'segments': (len(report['segments'].get('found_dates', [])) / len(expected_dates) * 100) if expected_dates else 0,
                'websites': (len(report['websites'].get('found_dates', [])) / len(expected_dates) * 100) if expected_dates else 0
            }
        }
        
        return report
    
    def _generate_expected_dates(self, start_date: str, end_date: str) -> List[str]:
        """
        Génère la liste des dates attendues (format YYYY-MM-01)
        
        Args:
            start_date: Date de début
            end_date: Date de fin
            
        Returns:
            Liste des dates
        """
        dates = []
        current = datetime.strptime(start_date, '%Y-%m-%d')
        end = datetime.strptime(end_date, '%Y-%m-%d')
        
        while current <= end:
            # Format YYYY-MM-01 pour les données mensuelles
            dates.append(current.strftime('%Y-%m-01'))
            
            # Passer au mois suivant
            if current.month == 12:
                current = current.replace(year=current.year + 1, month=1)
            else:
                current = current.replace(month=current.month + 1)
        
        return sorted(list(set(dates)))  # Éliminer les doublons
    
    def _check_segments_data(self, expected_dates: List[str]) -> Dict:
        """
        Vérifie les données des segments
        
        Args:
            expected_dates: Liste des dates attendues
            
        Returns:
            Rapport des segments
        """
        query = f"""
        SELECT 
            date,
            COUNT(DISTINCT segment_id) as segment_count,
            COUNT(*) as total_rows,
            COUNT(DISTINCT extraction_date) as extraction_days
        FROM `{self.project_id}.{BIGQUERY_DATASET}.segments_data`
        WHERE date IN ({','.join([f"'{d}'" for d in expected_dates])})
        GROUP BY date
        ORDER BY date
        """
        
        try:
            results = self.client.query(query).result()
            
            data = {
                'found_dates': [],
                'details': {}
            }
            
            for row in results:
                data['found_dates'].append(row.date)
                data['details'][row.date] = {
                    'segment_count': row.segment_count,
                    'total_rows': row.total_rows,
                    'extraction_days': row.extraction_days
                }
            
            return data
            
        except Exception as e:
            logger.error(f"Erreur lors de la vérification des segments: {e}")
            return {'found_dates': [], 'details': {}, 'error': str(e)}
    
    def _check_websites_data(self, expected_dates: List[str]) -> Dict:
        """
        Vérifie les données des sites web
        
        Args:
            expected_dates: Liste des dates attendues
            
        Returns:
            Rapport des sites web
        """
        query = f"""
        SELECT 
            date,
            COUNT(DISTINCT domain) as website_count,
            COUNT(*) as total_rows,
            COUNT(DISTINCT extraction_date) as extraction_days
        FROM `{self.project_id}.{BIGQUERY_DATASET}.websites_data`
        WHERE date IN ({','.join([f"'{d}'" for d in expected_dates])})
        GROUP BY date
        ORDER BY date
        """
        
        try:
            results = self.client.query(query).result()
            
            data = {
                'found_dates': [],
                'details': {}
            }
            
            for row in results:
                data['found_dates'].append(row.date)
                data['details'][row.date] = {
                    'website_count': row.website_count,
                    'total_rows': row.total_rows,
                    'extraction_days': row.extraction_days
                }
            
            return data
            
        except Exception as e:
            logger.error(f"Erreur lors de la vérification des sites web: {e}")
            return {'found_dates': [], 'details': {}, 'error': str(e)}
    
    def fill_missing_data(self, missing_dates: List[str], data_type: str = 'both',
                         limit_segments: int = None) -> Dict:
        """
        Récupère les données manquantes
        
        Args:
            missing_dates: Liste des dates manquantes (format YYYY-MM-01)
            data_type: 'segments', 'websites', or 'both'
            limit_segments: Limiter le nombre de segments
            
        Returns:
            Statistiques de récupération
        """
        stats = {
            'dates_processed': 0,
            'segments_extracted': 0,
            'websites_extracted': 0,
            'errors': []
        }
        
        logger.info(f"Récupération de {len(missing_dates)} dates manquantes")
        
        for date_str in missing_dates:
            try:
                # Convertir en format YYYY-MM pour l'API
                period = {
                    'start_date': date_str[:7],  # YYYY-MM
                    'end_date': date_str[:7]
                }
                
                logger.info(f"Récupération pour {period['start_date']}")
                
                if data_type in ['segments', 'both']:
                    segment_stats = extract_and_save_segments(
                        api_client=self.api_client,
                        period=period,
                        limit=limit_segments
                    )
                    stats['segments_extracted'] += segment_stats['success']
                
                if data_type in ['websites', 'both']:
                    # Charger la liste actuelle des sites web
                    domains = load_websites()
                    website_stats = extract_and_save_websites(
                        api_client=self.api_client,
                        period=period,
                        domains=domains
                    )
                    stats['websites_extracted'] += website_stats['success']
                
                stats['dates_processed'] += 1
                
                # Pause entre les dates
                time.sleep(3)
                
            except Exception as e:
                logger.error(f"Erreur pour {date_str}: {e}")
                stats['errors'].append({'date': date_str, 'error': str(e)})
        
        return stats
    
    def generate_weekly_report(self) -> Dict:
        """
        Génère un rapport hebdomadaire de complétude
        
        Returns:
            Rapport hebdomadaire
        """
        # Dernière semaine
        end_date = datetime.now()
        start_date = end_date - timedelta(days=7)
        
        # Vérifier le mois précédent (données mensuelles)
        last_month = (end_date.replace(day=1) - timedelta(days=1))
        check_start = last_month.replace(day=1).strftime('%Y-%m-%d')
        check_end = last_month.strftime('%Y-%m-%d')
        
        report = self.check_data_completeness(check_start, check_end)
        
        # Ajouter des recommandations
        report['recommendations'] = []
        
        if report['summary']['segments_missing'] > 0:
            report['recommendations'].append({
                'type': 'segments',
                'action': 'fill_missing',
                'dates': report['missing_dates']['segments'],
                'priority': 'high' if report['summary']['completeness_rate']['segments'] < 90 else 'medium'
            })
        
        if report['summary']['websites_missing'] > 0:
            report['recommendations'].append({
                'type': 'websites',
                'action': 'fill_missing',
                'dates': report['missing_dates']['websites'],
                'priority': 'high' if report['summary']['completeness_rate']['websites'] < 90 else 'medium'
            })
        
        return report
    
    def generate_monthly_report(self, year: int, month: int) -> Dict:
        """
        Génère un rapport mensuel détaillé
        
        Args:
            year: Année
            month: Mois
            
        Returns:
            Rapport mensuel
        """
        start_date = f"{year}-{month:02d}-01"
        
        # Dernier jour du mois
        if month == 12:
            end_date = f"{year}-{month:02d}-31"
        else:
            next_month = datetime(year, month + 1, 1) - timedelta(days=1)
            end_date = next_month.strftime('%Y-%m-%d')
        
        report = self.check_data_completeness(start_date, end_date)
        
        # Ajouter des statistiques détaillées
        report['detailed_stats'] = {
            'segments': self._get_detailed_segment_stats(year, month),
            'websites': self._get_detailed_website_stats(year, month)
        }
        
        return report
    
    def _get_detailed_segment_stats(self, year: int, month: int) -> Dict:
        """
        Obtient des statistiques détaillées pour les segments
        """
        query = f"""
        SELECT 
            segment_name,
            COUNT(*) as data_points,
            AVG(visits) as avg_visits,
            AVG(bounce_rate) as avg_bounce_rate,
            AVG(pages_per_visit) as avg_pages_per_visit
        FROM `{self.project_id}.{BIGQUERY_DATASET}.segments_data`
        WHERE EXTRACT(YEAR FROM date) = {year}
          AND EXTRACT(MONTH FROM date) = {month}
        GROUP BY segment_name
        ORDER BY avg_visits DESC
        """
        
        try:
            results = self.client.query(query).result()
            return [dict(row) for row in results]
        except Exception as e:
            logger.error(f"Erreur stats segments: {e}")
            return []
    
    def _get_detailed_website_stats(self, year: int, month: int) -> Dict:
        """
        Obtient des statistiques détaillées pour les sites web
        """
        query = f"""
        SELECT 
            domain,
            COUNT(*) as data_points,
            AVG(visits) as avg_visits,
            AVG(bounce_rate) as avg_bounce_rate,
            AVG(pages_per_visit) as avg_pages_per_visit
        FROM `{self.project_id}.{BIGQUERY_DATASET}.websites_data`
        WHERE EXTRACT(YEAR FROM date) = {year}
          AND EXTRACT(MONTH FROM date) = {month}
        GROUP BY domain
        ORDER BY avg_visits DESC
        """
        
        try:
            results = self.client.query(query).result()
            return [dict(row) for row in results]
        except Exception as e:
            logger.error(f"Erreur stats websites: {e}")
            return []


import time

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Vérification de la disponibilité des données')
    subparsers = parser.add_subparsers(dest='command', help='Commandes disponibles')
    
    # Commande check
    parser_check = subparsers.add_parser('check', help='Vérifier la complétude des données')
    parser_check.add_argument('--start-date', required=True, help='Date de début (YYYY-MM-DD)')
    parser_check.add_argument('--end-date', required=True, help='Date de fin (YYYY-MM-DD)')
    parser_check.add_argument('--type', choices=['segments', 'websites', 'both'], 
                            default='both', help='Type de données à vérifier')
    
    # Commande fill
    parser_fill = subparsers.add_parser('fill', help='Récupérer les données manquantes')
    parser_fill.add_argument('--start-date', help='Date de début (YYYY-MM-DD)')
    parser_fill.add_argument('--end-date', help='Date de fin (YYYY-MM-DD)')
    parser_fill.add_argument('--type', choices=['segments', 'websites', 'both'], 
                           default='both', help='Type de données à récupérer')
    parser_fill.add_argument('--limit-segments', type=int, help='Limiter le nombre de segments')
    
    # Commande weekly-report
    parser_weekly = subparsers.add_parser('weekly-report', help='Générer un rapport hebdomadaire')
    
    # Commande monthly-report
    parser_monthly = subparsers.add_parser('monthly-report', help='Générer un rapport mensuel')
    parser_monthly.add_argument('--year', type=int, required=True, help='Année')
    parser_monthly.add_argument('--month', type=int, required=True, help='Mois (1-12)')
    
    args = parser.parse_args()
    
    checker = DataAvailabilityChecker()
    
    if args.command == 'check':
        report = checker.check_data_completeness(
            args.start_date, 
            args.end_date,
            args.type
        )
        
        print("\nRAPPORT DE COMPLÉTUDE DES DONNÉES")
        print("="*50)
        print(f"Période: {report['period']}")
        print(f"Dates attendues: {report['summary']['expected_dates']}")
        
        if args.type in ['segments', 'both']:
            print(f"\nSegments:")
            print(f"  - Complètes: {report['summary']['segments_complete']}")
            print(f"  - Manquantes: {report['summary']['segments_missing']}")
            print(f"  - Taux: {report['summary']['completeness_rate']['segments']:.1f}%")
        
        if args.type in ['websites', 'both']:
            print(f"\nSites web:")
            print(f"  - Complètes: {report['summary']['websites_complete']}")
            print(f"  - Manquantes: {report['summary']['websites_missing']}")
            print(f"  - Taux: {report['summary']['completeness_rate']['websites']:.1f}%")
        
        if report['missing_dates']['both']:
            print(f"\nDates manquantes:")
            for date in report['missing_dates']['both'][:10]:
                print(f"  - {date}")
            if len(report['missing_dates']['both']) > 10:
                print(f"  ... et {len(report['missing_dates']['both']) - 10} autres")
    
    elif args.command == 'fill':
        # D'abord vérifier ce qui manque
        if args.start_date and args.end_date:
            report = checker.check_data_completeness(
                args.start_date,
                args.end_date,
                args.type
            )
            
            missing = report['missing_dates']['both']
            if args.type == 'segments':
                missing = report['missing_dates']['segments']
            elif args.type == 'websites':
                missing = report['missing_dates']['websites']
            
            if missing:
                print(f"\n{len(missing)} dates manquantes trouvées")
                response = input("Voulez-vous les récupérer? (y/n): ")
                
                if response.lower() == 'y':
                    stats = checker.fill_missing_data(
                        missing,
                        args.type,
                        args.limit_segments
                    )
                    
                    print(f"\nRécupération terminée:")
                    print(f"  - Dates traitées: {stats['dates_processed']}")
                    print(f"  - Segments extraits: {stats['segments_extracted']}")
                    print(f"  - Sites web extraits: {stats['websites_extracted']}")
                    print(f"  - Erreurs: {len(stats['errors'])}")
            else:
                print("Aucune donnée manquante!")
    
    elif args.command == 'weekly-report':
        report = checker.generate_weekly_report()
        
        print("\nRAPPORT HEBDOMADAIRE")
        print("="*50)
        print(f"Complétude segments: {report['summary']['completeness_rate']['segments']:.1f}%")
        print(f"Complétude sites web: {report['summary']['completeness_rate']['websites']:.1f}%")
        
        if report['recommendations']:
            print("\nRecommandations:")
            for rec in report['recommendations']:
                print(f"  - {rec['type']}: {len(rec['dates'])} dates à récupérer (priorité: {rec['priority']})")
    
    elif args.command == 'monthly-report':
        report = checker.generate_monthly_report(args.year, args.month)
        
        print(f"\nRAPPORT MENSUEL - {args.year}/{args.month:02d}")
        print("="*50)
        print(f"Complétude segments: {report['summary']['completeness_rate']['segments']:.1f}%")
        print(f"Complétude sites web: {report['summary']['completeness_rate']['websites']:.1f}%")
        
        if report['detailed_stats']['segments']:
            print("\nTop 5 segments par visites:")
            for i, seg in enumerate(report['detailed_stats']['segments'][:5], 1):
                print(f"  {i}. {seg['segment_name']}: {seg['avg_visits']:,.0f} visites")
    
    else:
        parser.print_help() 