# Architecture Documentation

## System Overview

Healthclaim Guardian follows a **medallion architecture** pattern with separate concerns for data ingestion, transformation, feature engineering, model training, and inference.

## High-Level Architecture

```
┌─────────────────────────────────────────────────────────────────────────┐
│                           DATABRICKS WORKSPACE                          │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│  ┌─────────────────────────────────────────────────────────────────┐   │
│  │                    WORKFLOW ORCHESTRATION                        │   │
│  │                    (Databricks Jobs)                             │   │
│  └─────────────────────────────────────────────────────────────────┘   │
│                              │                                           │
│                              ▼                                           │
│  ┌─────────────────────────────────────────────────────────────────┐   │
│  │                     COMPUTE CLUSTER                              │   │
│  │                  (Shared Job Cluster)                            │   │
│  └─────────────────────────────────────────────────────────────────┘   │
│                              │                                           │
│         ┌────────────────────┼────────────────────┐                     │
│         ▼                    ▼                    ▼                     │
│  ┌─────────────┐     ┌─────────────┐     ┌─────────────┐               │
│  │   BRONZE    │     │   SILVER    │     │    GOLD     │               │
│  │   LAYER     │     │   LAYER     │     │   LAYER     │               │
│  │             │     │             │     │             │               │
│  │ Raw Delta   │────▶│ Clean Delta │────▶│ ML Output   │               │
│  │ Tables      │     │ Tables      │     │ Delta Table │               │
│  └─────────────┘     └─────────────┘     └─────────────┘               │
│         │                    │                    │                     │
│         │                    ▼                    │                     │
│         │             ┌─────────────┐            │                     │
│         │             │  FEATURES   │            │                     │
│         │             │   LAYER     │            │                     │
│         │             │             │            │                     │
│         │             │ ML Features │────────────┘                     │
│         │             │ Delta Table │                                  │
│         │             └─────────────┘                                  │
│         │                    │                                         │
│         │                    ▼                                         │
│         │             ┌─────────────┐                                  │
│         │             │   MLFLOW    │                                  │
│         │             │  REGISTRY   │                                  │
│         │             │             │                                  │
│         │             │ - Experiments                                  │
│         │             │ - Models                                       │
│         │             │ - Versions                                     │
│         │             └─────────────┘                                  │
│         │                    │                                         │
│         └────────────────────┴─────────────────────────────────────────┘
│                              │
│                              ▼
│                  ┌─────────────────────┐
│                  │   UNITY CATALOG     │
│                  │                     │
│                  │ healthclaim_guardian│
│                  │   └─ default        │
│                  │      ├─ bronze      │
│                  │      ├─ silver      │
│                  │      ├─ features    │
│                  │      └─ gold        │
│                  └─────────────────────┘
└─────────────────────────────────────────────────────────────────────────┘
```

## Component Architecture

### 1. Configuration Layer

```
src/healthclaim_guardian/
├── config.py           # Centralized configuration
├── secrets.py          # Secrets management
├── logging_config.py   # Logging setup
├── validation.py       # Data validation framework
└── model_registry.py   # MLflow model registry wrapper
```

**Responsibilities:**
- Load configuration from environment variables
- Manage Databricks authentication
- Provide consistent logging across components
- Validate data quality at each layer
- Manage model lifecycle

### 2. Data Pipeline Layer

```
src/
├── ingest/
│   └── generate_bronze.py    # Bronze ingestion
├── process/
│   ├── silver_cleansing.py   # Silver cleansing
│   └── gold_aggregation.py   # Gold anomaly detection
└── mlops/
    ├── feature_engineering.py # Feature creation
    └── train_model.py         # Model training
```

**Data Flow:**
1. **Bronze**: Raw data ingestion (schema-on-read)
2. **Silver**: Cleaned, validated data (schema-enforced)
3. **Features**: ML-ready feature tables
4. **Gold**: Final predictions with risk scores

### 3. ML Layer

```
MLflow Integration:
├── Experiments
│   └── /healthclaim_fraud
│       └── Runs (with params, metrics, artifacts)
│
├── Model Registry
│   └── healthclaim_fraud_detector
│       ├── Version 1 (Production)
│       ├── Version 2 (Staging)
│       └── Version 3 (Archived)
│
└── Artifacts
    └── fraud_detection_model/
        ├── MLmodel
        ├── conda.yaml
        └── sklearn_model.pkl
```

## Data Model

### Bronze Layer Schema

```python
StructType([
    StructField("claim_id",       StringType(),  nullable=False),
    StructField("patient_id",     StringType(),  nullable=False),
    StructField("hospital_id",    StringType(),  nullable=True),
    StructField("diagnosis_code", StringType(),  nullable=True),
    StructField("billed_amount",  DoubleType(),  nullable=True),
    StructField("claim_status",   StringType(),  nullable=True),
])
```

### Silver Layer Schema

Same as Bronze, with data quality guarantees:
- No negative `billed_amount`
- No invalid `diagnosis_code`
- No extreme outliers

### Features Layer Schema

```python
# Inherits all Silver columns plus:
StructField("hosp_avg_billed",     DoubleType(), nullable=True),
StructField("hosp_min_billed",     DoubleType(), nullable=True),
StructField("hosp_max_billed",     DoubleType(), nullable=True),
StructField("hosp_stddev_billed",  DoubleType(), nullable=True),
StructField("hosp_claim_count",    LongType(),   nullable=True),
StructField("amount_to_avg_ratio", DoubleType(), nullable=True),
StructField("amount_z_score",      DoubleType(), nullable=True),
StructField("is_above_2std",       BooleanType(),nullable=True),
```

