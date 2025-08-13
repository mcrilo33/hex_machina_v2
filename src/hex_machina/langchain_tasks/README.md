# LangChain Tasks CLI

A simple command-line interface for running LangChain tasks and experiments from YAML configuration files.

## Overview

The CLI follows LangChain's philosophy of simplicity and explicit configuration. Everything is configured in YAML files, and the CLI provides a minimal interface to execute tasks and experiments.

## Installation

The CLI is part of the `langchain_tasks` package and can be run directly as a module using poetry:

```bash
# Run as module with poetry
poetry run python -m src.hex_machina.langchain_tasks <command> [options]
```

## Commands

### `run` - Execute a Single Task

Run a single task from a YAML configuration file.

```bash
# Basic usage
poetry run python -m src.hex_machina.langchain_tasks run -c configs/enrichment/tasks/content_completeness.yaml

# With specific article ID
poetry run python -m src.hex_machina.langchain_tasks run -c configs/enrichment/tasks/content_completeness.yaml --article-id 123
```

**Options:**
- `-c, --config`: Path to task YAML config file (required)
- `--article-id`: Article ID from database (optional)

### `experiment` - Run Experiments

Run experiments with multiple task variations from a YAML configuration file.

```bash
# Basic usage
poetry run python -m src.hex_machina.langchain_tasks experiment -c configs/ingestion/experiments/content_completeness_optimization.yaml

# With test inputs
poetry run python -m src.hex_machina.langchain_tasks experiment -c configs/ingestion/experiments/content_completeness_optimization.yaml --input-file test_inputs.json
```

**Options:**
- `-c, --config`: Path to experiment YAML config file (required)
- `--input-file`: JSON file with test inputs (optional)

## Configuration Files

### Task Configuration

Tasks are defined in YAML files with the following structure:

```yaml
name: ContentCompletenessTask
description: "Evaluate content completeness using LangChain"
steps:
  - name: fetch_article
    runnable: article_fetcher
    config:
      database_path: "storage/articles.db"
  
  - name: evaluate_completeness
    runnable: content_completeness_evaluator
    config:
      model: "anthropic/claude-3.5-sonnet"
      temperature: 0.0
```

### Experiment Configuration

Experiments are defined in YAML files that specify multiple task variations:

```yaml
name: content_completeness_optimization
description: "Test different model configurations for content completeness"
task:
  name: ContentCompletenessTask
  steps:
    - name: fetch_article
      runnable: article_fetcher
      config:
        database_path: "storage/articles.db"
    
    - name: evaluate_completeness
      runnable: content_completeness_evaluator
      config:
        model: ["anthropic/claude-3.5-sonnet", "openai/gpt-4o-mini"]
        temperature: [0.0, 0.1, 0.3]
```

## Examples

### Running a Content Completeness Task

```bash
# Run the task
poetry run python -m src.hex_machina.langchain_tasks run -c configs/enrichment/tasks/content_completeness.yaml

# Output:
# 2025-01-27 10:30:00 - langchain_tasks.cli.run - INFO - Running task from config: configs/enrichment/tasks/content_completeness.yaml
# 2025-01-27 10:30:00 - langchain_tasks.cli.run - INFO - Loaded configuration: ContentCompletenessTask
# 2025-01-27 10:30:00 - langchain_tasks.cli.run - INFO - Executing task...
# 2025-01-27 10:30:00 - langchain_tasks.cli.run - INFO - Task completed successfully
```

### Running an Experiment

```bash
# Run the experiment
poetry run python -m src.hex_machina.langchain_tasks experiment -c configs/ingestion/experiments/content_completeness_optimization.yaml

# Output:
# 2025-01-27 10:30:00 - langchain_tasks.cli.experiment - INFO - Running experiment from config: configs/ingestion/experiments/content_completeness_optimization.yaml
# 2025-01-27 10:30:00 - langchain_tasks.cli.experiment - INFO - Loaded experiment configuration: content_completeness_optimization
# 2025-01-27 10:30:00 - langchain_tasks.cli.experiment - INFO - Executing experiment...
# 2025-01-27 10:30:00 - langchain_tasks.cli.experiment - INFO - Experiment completed successfully
# 2025-01-27 10:30:00 - langchain_tasks.cli.experiment - INFO - Total variations: 6
# 2025-01-27 10:30:00 - langchain_tasks.cli.experiment - INFO - Datasets created: 6
```

## Error Handling

The CLI follows a fail-fast approach:

- **Configuration validation**: YAML files are validated before execution
- **File existence**: Config and input files must exist and be readable
- **YAML parsing**: Invalid YAML files will cause immediate failure
- **Task execution**: Errors in task execution are logged and cause CLI failure

## Logging

The CLI uses Python's standard logging module with:

- **Level**: INFO by default
- **Format**: Timestamp, logger name, level, and message
- **Output**: Standard output (stdout)
- **Integration**: Uses existing logger names from the langchain_tasks system

## Philosophy

This CLI embodies LangChain's core principles:

1. **Explicit over Implicit**: All configurations must be explicit in YAML files
2. **Simple Interface**: Minimal CLI surface area, rich configuration files
3. **Fail Fast**: Immediate error reporting with clear context
4. **Composable**: Tasks can be chained and composed through configuration
5. **Observable**: Built-in logging for execution visibility

## Troubleshooting

### Common Issues

1. **File not found**: Ensure the config file path is correct and the file exists
2. **Invalid YAML**: Check YAML syntax using a YAML validator
3. **Missing dependencies**: Ensure all required runnables are registered
4. **Permission errors**: Check file read permissions

### Debug Mode

For more detailed logging, you can modify the logging level in the CLI code:

```python
logging.basicConfig(level=logging.DEBUG)
```

## Development

The CLI is designed to be easily extensible. To add new commands:

1. Add the command function to `cli.py`
2. Add the command parser in the `main()` function
3. Update tests in `tests/test_langchain_tasks_cli.py`
4. Update this README with usage examples

## Testing

Run the CLI tests using poetry:

```bash
# Run all tests
poetry run pytest tests/test_langchain_tasks_cli.py

# Run with verbose output
poetry run pytest tests/test_langchain_tasks_cli.py -v
```
