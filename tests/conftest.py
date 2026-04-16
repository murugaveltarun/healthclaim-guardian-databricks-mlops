"""
Pytest configuration and fixtures for Healthclaim Guardian tests.

This file:
- Configures pytest plugins and options
- Provides shared fixtures (Spark session, mock data)
- Sets up test environment
"""

import os
import sys
import pathlib
import json
import csv
from contextlib import contextmanager
from typing import Generator, Callable
from unittest.mock import Mock, patch

import pytest

# Try to import test dependencies
try:
    from databricks.connect import DatabricksSession
    from databricks.sdk import WorkspaceClient
    from pyspark.sql import SparkSession
    from pyspark.sql import DataFrame as SparkDataFrame
except ImportError:
    raise ImportError(
        "Test dependencies not installed.\n\n"
        "Run tests using 'uv run pytest'.\n"
        "See https://docs.astral.sh/uv to learn more about uv."
    )


# =============================================================================
# Pytest Configuration
# =============================================================================


def pytest_configure(config: pytest.Config):
    """Configure pytest session."""
    # Set up environment for tests
    os.environ.setdefault("DATABRICKS_HOST", "https://test.databricks.net")
    os.environ.setdefault("DATABRICKS_CATALOG", "test_catalog")
    os.environ.setdefault("DATABRICKS_SCHEMA", "test_schema")

    # Enable serverless compute if not specified
    _enable_fallback_compute()


def _enable_fallback_compute():
    """Enable serverless compute if no compute is specified."""
    try:
        conf = WorkspaceClient().config
        if conf.serverless_compute_id or conf.cluster_id or os.environ.get("SPARK_REMOTE"):
            return
    except Exception:
        pass

    os.environ["DATABRICKS_SERVERLESS_COMPUTE_ID"] = "auto"


# =============================================================================
# Core Fixtures
# =============================================================================


@pytest.fixture(scope="session")
def spark() -> SparkSession:
    """
    Provide a SparkSession fixture for tests.

    This fixture creates a DatabricksSession that can be used
    for DataFrame operations in tests.

    Example:
        def test_uses_spark(spark):
            df = spark.createDataFrame([(1,)], ["x"])
            assert df.count() == 1
    """
    return DatabricksSession.builder.getOrCreate()


@pytest.fixture
def load_fixture(spark: SparkSession) -> Callable[[str], SparkDataFrame]:
    """
    Provide a callable to load test data from fixtures/ directory.

    Supports JSON and CSV files.

    Example:
        def test_using_fixture(load_fixture):
            data = load_fixture("sample_claims.json")
            assert data.count() >= 1
    """

    def _loader(filename: str) -> SparkDataFrame:
        path = pathlib.Path(__file__).parent.parent / "fixtures" / filename
        suffix = path.suffix.lower()

        if suffix == ".json":
            rows = json.loads(path.read_text())
            return spark.createDataFrame(rows)
        elif suffix == ".csv":
            with path.open(newline="") as f:
                rows = list(csv.DictReader(f))
            return spark.createDataFrame(rows)
        else:
            raise ValueError(f"Unsupported fixture type for: {filename}")

    return _loader


# =============================================================================
# Mock Fixtures
# =============================================================================


@pytest.fixture
def mock_spark_session() -> Mock:
    """
    Provide a mock Spark session for unit tests.

    Use this when you don't need real Spark operations.
    """
    mock = Mock(spec=SparkSession)
    mock.read = Mock()
    mock.createDataFrame = Mock()
    return mock


@pytest.fixture
def mock_dataframe() -> Mock:
    """
    Provide a mock DataFrame for unit tests.

    Example:
        def test_with_mock_df(mock_dataframe):
            mock_dataframe.count.return_value = 100
            assert mock_dataframe.count() == 100
    """
    mock = Mock(spec=SparkDataFrame)
    mock.count.return_value = 0
    mock.filter.return_value = mock
    mock.select.return_value = mock
    mock.withColumn.return_value = mock
    mock.dropDuplicates.return_value = mock
    mock.fillna.return_value = mock
    return mock


