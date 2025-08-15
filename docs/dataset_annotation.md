# Dataset Annotation Feature

The dataset annotation feature allows you to interactively annotate examples in LangSmith datasets with custom metadata. This is useful for adding human annotations, quality scores, or other subjective assessments to your dataset examples.

## Overview

The annotation feature provides:
- **Interactive terminal-based interface** for annotating dataset examples
- **Configurable display fields** to show relevant information during annotation
- **Flexible annotation fields** supporting categorical and free-text inputs
- **Deep nested field access** using bracket notation (e.g., `metadata['source_domain']`)
- **Automatic text truncation** for long content (5000 character limit)
- **Fixed-width display** for consistent, readable formatting

## Usage

### 1. Create Annotation Configuration

Create a YAML configuration file defining your annotation session:

```yaml
# configs/annotations/dataset_annotation.yaml
annotation_session:
  name: "article_completeness_annotation"
  description: "Annotate article completeness examples with quality scores"
  
  dataset:
    name: "article_completeness_dataset"
    split: "train"
  
  display_fields:
    inputs:
      - "article_text"
      - "article_url"
      - "metadata['source_domain']"
      - "metadata['publication_date']"
    outputs:
      - "is_complete"
      - "reasoning"
      - "confidence_score"
  
  annotation_fields:
    inputs:
      - name: "article_text_quality"
        field_type: "categorical"
        options: ["high", "medium", "low"]
      - name: "content_relevance"
        field_type: "categorical"
        options: ["relevant", "somewhat_relevant", "irrelevant"]
    
    outputs:
      - name: "annotation_confidence"
        field_type: "categorical"
        options: ["high", "medium", "low"]
      - name: "notes"
        field_type: "free_text"
        options: "free_text"
```

### 2. Run Annotation Session

Use the CLI command to start the annotation session:

```bash
poetry run python -m src.hex_machina.langchain_tasks dataset annotate -c configs/annotations/dataset_annotation.yaml
```

### 3. Annotate Examples

The interface will:
1. Display each example with the specified input and output fields
2. Show annotation prompts for each configured annotation field
3. Save annotations to the example metadata
4. Progress through all examples in the dataset split

## Configuration Options

### Display Fields

Fields to display during annotation. Supports:
- **Simple fields**: `article_text`, `is_complete`
- **Nested fields**: `metadata['source_domain']`, `metadata['publication_date']`

### Annotation Fields

Fields to collect annotations for:

#### Categorical Fields
```yaml
- name: "quality_score"
  field_type: "categorical"
  options: ["high", "medium", "low"]
```

#### Free Text Fields
```yaml
- name: "notes"
  field_type: "free_text"
  options: "free_text"
```

## Field Access Patterns

### Simple Fields
```yaml
inputs:
  - "article_text"
  - "is_complete"
```

### Nested Fields (Bracket Notation)
```yaml
inputs:
  - "metadata['source_domain']"
  - "metadata['publication_date']"
  - "user_data['preferences']"
```

## Output

Annotations are saved to the example metadata with the following key pattern:
- Input annotations: `annotation_inputs_{field_name}`
- Output annotations: `annotation_outputs_{field_name}`

Example metadata:
```json
{
  "annotation_inputs_article_text_quality": "high",
  "annotation_inputs_content_relevance": "relevant",
  "annotation_outputs_annotation_confidence": "high",
  "annotation_outputs_notes": "Well-structured article with clear conclusion"
}
```

## Display Format

The interface uses a fixed-width (80 characters) display with:
- Clear section separation (INPUTS, OUTPUTS, ANNOTATIONS)
- Bordered boxes for each section
- Automatic text truncation for long content
- Progress indicators showing current example and total count

## Example Session Flow

```
================================================================================
EXAMPLE abc123
================================================================================

INPUTS:
┌──────────────────────────────────────────────────────────────────────────────┐
│ article_text: This is a very long article about AI that contains many...    │
│ [truncated] ...conclusion.                                                  │
│                                                                              │
│ article_url: https://example.com/article/123                                │
│                                                                              │
│ metadata['source_domain']: techcrunch.com                                   │
└──────────────────────────────────────────────────────────────────────────────┘

OUTPUTS:
┌──────────────────────────────────────────────────────────────────────────────┐
│ is_complete: true                                                           │
│                                                                              │
│ reasoning: Article contains full content with proper conclusion             │
└──────────────────────────────────────────────────────────────────────────────┘

ANNOTATIONS:
┌──────────────────────────────────────────────────────────────────────────────┐
│ article_text_quality: [high/medium/low]                                    │
│ > high                                                                      │
│                                                                              │
│ content_relevance: [relevant/somewhat_relevant/irrelevant]                  │
│ > relevant                                                                  │
└──────────────────────────────────────────────────────────────────────────────┘
```

## Tips

1. **Start with a small dataset** to test your configuration
2. **Use descriptive field names** for easy identification later
3. **Group related annotations** in the same section (inputs vs outputs)
4. **Test your config** with a few examples before running on large datasets
5. **Use categorical fields** when possible for consistent annotations

## Troubleshooting

### Common Issues

1. **Dataset not found**: Verify the dataset name exists in LangSmith
2. **Split not found**: Check that the specified split exists in the dataset
3. **Field access errors**: Ensure field paths match the actual data structure
4. **Permission errors**: Verify your LangSmith API key has write access

### Debug Mode

Enable debug logging to see detailed information:
```bash
export LOG_LEVEL=DEBUG
poetry run python -m src.hex_machina.langchain_tasks dataset annotate -c configs/annotations/dataset_annotation.yaml
```
