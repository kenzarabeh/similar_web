# 🚀 Quick Start - SimilarWeb Data Pipeline

## ⏱️ Démarrage en 5 minutes

### 1️⃣ Installation express
```bash
# Cloner/Extraire le projet
cd similarweb_for_data_scientist_*

# Environnement virtuel
python3 -m venv venv
source venv/bin/activate

# Installer les dépendances
pip install -r requirements.txt

# Configuration
cp config/env.example config/.env
# → Éditer config/.env et ajouter votre clé API
```

### 2️⃣ Premier test
```bash
# Extraire les données du mois dernier
python scripts/daily_extraction.py --test_mode

# Si succès, extraire un mois complet
python scripts/daily_extraction.py --year 2025 --month 11
```

### 3️⃣ Vérifier les résultats
```bash
# Les données sont dans data/
ls data/segments/
ls data/websites/
```

## 📁 Structure du projet

```
📦 similarweb_for_data_scientist/
├── 📜 README.md                    # Guide complet
├── 🚀 QUICKSTART_DATA_SCIENTIST.md # Ce fichier
├── ☁️  DEPLOYMENT_GUIDE_GCP.md     # Guide déploiement cloud
├── 🔍 BIGQUERY_QUERIES_EXAMPLES.md # Requêtes SQL utiles
│
├── 📂 scripts/                     # Scripts Python
│   ├── similarweb_api.py          # API wrapper principal
│   ├── daily_extraction.py        # Extraction quotidienne
│   ├── historical_backfill.py     # Récupération historique
│   └── upload_to_bigquery.py      # Upload vers BigQuery
│
├── 📂 gcp_deployment/             # Tout pour GCP
│   ├── cloud_functions/          # Code des fonctions
│   ├── scripts/                  # Scripts de déploiement
│   └── terraform/                # Infrastructure as Code
│
├── 📂 config/                     # Configuration
│   ├── env.example              # Template variables
│   └── config.py                # Config Python
│
├── 📂 docs/                       # Documentation
│   ├── API_DOCUMENTATION.md     # Détails techniques
│   └── AUTOMATISATION_GCP.md    # Guide automatisation
│
└── 📂 notebooks/                  # Jupyter notebooks
    └── SimilarWeb_Exploration.ipynb
```

## 🎯 Cas d'usage principaux

### 📊 Extraction manuelle
```bash
# Mois spécifique
python scripts/daily_extraction.py --year 2025 --month 10

# Historique complet (12 mois)
python scripts/historical_backfill.py

# Segments uniquement
python scripts/extract_user_segments_only.py
```

### ☁️ Upload BigQuery (si GCP configuré)
```bash
# Upload des fichiers JSON locaux
python scripts/upload_to_bigquery.py
```

### 🔄 Automatisation GCP
Voir `DEPLOYMENT_GUIDE_GCP.md` pour le guide complet

## 💡 Tips essentiels

### 🔑 Clé API
- Demandez votre clé à l'équipe
- Testez avec `--test_mode` d'abord
- Quota typique : 10k appels/mois

### 📅 Délai des données
- SimilarWeb a un délai de 7 jours
- Données de novembre disponibles après le 7 décembre

### 🎯 Segments disponibles
- 88 segments personnalisés (avec `userOnlySegments=true`)
- Organisés par secteur : Parapharmacie, High-Tech, etc.

### 📈 Métriques extraites
- **Visits** : Nombre de visites
- **Share** : Part de marché
- **Bounce Rate** : Taux de rebond
- **Pages/Visit** : Pages par visite
- **Duration** : Durée moyenne (secondes)

## 🆘 Problèmes fréquents

| Problème | Solution |
|----------|----------|
| "API Key invalid" | Vérifier la clé dans `config/.env` |
| "Rate limit" | Le script gère automatiquement, patienter |
| Données manquantes | Vérifier le délai de 7 jours |
| Erreur Python | Vérifier Python 3.11+ et dépendances |

## 📞 Support

1. **Documentation** : Voir le dossier `docs/`
2. **Exemples SQL** : Voir `BIGQUERY_QUERIES_EXAMPLES.md`
3. **Notebook** : Explorer avec Jupyter

## ✅ Checklist de démarrage

- [ ] Clé API configurée dans `.env`
- [ ] Test avec `--test_mode` réussi
- [ ] Première extraction complète
- [ ] Données visibles dans `data/`
- [ ] (Optionnel) GCP configuré
- [ ] (Optionnel) BigQuery opérationnel

Bonne analyse ! 🎉 