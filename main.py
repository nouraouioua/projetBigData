"""
Script principal pour l'analyse de logs web
Intègre toutes les fonctionnalités: parsing, SQL, ML, GraphX, Streaming
"""

import sys
import argparse
from config.spark_config import create_spark_session, EXPORT_CONFIG
from src.log_parser import LogParser
from src.sql_analytics import SQLAnalytics
from src.anomaly_detection import AnomalyDetector
from src.graph_analyzer import GraphAnalyzer
from src.log_streamer import LogStreamer, prepare_streaming_data
from src.metrics_exporter import MetricsExporter, generate_grafana_metrics

def main():
    """Point d'entrée principal"""
    
    # Parser les arguments
    parser = argparse.ArgumentParser(description='Analyse de logs web avec Apache Spark')
    parser.add_argument('--mode', choices=['batch', 'streaming', 'all'], 
                       default='all', help='Mode d\'exécution')
    parser.add_argument('--data', default='data/NASA_access_log_full.txt',
                       help='Fichier de logs à analyser')
    parser.add_argument('--output', default='output',
                       help='Répertoire de sortie')
    parser.add_argument('--export-prometheus', action='store_true',
                       help='Exporter les métriques vers Prometheus')
    parser.add_argument('--k-clusters', type=int, default=5,
                       help='Nombre de clusters pour K-Means')
    
    args = parser.parse_args()
    
    print("=" * 100)
    print("🚀 ANALYSE DE LOGS WEB AVEC APACHE SPARK")
    print("=" * 100)
    print(f"Mode: {args.mode}")
    print(f"Fichier: {args.data}")
    print(f"Output: {args.output}")
    print("=" * 100)
    
    # Créer la session Spark
    spark = create_spark_session()
    
    if args.mode in ['batch', 'all']:
        run_batch_analysis(spark, args)
    
    if args.mode in ['streaming', 'all']:
        run_streaming_analysis(spark, args)
    
    if args.export_prometheus:
        run_prometheus_export(spark, args)
    
    print("\n" + "=" * 100)
    print("✅ ANALYSE TERMINÉE")
    print("=" * 100)
    
    # Garder Spark actif pour Prometheus
    if args.export_prometheus:
        print("\n⏳ Serveur Prometheus actif. Appuyez sur Ctrl+C pour arrêter...")
        try:
            import time
            while True:
                time.sleep(10)
        except KeyboardInterrupt:
            print("\n🛑 Arrêt du serveur...")
    
    spark.stop()


def run_batch_analysis(spark, args):
    """Exécuter l'analyse batch complète"""
    
    print("\n" + "=" * 100)
    print("📊 ANALYSE BATCH")
    print("=" * 100)
    
    # 1. PARSING
    print("\n### ÉTAPE 1: PARSING DES LOGS ###")
    parser = LogParser(spark)
    logs_df = parser.parse_logs(args.data)
    parser.get_schema_info(logs_df)
    
    # Cache pour performance
    logs_df.cache()
    
    # 2. ANALYSES SQL
    print("\n### ÉTAPE 2: ANALYSES SQL ###")
    analytics = SQLAnalytics(spark)
    kpis = analytics.generate_all_kpis(logs_df)
    
    # Sauvegarder les KPI en Parquet
    print("\n💾 Sauvegarde des KPI en Parquet...")
    analytics.save_kpis_to_parquet(kpis, f"{args.output}/parquet")
    
    # 3. DÉTECTION D'ANOMALIES
    print("\n### ÉTAPE 3: DÉTECTION D'ANOMALIES ###")
    detector = AnomalyDetector(spark)
    
    # K-Means clustering
    print("\n--- K-Means Clustering ---")
    anomalies_kmeans = detector.detect_anomalies_kmeans(logs_df, k=args.k_clusters)
    suspicious_ips = detector.get_suspicious_ips(anomalies_kmeans, top_n=50)
    
    # Analyse statistique
    print("\n--- Analyse Statistique ---")
    anomalies_stats = detector.detect_statistical_anomalies(logs_df, std_threshold=3.0)
    
    # Analyser le comportement des IP anormales
    detector.analyze_anomalous_behavior(logs_df, anomalies_kmeans)
    
    # Sauvegarder les anomalies
    print("\n💾 Sauvegarde des anomalies...")
    suspicious_ips.write.mode('overwrite').parquet(f"{args.output}/parquet/suspicious_ips")
    
    # 4. ANALYSE DE GRAPHE
    print("\n### ÉTAPE 4: ANALYSE DE GRAPHE (GraphX) ###")
    graph_analyzer = GraphAnalyzer(spark)
    
    # Construire le graphe
    graph = graph_analyzer.build_ip_url_graph(logs_df)
    
    # Analyses
    ip_connectivity = graph_analyzer.analyze_ip_connectivity(top_n=20)
    url_popularity = graph_analyzer.analyze_url_popularity(top_n=20)
    
    # Détecter les communautés
    print("\n--- Détection de Communautés ---")
    communities = graph_analyzer.find_communities()
    
    # Patterns suspects
    print("\n--- Patterns Suspects ---")
    suspicious_patterns = graph_analyzer.find_suspicious_patterns()
    
    # Export du graphe
    print("\n💾 Export du graphe pour visualisation...")
    graph_analyzer.export_graph_for_visualization(f"{args.output}")
    
    # 5. EXPORT POUR GRAFANA
    print("\n### ÉTAPE 5: EXPORT POUR GRAFANA ###")
    
    # Ajouter les anomalies aux KPI
    kpis['suspicious_ips'] = suspicious_ips
    kpis['ip_connectivity'] = ip_connectivity
    kpis['url_popularity'] = url_popularity
    
    generate_grafana_metrics(kpis, f"{args.output}/metrics")
    
    print("\n✅ Analyse batch terminée!")


