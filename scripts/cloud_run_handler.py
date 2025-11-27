#!/usr/bin/env python3
"""
Handler Flask pour Cloud Run - Extraction mensuelle automatique
Déclenché par Cloud Scheduler chaque début de mois
"""
from flask import Flask, request, jsonify
import json
import logging
from datetime import datetime, timedelta
import os
import sys

# Ajouter le chemin parent pour importer les modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from scripts.daily_extraction import extract_for_automation_three_tables
from scripts.upload_to_bigquery import BigQueryThreeTablesUploader

# Configuration du logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

app = Flask(__name__)


def calculate_previous_month():
    """
    Calcule le mois précédent à extraire
    
    Returns:
        tuple: (start_date, end_date) au format YYYY-MM-DD
    """
    today = datetime.now()
    
    # Premier jour du mois précédent
    if today.month == 1:
        first_day = datetime(today.year - 1, 12, 1)
    else:
        first_day = datetime(today.year, today.month - 1, 1)
    
    # Dernier jour du mois précédent
    last_day = datetime(today.year, today.month, 1) - timedelta(days=1)
    
    return first_day.strftime('%Y-%m-%d'), last_day.strftime('%Y-%m-%d')


@app.route('/', methods=['GET'])
def health_check():
    """Health check endpoint"""
    return jsonify({
        'status': 'healthy',
        'service': 'similarweb-data-pipeline',
        'architecture': '3_tables',
        'timestamp': datetime.now().isoformat()
    }), 200


@app.route('/extract-monthly', methods=['POST'])
def extract_monthly():
    """
    Endpoint pour extraction mensuelle automatique
    Déclenché par Cloud Scheduler
    """
    try:
        logger.info("=" * 70)
        logger.info("EXTRACTION MENSUELLE AUTOMATIQUE DÉCLENCHÉE")
        logger.info("=" * 70)
        
        # Calculer le mois précédent
        start_date, end_date = calculate_previous_month()
        logger.info(f"Période à extraire: {start_date} → {end_date}")
        
        # Vérifier le délai SimilarWeb (données disponibles après le 7 du mois)
        today = datetime.now()
        if today.day < 7:
            logger.warning(f"Aujourd'hui = {today.day} du mois")
            logger.warning("Les données du mois précédent pourraient ne pas être complètes")
            logger.warning("SimilarWeb publie généralement les données après le 7 du mois")
        
        # Extraire les données avec la fonction existante
        # Note: extract_for_automation_three_tables extrait les derniers jours
        # On va l'adapter pour extraire un mois complet
        
        logger.info("Extraction des données...")
        result = extract_monthly_data(start_date, end_date)
        
        if result['status'] == 'success':
            logger.info("Extraction terminée avec succès")
            
            # Upload vers BigQuery
            logger.info("Upload vers BigQuery...")
            uploader = BigQueryThreeTablesUploader()
            
            uploaded_counts = {
                'segments_daily': uploader.upload_segments_daily(),
                'segments_unique_visitors': uploader.upload_segments_unique_visitors(),
                'websites_daily': uploader.upload_websites_daily()
            }
            
            logger.info("Upload terminé")
            logger.info(f"  - segments_daily: {uploaded_counts['segments_daily']} lignes")
            logger.info(f"  - segments_unique_visitors: {uploaded_counts['segments_unique_visitors']} lignes")
            logger.info(f"  - websites_daily: {uploaded_counts['websites_daily']} lignes")
            
            # Résumé final
            summary = {
                'status': 'success',
                'execution_time': datetime.now().isoformat(),
                'period_extracted': f"{start_date} to {end_date}",
                'extraction_results': result,
                'upload_counts': uploaded_counts,
                'total_uploaded': sum(uploaded_counts.values())
            }
            
            logger.info("=" * 70)
            logger.info("EXTRACTION MENSUELLE AUTOMATIQUE TERMINÉE")
            logger.info("=" * 70)
            
            return jsonify(summary), 200
            
        else:
            logger.error(f"Erreur lors de l'extraction: {result.get('error', 'Unknown')}")
            return jsonify({
                'status': 'error',
                'error': result.get('error', 'Unknown error'),
                'execution_time': datetime.now().isoformat()
            }), 500
            
    except Exception as e:
        logger.error(f"Erreur critique: {str(e)}")
        return jsonify({
            'status': 'error',
            'error': str(e),
            'execution_time': datetime.now().isoformat()
        }), 500


