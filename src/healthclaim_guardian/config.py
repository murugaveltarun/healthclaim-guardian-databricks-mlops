"""
Centralized configuration for Healthclaim Guardian.

All configuration values are loaded from environment variables or Databricks Secrets.
This module provides a single source of truth for all settings.
"""

import os
from dataclasses import dataclass
from typing import Optional


@dataclass
class DatabricksConfig:
    """Databricks connection configuration."""
    host: str
    token: Optional[str] = None
    catalog: str = "healthclaim_guardian"
    schema: str = "default"

    @classmethod
    def from_env(cls) -> "DatabricksConfig":
        """Load configuration from environment variables."""
        host = os.getenv("DATABRICKS_HOST")
        token = os.getenv("DATABRICKS_TOKEN")  # Optional if using cluster auth

        if not host:
            raise ValueError(
                "DATABRICKS_HOST environment variable is not set. "
                "Please configure it or use Databricks cluster authentication."
            )

        return cls(
            host=host,
            token=token,
            catalog=os.getenv("DATABRICKS_CATALOG", "healthclaim_guardian"),
            schema=os.getenv("DATABRICKS_SCHEMA", "default"),
        )

    @property
    def database(self) -> str:
        """Return full database name (catalog.schema)."""
        return f"{self.catalog}.{self.schema}"


@dataclass
class PipelineConfig:
    """Pipeline configuration settings."""
    # Data generation
    num_records: int = 10000
    dirty_data_ratio: float = 0.10

    # Data cleansing
    max_billed_amount: float = 50000.0
    invalid_diagnosis_code: str = "INVALID-CODE-999"
    default_diagnosis_code: str = "UNKNOWN"

    # Feature engineering
    hospital_agg_columns: tuple = ("billed_amount",)

    # ML training
    mlflow_experiment_path: str = "/healthclaim_fraud"
    mlflow_model_name: str = "fraud_detection_model"
    kmeans_n_clusters: int = 3
    kmeans_random_state: int = 42
    feature_columns: tuple = ("billed_amount", "hosp_avg_billed", "amount_to_avg_ratio")

    # Anomaly detection
    anomaly_ratio_threshold: float = 1.1
    min_clusters_for_anomaly: int = 2

    # Model registry
    model_registry_name: str = "healthclaim_fraud_detector"
    model_stage: str = "Production"

    @classmethod
    def from_env(cls) -> "PipelineConfig":
        """Load configuration from environment variables."""
        return cls(
            num_records=int(os.getenv("PIPELINE_NUM_RECORDS", "10000")),
            dirty_data_ratio=float(os.getenv("PIPELINE_DIRTY_RATIO", "0.10")),
            max_billed_amount=float(os.getenv("PIPELINE_MAX_BILLED", "50000.0")),
            kmeans_n_clusters=int(os.getenv("ML_N_CLUSTERS", "3")),
            anomaly_ratio_threshold=float(os.getenv("ANOMALY_THRESHOLD", "1.1")),
            mlflow_experiment_path=os.getenv(
                "MLFLOW_EXPERIMENT_PATH", "/healthclaim_fraud"
            ),
            model_registry_name=os.getenv(
                "MODEL_REGISTRY_NAME", "healthclaim_fraud_detector"
            ),
        )


@dataclass
class TableConfig:
    """Table name configuration."""
    bronze_claims: str = "insurance_bronze_claims"
    silver_claims: str = "insurance_silver_claims"
    silver_features: str = "insurance_silver_features"
    gold_anomalies: str = "insurance_gold_anomalies"

    def get_table_name(self, layer: str) -> str:
        """Get table name by layer (bronze, silver, gold, features)."""
        return getattr(self, f"{layer}_claims", getattr(self, f"{layer}_features", None))


# Global configuration instances (lazy loaded)
_databricks_config: Optional[DatabricksConfig] = None
_pipeline_config: Optional[PipelineConfig] = None
_table_config = TableConfig()


def get_databricks_config() -> DatabricksConfig:
    """Get or create Databricks configuration."""
    global _databricks_config
    if _databricks_config is None:
        _databricks_config = DatabricksConfig.from_env()
    return _databricks_config


def get_pipeline_config() -> PipelineConfig:
    """Get or create pipeline configuration."""
    global _pipeline_config
    if _pipeline_config is None:
        _pipeline_config = PipelineConfig.from_env()
    return _pipeline_config


def get_table_config() -> TableConfig:
    """Get table configuration."""
    return _table_config


def get_full_table_name(table: str, database: Optional[str] = None) -> str:
    """Get fully qualified table name."""
    if database is None:
        db_config = get_databricks_config()
        database = db_config.database
    return f"{database}.{table}"
