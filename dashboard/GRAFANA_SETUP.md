# Configuration Grafana pour l'analyse de logs web

## Installation

### 1. Installer Grafana

**macOS:**
```bash
brew install grafana
brew services start grafana
```

**Linux:**
```bash
sudo apt-get install -y software-properties-common
sudo add-apt-repository "deb https://packages.grafana.com/oss/deb stable main"
wget -q -O - https://packages.grafana.com/gpg.key | sudo apt-key add -
sudo apt-get update
sudo apt-get install grafana
sudo systemctl start grafana-server
```

Grafana sera accessible sur: http://localhost:3000
- Username: admin
- Password: admin

### 2. Installer Prometheus (optionnel pour métriques temps réel)

**macOS:**
```bash
brew install prometheus
```

**Linux:**
```bash
wget https://github.com/prometheus/prometheus/releases/download/v2.45.0/prometheus-2.45.0.linux-amd64.tar.gz
tar xvfz prometheus-*.tar.gz
cd prometheus-*
./prometheus --config.file=prometheus.yml
```

## Configuration des Datasources

### Option 1: JSON API

1. Dans Grafana, aller à Configuration → Data Sources
2. Ajouter "JSON" datasource
3. URL: `file:///path/to/output/metrics/json`

### Option 2: CSV Plugin

1. Installer le plugin CSV:
```bash
grafana-cli plugins install marcusolsson-csv-datasource
```

2. **Activer le mode local** (requis pour accéder aux fichiers CSV locaux):
```bash
# Éditer le fichier de configuration Grafana
sudo nano /opt/homebrew/etc/grafana/grafana.ini

# Ajouter à la fin du fichier:
[plugin.grafana-csv-datasource]
allow_local_mode = true

# Sauvegarder (Ctrl+O, Enter, Ctrl+X)
```

3. Redémarrer Grafana:
```bash
brew services restart grafana
```

4. Ajouter "CSV" datasource:
   - Aller dans Configuration → Data Sources → Add data source
   - Chercher "CSV"
   - Dans "Path", entrer le chemin **absolu**: `/Users/client/Documents/Bigdata projet/output/metrics/csv`
   - Cliquer "Save & Test"

### Option 3: Prometheus

1. Ajouter "Prometheus" datasource
2. URL: `http://localhost:8000`
3. Scrape interval: 5s

## Configuration prometheus.yml

```yaml
global:
  scrape_interval: 5s

scrape_configs:
  - job_name: 'web_logs'
    static_configs:
      - targets: ['localhost:8000']
```

## Dashboards Recommandés

### 1. Overview Dashboard

**Panels:**
- Access Count per Minute (Time Series)
- Unique IPs (Stat)
- Total Requests (Stat)
- Error Rate (Gauge)

### 2. Traffic Analysis Dashboard

**Panels:**
- Traffic Volume Over Time (Time Series)
- Top URLs (Table)
- Top IPs (Table)
- HTTP Status Distribution (Pie Chart)

### 3. Anomaly Detection Dashboard

**Panels:**
- Anomalous IPs Count (Stat)
- Anomaly Score Distribution (Histogram)
- Suspicious IPs Table (Table)
- Error Heatmap (Heatmap)

### 4. Real-time Streaming Dashboard

**Panels:**
- New Logs Stream (Table)
- Requests per Second (Time Series)
- Latest Errors (Logs)

## Queries Exemples

### Panel: Access Count per Minute
```
Query: SELECT minute, access_count FROM access_per_minute
Visualization: Time Series
```

### Panel: Top URLs
```
Query: SELECT url, hit_count FROM top_urls LIMIT 10
Visualization: Table
```

### Panel: HTTP Status Distribution
```
Query: SELECT status_category, count FROM http_status
Visualization: Pie Chart
```

### Panel: Anomalous IPs
```
Query: SELECT ip, request_count, error_rate, anomaly_score 
       FROM anomalies WHERE is_anomaly = 1
Visualization: Table
```

## Variables Dashboard

Créer des variables pour filtrage dynamique:

1. **time_range**: Time range selector
2. **ip_filter**: IP address filter
3. **status_filter**: HTTP status filter

## Alertes

### Alert: High Error Rate
```
Condition: error_rate > 10%
Frequency: Every 1m
For: 5m
Notification: Email/Slack
```

### Alert: Anomaly Detected
```
Condition: anomalous_ips_count > 5
Frequency: Every 1m
For: 2m
Notification: Email/Slack
```

### Alert: Traffic Spike
```
Condition: requests_per_minute > threshold
Frequency: Every 1m
For: 5m
Notification: Email/Slack
```

## Export et Partage

1. **Export JSON**: Settings → JSON Model
2. **Snapshot**: Share → Snapshot
3. **PDF Report**: Install Image Renderer plugin

## Plugins Recommandés

```bash
# Heatmap
grafana-cli plugins install petrslavotinek-carpetplot-panel

# Flowchart
grafana-cli plugins install agenty-flowcharting-panel

# Worldmap
grafana-cli plugins install grafana-worldmap-panel
```

## Troubleshooting

### Problème: "Local mode has been disabled by your administrator"

**Solution 1: Activer le mode local**
```bash
# Éditer la configuration Grafana
sudo nano /opt/homebrew/etc/grafana/grafana.ini

# Ajouter cette section:
[plugin.grafana-csv-datasource]
allow_local_mode = true

# Redémarrer Grafana
brew services restart grafana
```

**Solution 2: Utiliser un serveur HTTP (alternative)**
```bash
# Démarrer un serveur HTTP simple dans le dossier metrics
cd output/metrics/csv
python3 -m http.server 8080

# Dans Grafana, utiliser:
# URL: http://localhost:8080/nom_du_fichier.csv
```

**Solution 3: Utiliser Infinity datasource (recommandé pour production)**
```bash
# Installer le plugin Infinity
grafana-cli plugins install yesoreyeram-infinity-datasource

# Il permet de charger des CSV via HTTP sans restrictions
```

### Problème: Pas de données

1. Vérifier que les fichiers JSON/CSV sont générés
2. Vérifier les permissions de fichiers
3. Vérifier le chemin de la datasource

### Problème: Métriques Prometheus non disponibles

1. Vérifier que le serveur Python tourne (`python main.py --export-prometheus`)
2. Vérifier que Prometheus scrape correctement: http://localhost:9090/targets
3. Vérifier les logs Prometheus

### Problème: Dashboard lent

1. Réduire l'intervalle de temps
2. Ajouter des agrégations
3. Limiter le nombre de séries
4. Utiliser des tables paginées
