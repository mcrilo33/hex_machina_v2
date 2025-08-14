#!/usr/bin/env python3
"""
LangSmith Dataset Cleanup Script

This script removes all LangSmith datasets created after a specified date.
Useful for cleaning up old experiment datasets and managing storage.

Usage:
    python scripts/cleanup_langsmith_datasets.py --after-date 2024-01-01
    python scripts/cleanup_langsmith_datasets.py --after-date 2024-01-01 --dry-run
    python scripts/cleanup_langsmith_datasets.py --after-date 2024-01-01 --confirm
"""

import argparse
import os
import sys
from datetime import datetime, timezone
from typing import List

# Add the src directory to the path so we can import our modules
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

# Load environment variables from .env file
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    print("Warning: python-dotenv not found. Install it with: poetry add python-dotenv")
    print("Continuing without .env file support...")

try:
    from langsmith import Client
except ImportError:
    print("Error: langsmith package not found. Install it with: poetry add langsmith")
    sys.exit(1)


def parse_date(date_string: str) -> datetime:
    """Parse date string into datetime object.

    Args:
        date_string: Date string in YYYY-MM-DD format

    Returns:
        datetime object

    Raises:
        ValueError: If date format is invalid
    """
    try:
        # Parse the date and set it to midnight UTC
        parsed_date = datetime.strptime(date_string, "%Y-%m-%d")
        return parsed_date.replace(tzinfo=timezone.utc)
    except ValueError as e:
        raise ValueError(
            f"Invalid date format: {date_string}. Use YYYY-MM-DD format."
        ) from e


def get_datasets_after_date(client: Client, after_date: datetime) -> List[dict]:
    """Get all datasets created after the specified date.

    Args:
        client: LangSmith client
        after_date: Datetime to filter datasets after

    Returns:
        List of dataset dictionaries
    """
    print(
        f"Fetching datasets created after {after_date.strftime('%Y-%m-%d %H:%M:%S UTC')}..."
    )

    datasets = []
    try:
        # Get all datasets
        all_datasets = client.list_datasets()

        for dataset in all_datasets:
            # Check if dataset has creation date and it's after our threshold
            if hasattr(dataset, "created_at") and dataset.created_at:
                if dataset.created_at > after_date:
                    datasets.append(
                        {
                            "id": dataset.id,
                            "name": dataset.name,
                            "created_at": dataset.created_at,
                            "description": getattr(
                                dataset, "description", "No description"
                            ),
                        }
                    )

        print(f"Found {len(datasets)} datasets created after the specified date.")

    except Exception as e:
        print(f"Error fetching datasets: {e}")
        return []

    return datasets


def delete_dataset(client: Client, dataset_id: str, dataset_name: str) -> bool:
    """Delete a specific dataset.
    
    Args:
        client: LangSmith client
        dataset_id: ID of the dataset to delete
        dataset_name: Name of the dataset for logging
        
    Returns:
        True if successful, False otherwise
    """
    try:
        # Use dataset_id for deletion
        client.delete_dataset(dataset_id=dataset_id)
        print(f"✅ Deleted dataset: {dataset_name} ({dataset_id})")
        return True
    except Exception as e:
        print(f"❌ Failed to delete dataset {dataset_name} ({dataset_id}): {e}")
        return False


def cleanup_datasets(
    client: Client, datasets: List[dict], dry_run: bool = False, confirm: bool = False
) -> None:
    """Clean up datasets by deleting them.

    Args:
        client: LangSmith client
        datasets: List of datasets to delete
        dry_run: If True, only show what would be deleted
        confirm: If True, skip confirmation prompt
    """
    if not datasets:
        print("No datasets to delete.")
        return

    if dry_run:
        print("\n🔍 DRY RUN MODE - No datasets will be deleted")
        print("Datasets that would be deleted:")
        for dataset in datasets:
            created_str = dataset["created_at"].strftime("%Y-%m-%d %H:%M:%S UTC")
            print(f"  - {dataset['name']} (created: {created_str})")
        return

    # Show datasets to be deleted
    print(f"\n🗑️  About to delete {len(datasets)} datasets:")
    for dataset in datasets:
        created_str = dataset["created_at"].strftime("%Y-%m-%d %H:%M:%S UTC")
        print(f"  - {dataset['name']} (created: {created_str})")

    # Confirmation prompt
    if not confirm:
        response = input(
            f"\n⚠️  Are you sure you want to delete {len(datasets)} datasets? (yes/no): "
        )
        if response.lower() not in ["yes", "y"]:
            print("Operation cancelled.")
            return

    # Delete datasets
    print(f"\n🗑️  Deleting {len(datasets)} datasets...")
    successful_deletions = 0

    for dataset in datasets:
        if delete_dataset(client, dataset["id"], dataset["name"]):
            successful_deletions += 1

    print(
        f"\n✅ Cleanup complete! Successfully deleted {successful_deletions}/{len(datasets)} datasets."
    )


def main():
    """Main function to run the dataset cleanup."""
    parser = argparse.ArgumentParser(
        description="Clean up LangSmith datasets created after a specific date",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Show what would be deleted (dry run)
  python scripts/cleanup_langsmith_datasets.py --after-date 2024-01-01 --dry-run
  
  # Delete datasets with confirmation prompt
  python scripts/cleanup_langsmith_datasets.py --after-date 2024-01-01
  
  # Delete datasets without confirmation
  python scripts/cleanup_langsmith_datasets.py --after-date 2024-01-01 --confirm
        """,
    )

    parser.add_argument(
        "--after-date",
        required=True,
        help="Date in YYYY-MM-DD format. Datasets created after this date will be deleted.",
    )

    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be deleted without actually deleting anything",
    )

    parser.add_argument(
        "--confirm",
        action="store_true",
        help="Skip confirmation prompt (use with caution!)",
    )

    args = parser.parse_args()

    # Parse the date
    try:
        after_date = parse_date(args.after_date)
    except ValueError as e:
        print(f"Error: {e}")
        sys.exit(1)

    # Check for LangSmith API key
    if not os.getenv("LANGCHAIN_API_KEY"):
        print("Error: LANGCHAIN_API_KEY environment variable not set.")
        print("\nTo fix this, you have several options:")
        print("\n1. Create a .env file in your project root:")
        print("   echo 'LANGCHAIN_API_KEY=your-api-key-here' > .env")
        print("\n2. Set the environment variable manually:")
        print("   export LANGCHAIN_API_KEY='your-api-key-here'")
        print("\n3. Install python-dotenv if not already installed:")
        print("   poetry add python-dotenv")
        print("\nThe .env file approach is recommended for development.")
        sys.exit(1)

    # Initialize LangSmith client
    try:
        client = Client()
        print("✅ Connected to LangSmith")
    except Exception as e:
        print(f"Error connecting to LangSmith: {e}")
        sys.exit(1)

    # Get datasets after the specified date
    datasets = get_datasets_after_date(client, after_date)

    if not datasets:
        print("No datasets found to delete.")
        return

    # Clean up datasets
    cleanup_datasets(client, datasets, dry_run=args.dry_run, confirm=args.confirm)


if __name__ == "__main__":
    main()
