# Dockerfile optimisé pour SimilarWeb Data Pipeline - Cloud Run
# Version corrigée avec Flask et toutes les dépendances

FROM python:3.11-slim

# Variables d'environnement pour Python
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PORT=8080

# Installer les dépendances système nécessaires
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    && rm -rf /var/lib/apt/lists/*

# Définir le répertoire de travail
WORKDIR /app

# IMPORTANT : Copier requirements.txt EN PREMIER
# Cela permet de profiter du cache Docker
COPY requirements.txt .

# Installer les dépendances Python
# Utiliser --no-cache-dir pour réduire la taille de l'image
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Copier tout le code source
COPY . .

# Créer les répertoires nécessaires
RUN mkdir -p data logs

# Exposer le port pour Cloud Run
EXPOSE 8080

# Health check (optionnel mais recommandé)
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD python -c "import requests; requests.get('http://localhost:8080/')" || exit 1

# Commande de démarrage
# Note : Cloud Run override cette commande mais c'est une bonne pratique de la mettre
CMD ["python", "scripts/cloud_run_handler.py"]