"""
Configuration Spark pour l'analyse de logs web
"""

from pyspark.sql import SparkSession

def create_spark_session(app_name="WebLogAnalysis"):
    """
    Créer une session Spark avec les configurations optimales
    """
    spark = SparkSession.builder \
        .appName(app_name) \
        .config("spark.sql.adaptive.enabled", "true") \
        .config("spark.sql.adaptive.coalescePartitions.enabled", "true") \
        .config("spark.driver.memory", "2g") \
        .config("spark.executor.memory", "2g") \
        .config("spark.sql.shuffle.partitions", "50") \
        .config("spark.local.dir", "/tmp/spark-temp") \
        .config("spark.jars.packages", "graphframes:graphframes:0.8.2-spark3.2-s_2.12") \
        .getOrCreate()
    
    # Configurer le niveau de log
    spark.sparkContext.setLogLevel("WARN")
    
    return spark

# Configuration pour le streaming
STREAMING_CONFIG = {
    "batch_interval": 10,  # secondes
    "checkpoint_dir": "output/checkpoints",
    "output_mode": "append"
}

# Configuration pour les exports
EXPORT_CONFIG = {
    "parquet_path": "output/parquet",
    "csv_path": "output/csv",
    "metrics_path": "output/metrics"
}

# Configuration Grafana/Prometheus
GRAFANA_CONFIG = {
    "prometheus_port": 8000,
    "metrics_interval": 5  # secondes
}
