# API Documentation

## Package API Reference

### Configuration Module

```python
from healthclaim_guardian.config import (
    DatabricksConfig,
    PipelineConfig,
    TableConfig,
    get_databricks_config,
    get_pipeline_config,
    get_table_config,
    get_full_table_name,
)
```

#### `DatabricksConfig`

Configuration for Databricks connection.

**Attributes:**
- `host` (str): Databricks workspace URL
- `token` (Optional[str]): Access token
- `catalog` (str): Unity Catalog name (default: `healthclaim_guardian`)
- `schema` (str): Schema name (default: `default`)
- `database` (property): Full database name (`catalog.schema`)

**Methods:**
```python
# Load from environment variables
config = DatabricksConfig.from_env()
```

#### `PipelineConfig`

Configuration for pipeline behavior.

**Attributes:**
- `num_records` (int): Number of records to generate (default: 10000)
- `dirty_data_ratio` (float): Fraction of dirty data (default: 0.10)
- `max_billed_amount` (float): Outlier threshold (default: 50000.0)
- `invalid_diagnosis_code` (str): Invalid code marker (default: "INVALID-CODE-999")
- `default_diagnosis_code` (str): Default for NULLs (default: "UNKNOWN")
- `kmeans_n_clusters` (int): K-Means cluster count (default: 3)
- `kmeans_random_state` (int): Random seed (default: 42)
- `feature_columns` (tuple): Feature column names
- `anomaly_ratio_threshold` (float): Anomaly threshold (default: 1.1)
- `mlflow_experiment_path` (str): MLflow experiment path
- `model_registry_name` (str): Model registry name

**Methods:**
```python
# Load from environment variables
config = PipelineConfig.from_env()
```

#### `TableConfig`

Configuration for table names.

**Attributes:**
- `bronze_claims`: Bronze layer table name
- `silver_claims`: Silver layer table name
- `silver_features`: Features table name
- `gold_anomalies`: Gold layer table name

**Methods:**
```python
# Get table name by layer
table_config.get_table_name("bronze")  # Returns "insurance_bronze_claims"
```

#### `get_full_table_name(table, database=None)`

Get fully qualified table name.

**Parameters:**
- `table` (str): Table name
- `database` (Optional[str]): Database name (default: from config)

**Returns:**
- `str`: Fully qualified table name

**Example:**
```python
get_full_table_name("my_table")  
# Returns: "healthclaim_guardian.default.my_table"
```

---

### Secrets Module

```python
from healthclaim_guardian.secrets import (
    SecretsManager,
    get_secrets_manager,
    setup_databricks_auth,
)
```

#### `SecretsManager`

Manages secure access to secrets.

**Methods:**
```python
# Initialize
secrets = SecretsManager(secrets_scope="healthclaim_guardian")

# Get a secret
token = secrets.get_secret("databricks-token", "DATABRICKS_TOKEN")

# Get specific secrets
host = secrets.get_databricks_host()
token = secrets.get_databricks_token()

# Validate all required secrets
is_valid = secrets.validate_secrets()
```

#### `setup_databricks_auth(secrets_scope="healthclaim_guardian")`

Set up Databricks authentication from secrets.

**Parameters:**
- `secrets_scope` (str): Databricks secrets scope name

**Returns:**
- `bool`: True if successful

**Side Effects:**
- Sets `DATABRICKS_HOST` and `DATABRICKS_TOKEN` environment variables

**Example:**
```python
from healthclaim_guardian.secrets import setup_databricks_auth

if setup_databricks_auth():
    print("Authentication configured successfully")
```

---

### Logging Module

```python
from healthclaim_guardian.logging_config import (
    setup_logger,
    get_logger,
)
```

#### `setup_logger(name, level=logging.INFO, log_format=None)`

Create a configured logger.

**Parameters:**
- `name` (str): Logger name
- `level` (int): Logging level
- `log_format` (Optional[str]): Custom format string

**Returns:**
- `logging.Logger`: Configured logger

**Example:**
```python
logger = setup_logger(__name__)
logger.info("Processing started")
logger.error("Something went wrong", exc_info=True)
```

---

### Model Registry Module

```python
from healthclaim_guardian.model_registry import (
    ModelRegistryManager,
    load_production_model,
    register_and_promote,
)
```

#### `ModelRegistryManager`

Manages MLflow model registry operations.

**Methods:**
```python
# Initialize
registry = ModelRegistryManager(model_name="healthclaim_fraud_detector")

# Register model from run
version = registry.register_model(run_id="abc123")

# Transition to stage
registry.transition_to_stage(version="1", stage="Production")

# Load latest model
model = registry.load_model(stage="Production")

# Get model info
info = registry.get_model_info(stage="Production")

# List all versions
versions = registry.list_all_versions()
```

#### `load_production_model()`

Load production model from registry.

**Returns:**
- `Optional[Any]`: Loaded sklearn model, or None if not found

**Example:**
```python
model = load_production_model()
if model:
    predictions = model.predict(X_scaled)
```

#### `register_and_promote(run_id, stage="Production")`

Register model and promote to stage.

**Parameters:**
- `run_id` (str): MLflow run ID
- `stage` (str): Target stage

**Returns:**
- `Optional[str]`: Version number if successful

---

### Validation Module

```python
from healthclaim_guardian.validation import (
    DataValidator,
    validate_layer,
    ValidationStatus,
    ValidationResult,
    ValidationReport,
)
```

