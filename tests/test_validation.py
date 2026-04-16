"""
Tests for data validation module.
"""

import pytest
from unittest.mock import Mock, MagicMock, patch
from healthclaim_guardian.validation import (
    DataValidator,
    ValidationStatus,
    ValidationResult,
    ValidationReport,
)


class TestValidationResult:
    """Tests for ValidationResult dataclass."""

    def test_create_result(self):
        """Test creating a validation result."""
        result = ValidationResult(
            expectation_name="test_check",
            status=ValidationStatus.PASSED,
            message="Test passed",
        )

        assert result.expectation_name == "test_check"
        assert result.status == ValidationStatus.PASSED
        assert result.message == "Test passed"
        assert result.details == {}

    def test_create_result_with_details(self):
        """Test creating a result with details."""
        result = ValidationResult(
            expectation_name="test_check",
            status=ValidationStatus.FAILED,
            message="Test failed",
            details={"error_code": 123},
        )

        assert result.details == {"error_code": 123}


class TestValidationReport:
    """Tests for ValidationReport."""

    def test_is_valid_when_passed(self):
        """Test is_valid property when all passed."""
        report = ValidationReport(
            table_name="test_table",
            layer="test",
            passed=5,
            failed=0,
            warnings=0,
        )

        assert report.is_valid is True

    def test_is_valid_when_failed(self):
        """Test is_valid property when any failed."""
        report = ValidationReport(
            table_name="test_table",
            layer="test",
            passed=3,
            failed=2,
            warnings=1,
        )

        assert report.is_valid is False

    def test_summary(self):
        """Test summary property."""
        report = ValidationReport(
            table_name="test_table",
            layer="test",
            passed=3,
            failed=1,
            warnings=1,
        )

        summary = report.summary

        assert "test_table" in summary
        assert "Passed: 3" in summary
        assert "Failed: 1" in summary
        assert "Warnings: 1" in summary


class TestDataValidator:
    """Tests for DataValidator."""

    @pytest.fixture
    def mock_spark(self):
        """Create a mock Spark session."""
        spark = Mock()
        return spark

    @pytest.fixture
    def mock_df(self):
        """Create a mock DataFrame."""
        df = Mock()
        df.columns = ["claim_id", "patient_id", "billed_amount", "claim_status"]
        df.count.return_value = 1000
        df.filter.return_value.count.return_value = 0
        return df

    def test_validate_bronze_success(self, mock_spark, mock_df, monkeypatch):
        """Test bronze validation when all checks pass."""
        monkeypatch.setenv("DATABRICKS_HOST", "https://test.databricks.net")

        mock_spark.read.table.return_value = mock_df

        validator = DataValidator(mock_spark, "bronze")
        report = validator.validate_bronze()

        assert report.is_valid is True
        assert report.passed >= 1

    def test_validate_bronze_empty_table(self, mock_spark, monkeypatch):
        """Test bronze validation with empty table."""
        monkeypatch.setenv("DATABRICKS_HOST", "https://test.databricks.net")

        mock_df = Mock()
        mock_df.columns = ["claim_id", "patient_id"]
        mock_df.count.return_value = 0
        mock_spark.read.table.return_value = mock_df

        validator = DataValidator(mock_spark, "bronze")
        report = validator.validate_bronze()

        assert any(r.status == ValidationStatus.FAILED for r in report.results)

    def test_validate_bronze_missing_columns(self, mock_spark, monkeypatch):
        """Test bronze validation with missing columns."""
        monkeypatch.setenv("DATABRICKS_HOST", "https://test.databricks.net")

        mock_df = Mock()
        mock_df.columns = ["claim_id"]  # Missing required columns
        mock_df.count.return_value = 100
        mock_spark.read.table.return_value = mock_df

        validator = DataValidator(mock_spark, "bronze")
        report = validator.validate_bronze()

        assert any(r.status == ValidationStatus.FAILED for r in report.results)
        assert any("required_columns" in r.expectation_name for r in report.results)

    def test_validate_silver_negative_amounts(self, mock_spark, monkeypatch):
        """Test silver validation detects negative amounts."""
        monkeypatch.setenv("DATABRICKS_HOST", "https://test.databricks.net")

        mock_df = Mock()
        mock_df.columns = ["claim_id", "patient_id", "billed_amount", "claim_status"]
        mock_df.count.return_value = 1000

        # First call: count() = 1000
        # Second call: filter for negative = 50
        # Third call: filter for invalid codes = 0
        mock_df.filter.return_value.count.side_effect = [0, 50, 0, 0]
        mock_spark.read.table.return_value = mock_df

        validator = DataValidator(mock_spark, "silver")
        report = validator.validate_silver()

        assert any(r.status == ValidationStatus.FAILED for r in report.results)
        assert any("negative" in r.expectation_name for r in report.results)

    def test_validate_features_null_ratios(self, mock_spark, monkeypatch):
        """Test features validation detects NULL ratios."""
        monkeypatch.setenv("DATABRICKS_HOST", "https://test.databricks.net")

        mock_df = Mock()
        mock_df.columns = ["claim_id", "hosp_avg_billed", "amount_to_avg_ratio"]
        mock_df.count.return_value = 1000
        # First filter: NULL ratios = 100
        # Second filter: negative ratios = 0
        mock_df.filter.return_value.count.side_effect = [100, 0]
        mock_spark.read.table.return_value = mock_df

        validator = DataValidator(mock_spark, "features")
        report = validator.validate_features()

        assert any(r.status == ValidationStatus.FAILED for r in report.results)


class TestValidateLayer:
    """Tests for validate_layer convenience function."""

    @patch("healthclaim_guardian.validation.DataValidator")
    def test_validate_layer_returns_bool(self, mock_validator_class, monkeypatch):
        """Test that validate_layer returns a boolean."""
        monkeypatch.setenv("DATABRICKS_HOST", "https://test.databricks.net")

        mock_validator = Mock()
        mock_validator.validate.return_value = ValidationReport(
            table_name="test",
            layer="bronze",
            passed=5,
            failed=0,
        )
        mock_validator_class.return_value = mock_validator

        from healthclaim_guardian.validation import validate_layer

        result = validate_layer(Mock(), "bronze")

        assert isinstance(result, bool)
        assert result is True
