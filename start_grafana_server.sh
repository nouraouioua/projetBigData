#!/bin/bash

# Script pour démarrer un serveur HTTP pour les métriques Grafana
# Alternative au mode local CSV de Grafana

echo "======================================================================"
echo "🚀 SERVEUR HTTP POUR MÉTRIQUES GRAFANA"
echo "======================================================================"
echo ""

# Vérifier si le dossier existe
if [ ! -d "output/metrics" ]; then
    echo "❌ Erreur: Le dossier output/metrics n'existe pas"
    echo "   Exécutez d'abord: python main.py"
    exit 1
fi

# Vérifier si des fichiers existent
CSV_COUNT=$(find output/metrics/csv -name "*.csv" 2>/dev/null | wc -l)
JSON_COUNT=$(find output/metrics/json -name "*.json" 2>/dev/null | wc -l)

echo "📊 Métriques disponibles:"
echo "   CSV:  $CSV_COUNT fichiers"
echo "   JSON: $JSON_COUNT fichiers"
echo ""

if [ $CSV_COUNT -eq 0 ] && [ $JSON_COUNT -eq 0 ]; then
    echo "⚠️  Aucune métrique trouvée. Exécutez d'abord:"
    echo "   python main.py"
    echo ""
    exit 1
fi

# Choisir le port
PORT=8080

# Vérifier si le port est disponible
if lsof -Pi :$PORT -sTCP:LISTEN -t >/dev/null ; then
    echo "⚠️  Le port $PORT est déjà utilisé"
    PORT=8081
    echo "   Utilisation du port $PORT à la place"
fi

echo "======================================================================"
echo "✅ Serveur démarré sur: http://localhost:$PORT"
echo "======================================================================"
echo ""
echo "📁 Répertoires disponibles:"
echo "   CSV:  http://localhost:$PORT/csv/"
echo "   JSON: http://localhost:$PORT/json/"
echo ""
echo "📖 Configuration Grafana:"
echo "   1. Installer le plugin: grafana-cli plugins install yesoreyeram-infinity-datasource"
echo "   2. Redémarrer Grafana: brew services restart grafana"
echo "   3. Ajouter datasource 'Infinity'"
echo "   4. Type: CSV"
echo "   5. URL: http://localhost:$PORT/csv/nom_fichier.csv"
echo ""
echo "💡 Exemples d'URLs:"
echo "   - http://localhost:$PORT/csv/access_per_hour.csv"
echo "   - http://localhost:$PORT/csv/top_urls.csv"
echo "   - http://localhost:$PORT/csv/suspicious_ips.csv"
echo ""
echo "Press Ctrl+C to stop"
echo "======================================================================"
echo ""

cd output/metrics
python3 -m http.server $PORT
