# Hex Machina v2 - CLI Structure

## Overview

Hex Machina v2 provides a comprehensive CLI system organized by functionality. Each CLI is designed to handle specific aspects of the AI-driven newsletter service.

## CLI Architecture

```
src/hex_machina/cli/
├── __init__.py          # Main CLI dispatcher
├── __main__.py          # Entry point (currently tasks CLI)
├── master.py            # Master CLI dispatcher (future)
├── tasks/               # Task management CLI ✅
├── workflows/           # Workflow orchestration CLI 🔄
├── datasets/            # Dataset management CLI 🔄
├── prompts/             # Prompt management CLI 🔄
└── evaluation/          # Evaluation CLI 🔄
```

## Current CLIs

### ✅ Tasks CLI (`tasks`)

**Purpose**: Run and manage enrichment tasks with LangChain and LangSmith integration.

**Usage**:
```bash
# Direct usage
python -m src.hex_machina.cli --help

# Commands
python -m src.hex_machina.cli list-tasks
python -m src.hex_machina.cli run --task ContentCompletenessLangChainTask --input input.json
python -m src.hex_machina.cli stats
python -m src.hex_machina.cli list-runs
python -m src.hex_machina.cli show-run <task_id>
```

**Features**:
- ✅ Task execution with JSON input/output
- ✅ LangSmith tracing and observability
- ✅ Local database storage
- ✅ Task statistics and monitoring
- ✅ YAML configuration support
- ✅ Error handling and logging

## Planned CLIs

### 🔄 Workflows CLI (`workflows`)

**Purpose**: Orchestrate complex workflows using LangGraph.

**Planned Commands**:
```bash
hex-machina workflows run --workflow newsletter-generation --config config.yaml
hex-machina workflows list
hex-machina workflows show <workflow_id>
hex-machina workflows monitor
```

**Features**:
- LangGraph workflow orchestration
- Workflow state management
- Parallel execution
- Workflow monitoring and debugging

### 🔄 Datasets CLI (`datasets`)

**Purpose**: Manage datasets for training and evaluation.

**Planned Commands**:
```bash
hex-machina datasets create --name my-dataset --source task-runs
hex-machina datasets list
hex-machina datasets export --name my-dataset --format json
hex-machina datasets sync --name my-dataset --langsmith
```

**Features**:
- Dataset creation from task runs
- LangSmith dataset synchronization
- Dataset versioning
- Export/import functionality

### 🔄 Prompts CLI (`prompts`)

**Purpose**: Manage prompt templates and versions.

**Planned Commands**:
```bash
hex-machina prompts create --name content-completeness --template template.txt
hex-machina prompts list
hex-machina prompts version --name content-completeness --version 2.0
hex-machina prompts sync --langsmith
```

**Features**:
- Prompt template management
- Version control
- LangSmith prompt sync
- Template validation

### 🔄 Evaluation CLI (`evaluation`)

**Purpose**: Run evaluation experiments and metrics.

**Planned Commands**:
```bash
hex-machina evaluation run --experiment completeness-eval --dataset test-data
hex-machina evaluation list
hex-machina evaluation compare --experiment1 exp1 --experiment2 exp2
hex-machina evaluation report --experiment exp1 --format html
```

**Features**:
- Evaluation experiment management
- Custom metrics
- Experiment comparison
- Report generation

## Usage Examples

### Current Usage (Tasks CLI)

```bash
# List available tasks
python -m src.hex_machina.cli list-tasks

# Run a task with JSON input
python -m src.hex_machina.cli run \
  --task ContentCompletenessLangChainTask \
  --input '{"title": "Test", "content": "..."}' \
  --config content_completeness

# View statistics
python -m src.hex_machina.cli stats

# Show specific run
python -m src.hex_machina.cli show-run task_abc123
```

### Future Usage (Master CLI)

```bash
# Master CLI (when implemented)
hex-machina --help
hex-machina tasks list-tasks
hex-machina workflows run --workflow newsletter
hex-machina datasets create --name training-data
hex-machina prompts create --name evaluation-prompt
hex-machina evaluation run --experiment completeness
```

## LangSmith Integration

All CLIs are designed to integrate with LangSmith for:

- **Tracing**: Complete execution traces
- **Monitoring**: Performance and success metrics
- **Debugging**: Error analysis and debugging
- **Collaboration**: Sharing experiments and results

## Configuration

Each CLI supports:

- **Environment Variables**: API keys, project names
- **YAML Configuration**: Task and workflow configs
- **Local Storage**: Input/output persistence
- **Logging**: Verbose and structured logging

## Development Status

- ✅ **Tasks CLI**: Fully implemented and tested
- 🔄 **Workflows CLI**: Planned (LangGraph integration)
- 🔄 **Datasets CLI**: Planned (LangSmith dataset sync)
- 🔄 **Prompts CLI**: Planned (Prompt versioning)
- 🔄 **Evaluation CLI**: Planned (Evaluation experiments)

## Next Steps

1. **Implement Workflows CLI** with LangGraph integration
2. **Implement Datasets CLI** with LangSmith dataset sync
3. **Implement Prompts CLI** with version control
4. **Implement Evaluation CLI** with custom metrics
5. **Create Master CLI** to unify all CLIs
6. **Add comprehensive testing** for all CLIs 