#!/usr/bin/env python3
"""
Example script demonstrating the dataset annotation feature.

This script shows how to use the annotation manager programmatically
to run annotation sessions on LangSmith datasets.
"""

import sys
from pathlib import Path

# Add the src directory to the path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from hex_machina.langchain_tasks.datasets import AnnotationConfig


def main():
    """Run an example annotation session."""

    # Example configuration data
    config_data = {
        "annotation_session": {
            "name": "example_annotation_session",
            "description": "Example annotation session for demonstration",
            "dataset": {"name": "example_dataset", "split": "train"},
            "display_fields": {
                "inputs": ["text", "metadata['source']"],
                "outputs": ["classification", "confidence"],
            },
            "annotation_fields": {
                "inputs": [
                    {
                        "name": "text_quality",
                        "field_type": "categorical",
                        "options": ["high", "medium", "low"],
                    }
                ],
                "outputs": [
                    {
                        "name": "annotation_notes",
                        "field_type": "free_text",
                        "options": "free_text",
                    }
                ],
            },
        }
    }

    # Create annotation config
    config = AnnotationConfig(**config_data)

    print("✅ Annotation configuration created successfully!")
    print(f"Session name: {config.annotation_session.name}")
    print(f"Dataset: {config.annotation_session.dataset['name']}")
    print(f"Split: {config.annotation_session.dataset['split']}")
    print()

    print("Display fields:")
    print(f"  Inputs: {config.annotation_session.display_fields['inputs']}")
    print(f"  Outputs: {config.annotation_session.display_fields['outputs']}")
    print()

    print("Annotation fields:")
    print(
        f"  Inputs: {[f.name for f in config.annotation_session.annotation_fields['inputs']]}"
    )
    print(
        f"  Outputs: {[f.name for f in config.annotation_session.annotation_fields['outputs']]}"
    )
    print()

    print("To run this annotation session, use:")
    print(
        "poetry run python -m src.hex_machina.langchain_tasks dataset annotate -c configs/annotations/dataset_annotation.yaml"
    )
    print()

    print("Or create a YAML file with the above configuration and run:")
    print(
        "poetry run python -m src.hex_machina.langchain_tasks dataset annotate -c your_config.yaml"
    )


if __name__ == "__main__":
    main()
