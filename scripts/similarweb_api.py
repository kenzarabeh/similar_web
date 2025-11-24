"""
Module principal pour les appels à l'API SimilarWeb
CORRIGÉ pour architecture 3 tables avec nouvelles méthodes spécialisées
"""
import requests
import time
import json
import logging
from typing import Dict, List, Optional, Any
import sys
import os

# Ajouter le chemin parent pour importer la config
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config.config import *

# Configuration du logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class SimilarWebAPI:
    """Classe pour gérer les interactions avec l'API SimilarWeb - Architecture 3 tables"""
    
    def __init__(self, api_key: str = None):
        """
        Initialise le client API
        
        Args:
            api_key: Clé API SimilarWeb (utilise la config par défaut si non fournie)
        """
        self.api_key = api_key or SIMILARWEB_API_KEY
        self.base_url = SIMILARWEB_BASE_URL
        self.headers = API_HEADERS.copy()
        
        # Endpoints websites (inchangés - avec unique_visitors)
        self.website_endpoints = {
            'visits': '/total-traffic-and-engagement/visits',
            'pages_per_visit': '/total-traffic-and-engagement/pages-per-visit',
            'avg_visit_duration': '/total-traffic-and-engagement/average-visit-duration',
            'bounce_rate': '/total-traffic-and-engagement/bounce-rate',
            'page_views': '/total-traffic-and-engagement/page-views',
            'desktop_mobile_split': '/total-traffic-and-engagement/visits-split',
            'unique_visitors_desktop': '/unique-visitors/desktop_unique_visitors',
            'unique_visitors_mobile': '/unique-visitors/mobileweb_unique_visitors'
        }
        
    def _make_request(self, endpoint: str, params: Dict = None, retry_count: int = 0) -> Optional[Dict]:
        """
        Effectue une requête à l'API avec gestion des erreurs et retry
        
        Args:
            endpoint: Endpoint de l'API (sans le base_url)
            params: Paramètres de la requête
            retry_count: Nombre de tentatives déjà effectuées
            
        Returns:
            Réponse JSON ou None en cas d'erreur
        """
        if params is None:
            params = {}
        
        # Ajouter la clé API aux paramètres
        params['api_key'] = self.api_key
        
        # Construire l'URL complète
        url = f"{self.base_url}{endpoint}"
        
        try:
            logger.info(f"Appel API: {endpoint}")
            response = requests.get(url, headers=self.headers, params=params)
            response.raise_for_status()
            
            # Respecter le rate limit
            time.sleep(API_RATE_LIMIT_DELAY)
            
            return response.json()
            
        except requests.exceptions.HTTPError as e:
            if e.response.status_code == 429:  # Rate limit
                logger.warning(f"Rate limit atteint, attente de {RETRY_DELAY * 2} secondes...")
                time.sleep(RETRY_DELAY * 2)
                
                if retry_count < MAX_RETRIES:
                    return self._make_request(endpoint, params, retry_count + 1)
                    
            logger.error(f"Erreur HTTP {e.response.status_code}: {e}")
            return None
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Erreur de requête: {e}")
            
            if retry_count < MAX_RETRIES:
                logger.info(f"Nouvelle tentative ({retry_count + 1}/{MAX_RETRIES})...")
                time.sleep(RETRY_DELAY)
                return self._make_request(endpoint, params, retry_count + 1)
                
            return None
    
    def _should_use_mtd(self, date_str: str) -> bool:
        """
        Détermine si MTD doit être utilisé selon la règle :
        - Si mois sélectionné = mois en cours → mtd=true  
        - Sinon → mtd=false
        
        Args:
            date_str: Date au format YYYY-MM ou YYYY-MM-DD
            
        Returns:
            True si le mois demandé = mois en cours, False sinon
        """
        from datetime import datetime
        
        try:
            # Extraire l'année et le mois de la date demandée
            if len(date_str) >= 7:  # YYYY-MM ou YYYY-MM-DD
                year_month = date_str[:7]  # YYYY-MM
                request_year, request_month = map(int, year_month.split('-'))
                
                # Date actuelle
                now = datetime.now()
                current_year = now.year
                current_month = now.month
                
                # MTD = TRUE si mois demandé = mois en cours
                is_current_month = (request_year == current_year and request_month == current_month)
                
                if is_current_month:
                    logger.info(f"MTD=TRUE : {year_month} = mois en cours ({current_year}-{current_month:02d})")
                else:
                    logger.info(f"MTD=FALSE : {year_month} ≠ mois en cours ({current_year}-{current_month:02d})")
                
                return is_current_month
                
        except Exception as e:
            logger.warning(f"Erreur détection MTD pour {date_str}: {e}")
            return False
        
        return False
    
    def get_custom_segments(self, user_only: bool = True) -> Optional[List[Dict]]:
        """
        Récupère la liste des segments personnalisés
        
        Args:
            user_only: Si True, récupère uniquement les segments créés par l'utilisateur
        
        Returns:
            Liste des segments ou None en cas d'erreur
        """
        logger.info(f"Récupération des segments personnalisés (user_only={user_only})...")
        
        # Ajouter le paramètre userOnlySegments si demandé
        params = {}
        if user_only:
            params['userOnlySegments'] = 'true'
        
        response = self._make_request('/segment/traffic-and-engagement/describe/', params)
        
        if response and 'response' in response:
            segments = response['response'].get('segments', [])
            logger.info(f"{len(segments)} segments récupérés")
            return segments
        else:
            logger.error("Impossible de récupérer les segments")
            return None

    def get_segment_data_daily_no_uv(self, segment_id: str, start_date: str, end_date: str, 
                                   country: str = DEFAULT_COUNTRY, 
                                   granularity: str = DEFAULT_GRANULARITY,
                                   mtd: bool = False):
        """
        Extraction segments daily SANS unique-visitors - Architecture 3 tables
        
        Args:
            segment_id: ID du segment
            start_date: Date de début
            end_date: Date de fin
            country: Code pays
            granularity: Granularité (daily/monthly)
            mtd: Month-to-date pour le mois en cours
            
        Returns:
            Données du segment sans unique_visitors
        """
        
        # Groupes de métriques SANS unique-visitors
        metrics_groups = [
            'visits,share',
            'bounce-rate,pages-per-visit,visit-duration',
            'page-views'  # SANS unique-visitors
        ]
        
        combined_data = None
        all_api_results = []
        
        for metrics_group in metrics_groups:
            params = {
                'start_date': start_date,
                'end_date': end_date,
                'country': country,
                'granularity': granularity,
                'metrics': metrics_group
            }
            
            # Ajouter MTD si nécessaire
            if mtd:
                params['mtd'] = 'true'
                logger.info(f"Utilisation MTD pour {start_date} (mois en cours)")
            
            endpoint = f'/segment/{segment_id}/total-traffic-and-engagement/query'
            result = self._make_request(endpoint, params)
            
            if result and 'segments' in result:
                all_api_results.append(result)
        
        # Combiner correctement tous les points de données
        if all_api_results:
            # Prendre le premier résultat comme base (contient tous les points de dates)
            base_result = all_api_results[0]
            combined_segments = []
            
            # Pour chaque point de données (date)
            for i, base_segment in enumerate(base_result['segments']):
                combined_segment = base_segment.copy()
                
                # Ajouter les métriques des autres appels API pour le même point (même index)
                for other_result in all_api_results[1:]:
                    if i < len(other_result['segments']):
                        other_segment = other_result['segments'][i]
                        
                        # Vérifier que c'est la même date
                        if other_segment.get('date') == combined_segment.get('date'):
                            # Ajouter les métriques manquantes
                            for key, value in other_segment.items():
                                if key not in combined_segment and key != 'date':
                                    combined_segment[key] = value
                
                combined_segments.append(combined_segment)
            
            combined_data = {
                'meta': base_result.get('meta', {}),
                'segments': combined_segments
            }
        
        return combined_data

    def get_segment_unique_visitors_only(self, segment_id: str, start_date: str, end_date: str, 
                                       country: str = DEFAULT_COUNTRY, 
                                       granularity: str = 'monthly',
                                       mtd: bool = False):
        """
        Extraction segments monthly SEULEMENT pour unique-visitors - Architecture 3 tables
        
        Args:
            segment_id: ID du segment
            start_date: Date de début
            end_date: Date de fin
            country: Code pays
            granularity: Granularité (monthly par défaut)
            mtd: Month-to-date pour le mois en cours
            
        Returns:
            Données du segment avec seulement unique_visitors
        """
        
        params = {
            'start_date': start_date,
            'end_date': end_date,
            'country': country,
            'granularity': granularity,
            'metrics': 'unique-visitors'  # SEULEMENT unique-visitors
        }
        
        # Ajouter MTD si nécessaire
        if mtd:
            params['mtd'] = 'true'
            logger.info(f"Utilisation MTD pour unique_visitors {start_date} (mois en cours)")
        
        endpoint = f'/segment/{segment_id}/total-traffic-and-engagement/query'
        result = self._make_request(endpoint, params)
        
        return result
    
    def get_website_metric(self, domain: str, metric_endpoint: str, 
                          start_date: str, end_date: str,
                          country: str = DEFAULT_COUNTRY,
                          granularity: str = DEFAULT_GRANULARITY,
                          mtd: bool = False) -> Optional[Dict]:
        """
        Récupère une métrique spécifique pour un site web
        AVEC SUPPORT MTD - pour websites_daily avec unique_visitors
        
        Args:
            domain: Domaine à analyser
            metric_endpoint: Endpoint de la métrique
            start_date: Date de début (format YYYY-MM-DD pour daily, YYYY-MM pour monthly)
            end_date: Date de fin (format YYYY-MM-DD pour daily, YYYY-MM pour monthly)
            country: Code pays
            granularity: Granularité ('daily' ou 'monthly')
            mtd: Month-to-date pour le mois en cours
            
        Returns:
            Données de la métrique ou None en cas d'erreur
        """
        # Si MTD est activé avec granularité daily, convertir les dates au format YYYY-MM
        api_start_date = start_date
        api_end_date = end_date
        
        if mtd and granularity == 'daily':
            # Extraire YYYY-MM de YYYY-MM-DD
            api_start_date = start_date[:7] if len(start_date) >= 7 else start_date
            api_end_date = end_date[:7] if len(end_date) >= 7 else end_date
            logger.info(f"MTD activé: conversion {start_date} → {api_start_date}")
        
        params = {
            'start_date': api_start_date,
            'end_date': api_end_date,
            'country': country,
            'granularity': granularity,
            'main_domain_only': 'false',
            'format': 'json'
        }
        
        # Ajouter MTD si nécessaire
        if mtd:
            params['mtd'] = 'true'
        
        endpoint = f'/website/{domain}{metric_endpoint}'
        
        return self._make_request(endpoint, params)

    def extract_segments_daily_architecture(self, start_date: str, end_date: str, 
                                          limit: int = None, user_only: bool = True,
                                          granularity: str = 'daily') -> List[Dict]:
        """
        Extrait segments DAILY sans unique_visitors - Architecture 3 tables
        AVEC SUPPORT MTD AUTOMATIQUE
        
        Args:
            start_date: Date de début
            end_date: Date de fin
            limit: Nombre maximum de segments à traiter
            user_only: Segments utilisateur seulement
            granularity: Granularité (daily)
            
        Returns:
            Liste des segments daily sans unique_visitors
        """
        results = []
        
        # Récupérer la liste des segments
        segments = self.get_custom_segments(user_only=user_only)
        if not segments:
            return results
        
        # Limiter si demandé
        if limit:
            segments = segments[:limit]
        
        # Détection automatique MTD
        use_mtd = self._should_use_mtd(start_date)
        if use_mtd:
            logger.info(f"🗓️ Extraction segments_daily avec MTD pour {start_date} (mois en cours)")
        
        logger.info(f"Extraction segments_daily: {len(segments)} segments...")
        
        for i, segment in enumerate(segments):
            segment_id = segment.get('segment_id')
            segment_name = segment.get('segment_name', 'N/A')
            
            logger.info(f"Segment daily {i+1}/{len(segments)}: {segment_name}")
            
            data = self.get_segment_data_daily_no_uv(
                segment_id=segment_id,
                start_date=start_date,
                end_date=end_date,
                granularity=granularity,
                mtd=use_mtd  # MTD automatique
            )
            
            if data:
                logger.info(f"Données daily récupérées pour {segment_name}")
                results.append({
                    'segment_id': segment_id,
                    'segment_name': segment_name,
                    'data': data,
                    'extraction_granularity': granularity,
                    'table_type': 'segments_daily',
                    'mtd_used': use_mtd,
                    'extraction_date': get_current_date()
                })
            else:
                logger.error(f"Échec daily pour {segment_name}")
                results.append({
                    'segment_id': segment_id,
                    'segment_name': segment_name,
                    'data': None,
                    'error': True,
                    'table_type': 'segments_daily',
                    'mtd_used': use_mtd,
                    'extraction_date': get_current_date()
                })
        
        return results

    def extract_segments_unique_visitors_architecture(self, start_date: str, end_date: str, 
                                                    limit: int = None, user_only: bool = True) -> List[Dict]:
        """
        Extrait segments MONTHLY seulement unique_visitors - Architecture 3 tables
        AVEC SUPPORT MTD AUTOMATIQUE
        
        Args:
            start_date: Date de début (format YYYY-MM)
            end_date: Date de fin (format YYYY-MM)
            limit: Nombre maximum de segments à traiter
            user_only: Segments utilisateur seulement
            
        Returns:
            Liste des segments unique_visitors seulement
        """
        results = []
        
        # Récupérer la liste des segments
        segments = self.get_custom_segments(user_only=user_only)
        if not segments:
            return results
        
        # Limiter si demandé
        if limit:
            segments = segments[:limit]
        
        # Détection automatique MTD
        use_mtd = self._should_use_mtd(start_date)
        if use_mtd:
            logger.info(f"🗓️ Extraction segments_unique_visitors avec MTD pour {start_date} (mois en cours)")
        
        logger.info(f"Extraction segments_unique_visitors: {len(segments)} segments...")
        
        for i, segment in enumerate(segments):
            segment_id = segment.get('segment_id')
            segment_name = segment.get('segment_name', 'N/A')
            
            logger.info(f"Segment unique_visitors {i+1}/{len(segments)}: {segment_name}")
            
            data = self.get_segment_unique_visitors_only(
                segment_id=segment_id,
                start_date=start_date,
                end_date=end_date,
                granularity='monthly',
                mtd=use_mtd  # MTD automatique
            )
            
            if data:
                logger.info(f"Données unique_visitors récupérées pour {segment_name}")
                results.append({
                    'segment_id': segment_id,
                    'segment_name': segment_name,
                    'data': data,
                    'extraction_granularity': 'monthly',
                    'table_type': 'segments_unique_visitors',
                    'mtd_used': use_mtd,
                    'extraction_date': get_current_date()
                })
            else:
                logger.error(f"Échec unique_visitors pour {segment_name}")
                results.append({
                    'segment_id': segment_id,
                    'segment_name': segment_name,
                    'data': None,
                    'error': True,
                    'table_type': 'segments_unique_visitors',
                    'mtd_used': use_mtd,
                    'extraction_date': get_current_date()
                })
        
        return results

    def extract_websites_daily_architecture(self, domains: List[str], start_date: str, end_date: str,
                                          granularity: str = 'daily') -> List[Dict]:
        """
        Extrait websites DAILY avec unique_visitors - Architecture 3 tables 
        AVEC SUPPORT MTD AUTOMATIQUE
        
        Args:
            domains: Liste des domaines à analyser
            start_date: Date de début
            end_date: Date de fin
            granularity: Granularité (daily)
            
        Returns:
            Liste des websites daily avec unique_visitors
        """
        results = []
        
        # Détection automatique MTD
        use_mtd = self._should_use_mtd(start_date)
        if use_mtd:
            logger.info(f"🗓️ Extraction websites_daily avec MTD pour {start_date} (mois en cours)")
        
        logger.info(f"Extraction websites_daily: {len(domains)} sites web...")
        
        for domain in domains:
            logger.info(f"Extraction {domain}")
            
            domain_results = {
                'domain': domain,
                'period': f"{start_date} to {end_date}",
                'extraction_date': get_current_date(),
                'extraction_granularity': granularity,
                'table_type': 'websites_daily',
                'mtd_used': use_mtd,
                'metrics': {}
            }
            
            # Extraire toutes les métriques incluant unique_visitors
            for metric_name, endpoint in self.website_endpoints.items():
                logger.info(f"  Extraction {metric_name}...")
                
                data = self.get_website_metric(
                    domain=domain,
                    metric_endpoint=endpoint,
                    start_date=start_date,
                    end_date=end_date,
                    granularity=granularity,
                    mtd=use_mtd  # MTD automatique
                )
                
                if data:
                    logger.info(f"    {metric_name} récupéré")
                    # DEBUG: Log structure unique_visitors
                    if 'unique_visitors' in metric_name and use_mtd:
                        if isinstance(data, dict) and 'unique_visitors' in data:
                            uv_points = data['unique_visitors']
                            logger.info(f"    {metric_name} (MTD): {len(uv_points) if isinstance(uv_points, list) else 'not list'} points")
                        
                    domain_results['metrics'][metric_name] = data
                else:
                    logger.error(f"    Échec {metric_name}")
                    domain_results['metrics'][metric_name] = None
            
            results.append(domain_results)
        
        return results

    # Méthodes de compatibilité pour les anciens scripts
    def extract_all_segments(self, start_date: str, end_date: str, 
                           limit: int = None, user_only: bool = True,
                           granularity: str = DEFAULT_GRANULARITY) -> List[Dict]:
        """
        Méthode de compatibilité - redirige vers segments_daily_architecture
        """
        return self.extract_segments_daily_architecture(start_date, end_date, limit, user_only, granularity)
    
    def extract_all_websites(self, domains: List[str], start_date: str, end_date: str,
                           granularity: str = DEFAULT_GRANULARITY) -> List[Dict]:
        """
        Méthode de compatibilité - redirige vers websites_daily_architecture
        """
        return self.extract_websites_daily_architecture(domains, start_date, end_date, granularity)


