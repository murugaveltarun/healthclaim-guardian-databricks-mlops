"""
ML Model Training - Train anomaly detection model.

This module trains a K-Means clustering model for detecting anomalous
healthcare claims. The model is logged to MLflow and registered to
the Model Registry for production use.

Model Details:
- Algorithm: K-Means Clustering (Scikit-learn)
- Features: billed_amount, hosp_avg_billed, amount_to_avg_ratio
- Preprocessing: StandardScaler for feature normalization
- Evaluation: Silhouette score, cluster statistics
"""

import os
from typing import Optional, Tuple
from databricks.connect import DatabricksSession
import mlflow
import mlflow.sklearn
from sklearn.preprocessing import StandardScaler
from sklearn.cluster import KMeans
from sklearn.metrics import silhouette_score
import pandas as pd

from healthclaim_guardian.config import get_pipeline_config, get_full_table_name
from healthclaim_guardian.logging_config import setup_logger
from healthclaim_guardian.secrets import setup_databricks_auth
from healthclaim_guardian.model_registry import ModelRegistryManager

logger = setup_logger(__name__)


def load_features(spark, table_name: str) -> Optional[pd.DataFrame]:
    """
    Load features from Spark table into Pandas for ML training.

    Args:
        spark: DatabricksSession
        table_name: Fully qualified table name

    Returns:
        Pandas DataFrame with features, or None if loading fails
    """
    logger.info(f"Loading features from {table_name}...")

    try:
        df = spark.read.table(table_name)
        pdf = df.toPandas()

        # Drop rows with any NULL values
        initial_count = len(pdf)
        pdf = pdf.dropna()
        dropped_count = initial_count - len(pdf)

        if dropped_count > 0:
            logger.info(f"Dropped {dropped_count} rows with NULL values")

        logger.info(f"Loaded {len(pdf):,} records for training")
        return pdf

    except Exception as e:
        logger.error(f"Failed to load features: {e}")
        return None


def prepare_features(
    pdf: pd.DataFrame,
    feature_columns: list,
) -> Tuple[pd.DataFrame, pd.DataFrame]:
    """
    Prepare features for training.

    Args:
        pdf: Pandas DataFrame with all features
        feature_columns: List of columns to use as features

    Returns:
        Tuple of (original data, scaled feature matrix)
    """
    logger.info(f"Preparing features: {feature_columns}")

    # Extract feature columns
    X = pdf[feature_columns].copy()

    # Standardize features
    scaler = StandardScaler()
    X_scaled = scaler.fit_transform(X)

    logger.info(f"Features standardized (mean={X_scaled.mean():.4f}, std={X_scaled.std():.4f})")

    return pdf, X_scaled


def train_kmeans(
    X_scaled: pd.DataFrame,
    n_clusters: int = 3,
    random_state: int = 42,
) -> KMeans:
    """
    Train K-Means clustering model.

    Args:
        X_scaled: Scaled feature matrix
        n_clusters: Number of clusters
        random_state: Random seed for reproducibility

    Returns:
        Trained KMeans model
    """
    logger.info(f"Training K-Means with {n_clusters} clusters...")

    model = KMeans(
        n_clusters=n_clusters,
        random_state=random_state,
        n_init="auto",
        max_iter=300,
    )
    model.fit(X_scaled)

    logger.info("K-Means training completed")
    return model


def evaluate_model(
    model: KMeans,
    X_scaled: pd.DataFrame,
    pdf: pd.DataFrame,
    feature_columns: list,
) -> dict:
    """
    Evaluate the trained model.

    Args:
        model: Trained KMeans model
        X_scaled: Scaled feature matrix
        pdf: Original Pandas DataFrame
        feature_columns: List of feature column names

    Returns:
        Dictionary of evaluation metrics
    """
    logger.info("Evaluating model...")

    # Predict clusters
    clusters = model.predict(X_scaled)

    # Calculate silhouette score (measure of cluster quality)
    silhouette = silhouette_score(X_scaled, clusters)
    logger.info(f"Silhouette score: {silhouette:.4f}")

    # Calculate cluster statistics
    pdf_temp = pdf.copy()
    pdf_temp["cluster"] = clusters

    cluster_stats = pdf_temp.groupby("cluster")[feature_columns].mean()
    logger.info(f"Cluster centers (original scale):\n{cluster_stats}")

    # Calculate inertia (within-cluster sum of squares)
    inertia = model.inertia_
    logger.info(f"Inertia: {inertia:.4f}")

    return {
        "silhouette_score": silhouette,
        "inertia": inertia,
        "n_clusters": len(model.cluster_centers_),
        "n_samples": len(pdf),
    }


