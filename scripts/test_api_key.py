#!/usr/bin/env python3
"""
Script pour vérifier quelle clé API est utilisée et combien de segments sont retournés
"""
import sys
import os

# Ajouter le chemin parent pour importer la config
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config.config import SIMILARWEB_API_KEY
from scripts.similarweb_api import SimilarWebAPI

def debug_api_key():
    """Affiche la clé API utilisée et teste le nombre de segments"""
    
    print("🔍 DEBUG CLÉS API")
    print("=" * 50)
    
    # 1. Vérifier quelle clé est dans la config
    print(f"Clé API depuis config.py: {SIMILARWEB_API_KEY[:8]}...{SIMILARWEB_API_KEY[-8:]}")
    print(f"Clé API complète: {SIMILARWEB_API_KEY}")
    
    # 2. Vérifier les variables d'environnement
    env_key = os.environ.get('SIMILARWEB_API_KEY', 'NON_DEFINI')
    print(f"Variable d'environnement: {env_key[:8] if env_key != 'NON_DEFINI' else env_key}")
    
    # 3. Vérifier le fichier .env s'il existe
    env_file_path = '.env'
    if os.path.exists(env_file_path):
        print(f"\nContenu du fichier .env:")
        with open(env_file_path, 'r') as f:
            lines = f.readlines()
            for line in lines:
                if 'SIMILARWEB_API_KEY' in line:
                    print(f"  {line.strip()}")
    else:
        print("Aucun fichier .env trouvé")
    
    # 4. Tester avec l'API
    print(f"\n🧪 TEST DE L'API")
    print("-" * 30)
    
    api = SimilarWebAPI()
    print(f"Clé utilisée par l'API: {api.api_key[:8]}...{api.api_key[-8:]}")
    
    # Test avec userOnlySegments=false
    print(f"\n📊 Test TOUS les segments (userOnlySegments=false)")
    all_segments = api.get_custom_segments(user_only=False)
    if all_segments:
        print(f"   Nombre total de segments: {len(all_segments)}")
        print(f"   Premiers segments:")
        for i, seg in enumerate(all_segments[:5]):
            print(f"   {i+1}. {seg.get('segment_name', 'N/A')}")
    
    # Test avec userOnlySegments=true
    print(f"\n📊 Test segments UTILISATEUR (userOnlySegments=true)")
    user_segments = api.get_custom_segments(user_only=True)
    if user_segments:
        print(f"   Nombre de segments utilisateur: {len(user_segments)}")
        print(f"   Premiers segments:")
        for i, seg in enumerate(user_segments[:5]):
            print(f"   {i+1}. {seg.get('segment_name', 'N/A')}")
    
    # Comparaison
    print(f"\n📋 RÉSUMÉ")
    print("-" * 30)
    total_segments = len(all_segments) if all_segments else 0
    user_only_segments = len(user_segments) if user_segments else 0
    
    print(f"Total segments: {total_segments}")
    print(f"Segments utilisateur: {user_only_segments}")
    print(f"Différence: {total_segments - user_only_segments}")
    
    return {
        'api_key': api.api_key,
        'total_segments': total_segments,
        'user_segments': user_only_segments
    }

if __name__ == "__main__":
    debug_api_key()