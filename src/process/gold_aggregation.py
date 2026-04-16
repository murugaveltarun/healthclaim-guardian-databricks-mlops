"""
Gold Layer - Anomaly Detection and Fraud Scoring.

This module applies the trained ML model to detect anomalous claims
and produces the final gold-layer output with fraud indicators.

Anomaly Detection Logic:
1. Load production model from MLflow Model Registry
2. Predict cluster assignments for all claims
3. Identify anomalous cluster (highest average ratio)
4. Apply threshold-based filtering for final anomaly flags
5. Generate fraud score and risk level
"""

from typing import Optional, Any
import mlflow
import mlflow.sklearn
from sklearn.preprocessing import StandardScaler
from databricks.connect import DatabricksSession
from pyspark.sql import DataFrame
from pyspark.sql import functions as F

from healthclaim_guardian.config import get_pipeline_config, get_full_table_name
from healthclaim_guardian.logging_config import setup_logger
from healthclaim_guardian.secrets import setup_databricks_auth
from healthclaim_guardian.model_registry import ModelRegistryManager

logger = setup_logger(__name__)


def load_production_model() -> Optional[Any]:
    """
    Load the production model from MLflow Model Registry.

    Returns:
        Loaded sklearn model, or None if not available
    """
    logger.info("Loading production model from Model Registry...")

    config = get_pipeline_config()
    registry = ModelRegistryManager(config.model_registry_name)

    model = registry.load_model(stage="Production")

    if model is None:
        logger.warning("No production model found - attempting to load from Staging")
        model = registry.load_model(stage="Staging")

    if model:
        logger.info("Model loaded successfully from registry")
    else:
        logger.error("No model available in Production or Staging")

    return model


def read_features_data(spark, table_name: str) -> Optional[DataFrame]:
    """Read features data from Spark table."""
    logger.info(f"Reading features from {table_name}...")

    try:
        df = spark.read.table(table_name)
        logger.info(f"Loaded {df.count():,} records")
        return df
    except Exception as e:
        logger.error(f"Failed to read features table: {e}")
        return None


def predict_anomalies(
    pdf,
    model: Any,
    feature_columns: list,
    config,
) -> tuple:
    """
    Apply model to predict anomalies.

    Args:
        pdf: Pandas DataFrame with features
        model: Trained KMeans model
        feature_columns: List of feature column names
        config: Pipeline configuration

    Returns:
        Tuple of (pdf with predictions, anomaly cluster label)
    """
    logger.info("Predicting anomalies...")

    # Prepare features
    X = pdf[feature_columns].copy()

    # Scale features (must match training preprocessing)
    scaler = StandardScaler()
    X_scaled = scaler.fit_transform(X)

    # Predict clusters
    pdf["cluster_prediction"] = model.predict(X_scaled)

    # Calculate cluster statistics
    cluster_stats = pdf.groupby("cluster_prediction")["amount_to_avg_ratio"].mean()
    logger.info(f"Cluster statistics (avg ratio):\n{cluster_stats}")

    # Identify anomaly cluster (highest average ratio)
    anomaly_cluster = None
    if len(cluster_stats) >= config.min_clusters_for_anomaly:
        anomaly_cluster = int(cluster_stats.idxmax())
        logger.info(f"Anomaly cluster identified: {anomaly_cluster}")
    else:
        logger.warning(
            f"Only {len(cluster_stats)} cluster(s) found - "
            "anomaly detection may be unreliable"
        )

    return pdf, anomaly_cluster


