# 📘 Guide de Déploiement sur Google Cloud Platform

Ce guide vous accompagne pas à pas pour déployer l'automatisation complète sur GCP.

## 🎯 Objectif final

Avoir une extraction automatique quotidienne qui :
- ✅ S'exécute tous les jours à 2h du matin
- ✅ Stocke les données dans BigQuery
- ✅ Gère les erreurs et les rattrapages automatiques
- ✅ Envoie des rapports hebdomadaires

## 📋 Prérequis

1. **Compte Google Cloud** avec facturation activée
2. **Clé API SimilarWeb** valide
3. **gcloud CLI** installé ([guide d'installation](https://cloud.google.com/sdk/docs/install))
4. **Droits administrateur** sur le projet GCP

## 🚀 Étape 1 : Configuration initiale GCP

### 1.1 Créer un nouveau projet
```bash
# Se connecter à GCP
gcloud auth login

# Créer un nouveau projet
gcloud projects create similarweb-data-[votre-nom] --name="SimilarWeb Data Pipeline"

# Définir ce projet comme projet par défaut
gcloud config set project similarweb-data-[votre-nom]
```

### 1.2 Activer les APIs nécessaires
```bash
# Activer les services requis
gcloud services enable cloudfunctions.googleapis.com
gcloud services enable cloudscheduler.googleapis.com
gcloud services enable bigquery.googleapis.com
gcloud services enable cloudbuild.googleapis.com
gcloud services enable storage.googleapis.com
```

### 1.3 Configurer la facturation
```bash
# Lister vos comptes de facturation
gcloud billing accounts list

# Lier le compte de facturation au projet
gcloud billing projects link similarweb-data-[votre-nom] \
  --billing-account=[BILLING_ACCOUNT_ID]
```

## 🗄️ Étape 2 : Configuration BigQuery

### 2.1 Créer le dataset
```bash
# Créer le dataset pour stocker les données
bq mk --dataset \
  --location=EU \
  --description="Données SimilarWeb - Segments et Sites Web" \
  similarweb-data-[votre-nom]:similarweb_data
```

### 2.2 Créer les tables
```bash
# Se placer dans le dossier des scripts GCP
cd gcp_deployment/scripts

# Rendre le script exécutable
chmod +x create_bigquery_tables.sh

# Modifier le PROJECT_ID dans le script
sed -i '' 's/similarweb-intel-dev/similarweb-data-[votre-nom]/g' create_bigquery_tables.sh

# Exécuter le script
./create_bigquery_tables.sh
```

### 2.3 Vérifier les tables
```bash
# Lister les tables créées
bq ls similarweb_data

# Voir le schéma d'une table
bq show similarweb_data.segments_data
```

## ⚙️ Étape 3 : Préparer la Cloud Function

### 3.1 Configurer les variables d'environnement
```bash
cd gcp_deployment/cloud_functions

# Créer le fichier .env.yaml pour la Cloud Function
cat > .env.yaml << EOF
SIMILARWEB_API_KEY: "VOTRE_CLE_API_ICI"
GCP_PROJECT_ID: "similarweb-data-[votre-nom]"
BIGQUERY_DATASET: "similarweb_data"
USER_ONLY_SEGMENTS: "true"
EOF
```

### 3.2 Mettre à jour la configuration
```python
# Éditer config.py pour mettre à jour le PROJECT_ID
# Remplacer 'similarweb-intel-dev' par 'similarweb-data-[votre-nom]'
```

### 3.3 Créer le bucket de stockage
```bash
# Créer un bucket pour les logs et backups
gsutil mb -l EU gs://similarweb-data-[votre-nom]-storage
```

## 🚀 Étape 4 : Déployer la Cloud Function

### 4.1 Déploiement
```bash
# Se placer dans le bon dossier
cd gcp_deployment/scripts

# Modifier le script de déploiement
sed -i '' 's/similarweb-intel-dev/similarweb-data-[votre-nom]/g' deploy_cloud_function.sh

# Déployer la fonction
./deploy_cloud_function.sh
```

### 4.2 Tester la fonction
```bash
# Tester avec un appel manuel
gcloud functions call similarweb-daily-extraction \
  --region=europe-west1 \
  --data='{"test_mode": true}'

# Voir les logs
gcloud functions logs read similarweb-daily-extraction \
  --region=europe-west1 \
  --limit=50
```

## ⏰ Étape 5 : Configurer l'automatisation

### 5.1 Créer les jobs Cloud Scheduler
```bash
cd gcp_deployment/scripts

# Modifier le script pour votre projet
sed -i '' 's/similarweb-intel-dev/similarweb-data-[votre-nom]/g' setup_scheduler_jobs.sh

# Créer les jobs
./setup_scheduler_jobs.sh
```

### 5.2 Jobs créés

1. **similarweb-daily-extraction** (2h00 tous les jours)
   - Extrait les données de J-1

2. **auto-fill-missing** (3h00 le mercredi)
   - Vérifie et remplit les données manquantes

3. **weekly-data-check** (9h00 le lundi)
   - Rapport hebdomadaire de complétude

4. **monthly-report** (10h00 le 1er du mois)
   - Rapport mensuel détaillé

### 5.3 Vérifier les jobs
```bash
# Lister tous les jobs
gcloud scheduler jobs list --location=europe-west1

# Déclencher manuellement un job
gcloud scheduler jobs run similarweb-daily-extraction \
  --location=europe-west1
```

## 📊 Étape 6 : Requêtes BigQuery utiles

### Vérifier les dernières données
```sql
-- Dernières extractions de segments
SELECT 
  DATE(extraction_timestamp) as date,
  COUNT(DISTINCT segment_id) as nb_segments,
  MAX(extraction_timestamp) as derniere_extraction
FROM `similarweb-data-[votre-nom].similarweb_data.segments_data`
WHERE DATE(extraction_timestamp) >= DATE_SUB(CURRENT_DATE(), INTERVAL 7 DAY)
GROUP BY date
ORDER BY date DESC;
```

### Analyser un segment spécifique
```sql
-- Evolution d'un segment
SELECT 
  segment_name,
  date,
  visits,
  share,
  bounce_rate
FROM `similarweb-data-[votre-nom].similarweb_data.segments_data`
WHERE segment_name LIKE '%Leclerc%'
ORDER BY date DESC
LIMIT 30;
```

## 🔍 Étape 7 : Monitoring et alertes

### 7.1 Configurer les métriques
```bash
# Créer une alerte si la fonction échoue
gcloud alpha monitoring policies create \
  --notification-channels=[YOUR_CHANNEL_ID] \
  --display-name="SimilarWeb Extraction Failed" \
  --condition-display-name="Function Error Rate > 0" \
  --condition-metric-type="cloudfunctions.googleapis.com/function/error_count"
```

### 7.2 Dashboard de monitoring
1. Aller dans la Console GCP > Monitoring
2. Créer un nouveau dashboard
3. Ajouter les métriques :
   - Exécutions de Cloud Functions
   - Erreurs de Cloud Functions
   - Requêtes BigQuery
   - Stockage utilisé

## 🚨 Dépannage

### Problème : "Permission denied"
```bash
# Donner les permissions nécessaires
gcloud projects add-iam-policy-binding similarweb-data-[votre-nom] \
  --member="serviceAccount:similarweb-data-[votre-nom]@appspot.gserviceaccount.com" \
  --role="roles/bigquery.dataEditor"
```

### Problème : "Quota exceeded"
- Vérifier dans Console > IAM & Admin > Quotas
- Augmenter les quotas si nécessaire

### Problème : Données manquantes
```bash
# Vérifier l'état d'une extraction spécifique
bq query --use_legacy_sql=false '
SELECT * 
FROM `similarweb-data-[votre-nom].similarweb_data.segments_data`
WHERE DATE(extraction_timestamp) = "2025-01-15"
LIMIT 10'
```

## 💰 Estimation des coûts

- **Cloud Functions** : ~0.50€/mois (400 exécutions)
- **Cloud Scheduler** : Gratuit (< 3 jobs)
- **BigQuery Storage** : ~1€/mois (< 10 GB)
- **BigQuery Queries** : ~2€/mois
- **Total estimé** : < 5€/mois

## ✅ Checklist finale

- [ ] Projet GCP créé et configuré
- [ ] APIs activées
- [ ] BigQuery dataset et tables créés
- [ ] Cloud Function déployée
- [ ] Cloud Scheduler jobs actifs
- [ ] Test d'extraction réussi
- [ ] Données visibles dans BigQuery
- [ ] Monitoring configuré

## 🎉 Félicitations !

Votre pipeline est maintenant opérationnel. Les données seront extraites automatiquement chaque jour à 2h du matin.

### Prochaines étapes suggérées
1. Connecter un outil de BI (Looker, Tableau, etc.)
2. Créer des alertes sur les variations importantes
3. Développer des modèles prédictifs
4. Automatiser les rapports

Pour toute question, consultez la documentation dans le dossier `docs/`. 