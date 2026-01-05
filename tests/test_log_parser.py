"""
Tests unitaires pour le log parser
"""

import unittest
from config.spark_config import create_spark_session
from src.log_parser import LogParser

class TestLogParser(unittest.TestCase):
    
    @classmethod
    def setUpClass(cls):
        """Créer une session Spark pour les tests"""
        cls.spark = create_spark_session("TestLogParser")
        cls.spark.sparkContext.setLogLevel("ERROR")
    
    @classmethod
    def tearDownClass(cls):
        """Arrêter Spark après les tests"""
        cls.spark.stop()
    
    def test_parse_valid_log_line(self):
        """Tester le parsing d'une ligne de log valide"""
        parser = LogParser(self.spark)
        
        # Créer un DataFrame de test
        test_data = [
            ('199.72.81.55 - - [01/Jul/1995:00:00:01 -0400] "GET /history/apollo/ HTTP/1.0" 200 6245',)
        ]
        test_df = self.spark.createDataFrame(test_data, ['value'])
        
        # Parser
        from pyspark.sql.functions import regexp_extract, to_timestamp, when
        from pyspark.sql.types import IntegerType, LongType
        from src.log_parser import APACHE_LOG_PATTERN
        
        result_df = test_df.select(
            regexp_extract('value', APACHE_LOG_PATTERN, 1).alias('ip'),
            regexp_extract('value', APACHE_LOG_PATTERN, 6).alias('url'),
            regexp_extract('value', APACHE_LOG_PATTERN, 8).alias('status')
        )
        
        result = result_df.collect()[0]
        
        self.assertEqual(result['ip'], '199.72.81.55')
        self.assertEqual(result['url'], '/history/apollo/')
        self.assertEqual(result['status'], '200')
    
    def test_parse_empty_dataframe(self):
        """Tester le parsing d'un DataFrame vide"""
        parser = LogParser(self.spark)
        
        empty_df = self.spark.createDataFrame([], 'value STRING')
        # Le parsing ne devrait pas échouer sur un DataFrame vide
        # (comportement à définir selon les besoins)


if __name__ == '__main__':
    unittest.main()
