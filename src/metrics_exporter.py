"""
Export de métriques pour Grafana via Prometheus
"""

from prometheus_client import Gauge, Counter, Histogram, start_http_server
from pyspark.sql import DataFrame
import time
from typing import Dict
import pyspark.sql.functions as F

class MetricsExporter:
    """Exporteur de métriques Prometheus pour monitoring Grafana"""
    
    def __init__(self, port: int = 8000):
        self.port = port
        
        # Définir les métriques Prometheus
        self.request_count = Counter(
            'log_requests_total',
            'Nombre total de requêtes',
            ['status_category']
        )
        
        self.requests_per_minute = Gauge(
            'log_requests_per_minute',
            'Nombre de requêtes par minute'
        )
        
        self.unique_ips = Gauge(
            'log_unique_ips',
            'Nombre d\'IPs uniques'
        )
        
        self.error_count = Counter(
            'log_errors_total',
            'Nombre total d\'erreurs',
            ['status_code']
        )
        
        self.bytes_transferred = Counter(
            'log_bytes_transferred_total',
            'Nombre total de bytes transférés'
        )
        
        self.anomalous_ips = Gauge(
            'log_anomalous_ips',
            'Nombre d\'IPs anormales détectées'
        )
        
        self.response_size = Histogram(
            'log_response_size_bytes',
            'Taille des réponses en bytes',
            buckets=[100, 1000, 10000, 100000, 1000000, float('inf')]
        )
        
    def start_server(self):
        """Démarrer le serveur HTTP Prometheus"""
        start_http_server(self.port)
        print(f"Serveur Prometheus démarré sur le port {self.port}")
        print(f"   Métriques disponibles sur: http://localhost:{self.port}/metrics")
    
    def update_metrics_from_dataframe(self, df: DataFrame):
        """
        Mettre à jour les métriques Prometheus à partir d'un DataFrame
        
        Args:
            df: DataFrame avec les logs parsés
        """
        # Compter les requêtes par catégorie de status
        status_counts = df.groupBy('status_category').count().collect()
        for row in status_counts:
            category = row['status_category']
            count = row['count']
            self.request_count.labels(status_category=category).inc(count)
        
        # Nombre d'IPs uniques
        unique_ip_count = df.select('ip').distinct().count()
        self.unique_ips.set(unique_ip_count)
        
        # Nombre d'erreurs par code
        error_counts = df.filter(F.col('is_error') == 1) \
            .groupBy('status').count().collect()
        for row in error_counts:
            status = str(row['status'])
            count = row['count']
            self.error_count.labels(status_code=status).inc(count)
        
        # Bytes transférés
        total_bytes = df.agg(F.sum('bytes')).collect()[0][0]
        if total_bytes:
            self.bytes_transferred.inc(total_bytes)
        
        # Taille des réponses (échantillonnage)
        sample_sizes = df.select('bytes').limit(1000).collect()
        for row in sample_sizes:
            if row['bytes']:
                self.response_size.observe(row['bytes'])
    
    def update_anomaly_metrics(self, anomalies_df: DataFrame):
        """
        Mettre à jour les métriques d'anomalies
        
        Args:
            anomalies_df: DataFrame avec les anomalies détectées
        """
        anomaly_count = anomalies_df.filter(F.col('is_anomaly') == 1).count()
        self.anomalous_ips.set(anomaly_count)


def export_to_json(df: DataFrame, output_path: str, metric_name: str):
    """
    Exporter un DataFrame en JSON pour Grafana JSON datasource
    Archive les fichiers existants avant de créer les nouveaux
    
    Args:
        df: DataFrame à exporter
        output_path: Chemin de sortie
        metric_name: Nom de la métrique
    """
    import os
    import shutil
    from datetime import datetime
    
    # Créer le répertoire de sortie si nécessaire
    os.makedirs(output_path, exist_ok=True)
    
    # Chemin du répertoire JSON
    json_dir = f"{output_path}/{metric_name}.json"
    
    # Si le répertoire existe déjà, le renommer avec timestamp
    if os.path.exists(json_dir):
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        archive_dir = f"{output_path}/archive"
        os.makedirs(archive_dir, exist_ok=True)
        archive_json = f"{archive_dir}/{metric_name}_{timestamp}.json"
        shutil.move(json_dir, archive_json)
    
    # Écrire le nouveau JSON
    df.write.mode('overwrite').json(json_dir)
    print(f"Exporté: {json_dir}")


def export_to_csv(df: DataFrame, output_path: str, metric_name: str):
    """
    Exporter un DataFrame en CSV pour Grafana CSV datasource
    Archive les fichiers existants avant de créer les nouveaux
    
    Args:
        df: DataFrame à exporter
        output_path: Chemin de sortie
        metric_name: Nom de la métrique
    """
    import os
    import shutil
    from datetime import datetime
    
    # Créer le répertoire de sortie si nécessaire
    os.makedirs(output_path, exist_ok=True)
    
    # Chemin du fichier CSV final
    csv_file = f"{output_path}/{metric_name}.csv"
    
    # Si le fichier existe déjà, le renommer avec timestamp
    if os.path.exists(csv_file):
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        archive_dir = f"{output_path}/archive"
        os.makedirs(archive_dir, exist_ok=True)
        archive_file = f"{archive_dir}/{metric_name}_{timestamp}.csv"
        shutil.move(csv_file, archive_file)
    
    # Écrire le nouveau CSV dans un répertoire temporaire
    temp_dir = f"{output_path}/_temp_{metric_name}"
    df.coalesce(1).write.mode('overwrite') \
        .option('header', 'true') \
        .csv(temp_dir)
    
    # Trouver le fichier CSV généré (Spark ajoute un préfixe)
    csv_files = [f for f in os.listdir(temp_dir) if f.endswith('.csv')]
    if csv_files:
        shutil.move(os.path.join(temp_dir, csv_files[0]), csv_file)
    
    # Nettoyer le répertoire temporaire
    shutil.rmtree(temp_dir, ignore_errors=True)
    
    print(f"Exporté: {csv_file}")


def generate_grafana_metrics(kpis: Dict[str, DataFrame], output_dir: str):
    """
    Générer tous les exports nécessaires pour Grafana
    
    Args:
        kpis: Dictionnaire de KPI DataFrames
        output_dir: Répertoire de sortie
    """
    print("\nEXPORT DES MÉTRIQUES POUR GRAFANA")
    print("=" * 100)
    
    import os
    os.makedirs(output_dir, exist_ok=True)
    
    # Export en JSON
    json_dir = f"{output_dir}/json"
    os.makedirs(json_dir, exist_ok=True)
    
    # Export en CSV
    csv_dir = f"{output_dir}/csv"
    os.makedirs(csv_dir, exist_ok=True)
    
    # Exporter chaque KPI
    for name, df in kpis.items():
        try:
            export_to_json(df, json_dir, name)
            export_to_csv(df, csv_dir, name)
        except Exception as e:
            print(f"Erreur lors de l'export de {name}: {e}")
    
    print(f"\nTous les exports terminés")
    print(f"   JSON: {json_dir}")
    print(f"   CSV: {csv_dir}")
