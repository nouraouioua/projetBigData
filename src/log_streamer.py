"""
Spark Structured Streaming pour ingérer des nouveaux logs en temps réel
Simule l'arrivée de nouveaux logs toutes les 10 secondes
"""

from pyspark.sql import SparkSession, DataFrame
from pyspark.sql.functions import col, window, count, current_timestamp
from pyspark.sql.streaming.query import StreamingQuery
import time
import os
from src.log_parser import LogParser

class LogStreamer:
    """Streaming de logs en temps réel avec Spark Structured Streaming"""
    
    def __init__(self, spark: SparkSession):
        self.spark = spark
        self.parser = LogParser(spark)
    
    def create_streaming_source(self, source_dir: str) -> DataFrame:
        """
        Créer une source de streaming qui lit les nouveaux fichiers
        dans un répertoire
        
        Args:
            source_dir: Répertoire contenant les fichiers de logs
        
        Returns:
            DataFrame en streaming
        """
        print(f"\nCRÉATION DE LA SOURCE STREAMING")
        print(f"Répertoire surveillé: {source_dir}")
        print("=" * 100)
        
        # Lire les fichiers texte en mode streaming
        streaming_df = self.spark.readStream \
            .format("text") \
            .option("maxFilesPerTrigger", 1) \
            .load(source_dir)
        
        return streaming_df
    
    def process_streaming_logs(self, streaming_df: DataFrame) -> DataFrame:
        """
        Parser et traiter les logs en streaming
        
        Args:
            streaming_df: DataFrame en streaming (texte brut)
        
        Returns:
            DataFrame en streaming avec logs parsés
        """
        from pyspark.sql.functions import (
            regexp_extract, to_timestamp, when, 
            hour, dayofweek, date_format
        )
        from pyspark.sql.types import IntegerType, LongType
        from src.log_parser import APACHE_LOG_PATTERN
        
        # Parser avec regex (même logique que LogParser mais en streaming)
        logs_df = streaming_df.select(
            regexp_extract('value', APACHE_LOG_PATTERN, 1).alias('ip'),
            regexp_extract('value', APACHE_LOG_PATTERN, 4).alias('timestamp_str'),
            regexp_extract('value', APACHE_LOG_PATTERN, 5).alias('method'),
            regexp_extract('value', APACHE_LOG_PATTERN, 6).alias('url'),
            regexp_extract('value', APACHE_LOG_PATTERN, 7).alias('protocol'),
            regexp_extract('value', APACHE_LOG_PATTERN, 8).alias('status'),
            regexp_extract('value', APACHE_LOG_PATTERN, 9).alias('bytes_str')
        )
        
        # Nettoyer et convertir
        logs_cleaned = logs_df.filter(
            (col('ip') != '') & (col('timestamp_str') != '')
        ).select(
            col('ip'),
            to_timestamp(col('timestamp_str'), 'dd/MMM/yyyy:HH:mm:ss Z').alias('timestamp'),
            col('method'),
            col('url'),
            col('protocol'),
            when(col('status') != '-', col('status').cast(IntegerType()))
            .otherwise(None).alias('status'),
            when(col('bytes_str') != '-', col('bytes_str').cast(LongType()))
            .otherwise(0).alias('bytes')
        ).withColumn(
            'processing_time', current_timestamp()
        ).withColumn(
            'hour', hour('timestamp')
        ).withColumn(
            'is_error', when(col('status') >= 400, 1).otherwise(0)
        )
        
        return logs_cleaned
    
    def aggregate_streaming_metrics(self, streaming_df: DataFrame) -> DataFrame:
        """
        Agréger des métriques en temps réel sur des fenêtres de temps
        
        Args:
            streaming_df: DataFrame en streaming avec logs parsés
        
        Returns:
            DataFrame avec métriques agrégées
        """
        from pyspark.sql.functions import sum as _sum, approx_count_distinct
        
        # Agrégation par fenêtre de 1 minute
        metrics = streaming_df \
            .withWatermark("timestamp", "10 minutes") \
            .groupBy(
                window("timestamp", "1 minute", "10 seconds")
            ).agg(
                count("*").alias("request_count"),
                approx_count_distinct("ip").alias("unique_ips"),
                _sum("bytes").alias("total_bytes"),
                _sum("is_error").alias("error_count")
            )
        
        return metrics
    
    def write_to_console(self, streaming_df: DataFrame, 
                         checkpoint_dir: str,
                         query_name: str = "console_output") -> StreamingQuery:
        """
        Écrire les résultats du streaming vers la console
        
        Args:
            streaming_df: DataFrame en streaming
            checkpoint_dir: Répertoire pour les checkpoints
            query_name: Nom de la query
        
        Returns:
            StreamingQuery
        """
        query = streaming_df.writeStream \
            .outputMode("append") \
            .format("console") \
            .option("truncate", "false") \
            .option("checkpointLocation", f"{checkpoint_dir}/{query_name}") \
            .queryName(query_name) \
            .trigger(processingTime="10 seconds") \
            .start()
        
        print(f"\nQuery '{query_name}' démarrée")
        print(f"Checkpoint: {checkpoint_dir}/{query_name}")
        
        return query
    
    def write_to_parquet(self, streaming_df: DataFrame,
                         output_path: str,
                         checkpoint_dir: str,
                         query_name: str = "parquet_output") -> StreamingQuery:
        """
        Écrire les résultats du streaming en format Parquet
        
        Args:
            streaming_df: DataFrame en streaming
            output_path: Chemin de sortie pour les fichiers Parquet
            checkpoint_dir: Répertoire pour les checkpoints
            query_name: Nom de la query
        
        Returns:
            StreamingQuery
        """
        query = streaming_df.writeStream \
            .outputMode("append") \
            .format("parquet") \
            .option("path", output_path) \
            .option("checkpointLocation", f"{checkpoint_dir}/{query_name}") \
            .queryName(query_name) \
            .trigger(processingTime="10 seconds") \
            .start()
        
        print(f"\nQuery '{query_name}' démarrée")
        print(f"Output: {output_path}")
        print(f"Checkpoint: {checkpoint_dir}/{query_name}")
        
        return query
    
    def write_to_memory(self, streaming_df: DataFrame,
                       query_name: str = "memory_table") -> StreamingQuery:
        """
        Écrire les résultats en mémoire (table temporaire)
        Utile pour les requêtes interactives
        
        Args:
            streaming_df: DataFrame en streaming
            query_name: Nom de la table en mémoire
        
        Returns:
            StreamingQuery
        """
        query = streaming_df.writeStream \
            .outputMode("append") \
            .format("memory") \
            .queryName(query_name) \
            .trigger(processingTime="10 seconds") \
            .start()
        
        print(f"\nQuery '{query_name}' démarrée")
        print(f"Accessible via: spark.sql('SELECT * FROM {query_name}')")
        
        return query
    
    def monitor_query(self, query: StreamingQuery, duration_seconds: int = 60):
        """
        Monitorer une query streaming pendant un certain temps
        
        Args:
            query: StreamingQuery à monitorer
            duration_seconds: Durée de monitoring en secondes
        """
        print(f"\nMONITORING DE LA QUERY '{query.name}'")
        print(f"Durée: {duration_seconds} secondes")
        print("=" * 100)
        
        start_time = time.time()
        
        try:
            while time.time() - start_time < duration_seconds:
                if query.isActive:
                    status = query.status
                    print(f"\nStatut: {status}")
                    
                    progress = query.lastProgress
                    if progress:
                        print(f"Lignes traitées: {progress.get('numInputRows', 0)}")
                        print(f"Taux de traitement: {progress.get('processedRowsPerSecond', 0):.2f} rows/sec")
                    
                    time.sleep(10)
                else:
                    print("Query arrêtée")
                    break
                    
        except KeyboardInterrupt:
            print("\nMonitoring interrompu par l'utilisateur")
        
        print(f"\nMonitoring terminé")
    
    def stop_all_queries(self):
        """Arrêter toutes les queries streaming actives"""
        active_queries = self.spark.streams.active
        
        if active_queries:
            print(f"\nArrêt de {len(active_queries)} queries actives...")
            for query in active_queries:
                print(f"  - Arrêt de '{query.name}'")
                query.stop()
            print("Toutes les queries sont arrêtées")
        else:
            print("\nℹ️  Aucune query active")


