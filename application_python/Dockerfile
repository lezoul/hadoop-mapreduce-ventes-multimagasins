# image de départ : Linux minimal avec Python 3.14 (même version que sous Windows)
FROM python:3.14-slim

# dossier de travail dans l'image
WORKDIR /app

# 1) les dépendances d'abord : cette couche est réutilisée tant que requirements.txt ne change pas
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 2) le code de l'application et son thème
COPY app.py lecture_resultats.py ./
COPY .streamlit/ ./.streamlit/

# l'application lira les résultats MapReduce dans ce dossier (fourni par un volume au lancement)
ENV DOSSIER_RESULTATS=/app/resultats

# port de Streamlit
EXPOSE 8501

# commande lancée au démarrage du conteneur
CMD ["streamlit", "run", "app.py", "--server.address=0.0.0.0", "--server.port=8501", "--server.headless=true"]
