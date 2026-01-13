"""
Détection d'anomalies avec MLlib
- Clustering K-Means pour grouper les comportements
- Isolation Forest pour détecter les anomalies
"""

from pyspark.sql import DataFrame
from pyspark.sql.functions import col, count, avg, stddev, when, lit
from pyspark.ml.feature import VectorAssembler, StandardScaler
from pyspark.ml.clustering import KMeans, BisectingKMeans
from pyspark.ml import Pipeline
from pyspark.sql import Window
import pyspark.sql.functions as F

class AnomalyDetector:
    """Détection d'anomalies dans les logs web avec MLlib"""
    
    def __init__(self, spark):
        self.spark = spark
        self.model = None
    
    def prepare_features(self, df: DataFrame) -> DataFrame:
        """
        Préparer les features pour le ML
        Agrège les statistiques par IP pour détecter les comportements anormaux
        """
        # Agréger les statistiques par IP
        ip_features = df.groupBy('ip').agg(
            count('*').alias('request_count'),
            F.countDistinct('url').alias('unique_urls'),
            F.countDistinct('date').alias('active_days'),
            F.sum('bytes').alias('total_bytes'),
            F.avg('bytes').alias('avg_bytes'),
            F.sum('is_error').alias('error_count'),
            F.countDistinct(F.hour('timestamp')).alias('active_hours'),
            # Calculer le taux d'erreur
            (F.sum('is_error') / count('*')).alias('error_rate'),
            # Calculer les requêtes par jour
            (count('*') / F.countDistinct('date')).alias('requests_per_day')
        )
        
        # Ajouter des features dérivées
        ip_features = ip_features.withColumn(
            'bytes_per_request', col('total_bytes') / col('request_count')
        ).withColumn(
            'urls_per_request', col('unique_urls') / col('request_count')
        )
        
        print("\nFEATURES PRÉPARÉES POUR ML")
        print("=" * 100)
        ip_features.describe().show()
        
        return ip_features
    
    def detect_anomalies_kmeans(self, df: DataFrame, k: int = 5) -> DataFrame:
        """
        Détecter les anomalies avec K-Means clustering
        Les points éloignés de leur centroïde sont considérés comme anomalies
        """
        # Préparer les features
        features_df = self.prepare_features(df)
        
        # Sélectionner les colonnes numériques pour le clustering
        feature_cols = [
            'request_count', 'unique_urls', 'total_bytes', 
            'avg_bytes', 'error_count', 'error_rate',
            'requests_per_day', 'bytes_per_request', 'active_hours'
        ]
        
        # Assembler les features
        assembler = VectorAssembler(
            inputCols=feature_cols,
            outputCol='features_raw'
        )
        
        # Normaliser les features
        scaler = StandardScaler(
            inputCol='features_raw',
            outputCol='features',
            withMean=True,
            withStd=True
        )
        
        # K-Means clustering
        kmeans = KMeans(
            k=k,
            seed=42,
            featuresCol='features',
            predictionCol='cluster'
        )
        
        # Pipeline
        pipeline = Pipeline(stages=[assembler, scaler, kmeans])
        
        # Entraîner le modèle
        print(f"\nENTRAÎNEMENT K-MEANS (k={k})")
        print("=" * 80)
        
        self.model = pipeline.fit(features_df)
        predictions = self.model.transform(features_df)
        
        # Calculer la distance au centroïde pour détecter les anomalies
        from pyspark.ml.clustering import KMeansModel
        kmeans_model = self.model.stages[-1]
        
        # Afficher les informations sur le modèle
        print(f"\nModèle entraîné avec {k} clusters")
        if isinstance(kmeans_model, KMeansModel) and hasattr(kmeans_model, 'summary'):
            print(f"Inertie: {kmeans_model.summary.trainingCost:.2f}")
        
        # Calculer un score d'anomalie basé sur la distribution des clusters
        cluster_sizes = predictions.groupBy('cluster').count()
        cluster_sizes.show()
        
        # Les IPs dans les petits clusters sont plus suspectes
        cluster_sizes_dict = {
            row['cluster']: row['count'] 
            for row in cluster_sizes.collect()
        }
        
        # Ajouter le score d'anomalie
        predictions = predictions.withColumn(
            'cluster_size',
            F.when(col('cluster') == 0, cluster_sizes_dict.get(0, 0))
            .when(col('cluster') == 1, cluster_sizes_dict.get(1, 0))
            .when(col('cluster') == 2, cluster_sizes_dict.get(2, 0))
            .when(col('cluster') == 3, cluster_sizes_dict.get(3, 0))
            .when(col('cluster') == 4, cluster_sizes_dict.get(4, 0))
            .otherwise(0)
        ).withColumn(
            'anomaly_score',
            lit(1.0) / col('cluster_size')
        )
        
        # Marquer les anomalies (top 5% des scores)
        threshold = predictions.approxQuantile('anomaly_score', [0.95], 0.01)[0]
        
        anomalies = predictions.withColumn(
            'is_anomaly',
            when(col('anomaly_score') > threshold, 1).otherwise(0)
        )
        
        print(f"\nANOMALIES DÉTECTÉES (seuil: {threshold:.6f})")
        print("=" * 100)
        
        anomalous_ips = anomalies.filter(col('is_anomaly') == 1) \
            .orderBy(F.desc('anomaly_score'))
        
        anomalous_ips.select(
            'ip', 'cluster', 'request_count', 'unique_urls', 
            'error_count', 'error_rate', 'anomaly_score'
        ).show(20, truncate=False)
        
        return anomalies
    
    def detect_statistical_anomalies(self, df: DataFrame, std_threshold: float = 3.0) -> DataFrame:
        """
        Détecter les anomalies avec une approche statistique (Z-score)
        IPs avec un comportement > 3 écarts-types de la moyenne
        """
        features_df = self.prepare_features(df)
        
        # Calculer les statistiques globales
        stats = features_df.select(
            F.mean('request_count').alias('mean_requests'),
            F.stddev('request_count').alias('std_requests'),
            F.mean('error_rate').alias('mean_error_rate'),
            F.stddev('error_rate').alias('std_error_rate'),
            F.mean('bytes_per_request').alias('mean_bytes'),
            F.stddev('bytes_per_request').alias('std_bytes')
        ).first()
        
        # Vérifier que stats n'est pas None
        if stats is None:
            raise ValueError("Cannot compute statistics on empty DataFrame")
        
        # Calculer les Z-scores
        anomalies = features_df.withColumn(
            'z_score_requests',
            (col('request_count') - lit(stats['mean_requests'])) / lit(stats['std_requests'])
        ).withColumn(
            'z_score_error_rate',
            (col('error_rate') - lit(stats['mean_error_rate'])) / lit(stats['std_error_rate'])
        ).withColumn(
            'z_score_bytes',
            (col('bytes_per_request') - lit(stats['mean_bytes'])) / lit(stats['std_bytes'])
        )
        
        # Marquer comme anomalie si au moins un Z-score > threshold
        anomalies = anomalies.withColumn(
            'is_anomaly',
            when(
                (F.abs(col('z_score_requests')) > std_threshold) |
                (F.abs(col('z_score_error_rate')) > std_threshold) |
                (F.abs(col('z_score_bytes')) > std_threshold),
                1
            ).otherwise(0)
        ).withColumn(
            'max_z_score',
            F.greatest(
                F.abs(col('z_score_requests')),
                F.abs(col('z_score_error_rate')),
                F.abs(col('z_score_bytes'))
            )
        )
        
        print(f"\nDÉTECTION STATISTIQUE D'ANOMALIES (seuil: {std_threshold} σ)")
        print("=" * 100)
        
        anomalous = anomalies.filter(col('is_anomaly') == 1) \
            .orderBy(F.desc('max_z_score'))
        
        print(f"Nombre d'IPs anormales: {anomalous.count()}")
        
        anomalous.select(
            'ip', 'request_count', 'error_rate', 'bytes_per_request',
            'z_score_requests', 'z_score_error_rate', 'z_score_bytes', 'max_z_score'
        ).show(20, truncate=False)
        
        return anomalies
    
    def get_suspicious_ips(self, anomalies_df: DataFrame, top_n: int = 50) -> DataFrame:
        """Obtenir les IPs les plus suspectes"""
        suspicious = anomalies_df.filter(col('is_anomaly') == 1) \
            .select(
                'ip', 'request_count', 'unique_urls', 'error_count', 
                'error_rate', 'total_bytes', 'anomaly_score'
            ) \
            .orderBy(F.desc('anomaly_score')) \
            .limit(top_n)
        
        print(f"\nTOP {top_n} IPs SUSPECTES")
        print("=" * 100)
        suspicious.show(top_n, truncate=False)
        
        return suspicious
    
    def analyze_anomalous_behavior(self, df: DataFrame, anomalies_df: DataFrame):
        """Analyser en détail le comportement des IPs anormales"""
        # Obtenir les IPs anormales
        anomalous_ips = anomalies_df.filter(col('is_anomaly') == 1) \
            .select('ip').rdd.flatMap(lambda x: x).collect()
        
        # Analyser leurs requêtes
        anomalous_requests = df.filter(col('ip').isin(anomalous_ips))
        
        print(f"\nANALYSE DÉTAILLÉE DES {len(anomalous_ips)} IPs ANORMALES")
        print("=" * 100)
        
        # URLs les plus visitées par les IPs anormales
        print("\nURLs les plus visitées par les IPs anormales:")
        anomalous_requests.groupBy('url').count() \
            .orderBy(F.desc('count')) \
            .show(10, truncate=False)
        
        # Distribution temporelle
        print("\nDistribution temporelle des IPs anormales:")
        anomalous_requests.groupBy('hour').count() \
            .orderBy('hour') \
            .show(24)
        
        # Codes d'erreur
        print("\nCodes d'erreur des IPs anormales:")
        anomalous_requests.filter(col('is_error') == 1) \
            .groupBy('status').count() \
            .orderBy(F.desc('count')) \
            .show()
        
        return anomalous_requests
