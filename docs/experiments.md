# Experiments System

The Experiments System allows you to systematically test multiple task configurations to find optimal settings for your enrichment tasks.

## Overview

The experiments system provides:

- **Configuration Management**: Define experiments in YAML files
- **Multi-Configuration Testing**: Test multiple task configurations in a single experiment
- **Automatic Evaluation**: Evaluate results using LangChain evaluators
- **Results Comparison**: Compare performance across configurations
- **LangSmith Integration**: Track experiments and results in LangSmith
- **Reporting**: Generate detailed comparison reports

## Quick Start

### 1. Create an Experiment Configuration

Create a YAML file in `config/experiments/`:

```yaml
# config/experiments/my_experiment.yaml
experiment_name: "my_experiment"
description: "Test different model configurations"
created_at: "2025-08-07"

# Dataset to use for evaluation
evaluation_dataset: "my-dataset"
evaluation_split: "train"

# Evaluators to use for comparison
evaluators:
  - criteria_completeness
  - criteria_accuracy
  - criteria_relevance

# Task configurations to test
task_configs:
  - name: "baseline"
    description: "Current configuration"
    config:
      model: "openai/gpt-4o-mini"
      temperature: 0
      max_tokens: 1000
      prompt_template: "current"
  
  - name: "high_temp"
    description: "Higher temperature for creativity"
    config:
      model: "openai/gpt-4o-mini"
      temperature: 0.3
      max_tokens: 1000
      prompt_template: "current"
  
  - name: "different_model"
    description: "Try different model"
    config:
      model: "openai/gpt-3.5-turbo"
      temperature: 0
      max_tokens: 1000
      prompt_template: "current"

# Comparison metrics
comparison_metrics:
  primary: "criteria_completeness"
  secondary: ["criteria_accuracy", "criteria_relevance"]
  threshold: 0.8

# Experiment settings
settings:
  max_concurrent_runs: 3
  timeout_per_run: 300
  save_intermediate_results: true
```

### 2. Run the Experiment

```bash
# Validate configuration first
poetry run python -m src.hex_machina.cli experiments run my_experiment --validate-only

# Run the experiment
poetry run python -m src.hex_machina.cli experiments run my_experiment
```

### 3. View Results

```bash
# List experiment results
poetry run python -m src.hex_machina.cli experiments results

# Compare results across runs
poetry run python -m src.hex_machina.cli experiments compare my_experiment

# Generate detailed report
poetry run python -m src.hex_machina.cli experiments report my_experiment
```

## CLI Commands

### `experiments run <experiment_name>`

Run an experiment from a configuration file.

**Options:**
- `--validate-only`: Only validate configuration without running

**Example:**
```bash
poetry run python -m src.hex_machina.cli experiments run content_completeness_optimization
```

### `experiments list`

List all available experiment configurations.

**Example:**
```bash
poetry run python -m src.hex_machina.cli experiments list
```

### `experiments show <experiment_name>`

Show detailed information about an experiment configuration.

**Example:**
```bash
poetry run python -m src.hex_machina.cli experiments show content_completeness_optimization
```

### `experiments compare <experiment_name>`

Compare results from multiple runs of an experiment.

**Example:**
```bash
poetry run python -m src.hex_machina.cli experiments compare content_completeness_optimization
```

### `experiments report <experiment_name>`

Generate a detailed comparison report for an experiment.

**Options:**
- `--output-dir`: Output directory for report

**Example:**
```bash
poetry run python -m src.hex_machina.cli experiments report content_completeness_optimization
```

### `experiments results`

List experiment results.

**Options:**
- `--experiment-name`: Filter by experiment name

**Example:**
```bash
poetry run python -m src.hex_machina.cli experiments results --experiment-name content_completeness_optimization
```

## Configuration Reference

### Experiment Configuration Structure

