# 📐 Architecture Technique du Projet

## Vue d'Ensemble

Ce document décrit l'architecture technique complète du projet d'analyse de logs web.

## Architecture Globale

```
┌─────────────────────────────────────────────────────────────────┐
│                         DATA SOURCE                             │
│                    NASA Web Server Logs                         │
│              (Jul 1995 + Aug 1995 = 3.3M lignes)               │
└────────────────────────┬────────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────────┐
│                      SPARK CORE LAYER                           │
│                                                                 │
│  ┌──────────────┐    ┌──────────────┐    ┌──────────────┐     │
│  │   LogParser  │───▶│  DataFrame   │───▶│    Cache     │     │
│  │  (Regex)     │    │  (Structured)│    │              │     │
│  └──────────────┘    └──────────────┘    └──────────────┘     │
└────────────────────────┬────────────────────────────────────────┘
                         │
        ┌────────────────┼────────────────┬──────────────────┐
        │                │                │                  │
        ▼                ▼                ▼                  ▼
┌──────────────┐ ┌──────────────┐ ┌──────────────┐ ┌──────────────┐
│  Spark SQL   │ │    MLlib     │ │   GraphX     │ │  Streaming   │
│              │ │              │ │              │ │              │
│  Analytics   │ │  Clustering  │ │ IP-URL Graph │ │ Real-time    │
│  KPI         │ │  Anomalies   │ │ Communities  │ │ Processing   │
└──────┬───────┘ └──────┬───────┘ └──────┬───────┘ └──────┬───────┘
       │                │                │                 │
       └────────────────┴────────────────┴─────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────────┐
│                       EXPORT LAYER                              │
│                                                                 │
│  ┌─────────┐  ┌─────────┐  ┌───────────┐  ┌──────────────┐   │
│  │ Parquet │  │  JSON   │  │    CSV    │  │  Prometheus  │   │
│  └────┬────┘  └────┬────┘  └─────┬─────┘  └──────┬───────┘   │
└───────┼────────────┼─────────────┼────────────────┼───────────┘
        │            │             │                │
        └────────────┴─────────────┴────────────────┘
                         │
                         ▼
               ┌──────────────────┐
               │   GRAFANA        │
               │   Dashboard      │
               │   Visualization  │
               └──────────────────┘
```

## Composants Détaillés

### 1. Couche de Parsing (`src/log_parser.py`)

**Responsabilité:** Transformer les logs bruts en DataFrame structuré

**Technologies:**
- Spark Core (RDD)
- Spark SQL (DataFrame API)
- Regex avancé

**Pipeline:**
```
Log brut (texte)
    ↓ Regex Pattern Matching
IP, timestamp, method, URL, protocol, status, bytes
    ↓ Type Conversion
Integer, Long, Timestamp
    ↓ Feature Engineering
hour, day_of_week, is_error, status_category
    ↓
DataFrame structuré et typé
```

**Regex Pattern:**
```regex
^(\S+) (\S+) (\S+) \[([\w:/]+\s[+\-]\d{4})\] "(\S+)\s?(\S+)?\s?(\S+)?" (\d{3}|-) (\d+|-)
```

**Schéma de sortie:**
```python
root
 |-- ip: string
 |-- timestamp: timestamp
 |-- method: string
 |-- url: string
 |-- protocol: string
 |-- status: integer
 |-- bytes: long
 |-- hour: integer
 |-- day_of_week: integer
 |-- date: string
 |-- is_error: integer
 |-- status_category: string
```

### 2. Couche SQL Analytics (`src/sql_analytics.py`)

**Responsabilité:** Extraire des KPI et insights via SQL

**Opérations principales:**

#### a. Agrégations Temporelles
```sql
-- Accès par heure
SELECT date, hour, COUNT(*) as access_count, COUNT(DISTINCT ip) as unique_ips
FROM logs
GROUP BY date, hour
```

#### b. Classements
```sql
-- Top URLs
SELECT url, COUNT(*) as hit_count, COUNT(DISTINCT ip) as unique_visitors
FROM logs
GROUP BY url
ORDER BY hit_count DESC
LIMIT 20
```

#### c. Analyses d'Erreurs
```sql
-- Distribution des erreurs
SELECT status, url, COUNT(*) as error_count
FROM logs
WHERE status >= 400
GROUP BY status, url
```

#### d. Fenêtres Temporelles
```python
# Window de 10 minutes
window('timestamp', '10 minutes').alias('time_window')
```

