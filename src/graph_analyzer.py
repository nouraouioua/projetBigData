"""
Analyse de graphe avec GraphX/GraphFrames
Construire un graphe biparti IP ↔ URLs pour analyser les patterns d'accès
"""

from pyspark.sql import DataFrame
from pyspark.sql.functions import col, count, collect_list, size, desc
from graphframes import GraphFrame
import pyspark.sql.functions as F

class GraphAnalyzer:
    """Analyse de graphe des relations IP → URLs"""
    
    def __init__(self, spark):
        self.spark = spark
        self.graph = None
    
    def build_ip_url_graph(self, df: DataFrame) -> GraphFrame:
        """
        Construire un graphe biparti IP ↔ URL
        
        Vertices: IPs et URLs
        Edges: Connexions IP → URL avec poids = nombre de requêtes
        """
        print("\n🕸️  CONSTRUCTION DU GRAPHE IP ↔ URL")
        print("=" * 100)
        
        # Créer les vertices pour les IPs
        ip_vertices = df.select('ip').distinct() \
            .withColumn('id', col('ip')) \
            .withColumn('type', F.lit('ip')) \
            .select('id', 'type')  # Garder seulement id et type
        
        # Créer les vertices pour les URLs
        url_vertices = df.select('url').distinct() \
            .withColumn('id', col('url')) \
            .withColumn('type', F.lit('url')) \
            .select('id', 'type')  # Garder seulement id et type
        
        # Combiner tous les vertices
        vertices = ip_vertices.union(url_vertices)
        
        print(f"✅ Vertices créés: {vertices.count()}")
        print(f"   - IPs: {ip_vertices.count()}")
        print(f"   - URLs: {url_vertices.count()}")
        
        # Créer les edges IP → URL
        edges = df.groupBy('ip', 'url').agg(
            count('*').alias('weight'),
            F.sum('bytes').alias('total_bytes'),
            F.sum('is_error').alias('error_count')
        ).select(
            col('ip').alias('src'),
            col('url').alias('dst'),
            'weight',
            'total_bytes',
            'error_count'
        )
        
        print(f"✅ Edges créés: {edges.count()}")
        
        # Créer le GraphFrame
        self.graph = GraphFrame(vertices, edges)
        
        print("\n📊 STATISTIQUES DU GRAPHE")
        print("=" * 80)
        print(f"Nombre de vertices: {self.graph.vertices.count()}")
        print(f"Nombre d'edges: {self.graph.edges.count()}")
        
        return self.graph
    
    def analyze_ip_connectivity(self, top_n: int = 20) -> DataFrame:
        """
        Analyser la connectivité des IPs
        IPs accédant à beaucoup d'URLs différentes peuvent être des scrapers
        """
        if self.graph is None:
            raise ValueError("Le graphe n'a pas été construit. Appelez build_ip_url_graph d'abord.")
        
        print("\n🔗 ANALYSE DE CONNECTIVITÉ DES IPs")
        print("=" * 100)
        
        # Out-degree des IPs (nombre d'URLs visitées)
        ip_out_degrees = self.graph.outDegrees.filter(
            col('id').rlike(r'^\d+\.\d+\.\d+\.\d+')  # Filtrer les IPs
        ).withColumnRenamed('id', 'ip') \
          .withColumnRenamed('outDegree', 'urls_visited')
        
        # Joindre avec les edges pour avoir plus d'infos
        ip_stats = self.graph.edges.groupBy('src').agg(
            F.sum('weight').alias('total_requests'),
            F.sum('total_bytes').alias('total_bytes'),
            F.sum('error_count').alias('total_errors')
        ).withColumnRenamed('src', 'ip')
        
        ip_analysis = ip_out_degrees.join(ip_stats, 'ip') \
            .orderBy(desc('urls_visited'))
        
        print(f"\n📊 TOP {top_n} IPs PAR NOMBRE D'URLs VISITÉES")
        ip_analysis.show(top_n, truncate=False)
        
        return ip_analysis
    
    def analyze_url_popularity(self, top_n: int = 20) -> DataFrame:
        """
        Analyser la popularité des URLs
        In-degree = nombre d'IPs différentes ayant visité l'URL
        """
        if self.graph is None:
            raise ValueError("Le graphe n'a pas été construit.")
        
        print("\n⭐ ANALYSE DE POPULARITÉ DES URLs")
        print("=" * 100)
        
        # In-degree des URLs (nombre d'IPs visiteurs)
        url_in_degrees = self.graph.inDegrees.filter(
            ~col('id').rlike(r'^\d+\.\d+\.\d+\.\d+')  # Filtrer les URLs
        ).withColumnRenamed('id', 'url') \
          .withColumnRenamed('inDegree', 'unique_visitors')
        
        # Joindre avec les edges pour avoir plus d'infos
        url_stats = self.graph.edges.groupBy('dst').agg(
            F.sum('weight').alias('total_hits'),
            F.sum('total_bytes').alias('total_bytes')
        ).withColumnRenamed('dst', 'url')
        
        url_analysis = url_in_degrees.join(url_stats, 'url') \
            .orderBy(desc('unique_visitors'))
        
        print(f"\n📊 TOP {top_n} URLs PAR NOMBRE DE VISITEURS UNIQUES")
        url_analysis.show(top_n, truncate=False)
        
        return url_analysis
    
    def find_communities(self) -> DataFrame:
        """
        Détecter les communautés dans le graphe avec Label Propagation
        Peut révéler des groupes d'IPs avec des comportements similaires
        """
        if self.graph is None:
            raise ValueError("Le graphe n'a pas été construit.")
        
        print("\n👥 DÉTECTION DE COMMUNAUTÉS (Label Propagation)")
        print("=" * 100)
        
        # Appliquer Label Propagation Algorithm
        communities = self.graph.labelPropagation(maxIter=5)
        
        # Analyser les communautés
        community_sizes = communities.groupBy('label').agg(
            count('*').alias('size'),
            F.sum(F.when(col('type') == 'ip', 1).otherwise(0)).alias('ip_count'),
            F.sum(F.when(col('type') == 'url', 1).otherwise(0)).alias('url_count')
        ).orderBy(desc('size'))
        
        print("\n📊 DISTRIBUTION DES COMMUNAUTÉS")
        community_sizes.show(20)
        
        # Afficher quelques exemples de chaque communauté
        print("\n🔍 EXEMPLES PAR COMMUNAUTÉ")
        for row in community_sizes.limit(5).collect():
            label = row['label']
            print(f"\n--- Communauté {label} (taille: {row['size']}) ---")
            communities.filter(col('label') == label) \
                .select('id', 'type') \
                .show(10, truncate=False)
        
        return communities
    
    def find_connected_components(self) -> DataFrame:
        """
        Trouver les composantes connexes du graphe
        """
        if self.graph is None:
            raise ValueError("Le graphe n'a pas été construit.")
        
        print("\n🔗 COMPOSANTES CONNEXES")
        print("=" * 100)
        
        components = self.graph.connectedComponents()
        
        # Analyser les composantes
        component_sizes = components.groupBy('component').agg(
            count('*').alias('size')
        ).orderBy(desc('size'))
        
        print("\n📊 DISTRIBUTION DES COMPOSANTES")
        component_sizes.show(20)
        
        return components
    
    def find_suspicious_patterns(self) -> DataFrame:
        """
        Identifier des patterns suspects basés sur le graphe:
        - IPs visitant beaucoup d'URLs (scraping potentiel)
        - IPs avec beaucoup d'erreurs
        - URLs avec beaucoup d'erreurs
        """
        if self.graph is None:
            raise ValueError("Le graphe n'a pas été construit.")
        
        print("\n🚨 PATTERNS SUSPECTS DÉTECTÉS")
        print("=" * 100)
        
        # Analyser les edges avec beaucoup d'erreurs
        high_error_edges = self.graph.edges.filter(
            col('error_count') > 0
        ).withColumn(
            'error_rate',
            col('error_count') / col('weight')
        ).filter(
            col('error_rate') > 0.5  # Plus de 50% d'erreurs
        ).orderBy(desc('error_count'))
        
        print("\n❌ CONNEXIONS AVEC TAUX D'ERREUR ÉLEVÉ")
        high_error_edges.show(20, truncate=False)
        
        # IPs générant beaucoup d'erreurs
        error_ips = self.graph.edges.groupBy('src').agg(
            F.sum('error_count').alias('total_errors'),
            F.sum('weight').alias('total_requests')
        ).withColumn(
            'error_rate',
            col('total_errors') / col('total_requests')
        ).filter(
            (col('total_errors') > 10) & (col('error_rate') > 0.3)
        ).orderBy(desc('total_errors'))
        
        print("\n⚠️  IPs AVEC BEAUCOUP D'ERREURS")
        error_ips.show(20, truncate=False)
        
        return high_error_edges
    
    def get_ip_neighbors(self, ip_address: str, limit: int = 20) -> DataFrame:
        """
        Obtenir les URLs visitées par une IP spécifique
        """
        if self.graph is None:
            raise ValueError("Le graphe n'a pas été construit.")
        
        neighbors = self.graph.edges.filter(col('src') == ip_address) \
            .select('dst', 'weight', 'total_bytes', 'error_count') \
            .withColumnRenamed('dst', 'url') \
            .withColumnRenamed('weight', 'visit_count') \
            .orderBy(desc('visit_count')) \
            .limit(limit)
        
        print(f"\n🌐 URLs visitées par {ip_address}")
        print("=" * 100)
        neighbors.show(limit, truncate=False)
        
        return neighbors
    
    def export_graph_for_visualization(self, output_dir: str):
        """
        Exporter le graphe pour visualisation externe (Gephi, Cytoscape, etc.)
        """
        if self.graph is None:
            raise ValueError("Le graphe n'a pas été construit.")
        
        # Exporter vertices
        vertices_path = f"{output_dir}/graph_vertices"
        self.graph.vertices.write.mode('overwrite').csv(vertices_path, header=True)
        
        # Exporter edges
        edges_path = f"{output_dir}/graph_edges"
        self.graph.edges.write.mode('overwrite').csv(edges_path, header=True)
        
        print(f"\n✅ Graphe exporté:")
        print(f"   - Vertices: {vertices_path}")
        print(f"   - Edges: {edges_path}")
