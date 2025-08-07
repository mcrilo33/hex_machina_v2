"""Database configuration for enrichment operations."""

import logging
from pathlib import Path
from typing import Optional

import yaml
from pydantic import Field

from src.hex_machina.core.base import BaseConfig


class DatabaseConfig(BaseConfig):
    """Database configuration for enrichment operations."""

    name: str = Field(default="database", description="Configuration name")
    db_path: str = Field(
        default="data/hex_machina.db", description="Database file path"
    )
    enable_by_default: bool = Field(
        default=True, description="Enable database storage by default"
    )
    batch_size: int = Field(
        default=10, description="Default batch size for processing articles"
    )
    max_concurrent: int = Field(default=5, description="Maximum concurrent tasks")


class DatabaseConfigManager:
    """Manager for database configuration."""

    def __init__(self, config_path: Optional[str] = None):
        """Initialize database config manager.

        Args:
            config_path: Path to database config file
        """
        self._logger = logging.getLogger("enrichment.config.database")
        self._config_path = config_path or "configs/enrichment/database.yaml"
        self._config: Optional[DatabaseConfig] = None

    def load_config(self) -> DatabaseConfig:
        """Load database configuration.

        Returns:
            DatabaseConfig instance
        """
        if self._config is not None:
            return self._config

        config_path = Path(self._config_path)
        if not config_path.exists():
            self._logger.warning(
                f"Database config not found at {config_path}, using defaults"
            )
            self._config = DatabaseConfig()
            return self._config

        try:
            with open(config_path, "r") as f:
                config_data = yaml.safe_load(f)

            # Extract database section
            db_data = config_data.get("database", {})
            self._config = DatabaseConfig(**db_data)

            self._logger.info(f"Loaded database config from {config_path}")
            return self._config

        except Exception as e:
            self._logger.error(f"Failed to load database config: {e}")
            self._config = DatabaseConfig()
            return self._config

    def get_db_path(self) -> str:
        """Get database path."""
        return self.load_config().db_path

    def get_enable_by_default(self) -> bool:
        """Get whether database storage is enabled by default."""
        return self.load_config().enable_by_default

    def get_batch_size(self) -> int:
        """Get default batch size."""
        return self.load_config().batch_size

    def get_max_concurrent(self) -> int:
        """Get maximum concurrent tasks."""
        return self.load_config().max_concurrent

    def reload_config(self) -> DatabaseConfig:
        """Reload configuration from file."""
        self._config = None
        return self.load_config()


# Global database config manager instance
database_config_manager = DatabaseConfigManager()