#### `DataValidator`

Validates data against expectations.

**Methods:**
```python
# Initialize
validator = DataValidator(spark, layer="silver")

# Run validation
report = validator.validate()

# Layer-specific validation
report = validator.validate_bronze()
report = validator.validate_silver()
report = validator.validate_features()
```

#### `validate_layer(spark, layer)`

Convenience function to validate a layer.

**Parameters:**
- `spark`: DatabricksSession
- `layer` (str): Layer name (bronze, silver, features)

**Returns:**
- `bool`: True if validation passed

**Example:**
```python
if validate_layer(spark, "silver"):
    print("Silver data is valid")
else:
    print("Silver data has quality issues")
```

#### `ValidationReport`

Contains validation results.

**Attributes:**
- `table_name` (str): Validated table name
- `layer` (str): Layer name
- `results` (List[ValidationResult]): Individual results
- `passed` (int): Passed count
- `failed` (int): Failed count
- `warnings` (int): Warning count
- `is_valid` (property): True if no failures

**Methods:**
```python
report.log_summary()  # Log summary to logger
```

#### `ValidationStatus`

Enum for validation result status.

**Values:**
- `PASSED`: Check passed
- `FAILED`: Check failed (critical)
- `WARNING`: Check failed (non-critical)
- `SKIPPED`: Check not run

---

## Pipeline Module API

### Bronze Ingestion (`src.ingest.generate_bronze`)

```python
from src.ingest.generate_bronze import (
    generate_messy_claims,
    create_schema,
    ingest_bronze_data,
)
```

#### `generate_messy_claims(num_records=10000, dirty_ratio=0.10)`

Generate synthetic claims data.

**Parameters:**
- `num_records` (int): Number of records
- `dirty_ratio` (float): Fraction with quality issues

**Returns:**
- `List[Tuple]`: List of claim records

#### `ingest_bronze_data(num_records=None, dirty_ratio=None, overwrite=True)`

Ingest data to bronze table.

**Parameters:**
- `num_records` (Optional[int]): Override default
- `dirty_ratio` (Optional[float]): Override default
- `overwrite` (bool): Overwrite existing table

**Returns:**
- `int`: Number of records ingested

---

### Silver Cleansing (`src.process.silver_cleansing`)

```python
from src.process.silver_cleansing import (
    cleanse_silver_data,
    DataQualityMetrics,
)
```

#### `cleanse_silver_data()`

Run silver layer cleansing.

**Returns:**
- `bool`: True if successful

---

### Feature Engineering (`src.mlops.feature_engineering`)

```python
from src.mlops.feature_engineering import (
    engineer_features,
)
```

#### `engineer_features()`

Run feature engineering.

**Returns:**
- `bool`: True if successful

---

### Model Training (`src.mlops.train_model`)

```python
from src.mlops.train_model import (
    train_and_register,
)
```

#### `train_and_register()`

Train model and register to MLflow.

**Returns:**
- `Optional[str]`: MLflow run ID if successful

---

### Gold Detection (`src.process.gold_aggregation`)

```python
from src.process.gold_aggregation import (
    generate_gold_layer,
)
```

#### `generate_gold_layer()`

Generate gold layer with anomaly detection.

**Returns:**
- `bool`: True if successful

---

## CLI Commands

The package exposes several CLI commands via entry points:

```bash
# Run pipeline stages
uv run ingest-bronze
uv run cleanse-silver
uv run engineer-features
uv run train-model
uv run detect-anomalies

# Run validation
uv run validate-bronze
uv run validate-silver
```

---

## Environment Variable Reference

| Variable | Default | Required | Description |
|----------|---------|----------|-------------|
| `DATABRICKS_HOST` | - | Yes | Databricks workspace URL |
| `DATABRICKS_TOKEN` | - | No | Personal access token |
| `DATABRICKS_CATALOG` | `healthclaim_guardian` | No | Unity Catalog |
| `DATABRICKS_SCHEMA` | `default` | No | Schema name |
| `PIPELINE_NUM_RECORDS` | `10000` | No | Records to generate |
| `PIPELINE_DIRTY_RATIO` | `0.10` | No | Dirty data fraction |
| `PIPELINE_MAX_BILLED` | `50000.0` | No | Outlier threshold |
| `ML_N_CLUSTERS` | `3` | No | K-Means clusters |
| `ANOMALY_THRESHOLD` | `1.1` | No | Anomaly ratio |
| `MODEL_REGISTRY_NAME` | `healthclaim_fraud_detector` | No | Registry name |
| `MLFLOW_EXPERIMENT_PATH` | `/healthclaim_fraud` | No | Experiment path |

---

## Error Handling

All modules use consistent error handling:

```python
try:
    result = some_operation()
    if result:
        logger.info("Operation succeeded")
        return 0
    else:
        logger.error("Operation failed")
        return 1
except Exception as e:
    logger.exception(f"Unexpected error: {e}")
    return 1
```

**Return Codes:**
- `0`: Success
- `1`: Failure

---

## Thread Safety

- Configuration objects are immutable after creation (thread-safe)
- `SecretsManager` uses internal caching (not thread-safe for concurrent writes)
- MLflow client is thread-safe
- Spark sessions should not be shared across threads

## Rate Limiting

When calling Databricks APIs:
- MLflow: 100 requests/minute
- Model Registry: 30 requests/minute
- Secrets API: 60 requests/minute

Implement retry logic with exponential backoff for rate-limited requests.
