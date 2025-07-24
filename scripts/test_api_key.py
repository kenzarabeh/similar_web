#!/usr/bin/env python3
"""
Script pour tester si votre clé API SimilarWeb fonctionne encore
"""
import requests
import sys
import os

# Ajouter le chemin parent pour importer la config
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config.config import SIMILARWEB_API_KEY

def test_api_key():
    """Test basique de la clé API"""
    
    print("🔑 TEST DE LA CLÉ API SIMILARWEB")
    print("=" * 50)
    print(f"Clé API: {SIMILARWEB_API_KEY[:8]}...{SIMILARWEB_API_KEY[-8:]}")
    
    # Test 1: Endpoint le plus basique (liste des segments)
    print(f"\n🧪 Test 1: Liste des segments...")
    
    url = "https://api.similarweb.com/v1/segment/traffic-and-engagement/describe/"
    params = {
        'api_key': SIMILARWEB_API_KEY,
        'userOnlySegments': 'true'
    }
    headers = {'accept': 'application/json'}
    
    try:
        response = requests.get(url, headers=headers, params=params)
        
        print(f"Status Code: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            if 'response' in data and 'segments' in data['response']:
                segments = data['response']['segments']
                print(f"✅ API Key VALIDE - {len(segments)} segments trouvés")
                
                if segments:
                    print(f"Premier segment: {segments[0].get('segment_name', 'N/A')}")
                return True
            else:
                print(f"❌ Réponse inattendue: {data}")
                return False
                
        elif response.status_code == 401:
            print(f"❌ ERREUR 401: Clé API invalide ou expirée")
            print(f"Vérifiez votre clé API dans config/.env")
            return False
            
        elif response.status_code == 403:
            print(f"❌ ERREUR 403: Accès interdit")
            print(f"Possible causes:")
            print(f"  - Quota API dépassé")
            print(f"  - Abonnement expiré ou suspendu")
            print(f"  - Restrictions d'accès aux segments")
            return False
            
        elif response.status_code == 429:
            print(f"❌ ERREUR 429: Rate limit atteint")
            print(f"Attendez quelques minutes et réessayez")
            return False
            
        else:
            print(f"❌ ERREUR {response.status_code}: {response.text}")
            return False
            
    except Exception as e:
        print(f"❌ ERREUR DE CONNEXION: {e}")
        return False

def test_website_endpoint():
    """Test avec un endpoint website (moins restrictif)"""
    
    print(f"\n🧪 Test 2: Endpoint website (amazon.fr)...")
    
    url = "https://api.similarweb.com/v1/website/amazon.fr/total-traffic-and-engagement/visits"
    params = {
        'api_key': SIMILARWEB_API_KEY,
        'start_date': '2024-01',
        'end_date': '2024-01',
        'country': 'fr',
        'granularity': 'monthly',
        'main_domain_only': 'false',
        'format': 'json'
    }
    headers = {'accept': 'application/json'}
    
    try:
        response = requests.get(url, headers=headers, params=params, timeout=10)
        
        print(f"Status Code: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            print(f"✅ Endpoint website fonctionne")
            if 'visits' in data:
                print(f"Données disponibles: {len(data['visits'])} points")
            return True
        else:
            print(f"❌ Échec: {response.status_code}")
            if response.status_code == 403:
                print(f"Même problème sur l'endpoint website")
            return False
            
    except Exception as e:
        print(f"❌ ERREUR: {e}")
        return False

def check_quota_info():
    """Essayer de récupérer des infos sur le quota"""
    
    print(f"\n📊 Informations sur votre compte...")
    print(f"Malheureusement, SimilarWeb ne fournit pas d'endpoint")
    print(f"pour vérifier le quota restant via l'API.")
    print(f"\nVérifiez manuellement sur:")
    print(f"🔗 https://account.similarweb.com/")
    print(f"   → Section 'API Usage' ou 'Billing'")

def main():
    """Test complet de l'API"""
    
    # Test de base
    segments_ok = test_api_key()
    
    # Test alternatif
    website_ok = test_website_endpoint()
    
    # Informations sur le quota
    check_quota_info()
    
    # Résumé
    print(f"\n📋 RÉSUMÉ")
    print("=" * 30)
    
    if segments_ok:
        print(f"✅ Clé API valide")
        print(f"✅ Accès aux segments OK")
        print(f"🤔 Le problème pourrait être temporaire")
        print(f"\n💡 Essayez de relancer votre extraction dans 1 heure")
        
    elif website_ok:
        print(f"✅ Clé API valide") 
        print(f"❌ Accès aux segments bloqué")
        print(f"✅ Accès aux websites OK")
        print(f"\n💡 Votre abonnement permet seulement les websites")
        
    else:
        print(f"❌ Problème avec la clé API")
        print(f"\n💡 Actions suggérées:")
        print(f"   1. Vérifiez votre quota sur account.similarweb.com")
        print(f"   2. Contactez le support SimilarWeb")
        print(f"   3. Vérifiez que votre abonnement est actif")

if __name__ == "__main__":
    main()