#!/usr/bin/env python3
"""
Script pour vérifier toutes les données manquantes depuis janvier 2024
"""
from datetime import datetime, date, timedelta
from google.cloud import bigquery

def check_missing_data():
    """Vérifie quelles données sont manquantes pour 2024 et 2025"""
    
    # Dates de début et fin
    start_date = date(2024, 1, 1)
    end_date = datetime.now().date() - timedelta(days=3)  # J-3 (délai SimilarWeb)
    
    # Initialiser BigQuery
    client = bigquery.Client(project='similarweb-intel-dev')
    
    # Récupérer les dates existantes
    query = """
    SELECT DISTINCT DATE(date) as existing_date
    FROM `similarweb-intel-dev.similarweb_data.segments_data`
    ORDER BY existing_date
    """
    
    existing_dates = set()
    for row in client.query(query).result():
        existing_dates.add(row.existing_date)
    
    print("📊 ANALYSE DES DONNÉES MANQUANTES")
    print("=" * 60)
    print(f"Période analysée: {start_date} à {end_date}")
    print(f"Données existantes: {len(existing_dates)} jours")
    print(f"Jours dans BigQuery: {sorted(existing_dates)}")
    
    # Calculer les données manquantes par mois
    current = start_date
    missing_by_month = {}
    total_missing = 0
    
    while current <= end_date:
        month_key = current.strftime('%Y-%m')
        if month_key not in missing_by_month:
            missing_by_month[month_key] = []
        
        if current not in existing_dates:
            missing_by_month[month_key].append(current)
            total_missing += 1
        
        current += timedelta(days=1)
    
    print(f"\n❌ DONNÉES MANQUANTES: {total_missing} jours")
    print("-" * 60)
    
    # Afficher par mois
    for month, days in missing_by_month.items():
        if days:
            print(f"\n📅 {month}: {len(days)} jours manquants")
            if len(days) <= 5:  # Afficher les dates si peu nombreuses
                for day in days:
                    print(f"   - {day}")
            else:
                print(f"   - Du {days[0]} au {days[-1]}")
    
    # Estimation du temps et coût
    print(f"\n💰 ESTIMATION POUR RÉCUPÉRER TOUTES LES DONNÉES")
    print("-" * 60)
    
    # Pour l'extraction quotidienne, on utilise la granularité 'daily'
    # Ce qui nécessite de faire des appels mois par mois
    months_to_extract = len(missing_by_month)
    api_calls = months_to_extract * 88 * 3  # 88 segments × 3 métriques
    time_estimate = (api_calls * 1.5) / 60  # 1.5 secondes par appel
    
    print(f"📅 Mois à extraire: {months_to_extract}")
    print(f"📞 Appels API estimés: {api_calls:,}")
    print(f"⏱️  Temps estimé: {time_estimate:.1f} heures")
    print(f"💵 Coût estimé: ~${api_calls * 0.001:.2f} (à $0.001/appel)")
    
    # Stratégie recommandée
    print(f"\n🎯 STRATÉGIE RECOMMANDÉE")
    print("-" * 60)
    print("1. BACKFILL HISTORIQUE (une fois)")
    print("   - Extraire toutes les données 2024 (par mois)")
    print("   - Extraire données 2025 jusqu'à aujourd'hui")
    print("   - Durée: ~1-2 jours en plusieurs batches")
    print("\n2. EXTRACTION QUOTIDIENNE (automatique)")
    print("   - Cloud Function qui vérifie J-2 à J-7")
    print("   - Récupère automatiquement les données manquantes")
    print("   - Coût: ~$0.50/jour")
    
    return {
        'total_days_expected': (end_date - start_date).days + 1,
        'days_existing': len(existing_dates),
        'days_missing': total_missing,
        'missing_by_month': missing_by_month
    }

if __name__ == "__main__":
    result = check_missing_data() 