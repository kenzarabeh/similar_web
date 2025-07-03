#!/bin/bash
# Script de configuration des jobs Cloud Scheduler

PROJECT_ID="similarweb-intel-dev"
REGION="europe-west1"

echo "🕐 Configuration des jobs Cloud Scheduler..."

# 1. Extraction quotidienne (déjà existante)
echo "✅ Job extraction quotidienne déjà configuré"

# 2. Vérification hebdomadaire (tous les lundis à 9h)
gcloud scheduler jobs create http weekly-data-check \
    --location=$REGION \
    --schedule="0 9 * * 1" \
    --time-zone="Europe/Paris" \
    --uri="https://europe-west1-similarweb-intel-dev.cloudfunctions.net/similarweb-data-checker" \
    --http-method=POST \
    --headers="Content-Type=application/json" \
    --message-body='{"action":"weekly_check"}' \
    --description="Vérification hebdomadaire de la complétude des données"

# 3. Rapport mensuel (le 1er de chaque mois à 10h)
gcloud scheduler jobs create http monthly-report \
    --location=$REGION \
    --schedule="0 10 1 * *" \
    --time-zone="Europe/Paris" \
    --uri="https://europe-west1-similarweb-intel-dev.cloudfunctions.net/similarweb-data-checker" \
    --http-method=POST \
    --headers="Content-Type=application/json" \
    --message-body='{"action":"monthly_report"}' \
    --description="Rapport mensuel détaillé"

# 4. Rattrapage automatique (tous les mercredis à 3h du matin)
gcloud scheduler jobs create http auto-fill-missing \
    --location=$REGION \
    --schedule="0 3 * * 3" \
    --time-zone="Europe/Paris" \
    --uri="https://europe-west1-similarweb-intel-dev.cloudfunctions.net/similarweb-data-checker" \
    --http-method=POST \
    --headers="Content-Type=application/json" \
    --message-body='{"action":"auto_fill","lookback_days":7}' \
    --description="Rattrapage automatique des données manquantes"

echo "✅ Jobs Cloud Scheduler configurés!" 