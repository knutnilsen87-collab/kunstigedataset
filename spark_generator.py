"""
Skalerbar grafgenerator for syntetiske eiendoms- og transaksjonsdata ved bruk av PySpark.
Designet for aa generere store volumer (hundretusenvis / millioner av noder og kanter)
og skrive direkte til Google Cloud Storage (GCS) eller BigQuery.
"""

from pyspark.sql import SparkSession
from pyspark.sql import functions as F
from pyspark.sql.types import (
    StructType, StructField, StringType, LongType, IntegerType
)
import uuid

def create_spark_session(app_name="SyntheticAMLGraphGenerator"):
    return SparkSession.builder \
        .appName(app_name) \
        .config("spark.sql.execution.arrow.pyspark.enabled", "true") \
        .getOrCreate()

def generate_synthetic_dataset(spark, num_properties=50000, num_actors=25000, num_hidden=500, output_bucket=None):
    print(f"Starter skalerbar generering med PySpark...")
    print(f"Parametere: {num_properties} eiendommer, {num_actors} aktører, {num_hidden} blankoskjøter")
    
    # 1. Generer entiteter (Personer og Selskaper)
    actors_df = spark.range(0, num_actors).select(
        F.expr("uuid()").alias("id"),
        F.when(F.rand() < 0.85, "person").otherwise("company").alias("type"),
        (F.rand() * 10000000 + 100000).cast("long").alias("initial_balance")
    )
    
    # 2. Generer Eiendommer
    properties_df = spark.range(0, num_properties).select(
        F.expr("uuid()").alias("id"),
        F.lit("property").alias("type"),
        F.lit(0).cast("long").alias("initial_balance")
    )
    
    # 3. Slå sammen alle entiteter
    entities_df = actors_df.select("id", "type").unionByName(properties_df.select("id", "type"))
    
    print("Entiteter generert.")
    return entities_df

if __name__ == "__main__":
    spark = create_spark_session()
    # Generer eksempel-batch
    # df = generate_synthetic_dataset(spark)
    print("PySpark-generator er klar for Dataproc Serverless / Cloud Dataproc.")
    spark.stop()
