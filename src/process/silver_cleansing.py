"""
Silver Layer - Data Cleansing and Validation.

This module transforms raw bronze data into clean, validated data
by applying data quality rules and corrections.

Cleansing Rules:
1. Drop exact duplicate records
2. Remove/filter invalid diagnosis codes
3. Impute NULL diagnosis codes with default value
4. Correct negative billing amounts (absolute value)
5. Filter extreme outliers (above threshold)
6. Validate data types and ranges
"""

from typing import Optional, Tuple
from databricks.connect import DatabricksSession
from pyspark.sql import DataFrame
from pyspark.sql.functions import col, abs as spark_abs, when, count

from healthclaim_guardian.config import get_pipeline_config, get_full_table_name
from healthclaim_guardian.logging_config import setup_logger
from healthclaim_guardian.secrets import setup_databricks_auth

logger = setup_logger(__name__)


class DataQualityMetrics:
    """Track data quality metrics during cleansing."""

    def __init__(self):
        self.initial_count = 0
        self.final_count = 0
        self.duplicates_removed = 0
        self.invalid_diagnosis_removed = 0
        self.negative_amounts_corrected = 0
        self.outliers_filtered = 0
        self.null_diagnosis_imputed = 0

    @property
    def records_removed(self) -> int:
        return self.initial_count - self.final_count

    @property
    def cleansing_rate(self) -> float:
        if self.initial_count == 0:
            return 0.0
        return self.records_removed / self.initial_count

    def log_summary(self, logger):
        """Log a summary of cleansing operations."""
        logger.info("=" * 60)
        logger.info("DATA CLEANSING SUMMARY")
        logger.info("=" * 60)
        logger.info(f"Initial records:       {self.initial_count:,}")
        logger.info(f"Final records:         {self.final_count:,}")
        logger.info(f"Records removed:       {self.records_removed:,} ({self.cleansing_rate:.1%})")
        logger.info(f"Duplicates removed:    {self.duplicates_removed:,}")
        logger.info(f"Invalid diagnosis:     {self.invalid_diagnosis_removed:,}")
        logger.info(f"Outliers filtered:     {self.outliers_filtered:,}")
        logger.info(f"Negative amounts fixed:{self.negative_amounts_corrected:,}")
        logger.info(f"NULL diagnosis imputed:{self.null_diagnosis_imputed:,}")
        logger.info("=" * 60)


def read_bronze_data(spark, table_name: str) -> Optional[DataFrame]:
    """Read data from bronze table."""
    logger.info(f"Reading bronze data from {table_name}")

    try:
        df = spark.read.table(table_name)
        logger.info(f"Successfully read {df.count()} records from bronze")
        return df
    except Exception as e:
        logger.error(f"Failed to read bronze table {table_name}: {e}")
        return None


def remove_duplicates(df: DataFrame, metrics: DataQualityMetrics) -> DataFrame:
    """Remove exact duplicate records."""
    initial_count = df.count()
    df_clean = df.dropDuplicates()
    final_count = df_clean.count()

    metrics.duplicates_removed = initial_count - final_count
    logger.info(f"Duplicates removed: {metrics.duplicates_removed}")

    return df_clean


def filter_invalid_diagnosis(
    df: DataFrame,
    invalid_code: str,
    metrics: DataQualityMetrics,
) -> DataFrame:
    """Remove records with invalid diagnosis codes."""
    initial_count = df.count()

    df_clean = df.filter(col("diagnosis_code") != invalid_code)
    final_count = df_clean.count()

    metrics.invalid_diagnosis_removed = initial_count - final_count
    logger.info(f"Records with invalid diagnosis removed: {metrics.invalid_diagnosis_removed}")

    return df_clean


def impute_null_diagnosis(
    df: DataFrame,
    default_code: str,
    metrics: DataQualityMetrics,
) -> DataFrame:
    """Impute NULL or empty diagnosis codes with default value."""
    # Count NULLs before imputation
    null_count = df.filter(
        (col("diagnosis_code").isNull()) | (col("diagnosis_code") == "")
    ).count()

    df_clean = df.fillna({"diagnosis_code": default_code})

    metrics.null_diagnosis_imputed = null_count
    logger.info(f"NULL diagnosis codes imputed: {metrics.null_diagnosis_imputed}")

    return df_clean


def correct_negative_amounts(
    df: DataFrame,
    metrics: DataQualityMetrics,
) -> DataFrame:
    """Convert negative billing amounts to positive values."""
    # Count negative amounts before correction
    negative_count = df.filter(col("billed_amount") < 0).count()

    df_clean = df.withColumn(
        "billed_amount",
        when(col("billed_amount") < 0, spark_abs(col("billed_amount")))
        .otherwise(col("billed_amount"))
    )

    metrics.negative_amounts_corrected = negative_count
    logger.info(f"Negative amounts corrected: {metrics.negative_amounts_corrected}")

    return df_clean


