"""
Healthclaim Guardian - Shared utilities and components.

This package provides configuration, logging, validation, and utility functions
for the healthclaim fraud detection pipeline.
"""

from healthclaim_guardian.config import (
    DatabricksConfig,
    PipelineConfig,
    TableConfig,
    get_databricks_config,
    get_pipeline_config,
    get_table_config,
    get_full_table_name,
)
from healthclaim_guardian.logging_config import setup_logger, get_logger
from healthclaim_guardian.secrets import (
    SecretsManager,
    get_secrets_manager,
    setup_databricks_auth,
)
from healthclaim_guardian.model_registry import (
    ModelRegistryManager,
    load_production_model,
    register_and_promote,
)
from healthclaim_guardian.validation import (
    DataValidator,
    validate_layer,
    ValidationStatus,
    ValidationResult,
    ValidationReport,
)

__all__ = [
    # Config
    "DatabricksConfig",
    "PipelineConfig",
    "TableConfig",
    "get_databricks_config",
    "get_pipeline_config",
    "get_table_config",
    "get_full_table_name",
    # Logging
    "setup_logger",
    "get_logger",
    # Secrets
    "SecretsManager",
    "get_secrets_manager",
    "setup_databricks_auth",
    # Model Registry
    "ModelRegistryManager",
    "load_production_model",
    "register_and_promote",
    # Validation
    "DataValidator",
    "validate_layer",
    "ValidationStatus",
    "ValidationResult",
    "ValidationReport",
]

__version__ = "0.1.0"
