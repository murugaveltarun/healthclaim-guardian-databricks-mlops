"""
Data Validation - Databricks Expectations for data quality.

This module defines data quality expectations for each pipeline layer
and validates data against these expectations before processing.

Expectations are defined for:
- Bronze layer: Raw ingested data (minimal validation)
- Silver layer: Cleaned data (strict validation)
- Features: ML-ready features (statistical validation)
"""

from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass, field
from enum import Enum

from healthclaim_guardian.config import get_pipeline_config, get_full_table_name
from healthclaim_guardian.logging_config import setup_logger

logger = setup_logger(__name__)


class ValidationStatus(Enum):
    """Status of a validation check."""
    PASSED = "passed"
    FAILED = "failed"
    WARNING = "warning"
    SKIPPED = "skipped"


@dataclass
class ValidationResult:
    """Result of a single validation check."""
    expectation_name: str
    status: ValidationStatus
    message: str
    details: Dict = field(default_factory=dict)


@dataclass
class ValidationReport:
    """Complete validation report for a dataset."""
    table_name: str
    layer: str
    results: List[ValidationResult] = field(default_factory=list)
    passed: int = 0
    failed: int = 0
    warnings: int = 0

    @property
    def is_valid(self) -> bool:
        """Check if all critical validations passed."""
        return self.failed == 0

    @property
    def summary(self) -> str:
        """Generate a summary string."""
        total = self.passed + self.failed + self.warnings
        return (
            f"Validation Report: {self.table_name}\n"
            f"  Total checks: {total}\n"
            f"  Passed: {self.passed}\n"
            f"  Failed: {self.failed}\n"
            f"  Warnings: {self.warnings}\n"
            f"  Overall: {'VALID' if self.is_valid else 'INVALID'}"
        )

    def log_summary(self):
        """Log the validation summary."""
        logger.info("=" * 60)
        logger.info(self.summary)
        logger.info("=" * 60)

        for result in self.results:
            if result.status == ValidationStatus.FAILED:
                logger.error(f"  [FAILED] {result.expectation_name}: {result.message}")
            elif result.status == ValidationStatus.WARNING:
                logger.warning(f"  [WARNING] {result.expectation_name}: {result.message}")