**Optimisations:**
- Broadcast joins pour petites tables
- Adaptive Query Execution
- Partitionnement adaptatif
- Cache des DataFrames fréquents

### 3. Couche ML (`src/anomaly_detection.py`)

**Responsabilité:** Détecter les comportements anormaux

#### a. Feature Engineering

**Features par IP:**
```python
features = [
    'request_count',      # Nombre total de requêtes
    'unique_urls',        # URLs uniques visitées
    'total_bytes',        # Bytes totaux transférés
    'error_count',        # Nombre d'erreurs
    'error_rate',         # Taux d'erreur (0-1)
    'requests_per_day',   # Moyenne requêtes/jour
    'bytes_per_request',  # Taille moyenne des requêtes
    'active_hours'        # Nombre d'heures d'activité
]
```

#### b. Pipeline ML

```
Features brutes
    ↓ VectorAssembler
Feature vector
    ↓ StandardScaler (mean=0, std=1)
Normalized features
    ↓ K-Means (k=5)
Cluster assignment
    ↓ Distance to centroid
Anomaly score
```

#### c. Algorithmes Utilisés

**1. K-Means Clustering**
- Nombre de clusters: 5 (configurable)
- Initialisation: k-means++
- Méthode de détection: Distance au centroïde + taille du cluster
- Anomalies: Points dans les petits clusters + haute distance

**2. Analyse Statistique (Z-score)**
```python
z_score = (value - mean) / std_dev
anomaly = |z_score| > 3.0
```

**Avantages:**
- K-Means: Identifie les groupes de comportements
- Z-score: Détecte les outliers extrêmes
- Complémentaires: Différents types d'anomalies

### 4. Couche Graphe (`src/graph_analyzer.py`)

**Responsabilité:** Analyser les relations IP ↔ URL

#### a. Structure du Graphe

**Type:** Graphe biparti (bipartite graph)

```
Vertices:
  - Type IP:   {id: "192.168.1.1", type: "ip"}
  - Type URL:  {id: "/index.html", type: "url"}

Edges:
  - Direction: IP → URL
  - Poids: nombre de requêtes
  - Attributs: total_bytes, error_count
```

#### b. Métriques de Graphe

**Out-degree (IPs):**
```python
# Nombre d'URLs visitées par une IP
out_degree = graph.outDegrees
```

**In-degree (URLs):**
```python
# Nombre d'IPs ayant visité une URL
in_degree = graph.inDegrees
```

**Community Detection:**
```python
# Label Propagation Algorithm
communities = graph.labelPropagation(maxIter=5)
```

#### c. Patterns Suspects

**Indicateurs:**
- IP avec out-degree > 500 → Scraper potentiel
- Edge avec error_rate > 50% → Attaque potentielle
- IP dans petit cluster isolé → Bot/Scanner

### 5. Couche Streaming (`src/log_streamer.py`)

**Responsabilité:** Traitement temps réel

#### a. Architecture Streaming

```
File Source (streaming)
    ↓ readStream
Raw text DataFrame
    ↓ Parser (regex)
Structured stream
    ↓ Aggregations (window)
Metrics stream
    ↓ writeStream
[Console | Parquet | Memory]
```

#### b. Configuration

**Trigger:** Processing time = 10 seconds
**Watermark:** 10 minutes (late data tolerance)
**Window:** 1 minute, slide 10 seconds

```python
streaming_df.writeStream \
    .trigger(processingTime="10 seconds") \
    .option("checkpointLocation", checkpoint_dir) \
    .start()
```

#### c. Outputs Multiples

1. **Console:** Debugging et monitoring
2. **Parquet:** Persistence pour analyse batch
3. **Memory:** Requêtes SQL interactives

### 6. Couche Export (`src/metrics_exporter.py`)

**Responsabilité:** Exporter pour visualisation

#### a. Formats Supportés

**1. Parquet**
- Format optimisé pour Spark
- Compression columnar
- Schema preservation

**2. JSON**
- Pour Grafana JSON API datasource
- Structure: `[{field1: value1, field2: value2}, ...]`

**3. CSV**
- Pour Grafana CSV plugin
- Header inclus
- UTF-8 encoding

**4. Prometheus**
- Métriques temps réel
- Format exposition Prometheus
- Pull model (port 8000)

#### b. Métriques Prometheus

