#!/bin/bash

# Script de lancement automatique complet
# Ce script configure et lance l'analyse complète

set -e  # Arrêter en cas d'erreur

echo "================================"
echo "LANCEMENT ANALYSE LOGS WEB"
echo "================================"

# Couleurs
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Fonction pour afficher les messages
print_success() {
    echo -e "${GREEN}[OK] $1${NC}"
}

print_error() {
    echo -e "${RED}[ERROR] $1${NC}"
}

print_info() {
    echo -e "${YELLOW}[INFO] $1${NC}"
}

# 1. Vérifier Python
print_info "Vérification de Python..."
if ! command -v python3 &> /dev/null; then
    print_error "Python 3 n'est pas installé"
    exit 1
fi
PYTHON_VERSION=$(python3 --version)
print_success "Python trouvé: $PYTHON_VERSION"

# 2. Vérifier Java
print_info "Vérification de Java..."
if ! command -v java &> /dev/null; then
    print_error "Java n'est pas installé. Installez Java 8 ou 11."
    exit 1
fi
JAVA_VERSION=$(java -version 2>&1 | head -n 1)
print_success "Java trouvé: $JAVA_VERSION"

# 3. Créer l'environnement virtuel si nécessaire
if [ ! -d "venv" ]; then
    print_info "Création de l'environnement virtuel..."
    python3 -m venv venv
    print_success "Environnement virtuel créé"
fi

# 4. Activer l'environnement virtuel
print_info "Activation de l'environnement virtuel..."
source venv/bin/activate

# 5. Installer les dépendances
print_info "Installation des dépendances..."
pip install --quiet --upgrade pip
pip install --quiet -r requirements.txt
print_success "Dépendances installées"

# 6. Vérifier si les données existent
if [ ! -f "data/NASA_access_log_full.txt" ]; then
    print_info "Les données n'existent pas. Téléchargement..."
    chmod +x download_data.sh
    ./download_data.sh
    print_success "Données téléchargées"
else
    print_success "Données trouvées"
fi

# 7. Créer les répertoires de sortie
print_info "Création des répertoires de sortie..."
mkdir -p output/parquet
mkdir -p output/metrics/json
mkdir -p output/metrics/csv
mkdir -p output/checkpoints
print_success "Répertoires créés"

# 8. Lancer l'analyse
print_info "Lancement de l'analyse..."
echo "================================"

# Choix du mode
if [ "$1" == "--batch" ]; then
    print_info "Mode: BATCH seulement"
    python3 main.py --mode batch
elif [ "$1" == "--streaming" ]; then
    print_info "Mode: STREAMING seulement"
    python3 main.py --mode streaming
elif [ "$1" == "--prometheus" ]; then
    print_info "Mode: BATCH avec export Prometheus"
    python3 main.py --mode batch --export-prometheus
else
    print_info "Mode: COMPLET (batch + streaming)"
    python3 main.py --mode all
fi

echo "================================"
print_success "ANALYSE TERMINÉE!"
echo "================================"

# 9. Afficher les résultats
print_info "Résultats disponibles dans:"
echo "  - output/parquet/       (KPI en Parquet)"
echo "  - output/metrics/       (Exports Grafana)"
echo "  - output/graph_*/       (Graphe IP-URL)"

echo ""
print_info "Commandes utiles:"
echo "  - Voir les IPs suspectes:  ls -lh output/parquet/suspicious_ips/"
echo "  - Voir les top URLs:       ls -lh output/parquet/top_urls/"
echo "  - Lancer Jupyter:          jupyter notebook notebooks/analysis.ipynb"
echo "  - Voir ce guide:           cat QUICKSTART.md"

echo ""
print_success "Projet prêt à être exploré!"
