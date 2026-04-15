import random
from faker import Faker
from databricks.connect import DatabricksSession
from pyspark.sql.types import StructType, StructField, StringType, DoubleType, IntegerType

# 1. Initialize Databricks Connect Session
# This seamlessly bridges your local VS Code to your cloud cluster
spark = DatabricksSession.builder.getOrCreate()
fake = Faker()


def generate_messy_claims(num_records=10000):
    """Generates synthetic medical claims with intentional dirty data."""
    data = []
    hospitals = [f"HOSP-{str(i).zfill(3)}" for i in range(1, 11)]
    valid_icd10 = ["J01.90", "E11.9", "I10", "M54.5", "NULL"]  # Includes deliberate NULLs

    for _ in range(num_records):
        # 90% clean data, 10% dirty data (negative amounts, extreme values)
        is_dirty = random.random() < 0.10

        claim_id = fake.uuid4()
        patient_id = fake.uuid4()
        hospital_id = random.choice(hospitals)
        diagnosis_code = random.choice(valid_icd10) if not is_dirty else "INVALID-CODE-999"

        # Inject negative billing amounts or massive outliers for dirty data
        billed_amount = round(random.uniform(100.0, 5000.0), 2)
        if is_dirty:
            billed_amount = random.choice([billed_amount * -1, billed_amount * 100])

        status = random.choice(["PENDING", "APPROVED", "DENIED"])

        data.append((claim_id, patient_id, hospital_id, diagnosis_code, billed_amount, status))

    return data


def main():
    print("Generating synthetic healthcare claims data...")
    raw_data = generate_messy_claims(10000)

    # Define PySpark Schema
    schema = StructType(
        [
            StructField("claim_id", StringType(), False),
            StructField("patient_id", StringType(), False),
            StructField("hospital_id", StringType(), True),
            StructField("diagnosis_code", StringType(), True),
            StructField("billed_amount", DoubleType(), True),
            StructField("claim_status", StringType(), True),
        ]
    )

    # Create DataFrame
    df = spark.createDataFrame(raw_data, schema=schema)

    # Write out to Unity Catalog / Hive Metastore as a Bronze Delta Table
    # Ensure your cluster has permissions to create databases/tables in this catalog
    database_name = "healthclaim_guardian.default"
    table_name = "insurance_bronze_claims"
    full_table_path = f"{database_name}.{table_name}"

    print(f"Writing {df.count()} records to Bronze table: {full_table_path}")

    df.write.format("delta").mode("overwrite").option("overwriteSchema", "true").saveAsTable(full_table_path)

    print("Bronze ingestion complete. Sample data:")
    df.show(5)


if __name__ == "__main__":
    main()
