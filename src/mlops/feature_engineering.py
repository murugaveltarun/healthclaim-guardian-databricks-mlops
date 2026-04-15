from databricks.connect import DatabricksSession
from pyspark.sql import functions as F

spark = DatabricksSession.builder.getOrCreate()

def engineer_features():
    database_name = "healthclaim_guardian.default"
    silver_table = f"{database_name}.insurance_silver_claims"
    features_table = f"{database_name}.insurance_silver_features"

    print(f"Reading Silver data from {silver_table}...")
    df = spark.read.table(silver_table)

    # 1. Create Hospital-Level Aggregations
    print("Calculating hospital baselines...")
    hosp_stats = df.groupBy("hospital_id").agg(
        F.avg("billed_amount").alias("hosp_avg_billed"),
        F.count("claim_id").alias("hosp_claim_count")
    )

    # 2. Join the baselines back to the individual claims
    features_df = df.join(hosp_stats, on="hospital_id", how="left")

    # 3. Create the Anomaly Feature (Ratio of claim to the hospital's average)
    print("Engineering ratio features...")
    features_df = features_df.withColumn(
        "amount_to_avg_ratio", 
        F.round(F.col("billed_amount") / F.col("hosp_avg_billed"), 3)
    )

    print(f"Writing features to {features_table}...")
    features_df.write \
        .format("delta") \
        .mode("overwrite") \
        .option("overwriteSchema", "true") \
        .saveAsTable(features_table)

    print("Feature Engineering complete. Sample features:")
    features_df.select("claim_id", "hospital_id", "billed_amount", "hosp_avg_billed", "amount_to_avg_ratio").show(5)

if __name__ == "__main__":
    engineer_features()