"""
MLflow Model Registry utility for Healthclaim Guardian.

Provides model registration, loading, and stage management
for the fraud detection models.
"""

import mlflow
from mlflow.tracking import MlflowClient
from typing import Optional, Dict, Any
from healthclaim_guardian.logging_config import setup_logger
from healthclaim_guardian.config import get_pipeline_config

logger = setup_logger(__name__)


class ModelRegistryManager:
    """
    Manages MLflow model registry operations.

    Handles:
    - Model registration
    - Stage transitions (Staging → Production)
    - Loading latest production model
    - Model version comparison
    """

    def __init__(self, model_name: Optional[str] = None):
        """
        Initialize the model registry manager.

        Args:
            model_name: Name of the model in registry (default from config)
        """
        config = get_pipeline_config()
        self.model_name = model_name or config.model_registry_name
        self.client = MlflowClient()
        logger.info(f"ModelRegistryManager initialized for model: {self.model_name}")

    def register_model(self, run_id: str, model_name: Optional[str] = None) -> str:
        """
        Register a model from an MLflow run.

        Args:
            run_id: ID of the MLflow run containing the model
            model_name: Optional override for model name

        Returns:
            The version number of the registered model
        """
        name = model_name or self.model_name
        model_uri = f"runs:/{run_id}/fraud_detection_model"

        logger.info(f"Registering model from run {run_id} as '{name}'...")

        try:
            # Check if model already exists
            existing_model = self.client.get_registered_model(name)
            if existing_model:
                logger.info(f"Model '{name}' already exists, registering new version")
        except mlflow.exceptions.MlflowException:
            logger.info(f"Creating new registered model '{name}'")

        # Register the model
        model_version = self.client.register_model(
            model_uri=model_uri,
            name=name,
        )

        logger.info(f"Model registered successfully as '{name}' version {model_version.version}")
        return model_version.version

    def transition_to_stage(self, version: str, stage: str) -> None:
        """
        Transition a model version to a specific stage.

        Args:
            version: Model version number
            stage: Target stage (Production, Staging, Archived)
        """
        logger.info(f"Transitioning model '{self.model_name}' version {version} to {stage}")

        self.client.transition_model_version_stage(
            name=self.model_name,
            version=version,
            stage=stage,
        )

        logger.info(f"Model '{self.model_name}' version {version} is now in {stage} stage")

    def get_latest_version(self, stage: str = "Production") -> Optional[str]:
        """
        Get the latest model version in a specific stage.

        Args:
            stage: Model stage to search for

        Returns:
            Model URI for the latest version, or None if not found
        """
        logger.info(f"Looking for latest '{self.model_name}' model in {stage} stage")

        try:
            latest_versions = self.client.get_latest_versions(
                name=self.model_name,
                stages=[stage],
            )

            if not latest_versions:
                logger.warning(f"No model found in {stage} stage")
                return None

            # Get the highest version number
            latest = max(latest_versions, key=lambda x: int(x.version))
            model_uri = f"models:/{self.model_name}/{stage}"

            logger.info(f"Found model version {latest.version} in {stage} stage")
            return model_uri

        except mlflow.exceptions.MlflowException as e:
            logger.error(f"Error getting latest model version: {e}")
            return None

    def load_model(self, stage: str = "Production"):
        """
        Load the latest model from a specific stage.

        Args:
            stage: Model stage to load from

        Returns:
            Loaded model object, or None if not found
        """
        model_uri = self.get_latest_version(stage)

        if model_uri is None:
            logger.warning(f"Cannot load model - no model found in {stage} stage")
            return None

        logger.info(f"Loading model from {model_uri}")

        try:
            import mlflow.sklearn
            model = mlflow.sklearn.load_model(model_uri)
            logger.info("Model loaded successfully")
            return model
        except Exception as e:
            logger.error(f"Failed to load model: {e}")
            return None

    def get_model_info(self, stage: str = "Production") -> Optional[Dict[str, Any]]:
        """
        Get information about a model version.

        Args:
            stage: Model stage

        Returns:
            Dictionary with model info, or None if not found
        """
        try:
            versions = self.client.get_latest_versions(
                name=self.model_name,
                stages=[stage],
            )

            if not versions:
                return None

            latest = max(versions, key=lambda x: int(x.version))

            return {
                "name": self.model_name,
                "version": latest.version,
                "stage": stage,
                "run_id": latest.run_id,
                "creation_timestamp": latest.creation_timestamp,
                "status": latest.status,
            }

        except mlflow.exceptions.MlflowException as e:
            logger.error(f"Error getting model info: {e}")
            return None

    def list_all_versions(self) -> list:
        """List all versions of the registered model."""
        try:
            versions = self.client.search_model_versions(
                f"name='{self.model_name}'"
            )
            return sorted(versions, key=lambda x: int(x.version), reverse=True)
        except mlflow.exceptions.MlflowException as e:
            logger.error(f"Error listing model versions: {e}")
            return []


def load_production_model() -> Optional[Any]:
    """
    Convenience function to load the production model.

    Returns:
        Loaded model or None if not available
    """
    registry = ModelRegistryManager()
    return registry.load_model(stage="Production")


def register_and_promote(run_id: str, stage: str = "Production") -> Optional[str]:
    """
    Register a model and promote it to a stage.

    Args:
        run_id: MLflow run ID
        stage: Target stage

    Returns:
        Model version if successful, None otherwise
    """
    registry = ModelRegistryManager()

    try:
        version = registry.register_model(run_id)
        registry.transition_to_stage(version, stage)
        logger.info(f"Model version {version} registered and promoted to {stage}")
        return version
    except Exception as e:
        logger.error(f"Failed to register and promote model: {e}")
        return None
