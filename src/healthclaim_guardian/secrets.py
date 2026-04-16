"""
Secrets management utility for Healthclaim Guardian.

Provides secure access to sensitive configuration values via:
1. Databricks Secrets (when running on Databricks)
2. Environment variables (fallback for local development)
3. Azure Key Vault integration (optional)
"""

import os
from typing import Optional
from healthclaim_guardian.logging_config import setup_logger

logger = setup_logger(__name__)


class SecretsManager:
    """
    Manages access to secrets from various secure backends.

    Priority order:
    1. Databricks Secrets (when dbutils is available)
    2. Environment variables
    3. Azure Key Vault (if configured)
    """

    def __init__(
        self,
        secrets_scope: str = "healthclaim_guardian",
        dbutils=None,
    ):
        """
        Initialize the secrets manager.

        Args:
            secrets_scope: Name of the Databricks secrets scope
            dbutils: Databricks dbutils object (auto-detected if None)
        """
        self.secrets_scope = secrets_scope
        self._dbutils = dbutils
        self._secrets_cache = {}

    @property
    def dbutils(self):
        """Lazy load dbutils if not provided."""
        if self._dbutils is None:
            try:
                from pyspark.dbutils import dbutils
                self._dbutils = dbutils
                logger.info("Databricks dbutils detected - using Databricks Secrets")
            except ImportError:
                logger.info("Databricks dbutils not available - using environment variables")
                self._dbutils = None
        return self._dbutils

    def get_secret(self, key: str, env_var: Optional[str] = None) -> Optional[str]:
        """
        Get a secret value.

        Args:
            key: Secret key name in Databricks Secrets
            env_var: Environment variable name as fallback (default: key.upper())

        Returns:
            Secret value or None if not found
        """
        # Check cache first
        if key in self._secrets_cache:
            return self._secrets_cache[key]

        env_var = env_var or key.upper()

        # Try Databricks Secrets first
        if self.dbutils is not None:
            try:
                secret_value = self.dbutils.secrets.get(
                    scope=self.secrets_scope,
                    key=key
                )
                self._secrets_cache[key] = secret_value
                logger.debug(f"Retrieved secret '{key}' from Databricks Secrets")
                return secret_value
            except Exception as e:
                logger.warning(f"Failed to get secret '{key}' from Databricks: {e}")

        # Fallback to environment variables
        env_value = os.getenv(env_var)
        if env_value:
            self._secrets_cache[key] = env_value
            logger.debug(f"Retrieved secret '{key}' from environment variable '{env_var}'")
            return env_value

        logger.warning(f"Secret '{key}' not found in Databricks Secrets or environment")
        return None

    def get_databricks_host(self) -> Optional[str]:
        """Get Databricks host URL."""
        return self.get_secret("databricks-host", "DATABRICKS_HOST")

    def get_databricks_token(self) -> Optional[str]:
        """Get Databricks token."""
        return self.get_secret("databricks-token", "DATABRICKS_TOKEN")

    def get_database_url(self) -> Optional[str]:
        """Get database connection URL."""
        return self.get_secret("database-url", "DATABASE_URL")

    def validate_secrets(self) -> bool:
        """
        Validate that required secrets are available.

        Returns:
            True if all required secrets are present, False otherwise
        """
        required_secrets = {
            "databricks-host": "DATABRICKS_HOST",
        }

        all_present = True
        for key, env_var in required_secrets.items():
            if not self.get_secret(key, env_var):
                logger.error(f"Required secret '{key}' (env: {env_var}) is not set")
                all_present = False

        return all_present


# Global secrets manager instance
_secrets_manager: Optional[SecretsManager] = None


def get_secrets_manager(secrets_scope: str = "healthclaim_guardian") -> SecretsManager:
    """Get or create the global secrets manager."""
    global _secrets_manager
    if _secrets_manager is None:
        _secrets_manager = SecretsManager(secrets_scope=secrets_scope)
    return _secrets_manager


def setup_databricks_auth(secrets_scope: str = "healthclaim_guardian") -> bool:
    """
    Set up Databricks authentication from secrets.

    This function sets the required environment variables for Databricks
    authentication, making it available to all downstream code.

    Args:
        secrets_scope: Name of the Databricks secrets scope

    Returns:
        True if authentication was set up successfully, False otherwise
    """
    secrets_mgr = get_secrets_manager(secrets_scope)

    host = secrets_mgr.get_databricks_host()
    token = secrets_mgr.get_databricks_token()

    if host:
        os.environ["DATABRICKS_HOST"] = host
        logger.info("DATABRICKS_HOST set from secrets")
    else:
        logger.error("DATABRICKS_HOST not found - authentication will fail")
        return False

    if token:
        os.environ["DATABRICKS_TOKEN"] = token
        logger.info("DATABRICKS_TOKEN set from secrets")
    # Token is optional when running on Databricks (uses cluster auth)

    return True
