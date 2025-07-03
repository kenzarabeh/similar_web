"""
Cloud Function pour l'extraction quotidienne SimilarWeb
"""
import os
import sys
from datetime import datetime

# Configuration pour Cloud Functions
sys.path.append(os.path.dirname(__file__))

from similarweb_api import SimilarWebAPI, save_results_to_json
from daily_extraction import main as extraction_main

def similarweb_extraction(request):
    """
    Point d'entrée HTTP pour Cloud Functions
    
    Args:
        request: Flask Request object
        
    Returns:
        JSON response avec le statut de l'extraction
    """
    # Parser les paramètres de la requête
    request_json = request.get_json(silent=True)
    request_args = request.args
    
    # Déterminer si c'est un test
    test_mode = False
    if request_json and 'test_mode' in request_json:
        test_mode = request_json['test_mode']
    elif request_args and 'test_mode' in request_args:
        test_mode = request_args.get('test_mode') == 'true'
    
    # Créer l'event pour la fonction
    event = {'test_mode': test_mode} if test_mode else None
    
    try:
        # Exécuter l'extraction
        result = extraction_main(event)
        
        return {
            'status': 'success',
            'data': result,
            'timestamp': datetime.now().isoformat()
        }, 200
        
    except Exception as e:
        return {
            'status': 'error',
            'error': str(e),
            'timestamp': datetime.now().isoformat()
        }, 500

# Alias pour le déploiement Cloud Functions
main = similarweb_extraction