def flag_anomalies(
    pdf,
    anomaly_cluster: Optional[int],
    config,
) -> pd.DataFrame:
    """
    Flag anomalous claims based on cluster and threshold.

    Args:
        pdf: DataFrame with cluster predictions
        anomaly_cluster: Label of anomalous cluster
        config: Pipeline configuration

    Returns:
        DataFrame with anomaly flags
    """
    if anomaly_cluster is None:
        logger.warning("No anomaly cluster identified - flagging all as non-anomalous")
        pdf["is_anomaly"] = False
        pdf["anomaly_confidence"] = 0.0
    else:
        # Flag as anomaly if in anomaly cluster AND above threshold
        pdf["is_anomaly"] = (
            (pdf["cluster_prediction"] == anomaly_cluster) &
            (pdf["amount_to_avg_ratio"] > config.anomaly_ratio_threshold)
        )

        # Calculate confidence score (how far above threshold)
        pdf["anomaly_confidence"] = pdf.apply(
            lambda row: min(1.0, (row["amount_to_avg_ratio"] - 1.0) / 2.0)
            if row["is_anomaly"] else 0.0,
            axis=1,
        )

    # Assign risk levels
    def assign_risk_level(row):
        if row["is_anomaly"]:
            if row["anomaly_confidence"] > 0.7:
                return "HIGH"
            elif row["anomaly_confidence"] > 0.4:
                return "MEDIUM"
            else:
                return "LOW"
        elif row["amount_to_avg_ratio"] > 1.5:
            return "REVIEW"
        else:
            return "NORMAL"

    pdf["risk_level"] = pdf.apply(assign_risk_level, axis=1)

    # Log anomaly statistics
    anomaly_count = pdf["is_anomaly"].sum()
    total_count = len(pdf)
    anomaly_rate = anomaly_count / total_count if total_count > 0 else 0

    logger.info(f"Anomaly detection results:")
    logger.info(f"  Total claims: {total_count:,}")
    logger.info(f"  Anomalies flagged: {anomaly_count:,} ({anomaly_rate:.1%})")
    logger.info(f"  Risk levels: {pdf['risk_level'].value_counts().to_dict()}")

    return pdf


def write_gold_layer(
    spark,
    pdf,
    table_name: str,
) -> bool:
    """
    Write gold layer data to Delta table.

    Args:
        spark: DatabricksSession
        pdf: Pandas DataFrame with gold layer data
        table_name: Target table name

    Returns:
        True if write successful, False otherwise
    """
    logger.info(f"Writing gold layer to {table_name}...")

    try:
        # Convert back to Spark DataFrame
        sdf = spark.createDataFrame(pdf)

        sdf.write.format("delta").mode("overwrite").saveAsTable(table_name)
        logger.info(f"Gold layer written successfully: {table_name}")
        return True

    except Exception as e:
        logger.error(f"Failed to write gold layer: {e}")
        return False


def generate_gold_layer() -> bool:
    """
    Main function to generate gold layer with anomaly detection.

    Returns:
        True if successful, False otherwise
    """
    # Import pandas at module level for type hints
    import pandas as pd

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

    # Load production model
    model = load_production_model()

    if model is None:
        logger.error("Cannot proceed without a trained model")
        logger.info("Please run the training pipeline first: python -m src.mlops.train_model")
        return False

    # Read features data
    features_table = get_full_table_name(table_config.silver_features)
    df = read_features_data(spark, features_table)

    if df is None:
        logger.error("Failed to read features data")
        return False

    # Convert to Pandas for ML prediction
    pdf = df.toPandas()
    pdf = pdf.dropna()

    # Predict anomalies
    pdf, anomaly_cluster = predict_anomalies(
        pdf,
        model,
        config.feature_columns,
        config,
    )

    # Flag anomalies and assign risk levels
    pdf = flag_anomalies(pdf, anomaly_cluster, config)

    # Write to gold table
    gold_table = get_full_table_name(table_config.gold_anomalies)

    if not write_gold_layer(spark, pdf, gold_table):
        return False

    # Show sample output
    logger.info("Sample gold layer data:")
    spark_df = spark.createDataFrame(
        pdf[
            [
                "claim_id",
                "patient_id",
                "hospital_id",
                "billed_amount",
                "amount_to_avg_ratio",
                "cluster_prediction",
                "is_anomaly",
                "anomaly_confidence",
                "risk_level",
            ]
        ]
    )
    spark_df.show(10, truncate=False)

    # Summary statistics
    logger.info("Gold layer generation completed successfully")

    return True


def main():
    """Entry point for gold layer generation."""
    try:
        # Set up authentication
        if setup_databricks_auth():
            logger.info("Databricks authentication configured")

        success = generate_gold_layer()

        if success:
            logger.info("Gold layer generation completed successfully")
            return 0
        else:
            logger.error("Gold layer generation failed")
            return 1

    except Exception as e:
        logger.exception(f"Gold layer generation failed: {e}")
        return 1


if __name__ == "__main__":
    exit(main())
