"""
Tests for model registry module.
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from healthclaim_guardian.model_registry import (
    ModelRegistryManager,
    load_production_model,
    register_and_promote,
)


class TestModelRegistryManager:
    """Tests for ModelRegistryManager."""

    @pytest.fixture
    def mock_mlflow_client(self):
        """Create a mock MLflow client."""
        with patch("healthclaim_guardian.model_registry.MlflowClient") as mock:
            yield mock

    @pytest.fixture
    def manager(self, monkeypatch):
        """Create a ModelRegistryManager instance."""
        monkeypatch.setenv("DATABRICKS_HOST", "https://test.databricks.net")
        return ModelRegistryManager(model_name="test_model")

    def test_init(self, manager):
        """Test initialization."""
        assert manager.model_name == "test_model"
        assert manager.client is not None

    def test_register_model(self, manager, mock_mlflow_client):
        """Test model registration."""
        mock_client = Mock()
        mock_client.register_model.return_value = Mock(version="1")
        manager.client = mock_client

        version = manager.register_model(run_id="abc123")

        assert version == "1"
        mock_client.register_model.assert_called_once()

    def test_transition_to_stage(self, manager, mock_mlflow_client):
        """Test stage transition."""
        mock_client = Mock()
        manager.client = mock_client

        manager.transition_to_stage(version="1", stage="Production")

        mock_client.transition_model_version_stage.assert_called_once_with(
            name="test_model",
            version="1",
            stage="Production",
        )

    def test_get_latest_version(self, manager, mock_mlflow_client):
        """Test getting latest version."""
        mock_client = Mock()
        mock_version = Mock()
        mock_version.version = "1"
        mock_client.get_latest_versions.return_value = [mock_version]
        manager.client = mock_client

        model_uri = manager.get_latest_version(stage="Production")

        assert model_uri == "models:/test_model/Production"

    def test_get_latest_version_not_found(self, manager, mock_mlflow_client):
        """Test when no version found."""
        mock_client = Mock()
        mock_client.get_latest_versions.return_value = []
        manager.client = mock_client

        model_uri = manager.get_latest_version(stage="Production")

        assert model_uri is None

    @patch("healthclaim_guardian.model_registry.mlflow.sklearn")
    def test_load_model(self, mock_sklearn, manager, mock_mlflow_client):
        """Test loading model."""
        mock_client = Mock()
        mock_version = Mock()
        mock_version.version = "1"
        mock_client.get_latest_versions.return_value = [mock_version]
        manager.client = mock_client

        mock_model = Mock()
        mock_sklearn.load_model.return_value = mock_model

        model = manager.load_model(stage="Production")

        assert model is not None
        mock_sklearn.load_model.assert_called_once()

    def test_get_model_info(self, manager, mock_mlflow_client):
        """Test getting model info."""
        mock_client = Mock()
        mock_version = Mock()
        mock_version.version = "1"
        mock_version.run_id = "abc123"
        mock_version.creation_timestamp = 1234567890
        mock_version.status = "READY"
        mock_client.get_latest_versions.return_value = [mock_version]
        manager.client = mock_client

        info = manager.get_model_info(stage="Production")

        assert info["version"] == "1"
        assert info["run_id"] == "abc123"

    def test_list_all_versions(self, manager, mock_mlflow_client):
        """Test listing all versions."""
        mock_client = Mock()
        mock_version1 = Mock()
        mock_version1.version = "2"
        mock_version2 = Mock()
        mock_version2.version = "1"
        mock_client.search_model_versions.return_value = [
            mock_version1,
            mock_version2,
        ]
        manager.client = mock_client

        versions = manager.list_all_versions()

        assert len(versions) == 2
        assert versions[0].version == "2"  # Sorted descending


class TestLoadProductionModel:
    """Tests for load_production_model convenience function."""

    @patch("healthclaim_guardian.model_registry.ModelRegistryManager")
    def test_load_production_model(self, mock_registry_class, monkeypatch):
        """Test loading production model."""
        monkeypatch.setenv("DATABRICKS_HOST", "https://test.databricks.net")

        mock_registry = Mock()
        mock_registry.load_model.return_value = "mocked_model"
        mock_registry_class.return_value = mock_registry

        model = load_production_model()

        assert model == "mocked_model"
        mock_registry.load_model.assert_called_once_with(stage="Production")


class TestRegisterAndPromote:
    """Tests for register_and_promote function."""

    @patch("healthclaim_guardian.model_registry.ModelRegistryManager")
    def test_register_and_promote_success(self, mock_registry_class, monkeypatch):
        """Test successful registration and promotion."""
        monkeypatch.setenv("DATABRICKS_HOST", "https://test.databricks.net")

        mock_registry = Mock()
        mock_registry.register_model.return_value = "1"
        mock_registry_class.return_value = mock_registry

        version = register_and_promote(run_id="abc123", stage="Production")

        assert version == "1"
        mock_registry.register_model.assert_called_once_with("abc123")
        mock_registry.transition_to_stage.assert_called_once_with(
            version="1", stage="Production"
        )

    @patch("healthclaim_guardian.model_registry.ModelRegistryManager")
    def test_register_and_promote_failure(self, mock_registry_class, monkeypatch):
        """Test when registration fails."""
        monkeypatch.setenv("DATABRICKS_HOST", "https://test.databricks.net")

        mock_registry = Mock()
        mock_registry.register_model.side_effect = Exception("Registration failed")
        mock_registry_class.return_value = mock_registry

        version = register_and_promote(run_id="abc123", stage="Production")

        assert version is None
