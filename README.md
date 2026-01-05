# Analyse de Logs Web - Detection d'Anomalies

Projet Big Data d'analyse de logs web NASA avec Apache Spark pour detecter les anomalies, pics d'activite, et patterns d'acces suspects.

![Spark](https://img.shields.io/badge/Apache%20Spark-3.5.0-orange)
![Python](https://img.shields.io/badge/Python-3.8+-blue)
![License](https://img.shields.io/badge/License-MIT-green)

## Table des Matieres

- [Description](#description)
- [Architecture](#architecture)
- [Fonctionnalites](#fonctionnalités)
- [Installation](#installation)
- [Utilisation](#utilisation)
- [Pipeline de Traitement](#pipeline-de-traitement)
- [Dashboard Grafana](#dashboard-grafana)
- [Resultats](#résultats)
- [Structure du Projet](#structure-du-projet)

## Description

Ce projet analyse les logs du serveur web NASA pour:
- Detecter les comportements anormaux (scraping, attaques, bots)
- Identifier les pics d'activite
- Analyser les patterns d'acces IP -> URLs
- Monitorer en temps reel avec streaming
- Visualiser avec Grafana

## Architecture

```
Logs Bruts (NASA)
    ↓
Spark Core (Parsing Regex)
    ↓
Spark SQL (Analytics & KPI)
    ↓
MLlib (Clustering K-Means + Anomalies)
    ↓
GraphX/GraphFrames (Graphe IP ↔ URL)
    ↓
Spark Streaming (Temps Réel)
    ↓
Export (Parquet, JSON, CSV, Prometheus)
    ↓
Grafana Dashboard
```

## Fonctionnalites

### 1. Parsing Avance
- Regex pour parser les logs Apache
- Extraction: IP, date, URL, methode HTTP, code status, bytes
- Validation et nettoyage des donnees
- Enrichissement avec metadonnees (heure, jour de semaine, categorie de status)

### 2. Analyses SQL
- Nombre d'acces par heure/minute
- Top URLs visitees
- Top IPs actives
- Distribution des codes HTTP
- Analyse des erreurs (4xx, 5xx)
- Detection des pics d'activite
- Volume de trafic temporel

### 3. Machine Learning (MLlib)
- **K-Means Clustering**: Grouper les IPs par comportement
- **Detection Statistique**: Z-score pour identifier les outliers
- **Features**: request_count, error_rate, bytes_per_request, unique_urls, active_hours
- **Identification** des IPs suspectes (scrapers, bots, attaquants)

### 4. Analyse de Graphe (GraphFrames)
- Graphe biparti IP <-> URL
- Connectivite des IPs (out-degree)
- Popularite des URLs (in-degree)
- Detection de communautes (Label Propagation)
- Identification de patterns suspects
- Export pour Gephi/Cytoscape

### 5. Spark Streaming
- Ingestion de nouveaux logs toutes les 10 secondes
- Traitement en temps reel
- Agregations par fenetre temporelle
- Multiple outputs: Console, Parquet, Memory

### 6. Dashboard Grafana
- Access count per minute
- Top endpoints
- Codes HTTP
- Points d'anomalie detectes
- Table des IPs suspectes
- Heatmap IP x URL
- Streaming des nouveaux logs

## Installation

### Prerequis

- Python 3.8+
- Java 8 ou 11 (pour Spark)
- Apache Spark 3.5.0
- Grafana (optionnel)
- Prometheus (optionnel)

### Installation des dependances

```bash
# Installer les packages Python
pip install -r requirements.txt

# Ou avec un environnement virtuel
python -m venv venv
source venv/bin/activate  # macOS/Linux
# ou
venv\Scripts\activate  # Windows
pip install -r requirements.txt
```

### Telecharger les donnees NASA

```bash
# Rendre le script executable
chmod +x download_data.sh

# Telecharger et decompresser les logs
./download_data.sh
```

Les fichiers telecharges:
- `data/NASA_access_log_Jul95` (1.8M lignes, ~200 MB)
- `data/NASA_access_log_Aug95` (1.5M lignes, ~168 MB)
- `data/NASA_access_log_full.txt` (combine)

**Note**: Un fichier sample `data/NASA_access_log_sample.txt` est disponible pour les tests.

## Utilisation

### Mode Batch (Analyse complete)

```bash
python main.py --mode batch --data data/NASA_access_log_sample.txt
```

### Mode Streaming (Temps reel)

```bash
python main.py --mode streaming --data data/NASA_access_log_sample.txt
```

### Mode Complet (Batch + Streaming)

```bash
python main.py --mode all --data data/NASA_access_log_sample.txt
```

### Avec export Prometheus

```bash
python main.py --mode batch --export-prometheus
```

### Parametres disponibles

```bash
python main.py --help

Options:
  --mode {batch,streaming,all}    Mode d'execution (defaut: all)
  --data DATA                     Fichier de logs (defaut: data/NASA_access_log_full.txt)
  --output OUTPUT                 Repertoire de sortie (defaut: output)
  --export-prometheus             Exporter vers Prometheus
  --k-clusters K                  Nombre de clusters K-Means (defaut: 5)
```

## Pipeline de Traitement

### 1. Parsing
```python
from src.log_parser import LogParser

parser = LogParser(spark)
logs_df = parser.parse_logs('data/NASA_access_log_sample.txt')
```

### 2. Analyses SQL
```python
from src.sql_analytics import SQLAnalytics

analytics = SQLAnalytics(spark)
kpis = analytics.generate_all_kpis(logs_df)
```

### 3. Detection d'Anomalies
```python
from src.anomaly_detection import AnomalyDetector

detector = AnomalyDetector(spark)
anomalies = detector.detect_anomalies_kmeans(logs_df, k=5)
suspicious = detector.get_suspicious_ips(anomalies, top_n=50)
```

### 4. Analyse de Graphe
```python
from src.graph_analyzer import GraphAnalyzer

graph_analyzer = GraphAnalyzer(spark)
graph = graph_analyzer.build_ip_url_graph(logs_df)
connectivity = graph_analyzer.analyze_ip_connectivity()
```

### 5. Streaming
```python
from src.log_streamer import LogStreamer

streamer = LogStreamer(spark)
streaming_df = streamer.create_streaming_source('stream_input/')
query = streamer.write_to_console(streaming_df, 'checkpoints/')
```

## Dashboard Grafana

### Installation et Configuration

Voir [dashboard/GRAFANA_SETUP.md](dashboard/GRAFANA_SETUP.md) pour:
- Installation de Grafana
- Configuration des datasources
- Import du dashboard
- Configuration des alertes

### Acces rapide

1. Installer Grafana:
```bash
brew install grafana  # macOS
brew services start grafana
```

2. Acceder a: http://localhost:3000
   - User: `admin`
   - Password: `admin`

3. Importer le dashboard: `dashboard/dashboard_template.json`

### Panels Disponibles

- **Access Count per Minute**: Timeline des acces
- **Total Requests**: Stat du nombre total
- **Error Rate**: Gauge du taux d'erreur
- **HTTP Status Distribution**: Pie chart des codes
- **Traffic Volume**: Timeline bytes/requetes
- **Top URLs**: Table des endpoints populaires
- **Suspicious IPs**: Table des anomalies

## Resultats

### KPI Generes

Tous les resultats sont exportes dans `output/`:

```
output/
├── parquet/              # DataFrames en Parquet
│   ├── access_per_hour/
│   ├── access_per_minute/
│   ├── top_urls/
│   ├── top_ips/
│   ├── http_status/
│   ├── errors/
│   ├── traffic_volume/
│   ├── peaks/
│   └── suspicious_ips/
├── metrics/              # Exports pour Grafana
│   ├── json/
│   └── csv/
├── graph_vertices/       # Export du graphe
├── graph_edges/
├── stream_input/         # Donnees streaming
└── streaming_metrics/    # Metriques streaming
```

### Exemples de Resultats

**Top 5 URLs:**
```
/shuttle/countdown/         45,000 hits
/images/NASA-logosmall.gif  35,000 hits
/shuttle/missions/          28,000 hits
/images/KSC-logosmall.gif   22,000 hits
/history/apollo/            18,000 hits
```

**IPs Anormales Detectees:**
- IPs avec >10,000 requetes/jour (potential scrapers)
- IPs avec taux d'erreur >50% (potential attackers)
- IPs visitant >500 URLs uniques (bots)

## Structure du Projet

```
Bigdata projet/
├── main.py                    # Script principal
├── requirements.txt           # Dependances Python
├── download_data.sh           # Script telechargement donnees
├── create_sample.sh           # Script creation fichier sample
├── run.sh                     # Script execution
├── README.md                  # Ce fichier
│
├── config/                    # Configuration
│   └── spark_config.py        # Config Spark
│
├── src/                       # Code source
│   ├── log_parser.py          # Parser de logs
│   ├── sql_analytics.py       # Analyses SQL
│   ├── anomaly_detection.py   # Detection d'anomalies ML
│   ├── graph_analyzer.py      # Analyse de graphe
│   ├── log_streamer.py        # Spark Streaming
│   └── metrics_exporter.py    # Export Prometheus/Grafana
│
├── notebooks/                 # Jupyter notebooks
│   └── analysis.ipynb         # Notebook d'analyse interactive
│
├── dashboard/                 # Configuration Grafana
│   ├── GRAFANA_SETUP.md       # Guide installation
│   └── dashboard_template.json # Template dashboard
│
├── tests/                     # Tests unitaires
│   └── test_log_parser.py     # Tests du parser
│
├── data/                      # Donnees
│   └── NASA_access_log_sample.txt  # Fichier sample de logs
│
└── output/                    # Resultats (cree automatiquement)
    ├── parquet/
    ├── metrics/
    ├── graph_vertices/
    └── graph_edges/
```

## Concepts Utilises

### Apache Spark
- **Spark Core**: RDD, transformations, actions
- **Spark SQL**: DataFrames, SQL queries, window functions
- **MLlib**: K-Means, feature engineering, pipelines
- **GraphFrames**: Graph analytics, community detection
- **Structured Streaming**: Micro-batch, watermarks, triggers

### Machine Learning
- **Clustering**: K-Means pour grouper comportements similaires
- **Anomaly Detection**: Z-score, distance au centroide
- **Feature Engineering**: Agregations, ratios, derivees
- **Evaluation**: Silhouette score, inertia

### Graph Theory
- **Bipartite Graph**: IP <-> URL
- **Degree Centrality**: Mesure de connectivite
- **Community Detection**: Label Propagation
- **Pattern Mining**: Suspicious connections

## Notes Techniques

### Performance

- **Caching**: Les DataFrames frequemment utilises sont mis en cache
- **Partitioning**: Optimisation du nombre de partitions (50 par defaut)
- **Adaptive Query Execution**: Active pour optimiser les jointures
- **Broadcast**: Petites tables broadcastees pour les joins

### Scalabilite

Le projet peut traiter:
- Millions de lignes de logs
- Milliers d'IPs uniques
- Dizaines de milliers d'URLs
- Streaming continu a haute frequence

### Limitations

- GraphFrames necessite Spark 3.x et Scala 2.12
- Le mode streaming simule les donnees (pas de source temps reel)
- Grafana necessite une configuration manuelle pour certaines visualisations

## Troubleshooting

### Probleme: "Java not found"
```bash
# macOS
brew install openjdk@11
export JAVA_HOME=$(/usr/libexec/java_home -v 11)

# Linux
sudo apt-get install openjdk-11-jdk
export JAVA_HOME=/usr/lib/jvm/java-11-openjdk-amd64
```

### Probleme: "Cannot import pyspark"
```bash
pip install pyspark==3.5.0
```

### Probleme: "GraphFrames not found"
```bash
pip install graphframes
# Ou demarrer spark avec:
# --packages graphframes:graphframes:0.8.2-spark3.2-s_2.12
```

### Probleme: Memoire insuffisante
Ajuster dans `config/spark_config.py`:
```python
.config("spark.driver.memory", "8g")
.config("spark.executor.memory", "8g")
```

## Ressources

- [Dataset NASA Web Logs](https://ita.ee.lbl.gov/html/contrib/NASA-HTTP.html)
- [Apache Spark Documentation](https://spark.apache.org/docs/latest/)
- [GraphFrames Guide](https://graphframes.github.io/graphframes/docs/_site/index.html)
- [Grafana Documentation](https://grafana.com/docs/)
- [Prometheus Documentation](https://prometheus.io/docs/)

## Dependances

Les principales dependances Python (voir `requirements.txt`):
- pyspark==3.5.0
- pandas>=2.2.0
- numpy>=1.26.0
- matplotlib>=3.8.0
- seaborn>=0.13.0
- graphframes
- scikit-learn>=1.3.0
- prometheus-client>=0.19.0

## Contribution

Les contributions sont bienvenues! N'hesitez pas a:
- Signaler des bugs
- Proposer des ameliorations
- Ajouter de nouvelles analyses
- Ameliorer la documentation

## License

MIT License - voir LICENSE file pour details

## Auteur

Projet Big Data - Analyse de Logs Web
