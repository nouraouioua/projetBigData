#!/bin/bash

# Script pour télécharger les logs NASA Web Server
# Source: https://ita.ee.lbl.gov/html/contrib/NASA-HTTP.html

echo "Telechargement des logs NASA Web Server..."

# Créer le dossier data s'il n'existe pas
mkdir -p data

# Télécharger les fichiers de logs
echo "Téléchargement de Jul 95..."
curl -o data/NASA_access_log_Jul95.gz ftp://ita.ee.lbl.gov/traces/NASA_access_log_Jul95.gz

echo "Téléchargement de Aug 95..."
curl -o data/NASA_access_log_Aug95.gz ftp://ita.ee.lbl.gov/traces/NASA_access_log_Aug95.gz

# Décompresser les fichiers
echo "Decompression des fichiers..."
gunzip -f data/NASA_access_log_Jul95.gz
gunzip -f data/NASA_access_log_Aug95.gz

# Fusionner les deux fichiers
echo "Fusion des fichiers..."
cat data/NASA_access_log_Jul95 data/NASA_access_log_Aug95 > data/NASA_access_log_full.txt

echo "Telechargement termine!"
echo "Statistiques:"
wc -l data/NASA_access_log_full.txt
ls -lh data/