def run_streaming_analysis(spark, args):
    """Exécuter l'analyse streaming"""
    
    print("\n" + "=" * 100)
    print("🌊 ANALYSE STREAMING")
    print("=" * 100)
    
    # Préparer les données de streaming (simuler)
    stream_dir = f"{args.output}/stream_input"
    
    print("\n📦 Préparation des données de streaming...")
    print("(Diviser le fichier en chunks pour simuler le streaming)")
    
    import os
    if not os.path.exists(args.data):
        print(f"❌ Fichier {args.data} introuvable. Téléchargez d'abord les données.")
        return
    
    # Créer le répertoire de streaming
    os.makedirs(stream_dir, exist_ok=True)
    
    # Initialiser le streamer
    streamer = LogStreamer(spark)
    
    # Créer la source de streaming
    streaming_df = streamer.create_streaming_source(stream_dir)
    
    # Parser les logs en streaming
    parsed_stream = streamer.process_streaming_logs(streaming_df)
    
    # Agréger les métriques
    metrics_stream = streamer.aggregate_streaming_metrics(parsed_stream)
    
    # Écrire vers la console
    console_query = streamer.write_to_console(
        parsed_stream.select('ip', 'timestamp', 'method', 'url', 'status', 'bytes'),
        f"{args.output}/checkpoints",
        "streaming_logs"
    )
    
    # Écrire les métriques vers Parquet
    metrics_query = streamer.write_to_parquet(
        metrics_stream,
        f"{args.output}/streaming_metrics",
        f"{args.output}/checkpoints",
        "streaming_metrics"
    )
    
    # Écrire en mémoire pour requêtes interactives
    memory_query = streamer.write_to_memory(parsed_stream, "live_logs")
    
    print("\n✅ Queries de streaming démarrées!")
    print("\nQueries actives:")
    for query in spark.streams.active:
        print(f"  - {query.name}: {query.status}")
    
    # Lancer la simulation de streaming dans un thread séparé
    print("\n🎬 Démarrage de la simulation de streaming...")
    print("   (Les chunks seront créés toutes les 10 secondes)")
    
    import threading
    streaming_thread = threading.Thread(
        target=prepare_streaming_data,
        args=(args.data, stream_dir, 1000, 10)
    )
    streaming_thread.daemon = True
    streaming_thread.start()
    
    # Monitorer pendant 2 minutes
    streamer.monitor_query(console_query, duration_seconds=120)
    
    # Arrêter toutes les queries
    streamer.stop_all_queries()
    
    print("\n✅ Analyse streaming terminée!")


def run_prometheus_export(spark, args):
    """Exporter les métriques vers Prometheus"""
    
    print("\n" + "=" * 100)
    print("📡 EXPORT PROMETHEUS")
    print("=" * 100)
    
    # Parser les logs
    parser = LogParser(spark)
    logs_df = parser.parse_logs(args.data)
    
    # Créer l'exporteur
    exporter = MetricsExporter(port=8000)
    exporter.start_server()
    
    # Mettre à jour les métriques
    print("\n📊 Mise à jour des métriques...")
    exporter.update_metrics_from_dataframe(logs_df)
    
    # Détecter les anomalies et mettre à jour
    detector = AnomalyDetector(spark)
    anomalies = detector.detect_anomalies_kmeans(logs_df, k=args.k_clusters)
    exporter.update_anomaly_metrics(anomalies)
    
    print("\n✅ Métriques exportées vers Prometheus")
    print(f"   URL: http://localhost:8000/metrics")


if __name__ == '__main__':
    main()
