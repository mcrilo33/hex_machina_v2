# Annotation Configurations

This directory contains configuration files for dataset annotation sessions.

## Purpose

Annotation configurations define how to run interactive annotation sessions on LangSmith datasets. They specify:
- Which dataset and split to annotate
- Which fields to display during annotation
- Which fields to collect annotations for
- The type and options for each annotation field

## File Structure

- `dataset_annotation.yaml` - Example configuration for article completeness annotation

## Usage

Run an annotation session using:

```bash
poetry run python -m src.hex_machina.langchain_tasks dataset annotate -c configs/annotations/your_config.yaml
```

## Configuration Format

Each configuration file should follow this structure:

```yaml
annotation_session:
  name: "session_name"
  description: "Session description"
  
  dataset:
    name: "dataset_name"
    split: "split_name"
  
  display_fields:
    inputs: ["field1", "field2", "metadata['nested_field']"]
    outputs: ["output1", "output2"]
  
  annotation_fields:
    inputs:
      - name: "field_name"
        field_type: "categorical"  # or "free_text"
        options: ["option1", "option2"]  # or "free_text"
    outputs:
      - name: "field_name"
        field_type: "free_text"
        options: "free_text"
```

## Field Types

### Categorical Fields
- **field_type**: `"categorical"`
- **options**: List of valid choices (e.g., `["high", "medium", "low"]`)

### Free Text Fields
- **field_type**: `"free_text"`
- **options**: `"free_text"`

## Nested Field Access

Use bracket notation to access nested fields:
- `metadata['source_domain']`
- `user_data['preferences']`
- `nested['deep']['field']`

## Examples

See `dataset_annotation.yaml` for a complete example configuration.