def log_to_mlflow(
    model: KMeans,
    metrics: dict,
    feature_columns: list,
    config,
) -> str:
    """
    Log model and metrics to MLflow.

    Args:
        model: Trained model
        metrics: Evaluation metrics
        feature_columns: List of feature names
        config: Pipeline configuration

    Returns:
        Run ID of the MLflow run
    """
    # Set up MLflow tracking
    mlflow.set_tracking_uri("databricks")
    mlflow.set_experiment(config.mlflow_experiment_path)

    logger.info(f"Logging to MLflow experiment: {config.mlflow_experiment_path}")

    with mlflow.start_run(run_name="kmeans_fraud_detection") as run:
        # Log parameters
        mlflow.log_param("algorithm", "Scikit-Learn KMeans")
        mlflow.log_param("n_clusters", config.kmeans_n_clusters)
        mlflow.log_param("random_state", config.kmeans_random_state)
        mlflow.log_param("features", feature_columns)
        mlflow.log_param("experiment_path", config.mlflow_experiment_path)

        # Log metrics
        mlflow.log_metric("silhouette_score", metrics["silhouette_score"])
        mlflow.log_metric("inertia", metrics["inertia"])
        mlflow.log_metric("n_samples", metrics["n_samples"])

        # Log the model
        mlflow.sklearn.log_model(
            sk_model=model,
            artifact_path="fraud_detection_model",
            registered_model_name=config.model_registry_name,
        )

        logger.info(f"Model logged to MLflow run: {run.info.run_id}")

    return run.info.run_id


def train_and_register() -> Optional[str]:
    """
    Main training function - trains model and registers to MLflow.

    Returns:
        Run ID if training successful, None otherwise
    """
    # Load configuration
    config = get_pipeline_config()

    # Initialize Spark session
    try:
        spark = DatabricksSession.builder.getOrCreate()
        logger.info("Databricks session initialized")
    except Exception as e:
        logger.error(f"Failed to initialize Databricks session: {e}")
        return None

    # Load features
    features_table = get_full_table_name(config.table_config.silver_features)
    pdf = load_features(spark, features_table)

    if pdf is None or len(pdf) == 0:
        logger.error("No features loaded - aborting training")
        return None

    # Prepare features
    pdf, X_scaled = prepare_features(pdf, config.feature_columns)

    # Train model
    model = train_kmeans(
        X_scaled,
        n_clusters=config.kmeans_n_clusters,
        random_state=config.kmeans_random_state,
    )

    # Evaluate model
    metrics = evaluate_model(model, X_scaled, pdf, config.feature_columns)

    # Log to MLflow and get run ID
    run_id = log_to_mlflow(model, metrics, config.feature_columns, config)

    # Register model to Model Registry
    logger.info("Registering model to Model Registry...")
    registry = ModelRegistryManager(config.model_registry_name)

    try:
        version = registry.register_model(run_id)
        registry.transition_to_stage(version, "Production")
        logger.info(f"Model registered and promoted to Production (version {version})")
    except Exception as e:
        logger.warning(f"Model registration failed: {e}")
        logger.info("Model logged to MLflow but not registered")

    return run_id


def main():
    """Entry point for model training."""
    try:
        # Set up authentication from secrets
        if setup_databricks_auth():
            logger.info("Databricks authentication configured from secrets")
        else:
            logger.warning("Using default authentication (may fail if not on Databricks)")

        run_id = train_and_register()

        if run_id:
            logger.info(f"Model training completed successfully (run_id: {run_id})")
            return 0
        else:
            logger.error("Model training failed")
            return 1

    except Exception as e:
        logger.exception(f"Model training failed with exception: {e}")
        return 1


if __name__ == "__main__":
    exit(main())
