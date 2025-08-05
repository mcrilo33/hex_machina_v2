"""Configuration loader for ingestion operations."""

import logging
from typing import Optional

import yaml

from src.hex_machina.ingestion.models.config_models import IngestionConfig


class ConfigLoader:
    """Loads and validates ingestion configuration using a Pydantic model."""

    def __init__(self, config_path: str):
        """Initialize the config loader.

        Args:
            config_path: Path to the configuration file
        """
        self.config_path = config_path
        self.logger = logging.getLogger(__name__)

    def load(self) -> IngestionConfig:
        """Load and validate the configuration.

        Returns:
            IngestionConfig: The validated config object.
        Raises:
            FileNotFoundError: If the config file does not exist.
            pydantic.ValidationError: If the config is invalid.
        """
        try:
            with open(self.config_path, "r") as f:
                config_dict = yaml.safe_load(f)
            return IngestionConfig(**config_dict)
        except Exception as e:
            self.logger.error(
                f"Failed to load configuration from {self.config_path}: {e}"
            )
            raise


def load_ingestion_config(config_path: str) -> Optional[IngestionConfig]:
    """Load ingestion configuration from a YAML file.

    Args:
        config_path: Path to the configuration file

    Returns:
        IngestionConfig object or None if loading failed
    """
    try:
        loader = ConfigLoader(config_path)
        return loader.load()
    except Exception as e:
        logger = logging.getLogger(__name__)
        logger.error(f"Failed to load ingestion config: {e}")
        return None