@pytest.fixture
def mock_databricks_session():
    """
    Mock DatabricksSession.builder for testing.

    Example:
        def test_ingestion(mock_databricks_session):
            result = ingest_bronze_data()
            assert result > 0
    """
    with patch("databricks.connect.DatabricksSession.builder") as mock_builder:
        mock_spark = Mock()
        mock_builder.getOrCreate.return_value = mock_spark
        yield mock_builder


# =============================================================================
# Test Data Fixtures
# =============================================================================


@pytest.fixture
def sample_claim_data() -> list:
    """
    Provide sample claim data for testing.

    Returns a list of tuples matching the bronze schema.
    """
    return [
        ("CLM-00000001", "PAT-0001", "HOSP-001", "J01.90", 1500.00, "APPROVED"),
        ("CLM-00000002", "PAT-0002", "HOSP-001", "E11.9", 2500.00, "PENDING"),
        ("CLM-00000003", "PAT-0003", "HOSP-002", "I10", -500.00, "DENIED"),  # Negative
        ("CLM-00000004", "PAT-0004", "HOSP-002", "INVALID-CODE-999", 3000.00, "APPROVED"),  # Invalid
        ("CLM-00000005", "PAT-0005", "HOSP-003", "M54.5", 150000.00, "APPROVED"),  # Outlier
        ("CLM-00000006", "PAT-0006", "HOSP-003", "", 800.00, "PENDING"),  # Empty diagnosis
        ("CLM-00000007", "PAT-0007", "HOSP-001", None, 1200.00, "APPROVED"),  # NULL diagnosis
    ]


@pytest.fixture
def sample_features_data() -> list:
    """
    Provide sample features data for ML testing.

    Returns a list of dicts with feature columns.
    """
    return [
        {
            "claim_id": "CLM-001",
            "hospital_id": "HOSP-001",
            "billed_amount": 1500.00,
            "hosp_avg_billed": 1400.00,
            "hosp_stddev_billed": 200.00,
            "amount_to_avg_ratio": 1.07,
        },
        {
            "claim_id": "CLM-002",
            "hospital_id": "HOSP-001",
            "billed_amount": 5000.00,
            "hosp_avg_billed": 1400.00,
            "hosp_stddev_billed": 200.00,
            "amount_to_avg_ratio": 3.57,
        },
        {
            "claim_id": "CLM-003",
            "hospital_id": "HOSP-002",
            "billed_amount": 2000.00,
            "hosp_avg_billed": 1800.00,
            "hosp_stddev_billed": 300.00,
            "amount_to_avg_ratio": 1.11,
        },
    ]


@pytest.fixture
def mock_mlflow_client() -> Mock:
    """
    Provide a mock MLflow client for testing model operations.
    """
    mock = Mock()
    mock.get_registered_model.return_value = Mock()
    mock.register_model.return_value = Mock(version="1")
    mock.get_latest_versions.return_value = [Mock(version="1")]
    mock.search_model_versions.return_value = []
    return mock


# =============================================================================
# Environment Fixtures
# =============================================================================


@pytest.fixture
def clean_env(monkeypatch) -> Generator[None, None, None]:
    """
    Fixture to clean environment variables before each test.

    Restores original values after test completes.
    """
    # Store original values
    original = {
        "DATABRICKS_HOST": os.environ.get("DATABRICKS_HOST"),
        "DATABRICKS_TOKEN": os.environ.get("DATABRICKS_TOKEN"),
        "DATABRICKS_CATALOG": os.environ.get("DATABRICKS_CATALOG"),
        "DATABRICKS_SCHEMA": os.environ.get("DATABRICKS_SCHEMA"),
    }

    yield

    # Restore original values
    for key, value in original.items():
        if value is not None:
            os.environ[key] = value
        elif key in os.environ:
            del os.environ[key]


@pytest.fixture
def test_config_env(monkeypatch) -> None:
    """
    Set up test configuration environment variables.
    """
    monkeypatch.setenv("DATABRICKS_HOST", "https://test.databricks.net")
    monkeypatch.setenv("DATABRICKS_CATALOG", "test_catalog")
    monkeypatch.setenv("DATABRICKS_SCHEMA", "test_schema")
    monkeypatch.setenv("PIPELINE_NUM_RECORDS", "100")
    monkeypatch.setenv("ML_N_CLUSTERS", "2")
