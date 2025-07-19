# Hex Machina v2

◉ Hex Machina v2 – An AI-driven recurrent digest of the latest AI research and news.

## Overview

Hex Machina is a free, AI-driven newsletter service that automatically monitors AI research, blogs, and announcements, summarizes key insights, and delivers high-quality, concise newsletters.

**AI News, Compiled by the Machine.** You can find the newsletter at: https://hexmachina.beehiiv.com/

## Features

- **Ingestion**: Ingests articles from AI-related websites
- **Article Enrichment**: Adds tags, summaries, and metadata
- **Selection**: Selects most relevant items using unsupervised methods
- **Newsletter Generation**: Compiles and formats weekly updates
- **Orchestration**: Runs the full pipeline automatically

## Technology Stack

- **Python**: 3.10+
- **Dependency Management**: Poetry
- **Code Quality**: Ruff (formatting, linting, import sorting)
- **Type Checking**: Strict typing with `typing` module
- **Testing**: pytest
- **Documentation**: Google-style docstrings
- **Async Programming**: `async`/`await` patterns
- **Web Framework**: FastAPI
- **LLM Framework**: LangChain, LangGraph, LangSmith
- **Vector Database**: PostgreSQL + pgvector
- **Workflow Orchestration**: Prefect3 + ControlFlow
- **Containerization**: Docker & Docker Compose

## Project Structure

```
hex_machina_v2/
├── src/
│   ├── hex_machina/
│   │   ├── __init__.py
│   │   ├── ingestion/
│   │   ├── enrichment/
│   │   ├── selection/
│   │   ├── generation/
│   │   └── orchestration/
│   └── tests/
├── config/
├── docker/
├── scripts/
├── docs/
├── .github/
│   └── workflows/
├── pyproject.toml
├── Dockerfile
├── docker-compose.yml
└── README.md
```

## Quick Start

### Prerequisites

- Python 3.10+
- Poetry
- Docker & Docker Compose (optional)

### Installation

1. Clone the repository:
```bash
git clone https://github.com/mcrilo33/hex_machina_v2.git
cd hex_machina_v2
```

2. Install dependencies:
```bash
poetry install
```

3. Set up environment variables:
```bash
cp .env.example .env
# Edit .env with your API keys
```

## Development

### Code Quality

- **Formatting**: `poetry run ruff format`
- **Linting**: `poetry run ruff check`
- **Type Checking**: `poetry run mypy src/`
- **Testing**: `poetry run pytest`

### Pre-commit Hooks

Install pre-commit hooks:
```bash
poetry run pre-commit install
```

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Run tests and quality checks
5. Submit a pull request

## License

The code is public, you can look at it, but this software is proprietary and owned by **Mathieu Crilout**.  
Unauthorized use, distribution, or modification is prohibited.

## Contact

For questions or contributions, contact **Mathieu Crilout** at <mathieu.crilout@gmail.com>.