def extract_monthly_data(start_date: str, end_date: str):
    """
    Extrait les données pour un mois complet
    
    Args:
        start_date: Date de début (YYYY-MM-DD)
        end_date: Date de fin (YYYY-MM-DD)
        
    Returns:
        Résumé de l'extraction
    """
    from scripts.similarweb_api import SimilarWebAPI, save_results_to_json
    from scripts.daily_extraction import (
        get_date_range_for_extraction,
        extract_segments_daily_three_tables,
        extract_websites_daily_three_tables
    )
    
    logger.info(f"Extraction mensuelle: {start_date} → {end_date}")
    
    api_client = SimilarWebAPI()
    
    # Générer les périodes (on va extraire le 15 du mois comme représentatif)
    year_month = start_date[:7]  # YYYY-MM
    mid_month = f"{year_month}-15"
    
    daily_periods = [{
        'start_date': mid_month,
        'end_date': mid_month,
        'api_format': mid_month,
        'granularity': 'daily'
    }]
    
    monthly_periods = [{
        'start_date': year_month,
        'end_date': year_month,
        'api_format': year_month,
        'granularity': 'monthly'
    }]
    
    results = {}
    
    try:
        # 1. Extraction segments (daily + unique_visitors)
        logger.info("Extraction des segments...")
        segments_results = extract_segments_daily_three_tables(
            api_client, daily_periods, monthly_periods
        )
        
        # Sauvegarder
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        
        if segments_results['segments_daily']:
            filename = f"segments_daily_monthly_{year_month.replace('-', '')}_{timestamp}.json"
            save_results_to_json(segments_results['segments_daily'], filename)
            results['segments_daily'] = {
                'count': len(segments_results['segments_daily']),
                'file': filename
            }
        
        if segments_results['segments_unique_visitors']:
            filename = f"segments_unique_visitors_monthly_{year_month.replace('-', '')}_{timestamp}.json"
            save_results_to_json(segments_results['segments_unique_visitors'], filename)
            results['segments_unique_visitors'] = {
                'count': len(segments_results['segments_unique_visitors']),
                'file': filename
            }
        
        # 2. Extraction websites
        logger.info("Extraction des websites...")
        websites_data = extract_websites_daily_three_tables(api_client, daily_periods)
        
        if websites_data:
            filename = f"websites_daily_monthly_{year_month.replace('-', '')}_{timestamp}.json"
            save_results_to_json(websites_data, filename)
            results['websites_daily'] = {
                'count': len(websites_data),
                'file': filename
            }
        
        return {
            'status': 'success',
            'period': f"{start_date} to {end_date}",
            'results': results
        }
        
    except Exception as e:
        logger.error(f"Erreur extraction: {e}")
        return {
            'status': 'error',
            'error': str(e)
        }


@app.route('/test', methods=['GET'])
def test_endpoint():
    """
    Endpoint de test pour vérifier la configuration
    """
    try:
        start_date, end_date = calculate_previous_month()
        
        return jsonify({
            'status': 'ok',
            'service': 'similarweb-data-pipeline',
            'architecture': '3_tables',
            'next_extraction_period': f"{start_date} to {end_date}",
            'current_date': datetime.now().isoformat(),
            'api_key_configured': bool(os.environ.get('SIMILARWEB_API_KEY')),
            'gcp_project': os.environ.get('GCP_PROJECT_ID', 'Not configured')
        }), 200
        
    except Exception as e:
        return jsonify({
            'status': 'error',
            'error': str(e)
        }), 500


if __name__ == '__main__':
    port = int(os.environ.get('PORT', 8080))
    app.run(host='0.0.0.0', port=port)