```python
# Counter: Cumulative
log_requests_total{status_category="2xx_success"}
log_errors_total{status_code="404"}

# Gauge: Point-in-time
log_unique_ips
log_anomalous_ips

# Histogram: Distribution
log_response_size_bytes
```

## Flux de Données

### Mode Batch

```
1. Load logs → DataFrame
2. Parse → Structured DataFrame
3. Cache DataFrame
4. Fork processing:
   ├─ SQL Analytics → KPI DataFrames
   ├─ ML Clustering → Anomalies DataFrame
   ├─ Graph Analysis → Graph + Metrics
   └─ All → Join results
5. Export all → Parquet/JSON/CSV
6. Optional: Start Prometheus server
```

### Mode Streaming

```
1. Setup streaming source (file directory)
2. Create streaming DataFrame
3. Parse in streaming mode
4. Fork streaming queries:
   ├─ Console query (debug)
   ├─ Parquet query (persist)
   └─ Memory query (interactive)
5. Trigger simulation (chunks every 10s)
6. Monitor queries
7. Shutdown gracefully
```

## Optimisations de Performance

### 1. Caching Strategy

```python
# Cache DataFrames réutilisés
logs_df.cache()
```

### 2. Partitioning

```python
# Repartition pour balance
df.repartition(200)  # Default shuffle partitions
```

### 3. Broadcast Joins

```python
# Pour petites dimensions
from pyspark.sql.functions import broadcast
large_df.join(broadcast(small_df), "key")
```

### 4. Adaptive Query Execution

```python
spark.conf.set("spark.sql.adaptive.enabled", "true")
spark.conf.set("spark.sql.adaptive.coalescePartitions.enabled", "true")
```

### 5. Predicate Pushdown

```python
# Filtrer tôt dans le pipeline
df.filter(col('status') >= 400)  # Avant les aggregations
```

## Scalabilité

### Configuration Actuelle
- Driver Memory: 4GB
- Executor Memory: 4GB
- Partitions: 200

### Pour Scaler

**Cluster Spark:**
```python
spark = SparkSession.builder \
    .master("spark://master:7077") \
    .config("spark.executor.instances", "10") \
    .config("spark.executor.cores", "4") \
    .config("spark.executor.memory", "8g") \
    .getOrCreate()
```

**Optimisations pour Big Data:**
- Augmenter partitions: 2-3x le nombre de cores
- Dynamic allocation: auto-scale executors
- Compression: parquet with snappy
- Bucketing: pour joins fréquents

## Monitoring et Debugging

### Spark UI
- URL: http://localhost:4040
- Tabs: Jobs, Stages, Storage, Environment, Executors, SQL

### Métriques Clés
- Job duration
- Shuffle read/write
- GC time
- Spill (memory/disk)

### Logs
```python
spark.sparkContext.setLogLevel("WARN")  # Réduire verbosité
```

## Sécurité et Bonnes Pratiques

### 1. Validation des Données
```python
# Filtrer les lignes invalides
logs_df = logs_df.filter(
    (col('ip') != '') & 
    (col('timestamp').isNotNull())
)
```

### 2. Gestion des Erreurs
```python
try:
    result = process_data(df)
except Exception as e:
    logger.error(f"Processing failed: {e}")
    # Fallback ou retry
```

### 3. Checkpointing (Streaming)
```python
# Éviter la recomputation du DAG
query.option("checkpointLocation", checkpoint_dir)
```

## Technologies et Versions

- **Apache Spark:** 3.5.0
- **Python:** 3.8+
- **PySpark:** 3.5.0
- **GraphFrames:** 0.6+
- **Prometheus Client:** 0.19.0
- **Grafana:** Latest
- **Java:** 8 ou 11

## Limites Connues

1. **GraphFrames:** Nécessite Scala 2.12 (incompatibilité avec 2.13)
2. **Streaming Simulation:** Pas de vraie source temps réel
3. **Memory:** Nécessite au moins 8GB RAM pour dataset complet
4. **Grafana:** Configuration manuelle requise

## Extensions Futures

1. **ML avancé:** Isolation Forest, DBSCAN
2. **Deep Learning:** Autoencoders pour anomalies
3. **Geo-IP:** Mapping IP → Location
4. **Pattern Mining:** FP-Growth pour associations
5. **Time Series:** ARIMA pour prédictions
6. **Real-time Alerting:** Intégration Kafka

---

Cette architecture est modulaire et extensible. Chaque composant peut être remplacé ou amélioré indépendamment.
