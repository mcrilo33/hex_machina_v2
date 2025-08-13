# Prompt Templates

This directory contains YAML prompt template files that will be automatically discovered and registered by the `PromptRegistry`.

## How It Works

1. **Auto-Discovery**: The registry automatically scans this directory for YAML files
2. **Template Loading**: Each YAML file is loaded and validated
3. **Instant Registration**: No manual registration needed - just add your template files here

## Template File Requirements

Your prompt template YAML files must contain these fields:

```yaml
name: "template_name"                    # Required: Unique identifier
description: "What this template does"   # Required: Human-readable description
template: "Your prompt {variable}"       # Required: The actual template
```

## Example Templates

### Keyword Extraction
```yaml
name: "keyword_extraction"
description: "Extract keywords from text content"
template: "Extract keywords from the following text: {text_content}"
```

### Summarization
```yaml
name: "summarization"
description: "Summarize text content in a concise way"
template: "Please provide a concise summary of the following text: {text_content}"
```

### Content Analysis
```yaml
name: "content_analysis"
description: "Analyze the content and provide insights"
template: "Analyze the following content and provide key insights: {text_content}"
```

## File Naming

- Use descriptive names: `keyword_extraction.yaml`, `summarization.yaml`
- Use lowercase with underscores: `content_analysis.yaml`
- Files starting with `_` or `__` are ignored

## Template Variables

Use curly braces to define variables that will be filled at runtime:

```yaml
template: "Process this {input_text} with {options}"
```

Variables like `{input_text}` and `{options}` will be replaced with actual values when the template is used.

## Best Practices

1. **Clear Names**: Use descriptive template names
2. **Helpful Descriptions**: Explain what each template does
3. **Consistent Variables**: Use consistent variable naming
4. **Simple Templates**: Keep templates focused and clear
5. **Testing**: Test your templates with sample inputs

## Usage in Tasks

Reference your templates by name in task configurations:

```yaml
- name: prompt_template
  runnable: PromptTemplate
  config:
    prompt_name: "keyword_extraction"  # References the template above
  dataset: true
```
