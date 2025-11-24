#!/usr/bin/env python3
"""
Script pour extraire les données des segments utilisateur - Architecture 3 tables
Extraction segments_daily (sans unique_visitors) + segments_unique_visitors (monthly)
pour Mai 2024 et Mai 2025
"""
import sys
import os
import json
from datetime import datetime
import time

# Ajouter le chemin parent pour importer les modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from scripts.similarweb_api import SimilarWebAPI, save_results_to_json


def extract_and_save_segments_three_tables(api_client: SimilarWebAPI, period: dict, 
                                          user_only: bool = True) -> dict:
    """
    Extrait et sauvegarde les segments selon l'architecture 3 tables
    
    Args:
        api_client: Instance du client API
        period: Dictionnaire avec start_date, end_date, label
        user_only: Segments utilisateur uniquement
        
    Returns:
        Statistiques de l'extraction
    """
    print(f"\nExtraction segments 3 tables pour {period['label']}...")
    
    results = {
        'segments_daily': [],
        'segments_unique_visitors': [],
        'stats': {
            'segments_daily': {'total': 0, 'success': 0, 'errors': 0},
            'segments_unique_visitors': {'total': 0, 'success': 0, 'errors': 0}
        }
    }
    
    # 1. Extraction segments_daily (prendre le 15 du mois comme représentatif daily)
    year_month = period['start_date']  # Format YYYY-MM
    mid_month_date = f"{year_month}-15"
    print(f"  1. Segments daily pour {mid_month_date}")
    
    try:
        segments_daily_data = api_client.extract_segments_daily_architecture(
            start_date=mid_month_date,
            end_date=mid_month_date,
            limit=None,  # Pas de limite, on veut tous les segments
            user_only=user_only,
            granularity='daily'
        )
        
        results['segments_daily'] = segments_daily_data
        results['stats']['segments_daily'] = {
            'total': len(segments_daily_data),
            'success': len([s for s in segments_daily_data if not s.get('error')]),
            'errors': len([s for s in segments_daily_data if s.get('error')])
        }
        
        print(f"     → {results['stats']['segments_daily']['success']} segments daily extraits avec succès")
        
    except Exception as e:
        print(f"     → Erreur segments daily: {e}")
        results['stats']['segments_daily']['errors'] = 1
    
    # Pause entre les extractions
    time.sleep(3)
    
    # 2. Extraction segments_unique_visitors (monthly)
    print(f"  2. Segments unique_visitors pour {year_month}")
    
    try:
        segments_uv_data = api_client.extract_segments_unique_visitors_architecture(
            start_date=year_month,
            end_date=year_month,
            limit=None,  # Pas de limite, on veut tous les segments
            user_only=user_only
        )
        
        results['segments_unique_visitors'] = segments_uv_data
        results['stats']['segments_unique_visitors'] = {
            'total': len(segments_uv_data),
            'success': len([s for s in segments_uv_data if not s.get('error')]),
            'errors': len([s for s in segments_uv_data if s.get('error')])
        }
        
        print(f"     → {results['stats']['segments_unique_visitors']['success']} segments unique_visitors extraits avec succès")
        
    except Exception as e:
        print(f"     → Erreur segments unique_visitors: {e}")
        results['stats']['segments_unique_visitors']['errors'] = 1
    
    # Sauvegardes séparées avec timestamp
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    
    # Sauvegarder segments_daily
    if results['segments_daily']:
        filename_daily = f"user_segments_daily_{year_month.replace('-', '')}_{timestamp}.json"
        save_results_to_json(results['segments_daily'], filename_daily)
        print(f"     → Segments daily sauvegardés: {filename_daily}")
    
    # Sauvegarder segments_unique_visitors
    if results['segments_unique_visitors']:
        filename_uv = f"user_segments_unique_visitors_{year_month.replace('-', '')}_{timestamp}.json"
        save_results_to_json(results['segments_unique_visitors'], filename_uv)
        print(f"     → Segments unique_visitors sauvegardés: {filename_uv}")
    
    return results['stats']


