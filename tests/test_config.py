"""
Tests for configuration module.
"""

import os
import pytest
from healthclaim_guardian.config import (
    DatabricksConfig,
    PipelineConfig,
    TableConfig,
    get_databricks_config,
    get_pipeline_config,
    get_full_table_name,
)


class TestDatabricksConfig:
    """Tests for DatabricksConfig."""

    def test_from_env_with_host(self, monkeypatch):
        """Test loading config with DATABRICKS_HOST set."""
        monkeypatch.setenv("DATABRICKS_HOST", "https://test.databricks.net")
        monkeypatch.setenv("DATABRICKS_TOKEN", "test_token")
        monkeypatch.setenv("DATABRICKS_CATALOG", "test_catalog")
        monkeypatch.setenv("DATABRICKS_SCHEMA", "test_schema")

        config = DatabricksConfig.from_env()

        assert config.host == "https://test.databricks.net"
        assert config.token == "test_token"
        assert config.catalog == "test_catalog"
        assert config.schema == "test_schema"

    def test_from_env_without_host_raises(self, monkeypatch):
        """Test that missing DATABRICKS_HOST raises ValueError."""
        monkeypatch.delenv("DATABRICKS_HOST", raising=False)

        with pytest.raises(ValueError, match="DATABRICKS_HOST"):
            DatabricksConfig.from_env()

    def test_from_env_defaults(self, monkeypatch):
        """Test default catalog and schema values."""
        monkeypatch.setenv("DATABRICKS_HOST", "https://test.databricks.net")
        monkeypatch.delenv("DATABRICKS_CATALOG", raising=False)
        monkeypatch.delenv("DATABRICKS_SCHEMA", raising=False)

        config = DatabricksConfig.from_env()

        assert config.catalog == "healthclaim_guardian"
        assert config.schema == "default"

    def test_database_property(self, monkeypatch):
        """Test database property returns catalog.schema."""
        monkeypatch.setenv("DATABRICKS_HOST", "https://test.databricks.net")
        monkeypatch.setenv("DATABRICKS_CATALOG", "my_catalog")
        monkeypatch.setenv("DATABRICKS_SCHEMA", "my_schema")

        config = DatabricksConfig.from_env()

        assert config.database == "my_catalog.my_schema"


class TestPipelineConfig:
    """Tests for PipelineConfig."""

    def test_default_values(self):
        """Test default configuration values."""
        config = PipelineConfig()

        assert config.num_records == 10000
        assert config.dirty_data_ratio == 0.10
        assert config.max_billed_amount == 50000.0
        assert config.kmeans_n_clusters == 3
        assert config.anomaly_ratio_threshold == 1.1

    def test_from_env_overrides(self, monkeypatch):
        """Test that environment variables override defaults."""
        monkeypatch.setenv("PIPELINE_NUM_RECORDS", "5000")
        monkeypatch.setenv("PIPELINE_DIRTY_RATIO", "0.25")
        monkeypatch.setenv("PIPELINE_MAX_BILLED", "100000")
        monkeypatch.setenv("ML_N_CLUSTERS", "5")
        monkeypatch.setenv("ANOMALY_THRESHOLD", "2.0")

        config = PipelineConfig.from_env()

        assert config.num_records == 5000
        assert config.dirty_data_ratio == 0.25
        assert config.max_billed_amount == 100000.0
        assert config.kmeans_n_clusters == 5
        assert config.anomaly_ratio_threshold == 2.0

    def test_feature_columns(self):
        """Test feature columns are correctly defined."""
        config = PipelineConfig()

        assert "billed_amount" in config.feature_columns
        assert "hosp_avg_billed" in config.feature_columns
        assert "amount_to_avg_ratio" in config.feature_columns


class TestTableConfig:
    """Tests for TableConfig."""

    def test_table_names(self):
        """Test table name attributes."""
        config = TableConfig()

        assert config.bronze_claims == "insurance_bronze_claims"
        assert config.silver_claims == "insurance_silver_claims"
        assert config.silver_features == "insurance_silver_features"
        assert config.gold_anomalies == "insurance_gold_anomalies"

    def test_get_table_name(self):
        """Test get_table_name method."""
        config = TableConfig()

        assert config.get_table_name("bronze") == "insurance_bronze_claims"
        assert config.get_table_name("silver") == "insurance_silver_claims"
        assert config.get_table_name("features") == "insurance_silver_features"


class TestGetFullTableName:
    """Tests for get_full_table_name utility."""

    def test_with_default_database(self, monkeypatch):
        """Test with default catalog and schema."""
        monkeypatch.setenv("DATABRICKS_HOST", "https://test.databricks.net")

        table_name = get_full_table_name("test_table")

        assert table_name == "healthclaim_guardian.default.test_table"

    def test_with_custom_database(self, monkeypatch):
        """Test with custom database."""
        monkeypatch.setenv("DATABRICKS_HOST", "https://test.databricks.net")

        table_name = get_full_table_name("test_table", "custom_catalog.custom_schema")

        assert table_name == "custom_catalog.custom_schema.test_table"
