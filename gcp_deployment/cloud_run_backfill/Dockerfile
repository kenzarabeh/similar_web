FROM python:3.11-slim

WORKDIR /app

# Copier les fichiers nécessaires
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copier le code
COPY config/ ./config/
COPY scripts/ ./scripts/
COPY config.py .

# Créer les dossiers nécessaires
RUN mkdir -p data logs

# Script d'entrée
COPY run_backfill_cloud.py .

CMD ["python", "run_backfill_cloud.py"] 