### Gold Layer Schema

```python
# Inherits all Features columns plus:
StructField("cluster_prediction",  IntegerType(), nullable=True),
StructField("is_anomaly",          BooleanType(), nullable=True),
StructField("anomaly_confidence",  DoubleType(),  nullable=True),
StructField("risk_level",          StringType(),  nullable=True),
```

## Security Architecture

### Authentication Flow

```
┌──────────────┐
│   Pipeline   │
│   Component  │
└──────┬───────┘
       │
       ▼
┌─────────────────────────────────────────┐
│  SecretsManager                         │
│  ┌─────────────────────────────────┐   │
│  │ 1. Databricks Secrets (dbutils) │   │
│  │    (if running on Databricks)   │   │
│  └─────────────────────────────────┘   │
│              │                          │
│              ▼ (fallback)               │
│  ┌─────────────────────────────────┐   │
│  │ 2. Environment Variables        │   │
│  │    (DATABRICKS_*)               │   │
│  └─────────────────────────────────┘   │
└─────────────────────────────────────────┘
       │
       ▼
┌──────────────┐
│  Databricks  │
│   Cluster    │
└──────────────┘
```

### Secrets Scope

```
healthclaim_guardian (scope)
├── databricks-host
├── databricks-token
├── database-url (optional)
└── api-keys (optional)
```

## Deployment Architecture

### Environment Isolation

```
┌─────────────────────────────────────────────────────────────┐
│                    DATABRICKS WORKSPACE                      │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐         │
│  │     DEV     │  │   STAGING   │  │    PROD     │         │
│  │             │  │             │  │             │         │
│  │ - Debug     │  │ - Integration│  │ - Optimized │         │
│  │   logging   │  │   tests     │  │   cluster   │         │
│  │ - Small     │  │ - Medium    │  │ - Full      │         │
│  │   data      │  │   data      │  │   data      │         │
│  │ - Manual    │  │ - Daily     │  │ - Daily 2AM │         │
│  │   trigger   │  │   schedule  │  │   schedule  │         │
│  └─────────────┘  └─────────────┘  └─────────────┘         │
│                                                             │
│  Unity Catalog: healthclaim_guardian                        │
│  ├── dev schema (development)                               │
│  ├── staging schema (pre-production)                        │
│  └── prod schema (production)                               │
└─────────────────────────────────────────────────────────────┘
```

## Workflow Orchestration

### Task Dependencies

```
ingest_bronze
      │
      ▼
cleanse_silver
      │
      ▼
engineer_features
      │
      ├──────────────┐
      │              │
      ▼              │
train_model          │
      │              │
      ▼              │
detect_anomalies ◄───┘
```

### Retry Strategy

| Task | Timeout | Max Retries | Retry on Timeout |
|------|---------|-------------|------------------|
| ingest_bronze | 30 min | 2 | Yes |
| cleanse_silver | 30 min | 2 | No |
| engineer_features | 30 min | 2 | No |
| train_model | 60 min | 1 | No |
| detect_anomalies | 30 min | 2 | No |

## Monitoring Architecture

### Metrics Collection

```
Pipeline Execution
       │
       ▼
┌──────────────────────────────────┐
│  Databricks Job Metrics          │
│  - Task duration                 │
│  - Records processed             │
│  - Success/Failure status        │
└──────────────────────────────────┘
       │
       ▼
┌──────────────────────────────────┐
│  MLflow Metrics                  │
│  - Model performance             │
│  - Data drift indicators         │
│  - Training statistics           │
└──────────────────────────────────┘
       │
       ▼
┌──────────────────────────────────┐
│  Custom Business Metrics         │
│  - Anomaly rate                  │
│  - Risk level distribution       │
│  - Hospital-level statistics     │
└──────────────────────────────────┘
```

### Alerting Strategy

```
┌─────────────────────────────────────────────────────────┐
│                    ALERTING RULES                        │
├─────────────────────────────────────────────────────────┤
│                                                         │
│  Pipeline Failure                                       │
│  └─▶ Email: ml-team@synergech.com                      │
│                                                         │
│  High Anomaly Rate (>20%)                               │
│  └─▶ PagerDuty: Fraud Detection Team                   │
│                                                         │
│  Data Quality Failure                                   │
│  └─▶ Email: data-engineering@synergech.com             │
│                                                         │
│  Model Performance Degradation                          │
│  └─▶ Slack: #ml-alerts                                 │
│                                                         │
└─────────────────────────────────────────────────────────┘
```

## Scalability Considerations

### Horizontal Scaling

- **Cluster Autoscaling**: 2-8 workers based on load
- **Partitioned Writes**: Delta tables partitioned by date/hospital
- **Parallel Processing**: Spark distributed computing

### Data Volume Estimates

| Environment | Records | Storage | Processing Time |
|-------------|---------|---------|-----------------|
| Dev | 10,000 | ~1 MB | < 1 min |
| Staging | 100,000 | ~10 MB | < 5 min |
| Prod | 1,000,000 | ~100 MB | < 15 min |

### Cost Optimization

- Use spot instances for non-critical jobs
- Terminate idle clusters automatically
- Compress Delta table data
- Archive old data to cold storage
