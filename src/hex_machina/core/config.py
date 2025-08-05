"""Configuration management for the Hex Machina project."""

from pathlib import Path
from typing import Any, Dict

import yaml

from .exceptions import ConfigurationException


class ConfigManager:
    """Manages YAML configuration loading and composition."""

    def __init__(self, config_base_path: str = "src/hex_machina/configs"):
        self.config_base_path = Path(config_base_path)
        self._loaded_configs = {}

    def load_config(self, config_path: str) -> Dict[str, Any]:
        """Load configuration with support for references."""
        config_path = Path(config_path)

        # Resolve relative paths
        if not config_path.is_absolute():
            config_path = self.config_base_path / config_path

        if not config_path.exists():
            raise ConfigurationException(
                f"Configuration file not found: {config_path}", str(config_path)
            )

        # Load YAML
        try:
            with open(config_path, "r", encoding="utf-8") as f:
                config = yaml.safe_load(f)
        except yaml.YAMLError as e:
            raise ConfigurationException(
                f"Invalid YAML in config file: {e}", str(config_path)
            )

        # Resolve references
        resolved_config = self._resolve_references(config, config_path.parent)

        # Cache the resolved config
        self._loaded_configs[str(config_path)] = resolved_config

        return resolved_config

    def _resolve_references(
        self, config: Dict[str, Any], base_path: Path
    ) -> Dict[str, Any]:
        """Resolve config_ref references in configuration."""
        if not isinstance(config, dict):
            return config

        resolved_config = {}

        for key, value in config.items():
            if key == "config_ref" and isinstance(value, str):
                # Handle config reference
                ref_path = self._resolve_ref_path(value, base_path)
                ref_config = self.load_config(str(ref_path))
                resolved_config.update(ref_config)
            elif isinstance(value, dict):
                # Recursively resolve nested dictionaries
                resolved_config[key] = self._resolve_references(value, base_path)
            elif isinstance(value, list):
                # Handle lists
                resolved_config[key] = [
                    (
                        self._resolve_references(item, base_path)
                        if isinstance(item, dict)
                        else item
                    )
                    for item in value
                ]
            else:
                resolved_config[key] = value

        return resolved_config

    def _resolve_ref_path(self, ref: str, base_path: Path) -> Path:
        """Resolve a config reference to a file path."""
        # Handle anchor references (e.g., "file.yaml#anchor")
        if "#" in ref:
            file_path, anchor = ref.split("#", 1)
            # For now, we'll ignore anchors and just load the file
            # TODO: Implement anchor support
            ref = file_path

        # Resolve relative paths
        ref_path = Path(ref)
        if not ref_path.is_absolute():
            ref_path = base_path / ref_path

        return ref_path

    def get_config_section(self, config: Dict[str, Any], section_path: str) -> Any:
        """Get a specific section from configuration using dot notation."""
        sections = section_path.split(".")
        current = config

        for section in sections:
            if isinstance(current, dict) and section in current:
                current = current[section]
            else:
                raise ConfigurationException(
                    f"Configuration section not found: {section_path}",
                    details={
                        "available_sections": (
                            list(current.keys()) if isinstance(current, dict) else []
                        )
                    },
                )

        return current

    def validate_config(self, config: Dict[str, Any], schema: Dict[str, Any]) -> bool:
        """Validate configuration against a schema."""
        # TODO: Implement schema validation
        # For now, just check if required fields exist
        required_fields = schema.get("required", [])

        for field in required_fields:
            if field not in config:
                raise ConfigurationException(
                    f"Required configuration field missing: {field}",
                    details={
                        "required_fields": required_fields,
                        "available_fields": list(config.keys()),
                    },
                )

        return True

    def merge_configs(self, *configs: Dict[str, Any]) -> Dict[str, Any]:
        """Merge multiple configurations."""
        merged = {}

        for config in configs:
            merged.update(config)

        return merged

    def save_config(self, config: Dict[str, Any], output_path: str) -> None:
        """Save configuration to file."""
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        try:
            with open(output_path, "w", encoding="utf-8") as f:
                yaml.dump(config, f, default_flow_style=False, indent=2)
        except Exception as e:
            raise ConfigurationException(
                f"Failed to save configuration: {e}", str(output_path)
            )


class ConfigValidator:
    """Validates configuration files."""

    @staticmethod
    def validate_task_config(config: Dict[str, Any]) -> bool:
        """Validate task configuration."""
        required_fields = ["task_type", "name"]

        for field in required_fields:
            if field not in config:
                raise ConfigurationException(
                    f"Task configuration missing required field: {field}",
                    details={"required_fields": required_fields},
                )

        return True

    @staticmethod
    def validate_workflow_config(config: Dict[str, Any]) -> bool:
        """Validate workflow configuration."""
        required_fields = ["workflow_type", "name"]

        for field in required_fields:
            if field not in config:
                raise ConfigurationException(
                    f"Workflow configuration missing required field: {field}",
                    details={"required_fields": required_fields},
                )

        return True

    @staticmethod
    def validate_evaluator_config(config: Dict[str, Any]) -> bool:
        """Validate evaluator configuration."""
        required_fields = ["evaluator_type", "name"]

        for field in required_fields:
            if field not in config:
                raise ConfigurationException(
                    f"Evaluator configuration missing required field: {field}",
                    details={"required_fields": required_fields},
                )

        return True
