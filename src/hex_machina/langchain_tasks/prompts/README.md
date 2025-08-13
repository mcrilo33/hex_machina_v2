# Prompts Package

This package provides prompt template management and registry functionality for LangChain tasks.

## Features

- **Auto-discovery** of prompt templates from YAML files
- **Simple template format** with just name, description, and template
- **Registry lookup** by template name
- **Easy integration** with task configurations

## Usage

### 1. Using Prompt Templates in Task Configs

Instead of defining prompts inline, reference them by name:

```yaml
# Before (inline template)
- name: prompt_template
  runnable: PromptTemplate
  config:
    template: "Extract keywords from the following text: {text_content}"
  dataset: true

# After (using registry)
- name: prompt_template
  runnable: PromptTemplate
  config:
    prompt_name: "keyword_extraction"  # Reference by name
  dataset: true
```

### 2. Creating New Prompt Templates

Add new YAML files to the `templates/` directory:

```yaml
# templates/my_custom_prompt.yaml
name: "my_custom_prompt"
description: "Description of what this prompt does"
template: "Your prompt template with {variables}"
```

### 3. Programmatic Access

```python
from langchain_tasks.prompts import prompt_registry

# List all available templates
templates = prompt_registry.list_templates()
print(templates)

# Get a specific template
template = prompt_registry.get_template("keyword_extraction")
print(template["template"])

# Check if template exists
exists = prompt_registry.template_exists("keyword_extraction")
```

## Template Format

Each prompt template YAML file should contain:

- **name**: Unique identifier for the template
- **description**: Human-readable description
- **template**: The actual prompt template with {variables}

## Auto-Discovery

The registry automatically:
1. Scans the `templates/` directory for YAML files
2. Loads and validates each template
3. Makes them available for lookup by name
4. Logs discovery and validation results

## Best Practices

1. **Descriptive Names**: Use clear, descriptive template names
2. **Consistent Variables**: Use consistent variable naming across templates
3. **Clear Descriptions**: Write helpful descriptions for each template
4. **Version Control**: Keep templates in version control for tracking changes
