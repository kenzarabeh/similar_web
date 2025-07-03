"""
Module principal pour les appels à l'API SimilarWeb
Basé sur les scripts validés du notebook d'exploration
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
    """Classe pour gérer les interactions avec l'API SimilarWeb"""
    
    def __init__(self, api_key: str = None):
        """
        Initialise le client API
        
        Args:
            api_key: Clé API SimilarWeb (utilise la config par défaut si non fournie)
        """
        self.api_key = api_key or SIMILARWEB_API_KEY
        self.base_url = SIMILARWEB_BASE_URL
        self.headers = API_HEADERS.copy()
        
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
            logger.info(f"✅ {len(segments)} segments récupérés")
            return segments
        else:
            logger.error("❌ Impossible de récupérer les segments")
            return None
    
    def get_segment_data(self, segment_id: str, start_date: str, end_date: str, 
                        country: str = DEFAULT_COUNTRY, 
                        granularity: str = DEFAULT_GRANULARITY) -> Optional[Dict]:
        """
        Récupère les données de trafic pour un segment spécifique
        Fait plusieurs appels pour récupérer toutes les métriques
        
        Args:
            segment_id: ID du segment
            start_date: Date de début (format YYYY-MM)
            end_date: Date de fin (format YYYY-MM)
            country: Code pays
            granularity: Granularité (monthly, daily, weekly)
            
        Returns:
            Données du segment combinées ou None en cas d'erreur
        """
        from config.config import SEGMENT_METRICS_GROUPS
        
        combined_data = None
        all_segments_data = []
        
        # Faire un appel pour chaque groupe de métriques
        for metrics_group in SEGMENT_METRICS_GROUPS:
            params = {
                'start_date': start_date,
                'end_date': end_date,
                'country': country,
                'granularity': granularity,
                'metrics': metrics_group
            }
            
            endpoint = f'/segment/{segment_id}/total-traffic-and-engagement/query'
            result = self._make_request(endpoint, params)
            
            if result and 'segments' in result:
                all_segments_data.append(result['segments'][0])
        
        # Combiner toutes les métriques
        if all_segments_data:
            # Prendre le premier résultat comme base
            combined_segment = all_segments_data[0].copy()
            
            # Ajouter les métriques des autres appels
            for segment_data in all_segments_data[1:]:
                for key, value in segment_data.items():
                    if key not in combined_segment:
                        combined_segment[key] = value
            
            combined_data = {
                'meta': {},
                'segments': [combined_segment]
            }
        
        return combined_data
    
    def get_website_metric(self, domain: str, metric_endpoint: str, 
                          start_date: str, end_date: str,
                          country: str = DEFAULT_COUNTRY,
                          granularity: str = DEFAULT_GRANULARITY) -> Optional[Dict]:
        """
        Récupère une métrique spécifique pour un site web
        
        Args:
            domain: Domaine à analyser
            metric_endpoint: Endpoint de la métrique
            start_date: Date de début (format YYYY-MM)
            end_date: Date de fin (format YYYY-MM)
            country: Code pays
            granularity: Granularité
            
        Returns:
            Données de la métrique ou None en cas d'erreur
        """
        params = {
            'start_date': start_date,
            'end_date': end_date,
            'country': country,
            'granularity': granularity,
            'main_domain_only': 'false',
            'format': 'json'
        }
        
        endpoint = f'/website/{domain}{metric_endpoint}'
        return self._make_request(endpoint, params)
    
    def extract_all_segments(self, start_date: str, end_date: str, 
                           limit: int = None, user_only: bool = True) -> List[Dict]:
        """
        Extrait les données pour tous les segments personnalisés
        
        Args:
            start_date: Date de début (format YYYY-MM)
            end_date: Date de fin (format YYYY-MM)
            limit: Nombre maximum de segments à traiter (None = tous)
            user_only: Si True, récupère uniquement les segments créés par l'utilisateur
            
        Returns:
            Liste des résultats pour chaque segment
        """
        results = []
        
        # Récupérer la liste des segments
        segments = self.get_custom_segments(user_only=user_only)
        if not segments:
            return results
        
        # Limiter si demandé
        if limit:
            segments = segments[:limit]
        
        logger.info(f"Extraction de {len(segments)} segments...")
        
        for i, segment in enumerate(segments):
            segment_id = segment.get('segment_id')
            segment_name = segment.get('segment_name', 'N/A')
            
            logger.info(f"📊 Extraction {i+1}/{len(segments)}: {segment_name}")
            
            data = self.get_segment_data(segment_id, start_date, end_date)
            
            if data:
                logger.info(f"✅ Données récupérées pour {segment_name}")
                results.append({
                    'segment_id': segment_id,
                    'segment_name': segment_name,
                    'data': data,
                    'extraction_date': get_current_date()
                })
            else:
                logger.error(f"❌ Échec pour {segment_name}")
                results.append({
                    'segment_id': segment_id,
                    'segment_name': segment_name,
                    'data': None,
                    'error': True,
                    'extraction_date': get_current_date()
                })
        
        return results
    
    def extract_website_data(self, domain: str, start_date: str, end_date: str) -> Dict:
        """
        Extrait toutes les métriques pour un site web
        
        Args:
            domain: Domaine à analyser
            start_date: Date de début (format YYYY-MM)
            end_date: Date de fin (format YYYY-MM)
            
        Returns:
            Dictionnaire avec toutes les métriques du site
        """
        logger.info(f"🌐 Extraction pour {domain}")
        
        domain_results = {
            'domain': domain,
            'period': f"{start_date} to {end_date}",
            'extraction_date': get_current_date(),
            'metrics': {}
        }
        
        for metric_name, endpoint in WEBSITE_METRICS_ENDPOINTS.items():
            logger.info(f"  📊 Extraction {metric_name}...")
            
            data = self.get_website_metric(domain, endpoint, start_date, end_date)
            
            if data:
                logger.info(f"    ✅ {metric_name} récupéré")
                domain_results['metrics'][metric_name] = data
            else:
                logger.error(f"    ❌ Échec {metric_name}")
                domain_results['metrics'][metric_name] = None
        
        return domain_results
    
    def extract_all_websites(self, domains: List[str], start_date: str, end_date: str) -> List[Dict]:
        """
        Extrait les données pour plusieurs sites web
        
        Args:
            domains: Liste des domaines à analyser
            start_date: Date de début (format YYYY-MM)
            end_date: Date de fin (format YYYY-MM)
            
        Returns:
            Liste des résultats pour chaque domaine
        """
        results = []
        
        logger.info(f"Extraction de {len(domains)} sites web...")
        
        for domain in domains:
            result = self.extract_website_data(domain, start_date, end_date)
            results.append(result)
        
        return results


def save_results_to_json(data: Any, filename: str) -> None:
    """
    Sauvegarde les résultats dans un fichier JSON
    
    Args:
        data: Données à sauvegarder
        filename: Nom du fichier (sera créé dans le dossier data/)
    """
    filepath = os.path.join(DATA_PATH, filename)
    
    with open(filepath, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    
    logger.info(f"💾 Résultats sauvegardés dans {filepath}")


if __name__ == "__main__":
    # Test du module
    logger.info("Test du module SimilarWeb API...")
    
    # Initialiser le client
    api = SimilarWebAPI()
    
    # Test: Récupérer les segments
    segments = api.get_custom_segments()
    if segments:
        logger.info(f"Test réussi: {len(segments)} segments trouvés")
    else:
        logger.error("Test échoué: Impossible de récupérer les segments") 