def main():
    """
    Fonction principale - Extraction segments utilisateur architecture 3 tables
    """
    print("=" * 70)
    print("EXTRACTION SEGMENTS UTILISATEUR - ARCHITECTURE 3 TABLES")
    print("=" * 70)
    print("Tables de destination:")
    print("  • segments_daily (daily, sans unique_visitors)")
    print("  • segments_unique_visitors (monthly, seulement unique_visitors)")
    print("=" * 70)
    
    # Initialiser le client API
    api = SimilarWebAPI()
    
    # Vérifier d'abord combien de segments nous avons
    print("\nVérification des segments personnels...")
    user_segments = api.get_custom_segments(user_only=True)
    
    if not user_segments:
        print("[ERREUR] Aucun segment utilisateur trouvé!")
        return
        
    print(f"[SUCCESS] {len(user_segments)} segments personnels trouvés")
    
    # Afficher quelques exemples de segments
    print("\nExemples de segments:")
    for i, segment in enumerate(user_segments[:5]):  # Afficher les 5 premiers
        segment_name = segment.get('segment_name', 'N/A')
        segment_id = segment.get('segment_id', 'N/A')
        print(f"  {i+1}. {segment_name} (ID: {segment_id[:20]}...)")
    
    if len(user_segments) > 5:
        print(f"  ... et {len(user_segments) - 5} autres segments")
    
    # Périodes à extraire (Mai 2024 et Mai 2025)
    periods = [
        {'start_date': '2024-05', 'end_date': '2024-05', 'label': 'Mai 2024'},
        {'start_date': '2025-05', 'end_date': '2025-05', 'label': 'Mai 2025'}
    ]
    
    print(f"\nPériodes d'extraction:")
    for period in periods:
        print(f"  • {period['label']} ({period['start_date']})")
    
    # Estimation des appels API
    segments_count = len(user_segments)
    daily_calls = len(periods) * segments_count * 3  # 3 groupes de métriques pour daily
    uv_calls = len(periods) * segments_count * 1     # 1 appel pour unique_visitors
    total_calls = daily_calls + uv_calls
    estimated_time = (total_calls * 1.5) / 60  # 1.5 sec par appel
    
    print(f"\nEstimation:")
    print(f"  • Segments: {segments_count}")
    print(f"  • Appels API daily: {daily_calls}")
    print(f"  • Appels API unique_visitors: {uv_calls}")
    print(f"  • Total appels API: {total_calls}")
    print(f"  • Temps estimé: {estimated_time:.1f} minutes")
    
    # Confirmation
    response = input(f"\nContinuer avec l'extraction? (y/n): ")
    if response.lower() != 'y':
        print("Extraction annulée")
        return
    
    # Statistiques globales
    total_stats = {
        'segments_daily_extracted': 0,
        'segments_uv_extracted': 0,
        'errors_daily': 0,
        'errors_uv': 0,
        'start_time': datetime.now()
    }
    
    # Extraction pour chaque période
    for period in periods:
        try:
            period_stats = extract_and_save_segments_three_tables(
                api_client=api,
                period=period,
                user_only=True
            )
            
            # Agrégation des stats
            total_stats['segments_daily_extracted'] += period_stats['segments_daily']['success']
            total_stats['segments_uv_extracted'] += period_stats['segments_unique_visitors']['success']
            total_stats['errors_daily'] += period_stats['segments_daily']['errors']
            total_stats['errors_uv'] += period_stats['segments_unique_visitors']['errors']
            
            print(f"[SUCCESS] {period['label']} terminé")
            
            # Pause entre les périodes
            if period != periods[-1]:  # Pas de pause après la dernière période
                print("   Pause de 10 secondes...")
                time.sleep(10)
                
        except Exception as e:
            print(f"[ERREUR] Erreur pour {period['label']}: {e}")
            continue
    
    # Résumé final
    duration = (datetime.now() - total_stats['start_time']).total_seconds() / 60
    
    print("\n" + "=" * 70)
    print("EXTRACTION TERMINÉE - ARCHITECTURE 3 TABLES")
    print("=" * 70)
    print(f"Durée totale: {duration:.1f} minutes")
    print(f"Segments utilisateur: {len(user_segments)}")
    print("")
    print("RÉSULTATS PAR TABLE:")
    print(f"  • segments_daily: {total_stats['segments_daily_extracted']} extraits")
    print(f"    (daily, sans unique_visitors)")
    print(f"  • segments_unique_visitors: {total_stats['segments_uv_extracted']} extraits") 
    print(f"    (monthly, seulement unique_visitors)")
    print("")
    
    if total_stats['errors_daily'] > 0 or total_stats['errors_uv'] > 0:
        print("ERREURS:")
        print(f"  • segments_daily: {total_stats['errors_daily']} erreurs")
        print(f"  • segments_unique_visitors: {total_stats['errors_uv']} erreurs")
        print("")
    
    print("FICHIERS CRÉÉS dans le dossier 'data/':")
    print("  • user_segments_daily_*.json")
    print("  • user_segments_unique_visitors_*.json")
    print("")
    print("ÉTAPES SUIVANTES:")
    print("  1. Vérifier les fichiers JSON générés")
    print("  2. Upload vers BigQuery:")
    print("     python scripts/upload_to_bigquery.py --type segments_daily")
    print("     python scripts/upload_to_bigquery.py --type segments_uv")
    print("  3. Ou upload complet:")
    print("     python scripts/upload_to_bigquery.py --type all")
    
    # Créer un résumé détaillé
    summary = {
        'extraction_date': datetime.now().isoformat(),
        'architecture': '3_tables',
        'user_segments_count': len(user_segments),
        'periods_extracted': periods,
        'duration_minutes': duration,
        'results': {
            'segments_daily_extracted': total_stats['segments_daily_extracted'],
            'segments_uv_extracted': total_stats['segments_uv_extracted'],
            'errors_daily': total_stats['errors_daily'],
            'errors_uv': total_stats['errors_uv']
        },
        'tables_destination': {
            'segments_daily': 'données daily sans unique_visitors',
            'segments_unique_visitors': 'données monthly avec seulement unique_visitors'
        },
        'api_calls_estimation': {
            'segments_count': segments_count,
            'daily_calls': daily_calls,
            'uv_calls': uv_calls,
            'total_calls': total_calls
        }
    }
    
    save_results_to_json(summary, 'user_segments_extraction_summary_3_tables.json')
    print(f"\nRésumé détaillé sauvegardé: user_segments_extraction_summary_3_tables.json")
    print("=" * 70)


if __name__ == "__main__":
    main()