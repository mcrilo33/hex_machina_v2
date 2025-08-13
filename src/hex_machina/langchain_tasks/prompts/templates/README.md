# Prompt Templates

This directory contains YAML prompt template files that will be automatically discovered and registered by the `PromptRegistry`.

## How It Works

1. **Auto-Discovery**: The registry automatically scans this directory for YAML files
2. **Template Loading**: Each YAML file is loaded and validated
3. **Instant Registration**: No manual registration needed - just add your template files here

## Template Structure

All prompt templates follow a standardized structure based on the `agnostic_template.yaml`. This ensures consistency and clarity across all prompts.

### Standard Sections

```yaml
name: "template_name"                    # Required: Unique identifier
description: "What this template does"   # Required: Human-readable description
template: |
  # ROLE
  {role}

  # GOAL
  {goal}

  # CONTEXT
  {context}

  # INPUTS
  {inputs}

  # INSTRUCTIONS
  {instructions}

  # CONSTRAINTS
  {constraints}

  # OUTPUTS
  {outputs}

  # START
  {start}
```

### Section Descriptions

- **ROLE**: Defines who the AI should be (expert, specialist, etc.)
- **GOAL**: Clear statement of what the AI should accomplish
- **CONTEXT**: Background information and situational details
- **INPUTS**: What data or information the AI will receive
- **INSTRUCTIONS**: Step-by-step guidance for the AI
- **CONSTRAINTS**: Limitations, rules, and boundaries
- **OUTPUTS**: Expected format and structure of the response
- **START**: Action trigger to begin the task

## Example Templates

### Article Completeness Detection
```yaml
name: "article_completeness"
description: "Detect if an article is complete based on title and content analysis"
template: |
  # ROLE
  You are an expert content analyst specializing in web content quality assessment...

  # GOAL
  Determine if an article retrieved from an HTML page is complete...

  # CONTEXT
  Articles are automatically retrieved from HTML pages...

  # INPUTS
  TITLE: {title}
  CONTENT: {text_content}

  # INSTRUCTIONS
  1. Analyze the article title and content for completeness...

  # CONSTRAINTS
  - Use only the predefined reason codes provided...

  # OUTPUTS
  Return your assessment in this exact JSON format...

  # START
  Analyze the following article to determine if it's complete...
```

### Keyword Extraction
```yaml
name: "keyword_extraction"
description: "Extract keywords from text content"
template: |
  # ROLE
  You are an expert content analyst specializing in keyword extraction...

  # GOAL
  Extract the most relevant and meaningful keywords...

  # CONTEXT
  Keywords are essential for content categorization...

  # INPUTS
  TEXT: {text_content}

  # INSTRUCTIONS
  1. Read and analyze the provided text content...

  # CONSTRAINTS
  - Extract between 5-15 keywords...

  # OUTPUTS
  Return your keywords as a JSON array...

  # START
  Extract keywords from the following text content.
```

## File Naming

- Use descriptive names: `keyword_extraction.yaml`, `summarization.yaml`
- Use lowercase with underscores: `content_analysis.yaml`
- Files starting with `_` or `__` are ignored

## Template Variables

Use curly braces to define variables that will be filled at runtime:

```yaml
template: |
  # INPUTS
  TITLE: {title}
  CONTENT: {text_content}
```

Variables like `{title}` and `{content}` will be replaced with actual values when the template is used.

## Best Practices

1. **Follow the Structure**: Always use the standard 8-section format
2. **Clear Roles**: Define specific, relevant roles for the AI
3. **Specific Goals**: State clear, measurable objectives
4. **Relevant Context**: Provide necessary background information
5. **Clear Instructions**: Use numbered steps for complex tasks
6. **Defined Constraints**: Set clear boundaries and limitations
7. **Structured Outputs**: Specify exact response formats
8. **Actionable Start**: Provide clear action triggers

## Usage in Tasks

Reference your templates by name in task configurations:

```yaml
- name: prompt_template
  runnable: PromptTemplate
  config:
    prompt_name: "keyword_extraction"  # References the template above
  dataset: true
```
