#!/usr/bin/env python3
"""
Stratégie de backfill pour récupérer toutes les données historiques
"""

def create_backfill_plan():
    """Crée un plan optimisé pour récupérer toutes les données"""
    
    print("PLAN DE RÉCUPÉRATION DES DONNÉES HISTORIQUES")
    print("=" * 60)
    
    # Phase 1: Données mensuelles (plus rapide)
    print("\nPHASE 1: EXTRACTION MENSUELLE (Rapide)")
    print("-" * 40)
    print("Objectif: Vue d'ensemble rapide")
    print("Méthode: Granularité 'monthly'")
    print("Données: 1 point par mois (18 mois)")
    print("Durée: ~1 heure")
    print("\nMois à extraire:")
    
    months = [
        "2024-01", "2024-02", "2024-03", "2024-04", "2024-05", "2024-06",
        "2024-07", "2024-08", "2024-09", "2024-10", "2024-11", "2024-12",
        "2025-01", "2025-02", "2025-03", "2025-04", "2025-05", "2025-06"
    ]
    
    for i, month in enumerate(months):
        if i % 6 == 0:
            print()
        print(f"  {month}", end="")
    
    # Phase 2: Données quotidiennes (plus long)
    print("\n\nPHASE 2: EXTRACTION QUOTIDIENNE (Détaillée)")
    print("-" * 40)
    print("Objectif: Données complètes jour par jour")
    print("Méthode: Granularité 'daily'")
    print("Données: 532 jours")
    print("Durée: ~5-6 heures par batch de 100 jours")
    
    # Stratégie de batch
    print("\nBatches recommandés:")
    print("  Batch 1: Janvier-Mars 2024 (91 jours)")
    print("  Batch 2: Avril-Juin 2024 (91 jours)")
    print("  Batch 3: Juillet-Sept 2024 (92 jours)")
    print("  Batch 4: Oct-Déc 2024 (92 jours)")
    print("  Batch 5: Janvier-Mars 2025 (90 jours)")
    print("  Batch 6: Avril-Juin 2025 (78 jours)")
    
    # Commandes à exécuter
    print("\nCOMMANDES À EXÉCUTER")
    print("-" * 40)
    print("\n# 1. Test avec 1 mois (pour vérifier)")
    print("python3 scripts/historical_backfill.py --start-date 2024-01 --end-date 2024-01 --limit-segments 5")
    
    print("\n# 2. Extraction mensuelle complète")
    print("python3 scripts/historical_backfill.py --start-date 2024-01 --end-date 2025-06 --granularity monthly")
    
    print("\n# 3. Extraction quotidienne par batch")
    print("# Batch 1:")
    print("nohup python3 scripts/historical_backfill.py --start-date 2024-01-01 --end-date 2024-03-31 --granularity daily > batch1.log &")
    
    print("\n# 4. Vérifier les données manquantes après")
    print("python3 scripts/check_missing_data.py")
    
    # Automatisation future
    print("\nAUTOMATISATION FUTURE (Cloud Functions)")
    print("-" * 40)
    print("1. Déployer la Cloud Function avec logique rétroactive")
    print("2. Configurer Cloud Scheduler (quotidien à 2h)")
    print("3. La fonction vérifiera automatiquement J-2 à J-7")
    print("4. Plus jamais de données manquantes !")
    
    print("\nIMPORTANT")
    print("-" * 40)
    print("- Faire les extractions en dehors des heures de pointe")
    print("- Surveiller les quotas API")
    print("- Vérifier régulièrement avec check_missing_data.py")
    print("- Sauvegarder les JSON avant upload BigQuery")

if __name__ == "__main__":
    create_backfill_plan() 