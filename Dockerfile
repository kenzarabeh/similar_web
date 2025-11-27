# Dockerfile optimisé pour SimilarWeb Data Pipeline - Cloud Run
FROM python:3.11-slim

# Variables d'environnement
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PORT=8080

# Installer les dépendances système
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    && rm -rf /var/lib/apt/lists/*

# Définir le répertoire de travail
WORKDIR /app

# Copier requirements.txt EN PREMIER (pour le cache Docker)
COPY requirements.txt .

# Installer les dépendances Python
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Copier tout le code source
COPY . .

# Créer les répertoires nécessaires
RUN mkdir -p data logs

# Exposer le port
EXPOSE 8080

# Commande de démarrage avec gunicorn (plus robuste)
CMD ["gunicorn", \
     "--bind", "0.0.0.0:8080", \
     "--workers", "2", \
     "--threads", "4", \
     "--timeout", "3600", \
     "--access-logfile", "-", \
     "--error-logfile", "-", \
     "scripts.cloud_run_handler:app"]