class DataValidator:
    """
    Validates data against defined expectations.

    Usage:
        validator = DataValidator(spark, "bronze")
        report = validator.validate()
        if not report.is_valid:
            raise ValueError("Data validation failed")
    """

    def __init__(self, spark, layer: str):
        """
        Initialize validator for a specific layer.

        Args:
            spark: DatabricksSession
            layer: Pipeline layer (bronze, silver, features)
        """
        self.spark = spark
        self.layer = layer
        self.config = get_pipeline_config()
        self.report = ValidationReport(
            table_name=self._get_table_name(),
            layer=layer,
        )

    def _get_table_name(self) -> str:
        """Get fully qualified table name for the layer."""
        table_config = self.config.table_config
        table_map = {
            "bronze": table_config.bronze_claims,
            "silver": table_config.silver_claims,
            "features": table_config.silver_features,
            "gold": table_config.gold_anomalies,
        }
        table_name = table_map.get(self.layer, self.layer)
        return get_full_table_name(table_name)

    def _add_result(self, result: ValidationResult):
        """Add a validation result to the report."""
        self.report.results.append(result)

        if result.status == ValidationStatus.PASSED:
            self.report.passed += 1
            logger.debug(f"[PASSED] {result.expectation_name}")
        elif result.status == ValidationStatus.FAILED:
            self.report.failed += 1
            logger.error(f"[FAILED] {result.expectation_name}: {result.message}")
        elif result.status == ValidationStatus.WARNING:
            self.report.warnings += 1
            logger.warning(f"[WARNING] {result.expectation_name}: {result.message}")

    def validate_bronze(self) -> ValidationReport:
        """Validate bronze layer data."""
        logger.info(f"Validating bronze layer: {self.report.table_name}")

        try:
            df = self.spark.read.table(self.report.table_name)
        except Exception as e:
            self._add_result(ValidationResult(
                expectation_name="table_exists",
                status=ValidationStatus.FAILED,
                message=f"Cannot read table: {e}",
            ))
            return self.report

        # Expectation 1: Table is not empty
        count = df.count()
        if count > 0:
            self._add_result(ValidationResult(
                expectation_name="non_empty_table",
                status=ValidationStatus.PASSED,
                message=f"Table has {count:,} records",
                details={"record_count": count},
            ))
        else:
            self._add_result(ValidationResult(
                expectation_name="non_empty_table",
                status=ValidationStatus.FAILED,
                message="Table is empty",
            ))

        # Expectation 2: Required columns exist
        required_columns = {"claim_id", "patient_id", "billed_amount", "claim_status"}
        actual_columns = set(df.columns)
        missing_columns = required_columns - actual_columns

        if not missing_columns:
            self._add_result(ValidationResult(
                expectation_name="required_columns_exist",
                status=ValidationStatus.PASSED,
                message="All required columns present",
            ))
        else:
            self._add_result(ValidationResult(
                expectation_name="required_columns_exist",
                status=ValidationStatus.FAILED,
                message=f"Missing columns: {missing_columns}",
            ))

        # Expectation 3: claim_id is not null
        null_claims = df.filter(df["claim_id"].isNull()).count()
        if null_claims == 0:
            self._add_result(ValidationResult(
                expectation_name="claim_id_not_null",
                status=ValidationStatus.PASSED,
                message="No NULL claim_ids",
            ))
        else:
            self._add_result(ValidationResult(
                expectation_name="claim_id_not_null",
                status=ValidationStatus.WARNING,
                message=f"Found {null_claims} NULL claim_ids",
                details={"null_count": null_claims},
            ))

        # Expectation 4: billed_amount has values
        null_amounts = df.filter(df["billed_amount"].isNull()).count()
        if null_amounts < count * 0.01:  # Less than 1% nulls
            self._add_result(ValidationResult(
                expectation_name="billed_amount_populated",
                status=ValidationStatus.PASSED,
                message=f"Only {null_amounts} NULL billed_amounts ({null_amounts/count:.1%})",
            ))
        else:
            self._add_result(ValidationResult(
                expectation_name="billed_amount_populated",
                status=ValidationStatus.FAILED,
                message=f"Too many NULL billed_amounts: {null_amounts} ({null_amounts/count:.1%})",
            ))

        return self.report

    def validate_silver(self) -> ValidationReport:
        """Validate silver layer data (stricter than bronze)."""
        logger.info(f"Validating silver layer: {self.report.table_name}")

        # First run bronze validations
        bronze_report = self.validate_bronze()
        self.report.results.extend(bronze_report.results)
        self.report.passed += bronze_report.passed
        self.report.failed += bronze_report.failed
        self.report.warnings += bronze_report.warnings

        try:
            df = self.spark.read.table(self.report.table_name)
        except Exception as e:
            self._add_result(ValidationResult(
                expectation_name="table_exists",
                status=ValidationStatus.FAILED,
                message=f"Cannot read table: {e}",
            ))
            return self.report

        count = df.count()

        # Expectation 5: No negative billed_amounts
        negative_amounts = df.filter(df["billed_amount"] < 0).count()
        if negative_amounts == 0:
            self._add_result(ValidationResult(
                expectation_name="no_negative_amounts",
                status=ValidationStatus.PASSED,
                message="No negative billed_amounts",
            ))
        else:
            self._add_result(ValidationResult(
                expectation_name="no_negative_amounts",
                status=ValidationStatus.FAILED,
                message=f"Found {negative_amounts} negative billed_amounts",
            ))

        # Expectation 6: No invalid diagnosis codes
        invalid_codes = df.filter(
            df["diagnosis_code"] == self.config.invalid_diagnosis_code
        ).count()
        if invalid_codes == 0:
            self._add_result(ValidationResult(
                expectation_name="no_invalid_diagnosis_codes",
                status=ValidationStatus.PASSED,
                message="No invalid diagnosis codes",
            ))
        else:
            self._add_result(ValidationResult(
                expectation_name="no_invalid_diagnosis_codes",
                status=ValidationStatus.FAILED,
                message=f"Found {invalid_codes} invalid diagnosis codes",
            ))

        # Expectation 7: No extreme outliers
        outliers = df.filter(
            df["billed_amount"] >= self.config.max_billed_amount
        ).count()
        if outliers == 0:
            self._add_result(ValidationResult(
                expectation_name="no_extreme_outliers",
                status=ValidationStatus.PASSED,
                message=f"No amounts >= ${self.config.max_billed_amount:,.0f}",
            ))
        else:
            self._add_result(ValidationResult(
                expectation_name="no_extreme_outliers",
                status=ValidationStatus.FAILED,
                message=f"Found {outliers} extreme outliers",
            ))

        return self.report

    def validate_features(self) -> ValidationReport:
        """Validate feature engineering output."""
        logger.info(f"Validating features layer: {self.report.table_name}")

        try:
            df = self.spark.read.table(self.report.table_name)
        except Exception as e:
            self._add_result(ValidationResult(
                expectation_name="table_exists",
                status=ValidationStatus.FAILED,
                message=f"Cannot read table: {e}",
            ))
            return self.report

        count = df.count()

        # Expectation 1: Required feature columns exist
        required_features = {"hosp_avg_billed", "amount_to_avg_ratio"}
        actual_columns = set(df.columns)
        missing_features = required_features - actual_columns

        if not missing_features:
            self._add_result(ValidationResult(
                expectation_name="required_features_exist",
                status=ValidationStatus.PASSED,
                message="All required features present",
            ))
        else:
            self._add_result(ValidationResult(
                expectation_name="required_features_exist",
                status=ValidationStatus.FAILED,
                message=f"Missing features: {missing_features}",
            ))

        # Expectation 2: No NULL in critical features
        null_ratio = df.filter(df["amount_to_avg_ratio"].isNull()).count()
        if null_ratio == 0:
            self._add_result(ValidationResult(
                expectation_name="no_null_ratios",
                status=ValidationStatus.PASSED,
                message="No NULL ratio values",
            ))
        else:
            self._add_result(ValidationResult(
                expectation_name="no_null_ratios",
                status=ValidationStatus.FAILED,
                message=f"Found {null_ratio} NULL ratio values",
            ))

        # Expectation 3: Ratio values are positive
        negative_ratio = df.filter(df["amount_to_avg_ratio"] < 0).count()
        if negative_ratio == 0:
            self._add_result(ValidationResult(
                expectation_name="positive_ratios",
                status=ValidationStatus.PASSED,
                message="All ratios are positive",
            ))
        else:
            self._add_result(ValidationResult(
                expectation_name="positive_ratios",
                status=ValidationStatus.FAILED,
                message=f"Found {negative_ratio} negative ratios",
            ))

        return self.report

    def validate(self) -> ValidationReport:
        """
        Run validation for the configured layer.

        Returns:
            ValidationReport with all results
        """
        if self.layer == "bronze":
            return self.validate_bronze()
        elif self.layer == "silver":
            return self.validate_silver()
        elif self.layer == "features":
            return self.validate_features()
        else:
            self._add_result(ValidationResult(
                expectation_name="layer_validation",
                status=ValidationStatus.SKIPPED,
                message=f"Unknown layer: {self.layer}",
            ))
            return self.report


def validate_layer(spark, layer: str) -> bool:
    """
    Convenience function to validate a pipeline layer.

    Args:
        spark: DatabricksSession
        layer: Layer name (bronze, silver, features)

    Returns:
        True if validation passed, False otherwise
    """
    validator = DataValidator(spark, layer)
    report = validator.validate()
    report.log_summary()
    return report.is_valid