```yaml
experiment_name: string          # Required: Unique experiment name
description: string              # Required: Experiment description
created_at: string               # Optional: Creation timestamp

# Evaluation settings
evaluation_dataset: string       # Required: Dataset name
evaluation_split: string         # Optional: Dataset split to use
evaluators: [string]             # Required: List of evaluator names

# Task configurations
task_configs:                    # Required: List of configurations to test
  - name: string                 # Required: Configuration name
    description: string          # Required: Configuration description
    config: object               # Required: Task configuration

# Comparison settings
comparison_metrics:
  primary: string                # Required: Primary metric for ranking
  secondary: [string]            # Required: Secondary metrics
  threshold: float               # Optional: Minimum acceptable score

# Experiment settings
settings:
  max_concurrent_runs: int       # Optional: Max concurrent runs (default: 3)
  timeout_per_run: int           # Optional: Timeout per run in seconds (default: 300)
  save_intermediate_results: bool # Optional: Save intermediate results (default: true)
```

### Task Configuration

Each task configuration can include:

```yaml
config:
  model: string                  # Required: LLM model name
  temperature: float             # Required: Temperature setting
  max_tokens: int               # Required: Maximum tokens
  prompt_template: string       # Optional: Prompt template identifier
  # ... other task-specific parameters
```

### Available Evaluators

The following evaluators are available:

- `criteria_completeness`: Evaluates output completeness
- `criteria_accuracy`: Evaluates output accuracy
- `criteria_relevance`: Evaluates output relevance
- `criteria_clarity`: Evaluates output clarity
- `criteria_coherence`: Evaluates output coherence
- `qa`: Question-answer evaluation
- `embedding_distance`: Embedding-based similarity
- `string_distance`: String-based similarity
- `exact_match`: Exact string matching
- `json_validity`: JSON format validation

## Results and Reports

### Experiment Results

Results are saved to `reports/experiments/` with the following structure:

```json
{
  "experiment_name": "my_experiment",
  "started_at": "2025-08-07T10:00:00",
  "completed_at": "2025-08-07T10:15:00",
  "config": { /* experiment configuration */ },
  "task_results": {
    "baseline": {
      "workflow_operation_id": "exp_my_experiment_baseline_20250807_100000",
      "articles_processed": 10,
      "success_count": 9,
      "error_count": 1,
      "config_used": { /* task configuration */ }
    }
  },
  "evaluation_results": {
    "baseline": {
      "criteria_completeness": { "score": 0.85 },
      "criteria_accuracy": { "score": 0.92 }
    }
  },
  "summary": {
    "total_configurations": 3,
    "successful_runs": 3,
    "failed_runs": 0,
    "best_configuration": "baseline",
    "best_score": 0.85,
    "scores": {
      "baseline": 0.85,
      "high_temp": 0.78,
      "different_model": 0.82
    }
  }
}
```

### Comparison Reports

Comparison reports analyze multiple runs of the same experiment:

```json
{
  "experiment_name": "my_experiment",
  "total_runs": 5,
  "runs": [ /* individual run analyses */ ],
  "summary": {
    "total_runs": 5,
    "average_duration": 900.5,
    "best_overall_score": 0.87,
    "best_overall_config": "baseline",
    "most_consistent_config": "baseline",
    "config_performance": {
      "baseline": {
        "average_score": 0.85,
        "min_score": 0.82,
        "max_score": 0.87,
        "std_dev": 0.02,
        "runs_count": 5
      }
    }
  },
  "trends": {
    "score_trend": [ /* score progression over time */ ],
    "duration_trend": [ /* duration progression over time */ ],
    "success_rate_trend": [ /* success rate progression over time */ ]
  }
}
```

## LangSmith Integration

Experiments are automatically tracked in LangSmith:

- **Experiment Projects**: Each experiment creates a dedicated project
- **Run Tracking**: Individual task runs are tracked with configuration metadata
- **Evaluation Tracking**: Evaluation results are linked to task runs
- **Comparison**: LangSmith provides built-in comparison tools

### LangSmith Metadata

Each run includes metadata for tracking:

```python
metadata = {
    "experiment_name": "content_completeness_optimization",
    "config_name": "high_temp",
    "task_name": "ContentCompletenessLangChainTask",
    "model": "openai/gpt-4o-mini",
    "temperature": 0.3,
    "max_tokens": 1000,
    "evaluation_scores": {
        "criteria_completeness": 0.85,
        "criteria_accuracy": 0.92
    }
}
```

## Best Practices

### 1. Start Small