def save_results_to_json(data: Any, filename: str) -> None:
    """
    Sauvegarde les résultats dans un fichier JSON
    
    Args:
        data: Données à sauvegarder
        filename: Nom du fichier (sera créé dans le dossier data/)
    """
    # Créer le dossier data s'il n'existe pas
    os.makedirs(DATA_PATH, exist_ok=True)
    
    filepath = os.path.join(DATA_PATH, filename)
    
    with open(filepath, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    
    logger.info(f"Résultats sauvegardés dans {filepath}")


if __name__ == "__main__":
    # Test du module
    logger.info("Test du module SimilarWeb API - Architecture 3 tables...")
    
    # Initialiser le client
    api = SimilarWebAPI()
    
    # Test: Récupérer les segments
    segments = api.get_custom_segments()
    if segments:
        logger.info(f"Test réussi: {len(segments)} segments trouvés")
        
        # Test des nouvelles méthodes
        if len(segments) > 0:
            segment_id = segments[0]['segment_id']
            
            # Test segments daily sans UV
            daily_data = api.get_segment_data_daily_no_uv(segment_id, '2025-09-01', '2025-09-01', granularity='daily')
            logger.info(f"Test daily sans UV: {'Réussi' if daily_data else 'Échoué'}")
            
            # Test unique visitors seulement
            uv_data = api.get_segment_unique_visitors_only(segment_id, '2025-09', '2025-09')
            logger.info(f"Test unique visitors seulement: {'Réussi' if uv_data else 'Échoué'}")
    else:
        logger.error("Test échoué: Impossible de récupérer les segments")