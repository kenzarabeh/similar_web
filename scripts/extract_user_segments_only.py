#!/usr/bin/env python3
"""
Script pour extraire les données uniquement des 88 segments de l'utilisateur
pour Mai 2024 et Mai 2025
"""
import sys
import os
import json
from datetime import datetime

# Ajouter le chemin parent pour importer les modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from scripts.similarweb_api import SimilarWebAPI, save_results_to_json
from scripts.daily_extraction import extract_and_save_segments


def main():
    print("🚀 Extraction des données pour VOS 88 segments personnels")
    print("=" * 60)
    
    # Initialiser le client API
    api = SimilarWebAPI()
    
    # Vérifier d'abord combien de segments nous avons
    print("\n📊 Vérification des segments personnels...")
    user_segments = api.get_custom_segments(user_only=True)
    print(f"✅ {len(user_segments)} segments personnels trouvés")
    
    # Périodes à extraire
    periods = [
        {'start_date': '2024-05', 'end_date': '2024-05', 'label': 'Mai 2024'},
        {'start_date': '2025-05', 'end_date': '2025-05', 'label': 'Mai 2025'}
    ]
    
    total_stats = {
        'segments_extracted': 0,
        'errors': 0,
        'start_time': datetime.now()
    }
    
    for period in periods:
        print(f"\n📅 Extraction pour {period['label']}...")
        
        # Extraire et sauvegarder
        stats = extract_and_save_segments(
            api_client=api,
            period={'start_date': period['start_date'], 'end_date': period['end_date']},
            limit=None,  # Pas de limite, on veut tous les 88
            user_only=True  # IMPORTANT: uniquement les segments de l'utilisateur
        )
        
        total_stats['segments_extracted'] += stats['success']
        total_stats['errors'] += stats['errors']
        
        print(f"   ✅ {stats['success']} segments extraits avec succès")
        if stats['errors'] > 0:
            print(f"   ⚠️  {stats['errors']} erreurs")
    
    # Résumé final
    duration = (datetime.now() - total_stats['start_time']).total_seconds() / 60
    print(f"\n{'='*60}")
    print(f"✅ EXTRACTION TERMINÉE")
    print(f"   - Durée totale: {duration:.1f} minutes")
    print(f"   - Segments extraits: {total_stats['segments_extracted']}")
    print(f"   - Erreurs: {total_stats['errors']}")
    print(f"\n💡 Les fichiers JSON sont dans le dossier 'data/'")
    
    # Créer un résumé des segments extraits
    summary = {
        'extraction_date': datetime.now().isoformat(),
        'user_segments_count': len(user_segments),
        'periods_extracted': periods,
        'total_segments_extracted': total_stats['segments_extracted'],
        'total_errors': total_stats['errors'],
        'duration_minutes': duration
    }
    
    save_results_to_json(summary, 'user_segments_extraction_summary.json')
    print(f"📋 Résumé sauvegardé dans 'data/user_segments_extraction_summary.json'")


if __name__ == "__main__":
    main() 