def filter_outliers(
    df: DataFrame,
    max_amount: float,
    metrics: DataQualityMetrics,
) -> DataFrame:
    """Filter out extreme billing amount outliers."""
    initial_count = df.count()

    df_clean = df.filter(col("billed_amount") < max_amount)
    final_count = df_clean.count()

    metrics.outliers_filtered = initial_count - final_count
    logger.info(f"Outliers filtered (>${max_amount:,.0f}): {metrics.outliers_filtered}")

    return df_clean


def validate_silver_data(df: DataFrame) -> Tuple[bool, list]:
    """
    Validate the cleansed data meets quality standards.

    Returns:
        Tuple of (is_valid, list of validation errors)
    """
    errors = []

    # Check for negative amounts (should be none after cleansing)
    negative_count = df.filter(col("billed_amount") < 0).count()
    if negative_count > 0:
        errors.append(f"Found {negative_count} records with negative billed_amount")

    # Check for NULL required fields
    null_claim_id = df.filter(col("claim_id").isNull()).count()
    if null_claim_id > 0:
        errors.append(f"Found {null_claim_id} records with NULL claim_id")

    # Check for empty diagnosis codes
    empty_diagnosis = df.filter(col("diagnosis_code") == "").count()
    if empty_diagnosis > 0:
        errors.append(f"Found {empty_diagnosis} records with empty diagnosis_code")

    is_valid = len(errors) == 0
    return is_valid, errors


def cleanse_silver_data() -> bool:
    """
    Main cleansing function for silver layer.

    Returns:
        True if cleansing completed successfully, False otherwise
    """
    # Load configuration
    config = get_pipeline_config()
    table_config = config.table_config

    # Initialize metrics tracking
    metrics = DataQualityMetrics()

    # Initialize Spark session
    try:
        spark = DatabricksSession.builder.getOrCreate()
        logger.info("Databricks session initialized")
    except Exception as e:
        logger.error(f"Failed to initialize Databricks session: {e}")
        return False

    # Read bronze data
    bronze_table = get_full_table_name(table_config.bronze_claims)
    df = read_bronze_data(spark, bronze_table)

    if df is None:
        logger.error("Failed to read bronze data - aborting cleansing")
        return False

    metrics.initial_count = df.count()
    logger.info(f"Starting cleansing: {metrics.initial_count:,} records")

    # Apply cleansing transformations
    logger.info("Applying cleansing rule 1: Remove duplicates")
    df = remove_duplicates(df, metrics)

    logger.info("Applying cleansing rule 2: Filter invalid diagnosis codes")
    df = filter_invalid_diagnosis(df, config.invalid_diagnosis_code, metrics)

    logger.info("Applying cleansing rule 3: Impute NULL diagnosis codes")
    df = impute_null_diagnosis(df, config.default_diagnosis_code, metrics)

    logger.info("Applying cleansing rule 4: Correct negative amounts")
    df = correct_negative_amounts(df, metrics)

    logger.info("Applying cleansing rule 5: Filter outliers")
    df = filter_outliers(df, config.max_billed_amount, metrics)

    # Validate cleansed data
    logger.info("Validating cleansed data...")
    is_valid, errors = validate_silver_data(df)

    if not is_valid:
        logger.error("Data validation failed:")
        for error in errors:
            logger.error(f"  - {error}")
        return False

    logger.info("Data validation passed")

    # Write to silver table
    silver_table = get_full_table_name(table_config.silver_claims)
    metrics.final_count = df.count()

    logger.info(f"Writing {metrics.final_count:,} records to silver table: {silver_table}")

    try:
        df.write.format("delta").mode("overwrite").saveAsTable(silver_table)
        logger.info(f"Silver table written successfully: {silver_table}")
    except Exception as e:
        logger.error(f"Failed to write silver table: {e}")
        return False

    # Log summary
    metrics.log_summary(logger)

    # Show sample data
    logger.info("Sample data from silver layer:")
    df.show(5)

    return True


def main():
    """Entry point for silver cleansing."""
    try:
        # Attempt to set up auth from secrets
        setup_databricks_auth()

        success = cleanse_silver_data()

        if success:
            logger.info("Silver cleansing completed successfully")
            return 0
        else:
            logger.error("Silver cleansing failed")
            return 1

    except Exception as e:
        logger.exception(f"Silver cleansing failed with exception: {e}")
        return 1


if __name__ == "__main__":
    exit(main())
