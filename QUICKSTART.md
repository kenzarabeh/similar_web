# 🚀 Guide de Démarrage Rapide - SimilarWeb Intelligence Platform

## 📋 Prérequis

- Python 3.11+
- Clé API SimilarWeb (REST)
- Compte Google Cloud Platform (pour la phase de déploiement)

## 🎯 Étapes pour démarrer

### 1️⃣ Installation locale (5 minutes)

```bash
# Cloner ou télécharger le projet
cd similarweb_project

# Créer un environnement virtuel
python -m venv venv
source venv/bin/activate  # Mac/Linux
# ou
venv\Scripts\activate     # Windows

# Installer les dépendances
pip install -r requirements.txt
```

### 2️⃣ Configuration de l'API (2 minutes)

Créer un fichier `.env` à la racine :
```env
SIMILARWEB_API_KEY=votre_cle_api_rest_ici
```

Ou modifier directement `config/config.py` :
```python
SIMILARWEB_API_KEY = 'votre_cle_api_rest_ici'
```

### 3️⃣ Test du système (3 minutes)

```bash
# Vérifier que tout fonctionne
python test_local.py
```

Si tous les tests passent ✅, vous êtes prêt !

### 4️⃣ Première extraction (5-10 minutes)

```bash
# Mode test (10 segments seulement)
python scripts/daily_extraction.py --test

# Extraction complète pour avril 2024
python scripts/daily_extraction.py --start-date 2024-04 --end-date 2024-04
```

Les données seront sauvegardées dans `data/` :
- `segments_extraction_*.json`
- `websites_extraction_*.json`
- `extraction_summary_latest.json`

## 📊 Exploitation des données

### Analyser avec Jupyter

```bash
jupyter notebook notebooks/SimilarWeb_Exploration.ipynb
```

### Données extraites

**Segments** (138 segments personnalisés) :
- Visites mensuelles
- Part de marché

**Sites Web** (amazon.fr, joueclub.fr) :
- Visites
- Pages par visite
- Durée moyenne
- Taux de rebond
- Pages vues
- Répartition Desktop/Mobile

## 🌤️ Déploiement GCP (Phase suivante)

### Préparer le déploiement

```bash
python scripts/prepare_gcp_deployment.py
```

Cela créera :
- 📁 `gcp_deployment/cloud_functions/` - Code pour Cloud Functions
- 📁 `gcp_deployment/bigquery_schemas/` - Schémas des tables
- 📁 `gcp_deployment/terraform/` - Infrastructure as Code
- 📁 `gcp_deployment/scripts/` - Scripts de déploiement

### Déployer sur GCP

1. **Configurer GCP CLI** :
```bash
gcloud auth login
gcloud config set project votre-projet-gcp
```

2. **Créer les tables BigQuery** :
```bash
cd gcp_deployment/scripts
./create_bigquery_tables.sh votre-projet-gcp
```

3. **Déployer la Cloud Function** :
```bash
export SIMILARWEB_API_KEY=votre_cle_api
./deploy_cloud_function.sh votre-projet-gcp
```

## 🆘 Dépannage

### Erreur "Module not found"
```bash
# Assurez-vous d'être dans le bon dossier
cd similarweb_project
# Et que l'environnement virtuel est activé
source venv/bin/activate
```

### Erreur API 401
- Vérifiez votre clé API dans `.env`
- Assurez-vous d'utiliser la clé REST (pas Batch)

### Erreur API 429 (Rate Limit)
- Le script gère automatiquement les retry
- Attendez quelques secondes entre les exécutions

## 📞 Support

- **Documentation API** : https://developers.similarweb.com/
- **Ce projet** : Voir README.md pour plus de détails

---

💡 **Conseil** : Commencez avec le mode test (`--test`) pour valider votre configuration sans consommer trop de crédits API. 