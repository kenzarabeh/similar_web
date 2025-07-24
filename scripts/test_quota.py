#!/usr/bin/env python3
"""
Test pour vérifier si le problème est lié au quota API
"""
import requests
import sys
import os
from datetime import datetime

# Ajouter le chemin parent pour importer la config
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

def test_quota_with_both_keys():
    """Test avec les deux clés API pour voir si c'est un problème de quota général"""
    
    print("🔍 TEST DE QUOTA - DEUX CLÉS API")
    print("=" * 50)
    
    # Les deux clés API vues dans les logs
    old_key = "dc5e226abe0b4ba8bb506e192f61186a"  # Clé qui marchait ce matin
    new_key = "cf28c9c5f0fe4feebf3066d92a70e3c3"   # Nouvelle clé
    
    keys_to_test = [
        ("Ancienne clé (marchait ce matin)", old_key),
        ("Nouvelle clé (109 segments)", new_key)
    ]
    
    for key_name, api_key in keys_to_test:
        print(f"\n🧪 Test {key_name}")
        print(f"Clé: {api_key[:8]}...{api_key[-8:]}")
        
        # Test avec l'endpoint le plus simple
        url = "https://api.similarweb.com/v1/segment/traffic-and-engagement/describe/"
        params = {
            'api_key': api_key,
            'userOnlySegments': 'true'
        }
        
        try:
            response = requests.get(url, params=params, timeout=5)
            
            if response.status_code == 200:
                data = response.json()
                if 'response' in data and 'segments' in data['response']:
                    segments_count = len(data['response']['segments'])
                    print(f"✅ Clé valide - {segments_count} segments trouvés")
                    
                    # Test un appel de données (plus lourd)
                    if segments_count > 0:
                        test_data_extraction(api_key, data['response']['segments'][0])
                else:
                    print(f"⚠️  Réponse inattendue: {data}")
                    
            elif response.status_code == 403:
                print(f"❌ 403 Forbidden")
                print(f"   Causes possibles:")
                print(f"   - Quota API dépassé")
                print(f"   - Clé API expirée/suspendue")
                print(f"   - Restrictions d'accès")
                
            elif response.status_code == 429:
                print(f"❌ 429 Rate Limit")
                print(f"   Quota définitivement dépassé")
                
            else:
                print(f"❌ Erreur {response.status_code}: {response.text[:100]}")
                
        except Exception as e:
            print(f"❌ Erreur de connexion: {e}")

def test_data_extraction(api_key, first_segment):
    """Test d'extraction de données réelles"""
    
    segment_id = first_segment.get('segment_id')
    segment_name = first_segment.get('segment_name', 'N/A')
    
    print(f"  🔬 Test extraction données: {segment_name}")
    
    url = f"https://api.similarweb.com/v1/segment/{segment_id}/total-traffic-and-engagement/query"
    params = {
        'start_date': '2025-06',  # Mois récent
        'end_date': '2025-06',
        'country': 'fr',
        'granularity': 'monthly',
        'metrics': 'visits',
        'api_key': api_key
    }
    
    try:
        response = requests.get(url, params=params, timeout=5)
        
        if response.status_code == 200:
            print(f"  ✅ Extraction OK")
            return True
        elif response.status_code == 403:
            print(f"  ❌ 403 - Quota probablement dépassé")
            return False
        else:
            print(f"  ❌ Erreur {response.status_code}")
            return False
            
    except Exception as e:
        print(f"  ❌ Erreur: {e}")
        return False

def check_files_created_today():
    """Compter les fichiers d'extraction créés aujourd'hui pour estimer les appels API"""
    
    print(f"\n📁 FICHIERS CRÉÉS AUJOURD'HUI")
    print("=" * 40)
    
    today = datetime.now().strftime('%Y%m%d')
    
    import glob
    
    # Compter les fichiers d'extraction d'aujourd'hui
    patterns = [
        f"data/*extraction*{today}*.json",
        f"data/*backfill*{today}*.json"
    ]
    
    total_files = 0
    for pattern in patterns:
        files = glob.glob(pattern)
        total_files += len(files)
        if files:
            print(f"📄 {len(files)} fichiers correspondant à {pattern}")
            for file in files[:5]:  # Montrer les 5 premiers
                print(f"   - {os.path.basename(file)}")
            if len(files) > 5:
                print(f"   ... et {len(files) - 5} autres")
    
    print(f"\n📊 Total fichiers aujourd'hui: {total_files}")
    
    # Estimation des appels API
    estimated_calls = total_files * 10  # Estimation conservative
    print(f"📞 Appels API estimés: ~{estimated_calls}")
    
    if estimated_calls > 100:
        print(f"⚠️  Vous avez probablement fait beaucoup d'appels API aujourd'hui")
    
    return total_files

def main():
    """Test complet"""
    
    print(f"🕐 Test effectué le: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    # Compter l'activité d'aujourd'hui
    files_count = check_files_created_today()
    
    # Tester les deux clés API
    test_quota_with_both_keys()
    
    # Conclusion
    print(f"\n📋 DIAGNOSTIC QUOTA")
    print("=" * 30)
    print(f"Si TOUTES les clés donnent 403:")
    print(f"  👉 Quota journalier dépassé")
    print(f"  👉 Attendre demain (reset à minuit)")
    print(f"  👉 Ou contacter SimilarWeb pour augmenter le quota")
    print(f"\nSi une clé marche et pas l'autre:")
    print(f"  👉 Problème spécifique à une clé")
    print(f"  👉 Utiliser la clé qui fonctionne")
    
    print(f"\n💡 SOLUTIONS:")
    print(f"1. Attendre demain matin pour réessayer")
    print(f"2. Vérifier le quota sur account.similarweb.com")
    print(f"3. Utiliser les données déjà extraites en attendant")

if __name__ == "__main__":
    main()