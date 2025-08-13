# Hex Machina v2

AI-driven newsletter service that automatically monitors AI research and delivers concise summaries.

## Quick Start (No Docker, No Postgres)

### 1. Install Python dependencies
```bash
poetry install --only=main,dev
```

### 2. Set environment variables (optional)
```bash
# Example: (customize as needed)
export APP_NAME="Hex Machina v2"
export APP_VERSION="0.1.0"
```

### 3. Set API keys for LangChain Tasks
```bash
# Create a .env file with your API keys
echo "OPENAI_API_KEY=your-openai-api-key-here" > .env
echo "OPENROUTER_API_KEY=your-openrouter-api-key-here" >> .env
echo "ANTHROPIC_API_KEY=your-anthropic-api-key-here" >> .env

# Or source an existing .env file
source .env
```

**Note:** The LangChain Tasks CLI requires API keys to be available as environment variables. Make sure to set them before running any tasks that use LLM runnables.

### 4. Run the Ingestion Pipeline
```bash
poetry run python -m src.hex_machina.ingestion.ingestion_script --config tests/data/testing_scraping_config.yaml --verbose
```
- The pipeline is modular: all DB logic is in the storage module, and scrapers are fully decoupled from storage.
- Playwright-based scrapers can be configured via the YAML config (`scrapers.playwright.launch_args`).
- Ingestion metadata (including git commit, branch, and repo) is tracked for every run.

### 5. Run LangChain Tasks
```bash
# Run a single task
poetry run python -m src.hex_machina.langchain_tasks run -c configs/tasks/example_task.yaml

# Run with specific article ID
poetry run python -m src.hex_machina.langchain_tasks run -c configs/tasks/example_task.yaml --article-id 123

# Run an experiment
poetry run python -m src.hex_machina.langchain_tasks experiment -c configs/experiments/example_experiment.yaml
```

### 6. Run the End-to-End Test Workflow
```bash
python tests/data/run_ingestion_with_local_server.py
```
- This script:
  - Starts a local HTTP server for test HTML files
  - Updates the test feed to use `http://localhost:8000/` URLs
  - Runs the ingestion pipeline
  - Runs pytest to verify the ingested data (deduplication, error handling, metadata, etc.)
  - Cleans up the test DB and server

## Configuration
- **Test feeds:** Located in `tests/data/test_feed.xml` (edit or regenerate as needed)
- **Playwright launch args:** Set in `tests/data/testing_scraping_config.yaml` under `scrapers.playwright.launch_args`
- **Database path:** Set in the config under `global.db_path`
- **Task configurations:** Located in `configs/tasks/` directory
- **Experiment configurations:** Located in `configs/experiments/` directory

## Features
- Modular ingestion pipeline with pluggable storage (DuckDB + SQLAlchemy)
- Robust error handling and deduplication
- Per-article and per-run metadata, including git provenance
- Configurable Playwright browser flags for local and CI testing
- Automated end-to-end test with local server and pytest
- **LangChain Tasks CLI** for running AI-powered workflows
- **Article processing pipeline** with ArticleFetcher and EnrichmentSaver
- **Dataset generation** for training and evaluation

## Local Development
- No Docker or database server required.
- All storage is local and file-based for fast iteration.
- Test and dev artifacts (`.db`, `.bak`, etc.) are ignored via `.gitignore`.
- API keys are managed via environment variables or `.env` files.

## Troubleshooting

### Environment Variables Not Loading
If you encounter API key errors when running LangChain tasks, ensure your environment variables are properly loaded:

```bash
# Method 1: Export directly
export OPENAI_API_KEY="your-api-key-here"

# Method 2: Source .env file (recommended)
source .env

# Method 3: Load all variables from .env
export $(cat .env | xargs)

# Method 4: Use the helper script
source scripts/load_env.sh

# Verify the variable is set
echo $OPENAI_API_KEY
```

### Common Error: "api_key client option must be set"
This error occurs when the `OPENAI_API_KEY` environment variable is not available. Make sure to:
1. Set the environment variable before running the task
2. Use `source .env` instead of just `cat .env`
3. Verify the variable is loaded with `echo $OPENAI_API_KEY`

## Git Metadata
- Every ingestion run records the current git commit, branch, and repo in the `IngestionOperation` table for reproducibility and auditability.

## Error Handling
- All errors (connection, HTTP status, parsing, etc.) are tracked per article in the database for easy debugging and analysis.

---

**Ready to push your first version!**
