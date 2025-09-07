"""
Annotation session manager for interactive dataset annotation.

This module provides functionality for running interactive annotation sessions
on LangSmith datasets with configurable display and annotation fields.
"""

import logging
import os
from typing import Any, Dict, List, Optional

from langsmith import Client, schemas

from .annotation_models import AnnotationConfig, AnnotationSession


class AnnotationManager:
    """Manages interactive annotation sessions for LangSmith datasets."""

    # Constants
    TRUNCATION_LENGTH = 5000
    DISPLAY_WIDTH = 90  # Increased from 80 to 90 for better readability
    TRUNCATION_HALF_LENGTH = 1500  # Changed from 2500 to 1500

    def __init__(self, client: Optional[Client] = None):
        """Initialize the annotation manager.

        Args:
            client: LangSmith client. If None, creates a new one.
        """
        self.client = client or Client()
        self._logger = logging.getLogger("langchain_tasks.datasets.annotation_manager")

    def load_config(self, config_path: str) -> AnnotationConfig:
        """Load annotation configuration from YAML file.

        Args:
            config_path: Path to the YAML configuration file

        Returns:
            Loaded annotation configuration

        Raises:
            FileNotFoundError: If config file doesn't exist
            ValueError: If config is invalid
        """
        import yaml

        if not os.path.exists(config_path):
            raise FileNotFoundError(f"Configuration file not found: {config_path}")

        try:
            with open(config_path, "r", encoding="utf-8") as f:
                config_data = yaml.safe_load(f)

            config = AnnotationConfig(**config_data)
            self._logger.info(
                f"Loaded annotation config: {config.annotation_session.name}"
            )
            return config

        except Exception as e:
            raise ValueError(f"Failed to load annotation config: {e}")

    def get_dataset_examples(
        self, dataset_name: str, split: str
    ) -> List[schemas.Example]:
        """Fetch examples from a LangSmith dataset split.

        Args:
            dataset_name: Name of the dataset
            split: Name of the split to fetch

        Returns:
            List of examples from the dataset split

        Raises:
            ValueError: If dataset or split not found
        """
        try:
            # Find the dataset
            datasets = list(self.client.list_datasets())
            target_dataset = None

            for dataset in datasets:
                if dataset.name == dataset_name:
                    target_dataset = dataset
                    break

            if not target_dataset:
                raise ValueError(f"Dataset '{dataset_name}' not found")

            # Get examples from the specified split
            examples = list(
                self.client.list_examples(dataset_name=dataset_name, splits=[split])
            )

            if not examples:
                raise ValueError(
                    f"No examples found in split '{split}' of dataset '{dataset_name}'"
                )

            self._logger.info(f"Found {len(examples)} examples in split '{split}'")
            return examples

        except Exception as e:
            raise ValueError(f"Failed to fetch dataset examples: {e}")

    def _get_field_value(self, obj: Dict[str, Any], field_path: str) -> Any:
        """Get value from a field path, handling nested paths and JSON fields.

        Args:
            obj: Object to extract field from
            field_path: Field path like "['generations'][0][0]['text']['is_complete']"

        Returns:
            Field value or None if not found
        """
        try:
            # Handle complex nested paths like ['generations'][0][0]['text']['is_complete']
            if "['" in field_path and "']" in field_path:
                # Navigate through the path step by step
                current = obj
                path_parts = []

                # Parse the path: ['generations'][0][0]['text']['is_complete']
                remaining = field_path
                while remaining:
                    if remaining.startswith("['"):
                        # Find the closing bracket
                        end = remaining.find("']")
                        if end == -1:
                            break

                        # Extract the key/index
                        key_part = remaining[2:end]
                        path_parts.append(key_part)

                        # Move to next part
                        remaining = remaining[end + 2 :]
                    elif remaining.startswith("["):
                        # Handle array indices like [0]
                        end = remaining.find("]")
                        if end == -1:
                            break

                        # Extract the index
                        index_part = remaining[1:end]
                        path_parts.append(index_part)

                        # Move to next part
                        remaining = remaining[end + 1 :]
                    else:
                        break

                # Navigate through the path
                for i, part in enumerate(path_parts):
                    if part.isdigit():
                        # Array index
                        index = int(part)
                        if isinstance(current, list) and 0 <= index < len(current):
                            current = current[index]
                        else:
                            return None
                    else:
                        # Dict key
                        if isinstance(current, dict) and part in current:
                            current = current[part]
                        else:
                            # Check if current is a JSON string that needs parsing
                            if isinstance(current, str) and (
                                current.strip().startswith(("{", "["))
                                or current.strip().startswith("```json")
                            ):
                                try:
                                    parsed_json = self._parse_json_input(current)
                                    if (
                                        isinstance(parsed_json, dict)
                                        and part in parsed_json
                                    ):
                                        current = parsed_json[part]
                                    else:
                                        return None
                                except KeyError:
                                    return None
                            else:
                                return None

                return current
            else:
                # Simple field access
                return obj.get(field_path)

        except Exception as e:
            self._logger.debug(f"Failed to get field {field_path}: {e}")
            return None

    def _set_value(self, obj: Any, path: str, value: Any) -> Any:
        """Recursive method to set a value in a nested path.

        Args:
            obj: Object to modify
            path: Remaining path to navigate
            value: Value to set

        Returns:
            Updated object
        """
        # If we've reached the end of the path, return the value (with type casting)
        if not path:
            # Auto-convert string booleans to actual booleans
            if isinstance(value, str):
                if value.lower() in ["true", "1", "yes", "y"]:
                    value = True
                elif value.lower() in ["false", "0", "no", "n"]:
                    value = False
            return value

        # Parse the next part of the path
        if path.startswith("['"):
            # Field access: ['field_name']
            end = path.find("']")
            if end == -1:
                return obj

            field_name = path[2:end]
            remaining_path = path[end + 2 :]

            if isinstance(obj, dict):
                # Check if the current value is a JSON string
                current_value = obj.get(field_name)
                if isinstance(current_value, str) and (
                    current_value.strip().startswith(("{", "["))
                    or current_value.strip().startswith("```json")
                ):
                    # Parse the JSON string
                    try:
                        import json

                        parsed_json = self._parse_json_input(current_value)
                        # Recursively set the value in the parsed JSON
                        updated_json = self._set_value(
                            parsed_json, remaining_path, value
                        )
                        # Convert back to string and update
                        updated_string = json.dumps(updated_json, ensure_ascii=False)
                        obj[field_name] = updated_string
                    except Exception as e:
                        self._logger.error(f"Failed to parse JSON: {e}")
                        return obj
                else:
                    # Regular field, not a JSON string
                    obj[field_name] = self._set_value(
                        current_value, remaining_path, value
                    )
            else:
                return obj

        elif path.startswith("["):
            # Array access: [index]
            end = path.find("]")
            if end == -1:
                return obj

            index_str = path[1:end]
            remaining_path = path[end + 1 :]

            if index_str.isdigit() and isinstance(obj, list):
                index = int(index_str)
                if 0 <= index < len(obj):
                    # Check if the current value is a JSON string
                    current_value = obj[index]
                    if isinstance(current_value, str) and (
                        current_value.strip().startswith(("{", "["))
                        or current_value.strip().startswith("```json")
                    ):
                        # Parse the JSON string
                        try:
                            import json

                            parsed_json = self._parse_json_input(current_value)
                            # Recursively set the value in the parsed JSON
                            updated_json = self._set_value(
                                parsed_json, remaining_path, value
                            )
                            # Convert back to string and update
                            updated_string = json.dumps(
                                updated_json, ensure_ascii=False
                            )
                            obj[index] = updated_string
                        except Exception as e:
                            self._logger.error(f"Failed to parse JSON: {e}")
                            return obj
                    else:
                        # Regular array element, not a JSON string
                        obj[index] = self._set_value(
                            current_value, remaining_path, value
                        )
                else:
                    return obj
            else:
                return obj
        else:
            # Field access without brackets: field_name
            # Find the next bracket or end of string
            next_bracket = path.find("['")
            next_array = path.find("[")

            if next_bracket == -1 and next_array == -1:
                # No more path parts, this is the final field
                if isinstance(obj, dict) and path in obj:
                    # Check if the current value is a JSON string
                    current_value = obj[path]
                    if isinstance(current_value, str) and (
                        current_value.strip().startswith(("{", "["))
                        or current_value.strip().startswith("```json")
                    ):
                        # Parse the JSON string
                        try:
                            import json

                            parsed_json = self._parse_json_input(current_value)
                            # Recursively set the value in the parsed JSON
                            updated_json = self._set_value(parsed_json, "", value)
                            # Convert back to string and update
                            updated_string = json.dumps(
                                updated_json, ensure_ascii=False
                            )
                            obj[path] = updated_string
                        except Exception as e:
                            self._logger.error(f"Failed to parse JSON: {e}")
                            return obj
                    else:
                        # Regular field, not a JSON string
                        obj[path] = value
                    return obj
                else:
                    return obj

            # Find the next path separator
            if next_bracket == -1:
                next_sep = next_array
            elif next_array == -1:
                next_sep = next_bracket
            else:
                next_sep = min(next_bracket, next_array)

            field_name = path[:next_sep]
            remaining_path = path[next_sep:]

            if isinstance(obj, dict) and field_name in obj:
                # Check if the current value is a JSON string
                current_value = obj[field_name]
                if isinstance(current_value, str) and (
                    current_value.strip().startswith(("{", "["))
                    or current_value.strip().startswith("```json")
                ):
                    # Parse the JSON string
                    try:
                        import json

                        parsed_json = self._parse_json_input(current_value)
                        # Recursively set the value in the parsed JSON
                        updated_json = self._set_value(
                            parsed_json, remaining_path, value
                        )
                        # Convert back to string and update
                        updated_string = json.dumps(updated_json, ensure_ascii=False)
                        obj[field_name] = updated_string
                    except Exception as e:
                        self._logger.error(f"Failed to parse JSON: {e}")
                        return obj
                else:
                    # Regular field, not a JSON string
                    obj[field_name] = self._set_value(
                        current_value, remaining_path, value
                    )
            else:
                return obj

        return obj

    def _update_json_field(
        self, example: schemas.Example, field_path: str, value: Any
    ) -> None:
        """Simple method to update a field inside a JSON string representation.

        Args:
            example: Example to modify
            field_path: Field path like "['generations'][0][0]['text']['is_complete']"
            value: Value to set (will be auto-converted to proper type)
        """
        try:
            # Determine which section to update (inputs or outputs)
            if "outputs" in field_path:
                current_obj = example.outputs
            else:
                current_obj = example.inputs

            # Use the recursive method to update the value
            self._set_value(current_obj, field_path, value)

        except Exception as e:
            self._logger.error(f"Failed to update JSON field {field_path}: {e}")

    def _generate_backup_key(self, section: str, field_name: str) -> str:
        """Generate a backup key for storing original field values.

        Args:
            section: Section name (inputs or outputs)
            field_name: Field name/path

        Returns:
            Backup key string
        """
        # Clean the field name for use as a metadata key
        clean_name = field_name.replace("[", "_").replace("]", "").replace("'", "")
        return f"original_{section}_{clean_name}"

    def _truncate_text(self, text: str, max_length: int = None) -> str:
        """Truncate text to fit display width with ellipsis.

        Args:
            text: Text to truncate
            max_length: Maximum length (defaults to TRUNCATION_LENGTH)

        Returns:
            Truncated text
        """
        if max_length is None:
            max_length = self.TRUNCATION_LENGTH

        if len(text) <= max_length:
            return text

        # Truncate from middle
        half_length = self.TRUNCATION_HALF_LENGTH
        return f"{text[:half_length]}... [truncated] ...{text[-half_length:]}"

    def _display_field(self, field_name: str, value: Any) -> str:
        """Format a field for display.

        Args:
            field_name: Name of the field
            value: Field value

        Returns:
            Formatted field string
        """
        if value is None:
            return f"{field_name}: [EMPTY]"

        if isinstance(value, str):
            truncated_value = self._truncate_text(value)
            return f"{field_name}: {truncated_value}"
        else:
            return f"{field_name}: {value}"

    def _wrap_text(self, text: str, max_width: int) -> List[str]:
        """Wrap text to fit within max_width, breaking at word boundaries.

        Args:
            text: Text to wrap
            max_width: Maximum width for each line

        Returns:
            List of wrapped lines
        """
        if len(text) <= max_width:
            return [text]

        lines = []
        words = text.split()
        current_line = ""

        for word in words:
            # If adding this word would exceed the line width
            if len(current_line) + len(word) + 1 > max_width:
                if current_line:
                    lines.append(current_line)
                    current_line = word
                else:
                    # Word is too long for a single line, break it
                    lines.append(word[:max_width])
                    current_line = word[max_width:]
            else:
                if current_line:
                    current_line += " " + word
                else:
                    current_line = word

        if current_line:
            lines.append(current_line)

        return lines

    def _parse_json_input(self, value: str) -> Any:
        """Parse JSON input if it looks like JSON, otherwise return as-is.

        Args:
            value: Input string to parse

        Returns:
            Parsed JSON object or original string
        """
        if (
            value.startswith(("[", "{")) and value.endswith(("]", "}"))
        ) or value.startswith("```json"):
            try:
                import json

                if "```json" in value:
                    # Extract from markdown
                    start = value.find("```json") + 7
                    end = value.rfind("```")
                    json_text = value[start:end].strip()
                else:
                    json_text = value.strip()
                parsed_value = json.loads(json_text)
                return parsed_value
            except json.JSONDecodeError:
                return value
        return value

    def _display_example(
        self, example: schemas.Example, config: AnnotationSession
    ) -> None:
        """Display an example with the specified fields.

        Args:
            example: Example to display
            config: Annotation session configuration
        """
        print("=" * self.DISPLAY_WIDTH)
        print(f"EXAMPLE {example.id}")
        print("=" * self.DISPLAY_WIDTH)
        print()

        # Display inputs
        print("INPUTS:")
        print("┌" + "─" * (self.DISPLAY_WIDTH - 2) + "┐")

        # Include configured display fields + any replace fields from annotations
        input_display_fields: List[str] = list(config.display_fields.get("inputs", []))
        for f in config.annotation_fields.get("inputs", []):
            try:
                if (
                    getattr(f, "field_type", None) == "replace"
                    and f.name not in input_display_fields
                ):
                    input_display_fields.append(f.name)
            except Exception:
                pass

        for field_path in input_display_fields:
            value = self._get_field_value(example.inputs, field_path)
            field_display = self._display_field(field_path, value)

            # Wrap text to fit display width
            lines = self._wrap_text(field_display, self.DISPLAY_WIDTH - 4)

            for line in lines:
                print(f"│ {line:<{self.DISPLAY_WIDTH-4}} │")
            print("│" + " " * (self.DISPLAY_WIDTH - 2) + "│")

        print("└" + "─" * (self.DISPLAY_WIDTH - 2) + "┘")
        print()

        # Display outputs
        print("OUTPUTS:")
        print("┌" + "─" * (self.DISPLAY_WIDTH - 2) + "┐")

        output_display_fields: List[str] = list(
            config.display_fields.get("outputs", [])
        )
        for f in config.annotation_fields.get("outputs", []):
            try:
                if (
                    getattr(f, "field_type", None) == "replace"
                    and f.name not in output_display_fields
                ):
                    output_display_fields.append(f.name)
            except Exception:
                pass

        for field_path in output_display_fields:
            value = self._get_field_value(example.outputs, field_path)
            field_display = self._display_field(field_path, value)

            # Wrap text to fit display width
            lines = self._wrap_text(field_display, self.DISPLAY_WIDTH - 4)

            for line in lines:
                print(f"│ {line:<{self.DISPLAY_WIDTH-4}} │")
            print("│" + " " * (self.DISPLAY_WIDTH - 2) + "│")

        print("└" + "─" * (self.DISPLAY_WIDTH - 2) + "┘")
        print()

    def _collect_annotations(
        self, config: AnnotationSession, example: Optional[schemas.Example] = None
    ) -> Dict[str, Any]:
        """Collect annotations from the user.

        Args:
            config: Annotation session configuration

        Returns:
            Dictionary of collected annotations
        """
        annotations = {"inputs": {}, "outputs": {}}

        print("ANNOTATIONS:")
        print("┌" + "─" * (self.DISPLAY_WIDTH - 2) + "┐")
        # Controls help
        controls = "Commands: /s or /skip = skip field; /n or /next = next example; Enter = skip field"
        lines = self._wrap_text(controls, self.DISPLAY_WIDTH - 4)
        for line in lines:
            print(f"│ {line:<{self.DISPLAY_WIDTH-4}} │")
        print("│" + " " * (self.DISPLAY_WIDTH - 2) + "│")

        # Collect input annotations
        for field in config.annotation_fields.get("inputs", []):
            if field.field_type == "categorical":
                options_str = "/".join(field.options)
                print(f"│ {field.name}: [{options_str}]")
                print("│ > ", end="")
                value = input().strip()
                cmd = value.lower()
                if cmd in {"/skip", "/s", ""}:
                    print(f"│ Skipped {field.name}")
                    print("│" + " " * (self.DISPLAY_WIDTH - 2) + "│")
                    continue
                if cmd in {"/next", "/n"}:
                    annotations["__control__"] = "next"
                    print("│ Moving to next example...")
                    print("│" + " " * (self.DISPLAY_WIDTH - 2) + "│")
                    print("└" + "─" * (self.DISPLAY_WIDTH - 2) + "┘")
                    print()
                    return annotations

                # Try to parse JSON if the input looks like JSON
                value = self._parse_json_input(value)

                annotations["inputs"][field.name] = value
            elif field.field_type == "free_text":
                print(f"│ {field.name}:")
                print("│ > ", end="")
                value = input().strip()
                cmd = value.lower()
                if cmd in {"/skip", "/s", ""}:
                    print(f"│ Skipped {field.name}")
                    print("│" + " " * (self.DISPLAY_WIDTH - 2) + "│")
                    continue
                if cmd in {"/next", "/n"}:
                    annotations["__control__"] = "next"
                    print("│ Moving to next example...")
                    print("│" + " " * (self.DISPLAY_WIDTH - 2) + "│")
                    print("└" + "─" * (self.DISPLAY_WIDTH - 2) + "┘")
                    print()
                    return annotations

                # Try to parse JSON if the input looks like JSON
                value = self._parse_json_input(value)

                annotations["inputs"][field.name] = value
            elif field.field_type == "replace":
                # Get the current value to show what will be replaced (if example provided)
                current_value = None
                if example is not None:
                    current_value = self._get_field_value(example.inputs, field.name)
                print(f"│ {field.name}: [REPLACE FIELD]")
                if current_value is not None:
                    print(f"│ Current value: {current_value}")
                print("│ > ", end="")
                value = input().strip()
                # Skip to next field / next example controls
                if value.lower() in {"/skip", "/s", ""}:
                    # Empty input or /skip means skip this field
                    print(f"│ Skipped {field.name}")
                    print("│" + " " * (self.DISPLAY_WIDTH - 2) + "│")
                    continue
                if value.lower() in {"/next", "/n"}:
                    # Signal to skip remaining fields and move to next example
                    annotations["__control__"] = "next"
                    print("│ Moving to next example...")
                    print("│" + " " * (self.DISPLAY_WIDTH - 2) + "│")
                    print("└" + "─" * (self.DISPLAY_WIDTH - 2) + "┘")
                    print()
                    return annotations

                # Try to parse JSON if the input looks like JSON
                value = self._parse_json_input(value)

                annotations["inputs"][field.name] = value
            elif field.field_type == "boolean":
                print(f"│ {field.name}: [true/false]")
                print("│ > ", end="")
                value = input().strip().lower()
                cmd = value
                if cmd in {"/skip", "/s", ""}:
                    print(f"│ Skipped {field.name}")
                    print("│" + " " * (self.DISPLAY_WIDTH - 2) + "│")
                    continue
                if cmd in {"/next", "/n"}:
                    annotations["__control__"] = "next"
                    print("│ Moving to next example...")
                    print("│" + " " * (self.DISPLAY_WIDTH - 2) + "│")
                    print("└" + "─" * (self.DISPLAY_WIDTH - 2) + "┘")
                    print()
                    return annotations

                # Convert string input directly to boolean
                if value in ["true", "1", "yes", "y"]:
                    value = True
                elif value in ["false", "0", "no", "n"]:
                    value = False
                else:
                    print("│ Invalid boolean value. Using False.")
                    value = False

                annotations["inputs"][field.name] = value
            print("│" + " " * (self.DISPLAY_WIDTH - 2) + "│")

        # Collect output annotations
        for field in config.annotation_fields.get("outputs", []):
            if field.field_type == "categorical":
                options_str = "/".join(field.options)
                print(f"│ {field.name}: [{options_str}]")
                print("│ > ", end="")
                value = input().strip()
                cmd = value.lower()
                if cmd in {"/skip", "/s", ""}:
                    print(f"│ Skipped {field.name}")
                    print("│" + " " * (self.DISPLAY_WIDTH - 2) + "│")
                    continue
                if cmd in {"/next", "/n"}:
                    annotations["__control__"] = "next"
                    print("│ Moving to next example...")
                    print("│" + " " * (self.DISPLAY_WIDTH - 2) + "│")
                    print("└" + "─" * (self.DISPLAY_WIDTH - 2) + "┘")
                    print()
                    return annotations

                # Try to parse JSON if the input looks like JSON
                value = self._parse_json_input(value)

                annotations["outputs"][field.name] = value
            elif field.field_type == "free_text":
                print(f"│ {field.name}:")
                print("│ > ", end="")
                value = input().strip()
                cmd = value.lower()
                if cmd in {"/skip", "/s", ""}:
                    print(f"│ Skipped {field.name}")
                    print("│" + " " * (self.DISPLAY_WIDTH - 2) + "│")
                    continue
                if cmd in {"/next", "/n"}:
                    annotations["__control__"] = "next"
                    print("│ Moving to next example...")
                    print("│" + " " * (self.DISPLAY_WIDTH - 2) + "│")
                    print("└" + "─" * (self.DISPLAY_WIDTH - 2) + "┘")
                    print()
                    return annotations

                # Try to parse JSON if the input looks like JSON
                value = self._parse_json_input(value)

                annotations["outputs"][field.name] = value
            elif field.field_type == "replace":
                # Get the current value to show what will be replaced (if example provided)
                current_value = None
                if example is not None:
                    current_value = self._get_field_value(example.outputs, field.name)
                print(f"│ {field.name}: [REPLACE FIELD]")
                if current_value is not None:
                    print(f"│ Current value: {current_value}")
                print("│ > ", end="")
                value = input().strip()
                # Skip to next field / next example controls
                if value.lower() in {"/skip", "/s", ""}:
                    print(f"│ Skipped {field.name}")
                    print("│" + " " * (self.DISPLAY_WIDTH - 2) + "│")
                    continue
                if value.lower() in {"/next", "/n"}:
                    annotations["__control__"] = "next"
                    print("│ Moving to next example...")
                    print("│" + " " * (self.DISPLAY_WIDTH - 2) + "│")
                    print("└" + "─" * (self.DISPLAY_WIDTH - 2) + "┘")
                    print()
                    return annotations

                # Try to parse JSON if the input looks like JSON
                value = self._parse_json_input(value)

                annotations["outputs"][field.name] = value
            elif field.field_type == "boolean":
                print(f"│ {field.name}: [true/false]")
                print("│ > ", end="")
                value = input().strip().lower()
                cmd = value
                if cmd in {"/skip", "/s", ""}:
                    print(f"│ Skipped {field.name}")
                    print("│" + " " * (self.DISPLAY_WIDTH - 2) + "│")
                    continue
                if cmd in {"/next", "/n"}:
                    annotations["__control__"] = "next"
                    print("│ Moving to next example...")
                    print("│" + " " * (self.DISPLAY_WIDTH - 2) + "│")
                    print("└" + "─" * (self.DISPLAY_WIDTH - 2) + "┘")
                    print()
                    return annotations

                # Convert string input directly to boolean
                if value in ["true", "1", "yes", "y"]:
                    value = True
                elif value in ["false", "0", "no", "n"]:
                    value = False
                else:
                    print("│ Invalid boolean value. Using False.")
                    value = False

                annotations["outputs"][field.name] = value
            print("│" + " " * (self.DISPLAY_WIDTH - 2) + "│")

        print("└" + "─" * (self.DISPLAY_WIDTH - 2) + "┘")
        print()

        return annotations

    def _save_annotations(
        self,
        example: schemas.Example,
        annotations: Dict[str, Any],
        config: AnnotationSession,
    ) -> None:
        """Save annotations to the example metadata and replace fields if needed.

        Args:
            example: Example to annotate
            annotations: Collected annotations
        """
        try:
            # Get current metadata and data
            current_metadata = example.metadata or {}
            current_inputs = example.inputs.copy() if example.inputs else {}
            current_outputs = example.outputs.copy() if example.outputs else {}

            # Process annotations
            for section, fields in annotations.items():
                if section == "__control__":
                    # Skip control annotations
                    continue

                for field_name, value in fields.items():
                    if section == "inputs":
                        # Check if this is a replace field by looking at the config
                        is_replace = False
                        for field_config in config.annotation_fields.get("inputs", []):
                            if (
                                field_config.name == field_name
                                and field_config.field_type == "replace"
                            ):
                                is_replace = True
                                break

                        if is_replace:
                            # Backup original value in metadata
                            original_value = self._get_field_value(
                                current_inputs, field_name
                            )
                            backup_key = self._generate_backup_key("inputs", field_name)
                            current_metadata[backup_key] = original_value

                            # Update the field directly in the copied data
                            self._set_value(current_inputs, field_name, value)
                        else:
                            # Regular annotation
                            metadata_key = f"annotation_inputs_{field_name}"
                            current_metadata[metadata_key] = value

                    elif section == "outputs":
                        # Check if this is a replace field by looking at the config
                        is_replace = False
                        for field_config in config.annotation_fields.get("outputs", []):
                            if (
                                field_config.name == field_name
                                and field_config.field_type == "replace"
                            ):
                                is_replace = True
                                break

                        if is_replace:
                            # Backup original value in metadata
                            original_value = self._get_field_value(
                                current_outputs, field_name
                            )
                            backup_key = self._generate_backup_key(
                                "outputs", field_name
                            )
                            current_metadata[backup_key] = original_value

                            # Update the field directly in the copied data
                            self._set_value(current_outputs, field_name, value)
                        else:
                            # Regular annotation
                            metadata_key = f"annotation_outputs_{field_name}"
                            current_metadata[metadata_key] = value

            # Update the example with new data and metadata
            self.client.update_example(
                example_id=example.id,
                inputs=current_inputs,
                outputs=current_outputs,
                metadata=current_metadata,
            )

            self._logger.info(
                f"Saved annotations and field replacements for example {example.id}"
            )

        except Exception as e:
            self._logger.error(
                f"Failed to save annotations for example {example.id}: {e}"
            )

    def run_annotation_session(self, config_path: str) -> None:
        """Run a complete annotation session.

        Args:
            config_path: Path to the annotation configuration file
        """
        try:
            # Load configuration
            config = self.load_config(config_path)
            session = config.annotation_session

            # Fetch examples
            examples = self.get_dataset_examples(
                session.dataset["name"], session.dataset["split"]
            )

            print(f"Starting annotation session: {session.name}")
            print(
                f"Dataset: {session.dataset['name']} (split: {session.dataset['split']})"
            )
            print(f"Examples to annotate: {len(examples)}")
            print()

            # Process each example
            for i, example in enumerate(examples, 1):
                print(f"Processing example {i}/{len(examples)}")
                print()

                # Display the example
                self._display_example(example, session)

                # Collect annotations
                annotations = self._collect_annotations(session, example)

                # Check if we should skip to next example
                if annotations.get("__control__") == "next":
                    print(f"Skipped example {i}/{len(examples)}")
                    continue

                # Save annotations
                self._save_annotations(example, annotations, session)

                # Clear screen for next example
                os.system("cls" if os.name == "nt" else "clear")

                print(f"Completed example {i}/{len(examples)}")
                print()

            print("Annotation session completed successfully!")
            print(f"Annotated {len(examples)} examples")

        except Exception as e:
            self._logger.error(f"Annotation session failed: {e}")
            raise
