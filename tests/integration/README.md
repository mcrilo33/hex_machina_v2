# Integration Tests for Hex Machina Ingestion

This directory contains integration (end-to-end) tests for the ingestion pipeline.

## Structure

- `test_ingestion_e2e.py` (standalone script):
  - Orchestrates a full ingestion run using a local HTTP server and test feeds.
  - Runs the pipeline and verifies results using pytest.
- `integration_scraping_config.yaml`: Scrapy and scraper config for integration tests.
- `data/`: Contains test RSS feeds and other data files used by the integration tests.

## How to Run

From the project root:

```sh
python tests/integration/test_ingestion_e2e.py
```

## Notes
- The script will start a local HTTP server on port 8000 and clean up the test database after running.
- Make sure no other process is using port 8000.
- The test config and data files are designed to be self-contained and not affect production data. 