"""Configuration management for Hex Machina v2."""

import os
from pathlib import Path
from typing import Any, Dict, List, Optional

import yaml
from pydantic import BaseModel, Field

from .exceptions import ConfigurationException


class ConfigReference(BaseModel):
    """Reference to another configuration file."""

    config_ref: str = Field(description="Path to the referenced configuration file")
    overrides: Optional[Dict[str, Any]] = Field(
        default=None, description="Values to override in the referenced config"
    )


class ConfigManager:
    """Manages configuration loading, validation, and composition."""

    def __init__(self, config_dirs: Optional[List[str]] = None):
        """Initialize the configuration manager.

        Args:
            config_dirs: List of directories to search for configuration files
        """
        self.config_dirs = config_dirs or ["configs"]
        self._loaded_configs: Dict[str, Dict[str, Any]] = {}
        self._config_cache: Dict[str, Dict[str, Any]] = {}

    def load_config(
        self, config_path: str, resolve_refs: bool = True
    ) -> Dict[str, Any]:
        """Load a configuration file.

        Args:
            config_path: Path to the configuration file
            resolve_refs: Whether to resolve config_ref references

        Returns:
            Loaded configuration dictionary

        Raises:
            ConfigurationException: If the configuration cannot be loaded
        """
        # Check cache first
        cache_key = f"{config_path}:{resolve_refs}"
        if cache_key in self._config_cache:
            return self._config_cache[cache_key]

        # Find the config file
        config_file = self._find_config_file(config_path)
        if not config_file:
            raise ConfigurationException(f"Configuration file not found: {config_path}")

        # Load the YAML file
        try:
            with open(config_file, "r", encoding="utf-8") as f:
                config = yaml.safe_load(f)
        except Exception as e:
            raise ConfigurationException(
                f"Failed to load configuration {config_path}: {e}"
            )

        if config is None:
            raise ConfigurationException(f"Configuration file is empty: {config_path}")

        # Resolve references if requested
        if resolve_refs:
            config = self._resolve_references(config, config_file.parent)

        # Cache the result
        self._config_cache[cache_key] = config
        return config

    def _find_config_file(self, config_path: str) -> Optional[Path]:
        """Find a configuration file in the search directories.

        Args:
            config_path: Path to the configuration file

        Returns:
            Path to the found configuration file, or None if not found
        """
        # If it's an absolute path or relative to current directory, check directly
        if (
            os.path.isabs(config_path)
            or config_path.startswith("./")
            or config_path.startswith("../")
        ):
            path = Path(config_path)
            if path.exists():
                return path

        # Search in config directories
        for config_dir in self.config_dirs:
            # Try different extensions
            for ext in [".yaml", ".yml", ""]:
                path = Path(config_dir) / f"{config_path}{ext}"
                if path.exists():
                    return path

        return None

    def _resolve_references(
        self, config: Dict[str, Any], base_dir: Path
    ) -> Dict[str, Any]:
        """Resolve config_ref references in the configuration.

        Args:
            config: Configuration dictionary
            base_dir: Base directory for resolving relative paths

        Returns:
            Configuration with resolved references
        """
        if not isinstance(config, dict):
            return config

        resolved_config = {}

        for key, value in config.items():
            if key == "config_ref" and isinstance(value, str):
                # This is a reference, load the referenced config
                ref_config = self._load_referenced_config(value, base_dir)
                resolved_config.update(ref_config)
            elif isinstance(value, dict):
                # Recursively resolve references in nested dictionaries
                resolved_config[key] = self._resolve_references(value, base_dir)
            elif isinstance(value, list):
                # Resolve references in lists
                resolved_config[key] = [
                    (
                        self._resolve_references(item, base_dir)
                        if isinstance(item, dict)
                        else item
                    )
                    for item in value
                ]
            else:
                resolved_config[key] = value

        return resolved_config

    def _load_referenced_config(self, ref_path: str, base_dir: Path) -> Dict[str, Any]:
        """Load a referenced configuration file.

        Args:
            ref_path: Path to the referenced configuration
            base_dir: Base directory for resolving relative paths

        Returns:
            Loaded configuration dictionary
        """
        # Resolve relative paths
        if not os.path.isabs(ref_path):
            ref_path = str(base_dir / ref_path)

        # Load the referenced config
        ref_config = self.load_config(ref_path, resolve_refs=True)

        return ref_config

    def merge_configs(
        self, base_config: Dict[str, Any], override_config: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Merge two configurations, with override_config taking precedence.

        Args:
            base_config: Base configuration
            override_config: Configuration to merge on top

        Returns:
            Merged configuration
        """
        merged = base_config.copy()

        for key, value in override_config.items():
            if (
                key in merged
                and isinstance(merged[key], dict)
                and isinstance(value, dict)
            ):
                # Recursively merge nested dictionaries
                merged[key] = self.merge_configs(merged[key], value)
            else:
                # Override the value
                merged[key] = value

        return merged

    def validate_config(
        self, config: Dict[str, Any], schema: Optional[Dict[str, Any]] = None
    ) -> bool:
        """Validate a configuration against a schema.

        Args:
            config: Configuration to validate
            schema: Optional schema for validation

        Returns:
            True if configuration is valid

        Raises:
            ConfigurationException: If configuration is invalid
        """
        # For now, we'll do basic validation
        # In the future, we could add JSON Schema validation or Pydantic model validation

        if not isinstance(config, dict):
            raise ConfigurationException("Configuration must be a dictionary")

        # Add more validation logic here as needed

        return True

    def save_config(self, config: Dict[str, Any], config_path: str) -> None:
        """Save a configuration to a file.

        Args:
            config: Configuration to save
            config_path: Path where to save the configuration

        Raises:
            ConfigurationException: If the configuration cannot be saved
        """
        try:
            # Ensure the directory exists
            config_file = Path(config_path)
            config_file.parent.mkdir(parents=True, exist_ok=True)

            with open(config_file, "w", encoding="utf-8") as f:
                yaml.dump(config, f, default_flow_style=False, indent=2)
        except Exception as e:
            raise ConfigurationException(
                f"Failed to save configuration {config_path}: {e}"
            )

    def get_config_value(
        self, config: Dict[str, Any], key_path: str, default: Any = None
    ) -> Any:
        """Get a value from a nested configuration using dot notation.

        Args:
            config: Configuration dictionary
            key_path: Dot-separated path to the value (e.g., "database.host")
            default: Default value if the key is not found

        Returns:
            The value at the specified path, or the default value
        """
        keys = key_path.split(".")
        current = config

        for key in keys:
            if isinstance(current, dict) and key in current:
                current = current[key]
            else:
                return default

        return current

    def set_config_value(
        self, config: Dict[str, Any], key_path: str, value: Any
    ) -> None:
        """Set a value in a nested configuration using dot notation.

        Args:
            config: Configuration dictionary to modify
            key_path: Dot-separated path to the value (e.g., "database.host")
            value: Value to set
        """
        keys = key_path.split(".")
        current = config

        # Navigate to the parent of the target key
        for key in keys[:-1]:
            if key not in current:
                current[key] = {}
            current = current[key]

        # Set the value
        current[keys[-1]] = value
