"""
Tests for bronze layer ingestion.
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from src.ingest.generate_bronze import (
    generate_messy_claims,
    create_schema,
)


class TestGenerateMessyClaims:
    """Tests for synthetic data generation."""

    def test_generates_correct_number_of_records(self):
        """Test that correct number of records are generated."""
        records = generate_messy_claims(num_records=100)

        assert len(records) == 100

    def test_dirty_ratio_applied(self):
        """Test that dirty data ratio is applied."""
        # With 50% dirty ratio, we expect roughly half to be dirty
        records = generate_messy_claims(num_records=1000, dirty_ratio=0.50)

        # Check for some dirty data (negative amounts, extreme values, invalid codes)
        dirty_count = sum(
            1 for r in records
            if r[4] < 0 or r[4] > 50000 or r[3] in ["INVALID-CODE-999", "BAD-ICD", ""]
        )

        # Should have some dirty data (allowing for randomness)
        assert dirty_count > 0

    def test_record_structure(self):
        """Test that each record has correct structure."""
        records = generate_messy_claims(num_records=10)

        for record in records:
            assert len(record) == 6  # 6 fields per record
            assert isinstance(record[0], str)  # claim_id
            assert isinstance(record[1], str)  # patient_id
            assert isinstance(record[2], str)  # hospital_id
            assert isinstance(record[3], str)  # diagnosis_code
            assert isinstance(record[4], float)  # billed_amount
            assert isinstance(record[5], str)  # claim_status

    def test_hospital_ids_in_range(self):
        """Test that hospital IDs are in expected range."""
        records = generate_messy_claims(num_records=100)

        hospital_ids = {r[2] for r in records}

        for hosp_id in hospital_ids:
            assert hosp_id.startswith("HOSP-")
            assert len(hosp_id) == 8  # HOSP-XXX format

    def test_claim_status_values(self):
        """Test that claim status has valid values."""
        records = generate_messy_claims(num_records=100)

        valid_statuses = {"PENDING", "APPROVED", "DENIED"}
        statuses = {r[5] for r in records}

        assert statuses.issubset(valid_statuses)


class TestCreateSchema:
    """Tests for PySpark schema creation."""

    def test_schema_has_correct_fields(self):
        """Test schema has all required fields."""
        schema = create_schema()

        field_names = [f.name for f in schema.fields]

        assert "claim_id" in field_names
        assert "patient_id" in field_names
        assert "hospital_id" in field_names
        assert "diagnosis_code" in field_names
        assert "billed_amount" in field_names
        assert "claim_status" in field_names

    def test_claim_id_not_nullable(self):
        """Test that claim_id is not nullable."""
        schema = create_schema()

        claim_id_field = next(f for f in schema.fields if f.name == "claim_id")
        assert claim_id_field.nullable is False

    def test_billed_amount_is_double(self):
        """Test that billed_amount is DoubleType."""
        schema = create_schema()

        amount_field = next(f for f in schema.fields if f.name == "billed_amount")
        assert amount_field.dataType.typeName() == "double"


class TestIngestBronzeData:
    """Tests for bronze ingestion function."""

    @patch("src.ingest.generate_bronze.DatabricksSession")
    @patch("src.ingest.generate_bronze.generate_messy_claims")
    def test_ingest_bronze_data(self, mock_generate, mock_session, monkeypatch):
        """Test bronze ingestion completes successfully."""
        monkeypatch.setenv("DATABRICKS_HOST", "https://test.databricks.net")

        # Mock data generation
        mock_generate.return_value = [
            ("CLM-00000001", "PAT-0001", "HOSP-001", "J01.90", 1000.0, "APPROVED"),
        ]

        # Mock Spark session and DataFrame
        mock_spark = Mock()
        mock_df = Mock()
        mock_df.count.return_value = 1
        mock_spark.createDataFrame.return_value = mock_df
        mock_session.builder.getOrCreate.return_value = mock_spark

        from src.ingest.generate_bronze import ingest_bronze_data

        result = ingest_bronze_data(num_records=1)

        assert result == 1
        mock_df.write.format.assert_called_once_with("delta")
