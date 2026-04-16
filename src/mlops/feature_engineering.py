"""
Feature Engineering - Create ML features from cleansed data.

This module transforms silver data into ML-ready features by:
1. Creating hospital-level aggregations (baselines)
2. Computing claim-to-average ratios
3. Generating statistical features for anomaly detection

Features Created:
- hosp_avg_billed: Average billed amount per hospital
- hosp_claim_count: Number of claims per hospital
- amount_to_avg_ratio: Ratio of claim amount to hospital average
"""

from typing import Optional
from databricks.connect import DatabricksSession
from pyspark.sql import DataFrame
from pyspark.sql import functions as F

from healthclaim_guardian.config import get_pipeline_config, get_full_table_name
from healthclaim_guardian.logging_config import setup_logger
from healthclaim_guardian.secrets import setup_databricks_auth

logger = setup_logger(__name__)


def read_silver_data(spark, table_name: str) -> Optional[DataFrame]:
    """Read data from silver table."""
    logger.info(f"Reading silver data from {table_name}")

    try:
        df = spark.read.table(table_name)
        count = df.count()
        logger.info(f"Successfully read {count:,} records from silver")
        return df
    except Exception as e:
        logger.error(f"Failed to read silver table {table_name}: {e}")
        return None


def create_hospital_aggregations(df: DataFrame) -> DataFrame:
    """
    Create hospital-level aggregation features.

    Args:
        df: Silver claims DataFrame

    Returns:
        DataFrame with hospital-level statistics
    """
    logger.info("Creating hospital-level aggregations...")

    hosp_stats = df.groupBy("hospital_id").agg(
        F.avg("billed_amount").alias("hosp_avg_billed"),
        F.min("billed_amount").alias("hosp_min_billed"),
        F.max("billed_amount").alias("hosp_max_billed"),
        F.stddev("billed_amount").alias("hosp_stddev_billed"),
        F.count("claim_id").alias("hosp_claim_count"),
    )

    logger.info(f"Created aggregations for {hosp_stats.count()} hospitals")
    return hosp_stats


def join_hospital_features(
    claims_df: DataFrame,
    hosp_stats_df: DataFrame,
) -> DataFrame:
    """
    Join hospital aggregations back to individual claims.

    Args:
        claims_df: Individual claims DataFrame
        hosp_stats_df: Hospital statistics DataFrame

    Returns:
        DataFrame with joined features
    """
    logger.info("Joining hospital features to claims...")

    features_df = claims_df.join(
        hosp_stats_df,
        on="hospital_id",
        how="left",
    )

    logger.info(f"Joined DataFrame has {features_df.count()} records")
    return features_df


def create_ratio_features(df: DataFrame) -> DataFrame:
    """
    Create ratio-based anomaly features.

    Args:
        df: DataFrame with hospital aggregations

    Returns:
        DataFrame with ratio features
    """
    logger.info("Creating ratio features...")

    # Calculate ratio of claim amount to hospital average
    features_df = df.withColumn(
        "amount_to_avg_ratio",
        F.round(
            F.col("billed_amount") / F.col("hosp_avg_billed"),
            3,
        ),
    )

    # Calculate z-score based feature (how many stddev from mean)
    features_df = features_df.withColumn(
        "amount_z_score",
        F.when(
            F.col("hosp_stddev_billed") > 0,
            (F.col("billed_amount") - F.col("hosp_avg_billed")) / F.col("hosp_stddev_billed"),
        ).otherwise(0.0),
    )

    # Flag claims significantly above average
    features_df = features_df.withColumn(
        "is_above_2std",
        F.col("amount_z_score") > 2.0,
    )

    logger.info("Ratio features created")
    return features_df


def validate_features(df: DataFrame) -> bool:
    """
    Validate feature engineering output.

    Returns:
        True if validation passes, False otherwise
    """
    from pyspark.sql.functions import col

    errors = []

    # Check for NULL features
    null_ratio = df.filter(col("amount_to_avg_ratio").isNull()).count()
    if null_ratio > 0:
        errors.append(f"Found {null_ratio} records with NULL amount_to_avg_ratio")

    # Check for infinite or NaN values
    # (PySpark handles these differently, so we check for extreme values)
    extreme_ratio = df.filter(F.col("amount_to_avg_ratio") > 1000).count()
    if extreme_ratio > 0:
        errors.append(f"Found {extreme_ratio} records with extreme ratio (>1000)")

    if errors:
        for error in errors:
            logger.error(error)
        return False

    logger.info("Feature validation passed")
    return True


def engineer_features() -> bool:
    """
    Main feature engineering function.

    Returns:
        True if feature engineering completed successfully
    """
    # Load configuration
    config = get_pipeline_config()
    table_config = config.table_config

    # Initialize Spark session
    try:
        spark = DatabricksSession.builder.getOrCreate()
        logger.info("Databricks session initialized")
    except Exception as e:
        logger.error(f"Failed to initialize Databricks session: {e}")
        return False

    # Read silver data
    silver_table = get_full_table_name(table_config.silver_claims)
    df = read_silver_data(spark, silver_table)

    if df is None:
        logger.error("Failed to read silver data - aborting feature engineering")
        return False

    # Create hospital aggregations
    hosp_stats = create_hospital_aggregations(df)

    # Join back to claims
    features_df = join_hospital_features(df, hosp_stats)

    # Create ratio features
    features_df = create_ratio_features(features_df)

    # Validate features
    if not validate_features(features_df):
        logger.error("Feature validation failed")
        return False

    # Write to features table
    features_table = get_full_table_name(table_config.silver_features)
    record_count = features_df.count()

    logger.info(f"Writing {record_count:,} records to features table: {features_table}")

    try:
        features_df.write.format("delta").mode("overwrite").saveAsTable(features_table)
        logger.info(f"Features table written successfully: {features_table}")
    except Exception as e:
        logger.error(f"Failed to write features table: {e}")
        return False

    # Show sample features
    logger.info("Sample features:")
    features_df.select(
        "claim_id",
        "hospital_id",
        "billed_amount",
        "hosp_avg_billed",
        "hosp_stddev_billed",
        "amount_to_avg_ratio",
        "amount_z_score",
        "is_above_2std",
    ).show(5, truncate=False)

    # Log feature statistics
    logger.info("Feature statistics:")
    features_df.select(
        F.avg("amount_to_avg_ratio").alias("avg_ratio"),
        F.min("amount_to_avg_ratio").alias("min_ratio"),
        F.max("amount_to_avg_ratio").alias("max_ratio"),
        F.avg("amount_z_score").alias("avg_z_score"),
    ).show()

    return True


def main():
    """Entry point for feature engineering."""
    try:
        # Attempt to set up auth from secrets
        setup_databricks_auth()

        success = engineer_features()

        if success:
            logger.info("Feature engineering completed successfully")
            return 0
        else:
            logger.error("Feature engineering failed")
            return 1

    except Exception as e:
        logger.exception(f"Feature engineering failed with exception: {e}")
        return 1


if __name__ == "__main__":
    exit(main())
