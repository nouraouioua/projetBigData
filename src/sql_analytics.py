"""
Analyses SQL pour les KPI des logs web
"""

from pyspark.sql import DataFrame
from pyspark.sql.functions import (
    col, count, sum as _sum, avg, max as _max, min as _min,
    desc, window, date_format, countDistinct, round as _round
)
from pyspark.sql import Window
import pyspark.sql.functions as F

class SQLAnalytics:
    """Analyses SQL pour extraire des KPI des logs"""
    
    def __init__(self, spark):
        self.spark = spark
    
    def register_temp_view(self, df: DataFrame, view_name: str = "logs"):
        """Enregistrer le DataFrame comme vue temporaire pour SQL"""
        df.createOrReplaceTempView(view_name)
        return view_name
    
    def access_count_per_hour(self, df: DataFrame) -> DataFrame:
        """Nombre d'accès par heure"""
        result = df.groupBy('date', 'hour') \
            .agg(
                count('*').alias('access_count'),
                countDistinct('ip').alias('unique_ips'),
                _sum('bytes').alias('total_bytes'),
                avg('bytes').alias('avg_bytes')
            ) \
            .orderBy('date', 'hour')
        
        print("\nACCÈS PAR HEURE")
        print("=" * 100)
        result.show(24)
        
        return result
    
    def access_count_per_minute(self, df: DataFrame) -> DataFrame:
        """Nombre d'accès par minute (pour Grafana)"""
        result = df.withColumn(
            'minute', date_format('timestamp', 'yyyy-MM-dd HH:mm')
        ).groupBy('minute') \
            .agg(
                count('*').alias('access_count'),
                countDistinct('ip').alias('unique_ips')
            ) \
            .orderBy('minute')
        
        return result
    
    def top_urls(self, df: DataFrame, top_n: int = 20) -> DataFrame:
        """Top N URLs les plus visitées"""
        result = df.groupBy('url') \
            .agg(
                count('*').alias('hit_count'),
                countDistinct('ip').alias('unique_visitors'),
                _sum('bytes').alias('total_bytes')
            ) \
            .orderBy(desc('hit_count')) \
            .limit(top_n)
        
        print(f"\nTOP {top_n} URLs")
        print("=" * 100)
        result.show(top_n, truncate=False)
        
        return result
    
    def top_ips(self, df: DataFrame, top_n: int = 20) -> DataFrame:
        """Top N IPs les plus actives"""
        result = df.groupBy('ip') \
            .agg(
                count('*').alias('request_count'),
                countDistinct('url').alias('unique_urls'),
                _sum('bytes').alias('total_bytes'),
                _sum('is_error').alias('error_count')
            ) \
            .withColumn(
                'error_rate', _round(col('error_count') / col('request_count') * 100, 2)
            ) \
            .orderBy(desc('request_count')) \
            .limit(top_n)
        
        print(f"\nTOP {top_n} IPs")
        print("=" * 100)
        result.show(top_n, truncate=False)
        
        return result
    
    def http_status_distribution(self, df: DataFrame) -> DataFrame:
        """Distribution des codes HTTP"""
        result = df.groupBy('status', 'status_category') \
            .agg(count('*').alias('count')) \
            .orderBy('status')
        
        print("\nDISTRIBUTION DES CODES HTTP")
        print("=" * 80)
        result.show(50)
        
        # Résumé par catégorie
        summary = df.groupBy('status_category') \
            .agg(count('*').alias('count')) \
            .orderBy(desc('count'))
        
        print("\nRÉSUMÉ PAR CATÉGORIE")
        print("=" * 80)
        summary.show()
        
        return result
    
    def error_analysis(self, df: DataFrame) -> DataFrame:
        """Analyse des erreurs (4xx et 5xx)"""
        errors_df = df.filter(col('status') >= 400)
        
        result = errors_df.groupBy('status', 'url') \
            .agg(
                count('*').alias('error_count'),
                countDistinct('ip').alias('affected_ips')
            ) \
            .orderBy(desc('error_count'))
        
        print("\nANALYSE DES ERREURS")
        print("=" * 100)
        result.show(20, truncate=False)
        
        return result
    
    def traffic_volume_over_time(self, df: DataFrame) -> DataFrame:
        """Volume de trafic dans le temps (pour graphiques)"""
        result = df.groupBy(
            window('timestamp', '10 minutes').alias('time_window')
        ).agg(
            count('*').alias('request_count'),
            _sum('bytes').alias('total_bytes'),
            countDistinct('ip').alias('unique_ips'),
            avg('bytes').alias('avg_bytes')
        ).select(
            col('time_window.start').alias('window_start'),
            col('time_window.end').alias('window_end'),
            'request_count',
            'total_bytes',
            'unique_ips',
            'avg_bytes'
        ).orderBy('window_start')
        
        return result
    
    def peak_activity_detection(self, df: DataFrame, threshold_percentile: float = 0.95) -> DataFrame:
        """Détecter les pics d'activité"""
        # Calculer les accès par minute
        per_minute = df.withColumn(
            'minute', date_format('timestamp', 'yyyy-MM-dd HH:mm')
        ).groupBy('minute') \
            .agg(count('*').alias('access_count'))
        
        # Calculer le seuil (95e percentile)
        threshold = per_minute.approxQuantile('access_count', [threshold_percentile], 0.01)[0]
        
        # Identifier les pics
        peaks = per_minute.filter(col('access_count') > threshold) \
            .orderBy(desc('access_count'))
        
        print(f"\nPICS D'ACTIVITÉ (seuil: {threshold:.0f} requêtes/minute)")
        print("=" * 80)
        peaks.show(20)
        
        return peaks
    
    def generate_all_kpis(self, df: DataFrame) -> dict:
        """Générer tous les KPI principaux"""
        print("\n" + "=" * 100)
        print("GÉNÉRATION DE TOUS LES KPI")
        print("=" * 100)
        
        kpis = {
            'access_per_hour': self.access_count_per_hour(df),
            'access_per_minute': self.access_count_per_minute(df),
            'top_urls': self.top_urls(df),
            'top_ips': self.top_ips(df),
            'http_status': self.http_status_distribution(df),
            'errors': self.error_analysis(df),
            'traffic_volume': self.traffic_volume_over_time(df),
            'peaks': self.peak_activity_detection(df)
        }
        
        return kpis
    
    def save_kpis_to_parquet(self, kpis: dict, output_dir: str):
        """Sauvegarder tous les KPI en format Parquet"""
        for name, df in kpis.items():
            output_path = f"{output_dir}/{name}"
            df.write.mode('overwrite').parquet(output_path)
            print(f"Sauvegardé: {output_path}")
