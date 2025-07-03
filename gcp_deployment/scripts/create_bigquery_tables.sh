#!/bin/bash
# Script de création des tables BigQuery

PROJECT_ID=${1:-"similarweb-intel-dev"}
DATASET_ID="similarweb_data"

echo "📊 Création du dataset et des tables BigQuery..."

# Créer le dataset
bq mk --dataset --location=EU $PROJECT_ID:$DATASET_ID

# Créer la table segments
bq mk --table \
    --time_partitioning_field extraction_date \
    --time_partitioning_type DAY \
    $PROJECT_ID:$DATASET_ID.segments_data \
    ../bigquery_schemas/segments_schema.json

# Créer la table websites
bq mk --table \
    --time_partitioning_field extraction_date \
    --time_partitioning_type DAY \
    $PROJECT_ID:$DATASET_ID.websites_data \
    ../bigquery_schemas/websites_schema.json

echo "✅ Tables BigQuery créées!"
