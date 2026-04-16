# Healthclaim Guardian

**Healthcare Claims Fraud Detection Pipeline**

A production-grade ML pipeline for detecting anomalous healthcare claims using unsupervised learning (K-Means clustering). Built on Databricks with full MLOps practices.

![Python Version](https://img.shields.io/badge/python-3.10%20%7C%203.11%20%7C%203.12-blue)
![License](https://img.shields.io/badge/license-Proprietary-red)
![Databricks](https://img.shields.io/badge/Databricks-15.4-ff3621)

---

## Table of Contents

- [Overview](#overview)
- [Architecture](#architecture)
- [Features](#features)
- [Quick Start](#quick-start)
- [Installation](#installation)
- [Configuration](#configuration)
- [Pipeline Stages](#pipeline-stages)
- [MLOps](#mlops)
- [Data Quality](#data-quality)
- [Testing](#testing)
- [Deployment](#deployment)
- [Monitoring](#monitoring)
- [Security](#security)
- [Troubleshooting](#troubleshooting)
- [Contributing](#contributing)

---

## Overview

Healthclaim Guardian is a comprehensive fraud detection system that identifies anomalous healthcare claims using machine learning. The pipeline processes claims data through a medallion architecture (Bronze → Silver → Gold), engineers features, trains anomaly detection models, and flags suspicious claims for review.

### Business Value

- **Fraud Detection**: Identifies potentially fraudulent claims using statistical anomaly detection
- **Cost Savings**: Reduces manual review by automatically flagging high-risk claims
- **Compliance**: Maintains audit trail and data lineage for regulatory requirements
- **Scalability**: Processes millions of claims using Databricks distributed computing

---

## Architecture

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                        HEALTHCLAIM GUARDIAN PIPELINE                        │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  ┌──────────┐    ┌──────────┐    ┌──────────┐    ┌──────────┐              │
│  │  BRONZE  │───▶│  SILVER  │───▶│ FEATURES │───▶│   GOLD   │              │
│  │  (Raw)   │    │ (Clean)  │    │   (ML)   │    │(Output)  │              │
│  └──────────┘    └──────────┘    └──────────┘    └──────────┘              │
│       │               │               │               │                     │
│       ▼               ▼               ▼               ▼                     │
│  ┌──────────┐    ┌──────────┐    ┌──────────┐    ┌──────────┐              │
│  │ Generate │    │ Cleanse  │    │ Engineer │    │  Detect  │              │
│  │  Claims  │    │  Data    │    │ Features │    │Anomalies │              │
│  └──────────┘    └──────────┘    └──────────┘    └──────────┘              │
│                                         │                                   │
│                                         ▼                                   │
│                                  ┌──────────┐                               │
│                                  │  TRAIN   │                               │
│                                  │  MODEL   │                               │
│                                  └──────────┘                               │
│                                         │                                   │
│                                         ▼                                   │
│                                  ┌──────────┐                               │
│                                  │  MLflow  │                               │
│                                  │ Registry │                               │
│                                  └──────────┘                               │
└─────────────────────────────────────────────────────────────────────────────┘
```

### Data Flow

| Stage | Input | Output | Description |
|-------|-------|--------|-------------|
| **Bronze** | Raw claims | `insurance_bronze_claims` | Synthetic/raw ingested data |
| **Silver** | Bronze table | `insurance_silver_claims` | Cleaned, validated data |
| **Features** | Silver table | `insurance_silver_features` | ML-ready features with aggregations |
| **Training** | Features table | MLflow Model | Trained K-Means anomaly detector |
| **Gold** | Features + Model | `insurance_gold_anomalies` | Claims with fraud scores |

---

## Features

### Core Capabilities

- **Synthetic Data Generation**: Generates realistic healthcare claims with configurable data quality issues
- **Data Cleansing**: Automated removal of duplicates, invalid codes, negative amounts, and outliers
- **Feature Engineering**: Hospital-level aggregations, ratio features, z-scores
- **Anomaly Detection**: K-Means clustering with automatic cluster identification
- **Risk Scoring**: Claims assigned risk levels (HIGH, MEDIUM, LOW, NORMAL)

### MLOps Features

- **MLflow Integration**: Full experiment tracking and model registry
- **Model Versioning**: Automatic versioning and stage transitions (Staging → Production)
- **Reproducible Training**: Seeded random state, logged parameters and metrics
- **Model Evaluation**: Silhouette score, inertia, cluster statistics

### Data Quality

- **Validation Framework**: Databricks Expectations-style validation
- **Layer-wise Checks**: Different validation rules for bronze/silver/features
- **Quality Metrics**: Track cleansing rates, null counts, outlier counts
- **Automated Alerts**: Notifications on validation failures

### Security & Compliance

- **Secrets Management**: Databricks Secrets integration for credentials
- **No Hardcoded Secrets**: All sensitive values from secure storage
- **Audit Trail**: Full lineage from raw data to predictions
- **Environment Isolation**: Separate dev/staging/prod environments

---

## Quick Start

### Prerequisites

- Python 3.10-3.12
- UV package manager (`pip install uv`)
- Databricks workspace access
- Databricks CLI v0.200+

### 1. Clone and Setup

```bash
git clone <repository-url>
cd healthclaim_guardian
uv sync --dev
```

### 2. Configure Authentication

```bash
# Option A: Databricks CLI authentication
databricks configure

# Option B: Environment variables
export DATABRICKS_HOST="https://your-workspace.azuredatabricks.net"
export DATABRICKS_TOKEN="your-personal-access-token"
```

### 3. Run the Pipeline

```bash
# Run all stages sequentially
uv run python -m src.ingest.generate_bronze
uv run python -m src.process.silver_cleansing
uv run python -m src.mlops.feature_engineering
uv run python -m src.mlops.train_model
uv run python -m src.process.gold_aggregation

# Or use the workflow (recommended)
databricks bundle deploy
databricks run job --job-name healthclaim_guardian_pipeline
```

### 4. View Results

```bash
# Query the gold layer
databricks sql -c "SELECT * FROM healthclaim_guardian.default.insurance_gold_anomalies WHERE is_anomaly = true LIMIT 10"
```

---

## Installation

### Development Setup

```bash
# Install UV if not already installed
curl -LsSf https://astral.sh/uv/install.sh | sh

# Clone and install
git clone <repository-url>
cd healthclaim_guardian
uv sync --dev

# Verify installation
uv run pytest
uv run ruff check src/
```

### Production Deployment

```bash
# Deploy to production
databricks bundle deploy --target prod

# Run the production job
databricks bundle run --target prod
```

### Dependencies

| Package | Version | Purpose |
|---------|---------|---------|
| databricks-connect | 15.4.x | Databricks integration |
| scikit-learn | >=1.3.0 | ML algorithms |
| mlflow | >=2.10.0 | Model tracking |
| pandas | >=2.0.0 | Data manipulation |
| faker | >=21.0.0 | Synthetic data |

---

## Configuration

### Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `DATABRICKS_HOST` | (required) | Databricks workspace URL |
| `DATABRICKS_TOKEN` | (optional) | Personal access token |
| `DATABRICKS_CATALOG` | `healthclaim_guardian` | Unity Catalog name |
| `DATABRICKS_SCHEMA` | `default` | Schema/database name |
| `PIPELINE_NUM_RECORDS` | `10000` | Records to generate |
| `PIPELINE_DIRTY_RATIO` | `0.10` | Fraction of dirty data |
| `PIPELINE_MAX_BILLED` | `50000.0` | Max billed amount threshold |
| `ML_N_CLUSTERS` | `3` | K-Means cluster count |
| `ANOMALY_THRESHOLD` | `1.1` | Anomaly ratio threshold |
| `MODEL_REGISTRY_NAME` | `healthclaim_fraud_detector` | Model registry name |

### Databricks Secrets Setup

```bash
# Create secrets scope
databricks secrets create-scope --scope healthclaim_guardian

# Add secrets
databricks secrets put-secret --scope healthclaim_guardian --key databricks-host
databricks secrets put-secret --scope healthclaim_guardian --key databricks-token
```

---

## Pipeline Stages

### 1. Bronze Ingestion (`src/ingest/generate_bronze.py`)

Generates synthetic healthcare claims data with intentional data quality issues:

- Negative billing amounts
- Extreme outliers (100x normal)
- Invalid diagnosis codes
- NULL values

```bash
uv run python -m src.ingest.generate_bronze
```

**Output Table**: `insurance_bronze_claims`

### 2. Silver Cleansing (`src/process/silver_cleansing.py`)

Applies data quality rules:

1. Remove exact duplicates
2. Filter invalid diagnosis codes
3. Impute NULL diagnosis codes
4. Correct negative amounts (absolute value)
5. Filter extreme outliers

```bash
uv run python -m src.process.silver_cleansing
```

**Output Table**: `insurance_silver_claims`

### 3. Feature Engineering (`src/mlops/feature_engineering.py`)

Creates ML-ready features:

- Hospital-level aggregations (avg, min, max, stddev)
- Claim-to-average ratio
- Z-score feature
- Above-2-stddev flag

```bash
uv run python -m src.mlops.feature_engineering
```

**Output Table**: `insurance_silver_features`

### 4. Model Training (`src/mlops/train_model.py`)

Trains K-Means anomaly detection model:

- Loads features from Spark
- Standardizes features
- Trains K-Means clustering
- Evaluates with silhouette score
- Logs to MLflow and registers model

```bash
uv run python -m src.mlops.train_model
```

**Output**: MLflow registered model

### 5. Gold Detection (`src/process/gold_aggregation.py`)

Applies model to detect anomalies:

- Loads production model from registry
- Predicts cluster assignments
- Identifies anomalous cluster
- Assigns risk levels (HIGH/MEDIUM/LOW/NORMAL)
- Calculates confidence scores

```bash
uv run python -m src.process.gold_aggregation
```

**Output Table**: `insurance_gold_anomalies`

---

## MLOps

### MLflow Integration

The pipeline uses MLflow for:

- **Experiment Tracking**: All runs logged with parameters, metrics, artifacts
- **Model Registry**: Models promoted through stages (Staging → Production)
- **Model Lineage**: Track which data trained each model version

### Model Registry Workflow

```
1. Train model → Logged to MLflow run
2. Register model → Added to registry as version N
3. Validate model → Evaluate on holdout data
4. Promote to Production → Available for inference
```

### Loading Production Model

```python
from healthclaim_guardian.model_registry import load_production_model

model = load_production_model()  # Loads from Production stage
```

### Model Evaluation Metrics

| Metric | Description | Target |
|--------|-------------|--------|
| Silhouette Score | Cluster separation quality | > 0.5 |
| Inertia | Within-cluster variance | Minimize |
| N Clusters | Number of identified clusters | 2-5 |

---

## Data Quality

### Validation Rules

#### Bronze Layer
- Table is not empty
- Required columns exist
- claim_id is not NULL
- billed_amount is populated

#### Silver Layer (adds)
- No negative billed_amounts
- No invalid diagnosis codes
- No extreme outliers (>$50,000)

#### Features Layer
- Required feature columns exist
- No NULL ratio values
- All ratios are positive

### Running Validation

```python
from healthclaim_guardian.validation import validate_layer

# Validate silver layer
is_valid = validate_layer(spark, "silver")

if not is_valid:
    raise ValueError("Data quality check failed!")
```

---

## Testing

### Run Tests

```bash
# All tests
uv run pytest

# With coverage
uv run pytest --cov=src --cov-report=html

# Specific test file
uv run pytest tests/test_validation.py -v
```

### Test Structure

```
tests/
├── test_config.py       # Configuration tests
├── test_validation.py   # Data validation tests
├── test_bronze.py       # Bronze layer tests
├── test_silver.py       # Silver layer tests
├── test_features.py     # Feature engineering tests
└── test_model.py        # ML model tests
```

---

## Deployment

### Environments

| Environment | Purpose | Schedule | Data Volume |
|-------------|---------|----------|-------------|
| **Dev** | Development/testing | Manual | 10,000 records |
| **Staging** | Pre-prod validation | Daily | 100,000 records |
| **Prod** | Production | Daily 2 AM | 1,000,000 records |

### Deploy Commands

```bash
# Deploy to dev (default)
databricks bundle deploy

# Deploy to production
databricks bundle deploy --target prod

# Run job manually
databricks bundle run
```

### Workflow Schedule

Production workflow runs daily at 2 AM ET:
- Cron: `0 0 2 * * ?`
- Timezone: America/New_York
- Notifications on failure/success

---

## Monitoring

### Key Metrics

| Metric | Alert Threshold |
|--------|-----------------|
| Pipeline duration | > 2 hours |
| Anomaly rate | > 20% |
| Validation failures | Any |
| Model drift | Silhouette < 0.3 |

### Databricks Dashboards

Create dashboards for:
- Pipeline execution history
- Data quality trends
- Anomaly detection rates
- Model performance over time

### Alerting

Configure alerts in Databricks:
- Job failures → Email/Slack
- High anomaly rates → PagerDuty
- Data quality failures → Email

---

## Security

### Secrets Management

All sensitive credentials stored in Databricks Secrets:

```bash
# Required secrets
databricks secrets put-secret --scope healthclaim_guardian --key databricks-host
databricks secrets put-secret --scope healthclaim_guardian --key databricks-token
```

### Access Control

| Role | Permissions |
|------|-------------|
| Data Engineer | Read/Write all tables |
| Data Scientist | Read tables, Write models |
| Analyst | Read gold layer only |
| Admin | Full access |

### Network Security

- VPC injection for Databricks cluster
- Private link for data transfer
- IP access lists for workspace

---

## Troubleshooting

### Common Issues

#### "DATABRICKS_HOST not set"

```bash
export DATABRICKS_HOST="https://your-workspace.azuredatabricks.net"
```

#### "No module named 'healthclaim_guardian'"

```bash
uv sync --dev
```

#### "Model not found in Production stage"

Run the training pipeline first:
```bash
uv run python -m src.mlops.train_model
```

#### "Table not found"

Ensure pipeline stages run in order:
1. Bronze ingestion
2. Silver cleansing
3. Feature engineering
4. Model training
5. Gold detection

### Logs

View logs in:
- Databricks Job Run UI
- DBFS: `/logs/healthclaim_guardian/`
- Local stdout/stderr

---

## Contributing

### Development Workflow

1. Create feature branch
2. Make changes
3. Run tests: `uv run pytest`
4. Run linter: `uv run ruff check src/`
5. Submit PR

### Code Style

```bash
# Format code
uv run black src/ tests/
uv run isort src/ tests/

# Lint code
uv run ruff check src/ tests/

# Type check
uv run mypy src/
```

### Commit Messages

Follow conventional commits:
- `feat: add new feature`
- `fix: resolve bug`
- `docs: update documentation`
- `test: add tests`
- `refactor: improve code structure`

---

## License

Proprietary - Synergech Technology Solutions

---

## Support

For issues and questions:
- GitHub Issues: [Link to repo issues]
- Email: ml-team@synergech.com
- Slack: #healthclaim-guardian
