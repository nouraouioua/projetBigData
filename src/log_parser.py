"""
Module pour parser les logs Apache/NASA
Format: host logname time method url protocol status bytes
Exemple: 199.72.81.55 - - [01/Jul/1995:00:00:01 -0400] "GET /history/apollo/ HTTP/1.0" 200 6245
"""

import re
from pyspark.sql import DataFrame
from pyspark.sql.functions import (
    regexp_extract, col, to_timestamp, 
    when, trim, length, hour, dayofweek,
    date_format, unix_timestamp
)
from pyspark.sql.types import IntegerType, LongType

# Regex pour parser les logs Apache
APACHE_LOG_PATTERN = r'^(\S+) (\S+) (\S+) \[([\w:/]+\s[+\-]\d{4})\] "(\S+)\s?(\S+)?\s?(\S+)?" (\d{3}|-) (\d+|-)'

class LogParser:
    """Parser pour les logs Apache/NASA"""
    
    def __init__(self, spark):
        self.spark = spark
    
    def parse_logs(self, log_file_path: str) -> DataFrame:
        """
        Parser les logs bruts en DataFrame structuré
        
        Args:
            log_file_path: Chemin vers le fichier de logs
            
        Returns:
            DataFrame avec colonnes: ip, timestamp, method, url, protocol, status, bytes
        """
        # Lire le fichier de logs brut
        logs_raw = self.spark.read.text(log_file_path)
        
        # Parser avec regex
        logs_df = logs_raw.select(
            regexp_extract('value', APACHE_LOG_PATTERN, 1).alias('ip'),
            regexp_extract('value', APACHE_LOG_PATTERN, 2).alias('client_identity'),
            regexp_extract('value', APACHE_LOG_PATTERN, 3).alias('user_id'),
            regexp_extract('value', APACHE_LOG_PATTERN, 4).alias('timestamp_str'),
            regexp_extract('value', APACHE_LOG_PATTERN, 5).alias('method'),
            regexp_extract('value', APACHE_LOG_PATTERN, 6).alias('url'),
            regexp_extract('value', APACHE_LOG_PATTERN, 7).alias('protocol'),
            regexp_extract('value', APACHE_LOG_PATTERN, 8).alias('status'),
            regexp_extract('value', APACHE_LOG_PATTERN, 9).alias('bytes_str')
        )
        
        # Nettoyer et convertir les types
        logs_cleaned = logs_df.filter(
            (col('ip') != '') & (col('timestamp_str') != '')
        ).select(
            col('ip'),
            # Convertir timestamp
            to_timestamp(
                col('timestamp_str'), 
                'dd/MMM/yyyy:HH:mm:ss Z'
            ).alias('timestamp'),
            col('method'),
            col('url'),
            col('protocol'),
            # Convertir status en int
            when(col('status') != '-', col('status').cast(IntegerType()))
            .otherwise(None).alias('status'),
            # Convertir bytes en long
            when(col('bytes_str') != '-', col('bytes_str').cast(LongType()))
            .otherwise(0).alias('bytes')
        )
        
        # Ajouter des colonnes dérivées utiles
        logs_enriched = logs_cleaned.withColumn(
            'hour', hour('timestamp')
        ).withColumn(
            'day_of_week', dayofweek('timestamp')
        ).withColumn(
            'date', date_format('timestamp', 'yyyy-MM-dd')
        ).withColumn(
            'is_error', when(col('status') >= 400, 1).otherwise(0)
        ).withColumn(
            'status_category', 
            when(col('status').between(200, 299), '2xx_success')
            .when(col('status').between(300, 399), '3xx_redirect')
            .when(col('status').between(400, 499), '4xx_client_error')
            .when(col('status').between(500, 599), '5xx_server_error')
            .otherwise('unknown')
        )
        
        return logs_enriched
    
    def get_schema_info(self, df: DataFrame):
        """Afficher les informations du schéma"""
        print("=" * 80)
        print("SCHEMA DU DATAFRAME")
        print("=" * 80)
        df.printSchema()
        
        print("\n" + "=" * 80)
        print("APERÇU DES DONNÉES")
        print("=" * 80)
        df.show(10, truncate=False)
        
        print("\n" + "=" * 80)
        print("STATISTIQUES")
        print("=" * 80)
        print(f"Nombre total de lignes: {df.count():,}")
        
        return df
