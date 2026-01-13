# Grafana Quick Start Guide

## Problème: "Local mode has been disabled"

Vous avez **3 solutions** pour visualiser vos métriques dans Grafana:

---

## Solution 1: Serveur HTTP (Le plus simple)

### Étape 1: Démarrer le serveur
```bash
./start_grafana_server.sh
```

Le serveur démarre sur `http://localhost:8080`

### Étape 2: Installer le plugin Infinity dans Grafana
```bash
grafana-cli plugins install yesoreyeram-infinity-datasource
brew services restart grafana
```

### Étape 3: Configurer Grafana
1. Ouvrir Grafana: http://localhost:3000 (admin/admin)
2. Configuration → Data Sources → Add data source
3. Chercher **"Infinity"**
4. Type: **CSV**
5. URL: `http://localhost:8080/csv/access_per_hour.csv`
6. Save & Test

### Étape 4: Créer un dashboard
1. Create → Dashboard → Add visualization
2. Choisir datasource **Infinity**
3. Exemples d'URLs:
   - `http://localhost:8080/csv/access_per_hour.csv` - Trafic par heure
   - `http://localhost:8080/csv/top_urls.csv` - Top URLs
   - `http://localhost:8080/csv/top_ips.csv` - Top IPs
   - `http://localhost:8080/csv/suspicious_ips.csv` - IPs suspectes

---

## Solution 2: Activer le mode local (Permanent)

### Étape 1: Éditer la config Grafana
```bash
sudo nano /opt/homebrew/etc/grafana/grafana.ini
```

### Étape 2: Ajouter à la fin du fichier
```ini
[plugin.grafana-csv-datasource]
allow_local_mode = true
```

Sauvegarder: `Ctrl+O`, `Enter`, `Ctrl+X`

### Étape 3: Redémarrer Grafana
```bash
brew services restart grafana
```

### Étape 4: Configurer la datasource CSV
1. Configuration → Data Sources → Add data source
2. Chercher **"CSV"**
3. Path: `/Users/client/Documents/Bigdata projet/output/metrics/csv`
4. Save & Test

---

## Solution 3: Utiliser JSON API (Alternative)

### Créer un serveur API simple
```bash
cd output/metrics/json
python3 -m http.server 8081
```

### Configurer Grafana avec JSON datasource
1. Installer: `grafana-cli plugins install simpod-json-datasource`
2. Redémarrer: `brew services restart grafana`
3. Add datasource → JSON
4. URL: `http://localhost:8081`

---

## Fichiers de métriques disponibles

### CSV Files (`/csv/`)
- `access_per_hour.csv` - Accès par heure
- `access_per_minute.csv` - Accès par minute
- `top_urls.csv` - URLs les plus visitées
- `top_ips.csv` - IPs les plus actives
- `http_status.csv` - Distribution des codes HTTP
- `errors.csv` - Erreurs détaillées
- `traffic_volume.csv` - Volume de trafic
- `peaks.csv` - Pics d'activité
- `suspicious_ips.csv` - IPs anormales
- `ip_connectivity.csv` - Connectivité des IPs
- `url_popularity.csv` - Popularité des URLs

### JSON Files (`/json/`)
Mêmes fichiers en format JSON

---

## Exemples de Panels Grafana

### Panel 1: Trafic par heure
- **Datasource**: Infinity
- **URL**: `http://localhost:8080/csv/access_per_hour.csv`
- **Visualization**: Time series
- **X-axis**: date + hour
- **Y-axis**: access_count

### Panel 2: Top 10 URLs
- **Datasource**: Infinity
- **URL**: `http://localhost:8080/csv/top_urls.csv`
- **Visualization**: Table
- **Columns**: url, hit_count, unique_visitors, total_bytes

### Panel 3: IPs Suspectes
- **Datasource**: Infinity
- **URL**: `http://localhost:8080/csv/suspicious_ips.csv`
- **Visualization**: Table
- **Columns**: ip, request_count, error_rate, anomaly_score

### Panel 4: Codes HTTP
- **Datasource**: Infinity
- **URL**: `http://localhost:8080/csv/http_status.csv`
- **Visualization**: Pie chart
- **Legend**: status_category
- **Values**: count

---

## Troubleshooting

### Le serveur ne démarre pas
```bash
# Vérifier si le port est utilisé
lsof -i :8080

# Utiliser un autre port
cd output/metrics && python3 -m http.server 8081
```

### Grafana ne se connecte pas
```bash
# Vérifier que Grafana tourne
brew services list | grep grafana

# Redémarrer Grafana
brew services restart grafana

# Voir les logs
tail -f /opt/homebrew/var/log/grafana/grafana.log
```

### Pas de données dans les fichiers
```bash
# Régénérer les métriques
python main.py

# Vérifier les fichiers
ls -lh output/metrics/csv/
ls -lh output/metrics/json/
```

---

## Documentation complète

Pour plus de détails, voir: `dashboard/GRAFANA_SETUP.md`
