from databricks.connect import DatabricksSession
from pyspark.sql.functions import col, abs as spark_abs

# Initialize Databricks Connect Session
spark = DatabricksSession.builder.getOrCreate()

def clean_bronze_data():
    database_name = "healthclaim_guardian.default"
    bronze_table = f"{database_name}.insurance_bronze_claims"
    silver_table = f"{database_name}.insurance_silver_claims"

    print(f"Reading raw data from {bronze_table}...")
    try:
        df = spark.read.table(bronze_table)
    except Exception as e:
        print(f"Error reading Bronze table. Ensure the ingestion task ran successfully. Details: {e}")
        return

    initial_count = df.count()
    print(f"Initial record count: {initial_count}")

    print("Applying data cleansing rules...")
    
    # 1. Drop exact duplicates
    df_cleaned = df.dropDuplicates()
    
    # 2. Remove records with completely invalid diagnosis codes
    df_cleaned = df_cleaned.filter(col("diagnosis_code") != "INVALID-CODE-999")
    
    # 3. Handle NULL diagnosis codes (impute with a default value)
    df_cleaned = df_cleaned.fillna({"diagnosis_code": "UNKNOWN"})
    
    # 4. Correct negative billing amounts (assuming they are data entry errors)
    df_cleaned = df_cleaned.withColumn("billed_amount", spark_abs(col("billed_amount")))
    
    # 5. Filter out massive outliers (the 100x multiplier we injected)
    # Assuming any single claim over $50,000 in this dataset is an error to be removed at this stage
    df_cleaned = df_cleaned.filter(col("billed_amount") < 50000.0)

    final_count = df_cleaned.count()
    print(f"Cleaned record count: {final_count} (Removed/Modified records from initial load)")

    print(f"Writing clean data to Silver table: {silver_table}...")
    df_cleaned.write \
        .format("delta") \
        .mode("overwrite") \
        .option("overwriteSchema", "true") \
        .saveAsTable(silver_table)
        
    print("Silver processing complete. Sample data:")
    df_cleaned.show(5)

if __name__ == "__main__":
    clean_bronze_data()