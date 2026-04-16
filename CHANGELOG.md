# Changelog

All notable changes to Healthclaim Guardian are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- Complete MLOps pipeline with MLflow Model Registry integration
- Centralized configuration management via environment variables
- Secrets management with Databricks Secrets integration
- Comprehensive data validation framework
- Risk scoring with confidence levels (HIGH/MEDIUM/LOW/NORMAL)
- Z-score feature for statistical anomaly detection
- Hospital-level aggregation features (avg, min, max, stddev)
- Full test suite with unit and integration tests
- Extensive documentation (README, Architecture, Runbook, API docs)
- Databricks workflow definition for orchestration
- Environment-specific configurations (dev/staging/prod)

### Changed
- **BREAKING**: Removed hardcoded credentials - now requires `DATABRICKS_HOST` environment variable
- **BREAKING**: Model loading now uses Model Registry instead of hardcoded run_id
- Replaced `print()` statements with proper logging framework
- Improved error handling throughout all pipeline stages
- Enhanced anomaly detection with configurable thresholds
- Updated data generation with more realistic synthetic data

### Fixed
- Missing `mlflow` import in gold_aggregation.py
- Hardcoded model run_id causing model loading failures
- Security vulnerability: exposed Databricks token in source code
- Schema drift issues with `overwriteSchema` on every write
- No validation of data quality before processing

### Security
- Removed all hardcoded credentials
- Added secrets management utility
- Implemented secure authentication flow
- Added security documentation to runbook

---

## [0.1.0] - 2026-04-16

### Added
- Initial project structure
- Bronze layer: Synthetic data generation
- Silver layer: Data cleansing pipeline
- Feature engineering: ML feature creation
- Model training: K-Means anomaly detection
- Gold layer: Fraud prediction output
- Basic MLflow integration
- PySpark-based data processing
- Delta Lake storage

### Dependencies
- Python 3.10-3.12
- Databricks Connect 15.4.x
- Scikit-learn >= 1.3.0
- MLflow >= 2.10.0
- Pandas >= 2.0.0
- Faker >= 21.0.0

---

## Version History

| Version | Date | Description |
|---------|------|-------------|
| 0.1.0 | 2026-04-16 | Initial release |
| Unreleased | 2026-04-16 | Production-ready release |

---

## Upcoming Features (Roadmap)

### v0.2.0
- [ ] Real-time inference API
- [ ] Model performance monitoring dashboard
- [ ] Automated retraining triggers
- [ ] SHAP-based explainability

### v0.3.0
- [ ] Support for multiple ML models (Isolation Forest, Autoencoders)
- [ ] A/B testing framework for model comparison
- [ ] Feedback loop for false positive tracking
- [ ] Integration with fraud investigation workflow

### v1.0.0
- [ ] Multi-tenant support
- [ ] HL7/FHIR data ingestion
- [ ] Real-time streaming inference
- [ ] Advanced feature store integration
- [ ] Compliance reporting (HIPAA, SOC2)

---

## Migration Guide

### Migrating from v0.0.1 to v0.1.0

#### 1. Update Environment Variables

```bash
# Required: Set Databricks host
export DATABRICKS_HOST="https://your-workspace.azuredatabricks.net"

# Optional: Set Databricks token (or use secrets)
export DATABRICKS_TOKEN="your-token"
```

#### 2. Update Model Loading Code

**Before (v0.0.1):**
```python
# Hardcoded run_id
model_uri = "runs:6f9aa7a9e85c4118a22b03f6f014ec16/fraud_detection_model"
model = mlflow.sklearn.load_model(model_uri)
```

**After (v0.1.0):**
```python
# Load from Model Registry
from healthclaim_guardian.model_registry import load_production_model
model = load_production_model()
```

#### 3. Install New Dependencies

```bash
uv sync --dev
```

#### 4. Run Data Validation

```python
from healthclaim_guardian.validation import validate_layer

# Add validation before processing
if not validate_layer(spark, "silver"):
    raise ValueError("Data quality check failed")
```

---

## Breaking Changes

### Version 0.1.0
- Hardcoded credentials removed - must use environment variables or secrets
- Model loading requires Model Registry - update training pipeline first
- Configuration now loaded from `healthclaim_guardian.config` module

---

## Contributors

- Healthclaim Guardian Team
- ML Engineering @ Synergech Technology Solutions

For questions or contributions, see [CONTRIBUTING.md](CONTRIBUTING.md)
