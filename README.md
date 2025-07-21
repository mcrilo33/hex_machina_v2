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

### 3. Run the Ingestion Pipeline
```bash
poetry run python -m src.hex_machina.ingestion.ingestion_script --config tests/data/testing_scraping_config.yaml --verbose
```
- The pipeline is modular: all DB logic is in the storage module, and scrapers are fully decoupled from storage.
- Playwright-based scrapers can be configured via the YAML config (`scrapers.playwright.launch_args`).
- Ingestion metadata (including git commit, branch, and repo) is tracked for every run.

### 4. Run the End-to-End Test Workflow
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

## Features
- Modular ingestion pipeline with pluggable storage (DuckDB + SQLAlchemy)
- Robust error handling and deduplication
- Per-article and per-run metadata, including git provenance
- Configurable Playwright browser flags for local and CI testing
- Automated end-to-end test with local server and pytest

## Local Development
- No Docker or database server required.
- All storage is local and file-based for fast iteration.
- Test and dev artifacts (`.db`, `.bak`, etc.) are ignored via `.gitignore`.

## Git Metadata
- Every ingestion run records the current git commit, branch, and repo in the `IngestionOperation` table for reproducibility and auditability.

## Error Handling
- All errors (connection, HTTP status, parsing, etc.) are tracked per article in the database for easy debugging and analysis.

---

**Ready to push your first version!**