Begin with simple experiments testing 2-3 configurations:

```yaml
task_configs:
  - name: "baseline"
    config:
      model: "openai/gpt-4o-mini"
      temperature: 0
      max_tokens: 1000
  
  - name: "high_temp"
    config:
      model: "openai/gpt-4o-mini"
      temperature: 0.3
      max_tokens: 1000
```

### 2. Use Meaningful Names

Choose descriptive configuration names:

```yaml
- name: "gpt4_low_temp"      # Good
- name: "config_1"           # Avoid
```

### 3. Test One Variable at a Time

Focus on one parameter per experiment:

```yaml
# Test temperature variations
task_configs:
  - name: "temp_0"
    config: { temperature: 0 }
  - name: "temp_0.1"
    config: { temperature: 0.1 }
  - name: "temp_0.3"
    config: { temperature: 0.3 }
```

### 4. Use Representative Datasets

Choose datasets that represent your use case:

```yaml
evaluation_dataset: "production_articles"
evaluation_split: "validation"  # Use validation split for unbiased evaluation
```

### 5. Monitor Resource Usage

Set appropriate timeouts and concurrency limits:

```yaml
settings:
  max_concurrent_runs: 2      # Limit concurrent runs
  timeout_per_run: 600        # 10 minutes per run
```

## Troubleshooting

### Common Issues

1. **Configuration Validation Errors**
   - Check required fields in YAML
   - Verify dataset exists
   - Ensure evaluators are available

2. **Task Execution Failures**
   - Check API keys and quotas
   - Verify model names
   - Review task configuration

3. **Evaluation Errors**
   - Ensure dataset has sufficient examples
   - Check evaluator configuration
   - Verify LangSmith connectivity

### Debug Commands

```bash
# Validate configuration
poetry run python -m src.hex_machina.cli experiments run my_experiment --validate-only

# Check available evaluators
poetry run python -m src.hex_machina.cli evaluation list-evaluators

# List datasets
poetry run python -m src.hex_machina.cli datasets list
```

## Examples

### Example 1: Model Comparison

```yaml
experiment_name: "model_comparison"
description: "Compare different LLM models"
evaluation_dataset: "test-dataset"
evaluators: ["criteria_completeness", "criteria_accuracy"]

task_configs:
  - name: "gpt4_mini"
    config:
      model: "openai/gpt-4o-mini"
      temperature: 0
      max_tokens: 1000
  
  - name: "gpt35_turbo"
    config:
      model: "openai/gpt-3.5-turbo"
      temperature: 0
      max_tokens: 1000
  
  - name: "claude_haiku"
    config:
      model: "anthropic/claude-3-haiku"
      temperature: 0
      max_tokens: 1000
```

### Example 2: Temperature Optimization

```yaml
experiment_name: "temperature_optimization"
description: "Find optimal temperature setting"
evaluation_dataset: "creative_writing"
evaluators: ["criteria_creativity", "criteria_coherence"]

task_configs:
  - name: "temp_0"
    config: { temperature: 0, max_tokens: 1000 }
  - name: "temp_0.1"
    config: { temperature: 0.1, max_tokens: 1000 }
  - name: "temp_0.3"
    config: { temperature: 0.3, max_tokens: 1000 }
  - name: "temp_0.5"
    config: { temperature: 0.5, max_tokens: 1000 }
  - name: "temp_0.7"
    config: { temperature: 0.7, max_tokens: 1000 }
```

### Example 3: Prompt Template Testing

```yaml
experiment_name: "prompt_optimization"
description: "Test different prompt templates"
evaluation_dataset: "summarization"
evaluators: ["criteria_completeness", "criteria_conciseness"]

task_configs:
  - name: "template_simple"
    config:
      model: "openai/gpt-4o-mini"
      temperature: 0
      max_tokens: 1000
      prompt_template: "simple_summary"
  
  - name: "template_detailed"
    config:
      model: "openai/gpt-4o-mini"
      temperature: 0
      max_tokens: 1000
      prompt_template: "detailed_summary"
  
  - name: "template_structured"
    config:
      model: "openai/gpt-4o-mini"
      temperature: 0
      max_tokens: 1000
      prompt_template: "structured_summary"
```
