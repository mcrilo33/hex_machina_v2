# Scripts Directory

This directory contains utility scripts for managing and maintaining the hex_machina project.

## Available Scripts

### cleanup_langsmith_datasets.py

A utility script to clean up LangSmith datasets created after a specific date. Useful for managing storage and removing old experiment datasets.

#### Prerequisites

- Python 3.7+
- Poetry for dependency management
- `langsmith` package installed via Poetry
- `python-dotenv` package for environment variable management
- `LANGCHAIN_API_KEY` environment variable set (preferably via .env file)

#### Installation

```bash
# Install required packages using Poetry
poetry add langsmith python-dotenv

# Create a .env file in your project root
echo 'LANGCHAIN_API_KEY=your-api-key-here' > .env

# Or manually set the environment variable
export LANGCHAIN_API_KEY='your-api-key-here'
```

#### Environment Setup (Recommended)

The script automatically loads environment variables from a `.env` file in your project root. This is the recommended approach for development:

1. **Create a .env file** in your project root:
   ```bash
   echo 'LANGCHAIN_API_KEY=your-actual-api-key-here' > .env
   ```

2. **Add .env to .gitignore** (if not already there):
   ```bash
   echo '.env' >> .gitignore
   ```

3. **Never commit your .env file** - it contains sensitive information!

4. **The script will automatically detect and load** the API key from the .env file.

**Note**: The .env file approach is safer and more convenient than manually setting environment variables each time.

#### Usage

```bash
# Show what would be deleted (dry run - recommended first step)
poetry run python scripts/cleanup_langsmith_datasets.py --after-date 2024-01-01 --dry-run

# Delete datasets with confirmation prompt
poetry run python scripts/cleanup_langsmith_datasets.py --after-date 2024-01-01

# Delete datasets without confirmation (use with caution!)
poetry run python scripts/cleanup_langsmith_datasets.py --after-date 2024-01-01 --confirm
```

#### Options

- `--after-date`: Required. Date in YYYY-MM-DD format. Datasets created after this date will be deleted.
- `--dry-run`: Optional. Show what would be deleted without actually deleting anything.
- `--confirm`: Optional. Skip confirmation prompt (use with caution!).

#### Examples

```bash
# Clean up datasets from 2024
poetry run python scripts/cleanup_langsmith_datasets.py --after-date 2024-01-01 --dry-run

# Clean up datasets from last month
poetry run python scripts/cleanup_langsmith_datasets.py --after-date 2024-11-01 --dry-run

# Actually delete datasets from 2024 (with confirmation)
poetry run python scripts/cleanup_langsmith_datasets.py --after-date 2024-01-01
```

#### Safety Features

- **Dry Run Mode**: Always use `--dry-run` first to see what would be deleted
- **Confirmation Prompt**: Script asks for confirmation before deleting (unless `--confirm` is used)
- **Detailed Logging**: Shows exactly what datasets are being deleted
- **Error Handling**: Continues processing even if some deletions fail

#### What It Does

1. Connects to LangSmith using your API key
2. Fetches all datasets created after the specified date
3. Shows you which datasets will be deleted
4. Asks for confirmation (unless `--confirm` is used)
5. Deletes the datasets and reports results

#### Warning

⚠️ **This script permanently deletes datasets from LangSmith. There is no undo!**

- Always use `--dry-run` first to verify what will be deleted
- Make sure you have backups if needed
- Double-check the date parameter before running
- Consider the impact on any ongoing experiments or evaluations
