"""
Bronze Layer Ingestion - Generate synthetic healthcare claims data.

This module generates synthetic medical claims data with intentional data quality issues
for testing the fraud detection pipeline. In production, this would be replaced by
real data ingestion from healthcare providers, claims systems, or HL7/FHIR APIs.

Data Quality Issues Injected:
- Negative billing amounts (data entry errors)
- Extreme outliers (100x normal values)
- Invalid diagnosis codes
- NULL values in required fields
"""

import random
from typing import List, Tuple
from faker import Faker
from databricks.connect import DatabricksSession
from pyspark.sql.types import (
    StructType,
    StructField,
    StringType,
    DoubleType,
    TimestampType,
)

from healthclaim_guardian.config import get_pipeline_config, get_full_table_name
from healthclaim_guardian.logging_config import setup_logger
from healthclaim_guardian.secrets import setup_databricks_auth

logger = setup_logger(__name__)


def generate_messy_claims(
    num_records: int = 10000,
    dirty_ratio: float = 0.10,
) -> List[Tuple]:
    """
    Generate synthetic medical claims with intentional dirty data.

    Args:
        num_records: Number of records to generate
        dirty_ratio: Fraction of records with data quality issues

    Returns:
        List of tuples containing claim data
    """
    data = []
    hospitals = [f"HOSP-{str(i).zfill(3)}" for i in range(1, 11)]
    valid_icd10 = ["J01.90", "E11.9", "I10", "M54.5", "Z00.00", "R53.83"]

    for i in range(num_records):
        is_dirty = random.random() < dirty_ratio

        claim_id = f"CLM-{i:08d}"
        patient_id = f"PAT-{random.randint(1, 5000):05d}"
        hospital_id = random.choice(hospitals)

        # Inject invalid diagnosis codes for dirty data
        if is_dirty:
            diagnosis_code = random.choice(["INVALID-CODE-999", "BAD-ICD", ""])
        else:
            diagnosis_code = random.choice(valid_icd10)

        # Generate billed amount with potential issues
        base_amount = round(random.uniform(100.0, 5000.0), 2)
        if is_dirty:
            issue_type = random.choice(["negative", "extreme", "zero"])
            if issue_type == "negative":
                billed_amount = round(-1 * random.uniform(100, 5000), 2)
            elif issue_type == "extreme":
                billed_amount = round(base_amount * 100, 2)  # 100x multiplier
            else:
                billed_amount = 0.0
        else:
            billed_amount = base_amount

        # Claim status with realistic distribution
        status_weights = [0.3, 0.5, 0.2]  # 30% pending, 50% approved, 20% denied
        status = random.choices(["PENDING", "APPROVED", "DENIED"], weights=status_weights)[0]

        data.append((
            claim_id,
            patient_id,
            hospital_id,
            diagnosis_code,
            billed_amount,
            status,
        ))

    return data


def create_schema() -> StructType:
    """Create PySpark schema for bronze claims table."""
    return StructType(
        [
            StructField("claim_id", StringType(), nullable=False),
            StructField("patient_id", StringType(), nullable=False),
            StructField("hospital_id", StringType(), nullable=True),
            StructField("diagnosis_code", StringType(), nullable=True),
            StructField("billed_amount", DoubleType(), nullable=True),
            StructField("claim_status", StringType(), nullable=True),
        ]
    )


def ingest_bronze_data(
    num_records: int = None,
    dirty_ratio: float = None,
    overwrite: bool = True,
) -> int:
    """
    Main ingestion function for bronze layer.

    Args:
        num_records: Number of records to generate (default from config)
        dirty_ratio: Fraction of dirty data (default from config)
        overwrite: Whether to overwrite existing table

    Returns:
        Number of records ingested
    """
    # Load configuration
    config = get_pipeline_config()
    num_records = num_records or config.num_records
    dirty_ratio = dirty_ratio or config.dirty_data_ratio

    logger.info(f"Starting bronze ingestion: {num_records} records, {dirty_ratio:.1%} dirty data")

    # Initialize Spark session
    try:
        spark = DatabricksSession.builder.getOrCreate()
        logger.info("Databricks session initialized")
    except Exception as e:
        logger.error(f"Failed to initialize Databricks session: {e}")
        raise

    # Generate synthetic data
    logger.info("Generating synthetic claims data...")
    raw_data = generate_messy_claims(num_records, dirty_ratio)

    # Create DataFrame
    schema = create_schema()
    df = spark.createDataFrame(raw_data, schema=schema)

    # Get table name
    table_name = get_full_table_name(config.table_config.bronze_claims)
    logger.info(f"Target table: {table_name}")

    # Write to Delta table
    mode = "overwrite" if overwrite else "append"
    logger.info(f"Writing {df.count()} records to {table_name} (mode={mode})")

    try:
        df.write.format("delta").mode(mode).saveAsTable(table_name)
        logger.info(f"Bronze ingestion complete: {df.count()} records written")
    except Exception as e:
        logger.error(f"Failed to write bronze table: {e}")
        raise

    # Show sample data
    logger.info("Sample data from bronze layer:")
    df.show(5)

    return df.count()


def main():
    """Entry point for bronze ingestion."""
    try:
        # Attempt to set up auth from secrets (optional, falls back to env vars)
        setup_databricks_auth()

        record_count = ingest_bronze_data()
        logger.info(f"Bronze ingestion completed successfully: {record_count} records")
        return 0

    except Exception as e:
        logger.exception(f"Bronze ingestion failed: {e}")
        return 1


if __name__ == "__main__":
    exit(main())
