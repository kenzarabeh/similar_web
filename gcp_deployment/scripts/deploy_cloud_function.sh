#!/bin/bash
# Script de déploiement Cloud Function

PROJECT_ID=${1:-"similarweb-intel-dev"}
FUNCTION_NAME="similarweb-daily-extraction"
REGION="europe-west1"

echo "🚀 Déploiement de la Cloud Function..."

cd ../cloud_functions

gcloud functions deploy $FUNCTION_NAME \
    --runtime python311 \
    --trigger-http \
    --entry-point main \
    --memory 512MB \
    --timeout 540s \
    --region $REGION \
    --project $PROJECT_ID \
    --set-env-vars SIMILARWEB_API_KEY=$SIMILARWEB_API_KEY,GCP_PROJECT_ID=$PROJECT_ID,USER_ONLY_SEGMENTS=true \
    --allow-unauthenticated

echo "✅ Cloud Function déployée!"