def prepare_streaming_data(source_file: str, stream_dir: str, 
                          chunk_size: int = 1000, delay_seconds: int = 10):
    """
    Fonction utilitaire pour simuler le streaming en divisant
    un fichier de logs en plusieurs petits fichiers
    
    Args:
        source_file: Fichier de logs source
        stream_dir: Répertoire où placer les chunks
        chunk_size: Nombre de lignes par chunk
        delay_seconds: Délai entre les chunks (pour simulation)
    """
    import os
    import time
    
    print(f"\nPRÉPARATION DES DONNÉES POUR STREAMING")
    print(f"Source: {source_file}")
    print(f"Destination: {stream_dir}")
    print(f"Taille des chunks: {chunk_size} lignes")
    print(f"Délai: {delay_seconds} secondes")
    print("=" * 100)
    
    # Créer le répertoire de streaming
    os.makedirs(stream_dir, exist_ok=True)
    
    # Lire le fichier source avec gestion d'encodage
    try:
        with open(source_file, 'r', encoding='utf-8') as f:
            lines = f.readlines()
    except UnicodeDecodeError:
        # Essayer avec latin-1 si UTF-8 échoue
        with open(source_file, 'r', encoding='latin-1') as f:
            lines = f.readlines()
    
    total_lines = len(lines)
    num_chunks = (total_lines + chunk_size - 1) // chunk_size
    
    print(f"\nTotal de lignes: {total_lines:,}")
    print(f"Nombre de chunks: {num_chunks}")
    
    # Diviser en chunks et écrire avec délai
    for i in range(num_chunks):
        start_idx = i * chunk_size
        end_idx = min((i + 1) * chunk_size, total_lines)
        
        chunk_file = f"{stream_dir}/logs_chunk_{i:04d}.txt"
        
        with open(chunk_file, 'w') as f:
            f.writelines(lines[start_idx:end_idx])
        
        print(f"Chunk {i+1}/{num_chunks} écrit: {chunk_file} ({end_idx - start_idx} lignes)")
        
        if i < num_chunks - 1:  # Ne pas attendre après le dernier chunk
            time.sleep(delay_seconds)
    
    print(f"\nPréparation terminée: {num_chunks} chunks créés")
