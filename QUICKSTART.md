# Guide de Démarrage Rapide

Ce guide vous permet de démarrer rapidement avec l'analyse de logs web.

## Installation Rapide (5 minutes)

### 1. Installer les prérequis

```bash
# Vérifier Python
python --version  # Doit être 3.8+

# Vérifier Java
java -version  # Doit être Java 8 ou 11

# Si Java n'est pas installé:
# macOS:
brew install openjdk@11

# Linux:
sudo apt-get install openjdk-11-jdk
```

### 2. Installer les dépendances Python

```bash
pip install -r requirements.txt
```

### 3. Télécharger les données

```bash
chmod +x download_data.sh
./download_data.sh
```

Cela télécharge environ 400 MB de logs NASA (peut prendre quelques minutes).

## Lancement Rapide

### Option 1: Analyse Complète (Recommandé)

```bash
python main.py
```

Cette commande exécute:
- Parsing des logs
- Analyses SQL et KPI
- Détection d'anomalies ML
- Analyse de graphe
- Simulation streaming
- Export pour Grafana

**Durée:** 5-10 minutes (selon votre machine)

### Option 2: Analyse Batch Seulement

```bash
python main.py --mode batch
```

Plus rapide, sans le streaming (2-3 minutes).

### Option 3: Jupyter Notebook (Interactive)

```bash
jupyter notebook notebooks/analysis.ipynb
```

Parfait pour explorer les données de manière interactive.

## Résultats

Après l'exécution, vous trouverez:

```
output/
├── parquet/              # Tous les KPI en format Parquet
│   ├── access_per_hour/
│   ├── top_urls/
│   ├── suspicious_ips/
│   └── ...
├── metrics/              # Exports pour Grafana
│   ├── json/
│   └── csv/
└── graph_vertices/       # Graphe IP-URL
```

## Visualisation avec Grafana (Optionnel)

### Installation

```bash
# macOS
brew install grafana
brew services start grafana

# Linux
sudo apt-get install grafana
sudo systemctl start grafana-server
```

### Configuration

1. Ouvrir http://localhost:3000
2. Login: `admin` / `admin`
3. Importer le dashboard: `dashboard/dashboard_template.json`
4. Voir [dashboard/GRAFANA_SETUP.md](dashboard/GRAFANA_SETUP.md) pour plus de détails

## Vérifier les Résultats

### Voir les logs parsés

```bash
ls -lh data/
```

### Voir les KPI générés

```bash
ls -R output/parquet/
```

### Lire un KPI avec PySpark

```python
from pyspark.sql import SparkSession

spark = SparkSession.builder.appName("ReadKPI").getOrCreate()
top_urls = spark.read.parquet("output/parquet/top_urls")
top_urls.show()
```

## Commandes Utiles

### Voir les IPs suspectes

```python
suspicious = spark.read.parquet("output/parquet/suspicious_ips")
suspicious.show(truncate=False)
```

### Voir les pics d'activité

```python
peaks = spark.read.parquet("output/parquet/peaks")
peaks.show()
```

### Voir les erreurs

```python
errors = spark.read.parquet("output/parquet/errors")
errors.show()
```

## Paramètres Avancés

### Changer le nombre de clusters K-Means

```bash
python main.py --k-clusters 10
```

### Utiliser un fichier de logs différent

```bash
python main.py --data data/NASA_access_log_Jul95
```

### Spécifier un répertoire de sortie

```bash
python main.py --output my_output/
```

### Activer l'export Prometheus

```bash
python main.py --export-prometheus
```

Ensuite accéder aux métriques: http://localhost:8000/metrics

## Troubleshooting Rapide

### Erreur: "Java not found"

```bash
export JAVA_HOME=$(/usr/libexec/java_home -v 11)  # macOS
# ou
export JAVA_HOME=/usr/lib/jvm/java-11-openjdk-amd64  # Linux
```

### Erreur: "pyspark not found"

```bash
pip install pyspark==3.5.0
```

### Erreur: Mémoire insuffisante

Éditer `config/spark_config.py` et réduire:
```python
.config("spark.driver.memory", "2g")  # Au lieu de 4g
```

### Le téléchargement est trop lent

Télécharger manuellement:
- Jul 95: ftp://ita.ee.lbl.gov/traces/NASA_access_log_Jul95.gz
- Aug 95: ftp://ita.ee.lbl.gov/traces/NASA_access_log_Aug95.gz

Puis décompresser dans `data/`

## Prochaines Étapes

1. **Explorer les résultats** dans `output/parquet/`
2. **Ouvrir le Notebook** pour l'analyse interactive
3. **Configurer Grafana** pour la visualisation
4. **Personnaliser** les analyses dans `src/`
5. **Ajouter** vos propres KPI

## Support

Pour plus d'informations:
- README complet: [README.md](README.md)
- Setup Grafana: [dashboard/GRAFANA_SETUP.md](dashboard/GRAFANA_SETUP.md)
- Code source: `src/`

## Timeline Estimée

- Installation: 5 min
- Téléchargement données: 5-10 min
- Première analyse: 5-10 min
- Setup Grafana: 10 min (optionnel)

**Total: ~30 minutes pour être opérationnel!**

---

**Bon analyse!**
