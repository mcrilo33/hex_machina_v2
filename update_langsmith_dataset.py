#!/usr/bin/env python3
"""Script to update LangSmith dataset with manual corrections from JSON file."""

import asyncio
import json
import logging
import os
import sys

# Load environment variables
from dotenv import load_dotenv

load_dotenv()

# Add the src directory to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "src"))

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def update_langsmith_dataset():
    """Update LangSmith dataset with manual corrections from JSON file."""

    print("🔄 Updating LangSmith Dataset with Manual Corrections")
    print("=" * 60)

    # Check API keys
    if not os.getenv("LANGSMITH_API_KEY"):
        print("❌ LANGSMITH_API_KEY not found in environment")
        print("   Please set LANGSMITH_API_KEY in your .env file")
        return

    # Load the JSON file
    json_file = "ground_truth_test_articles_2025-08-01_001_20250801_163011.json"

    if not os.path.exists(json_file):
        print(f"❌ JSON file not found: {json_file}")
        return

    print(f"📄 Loading corrections from: {json_file}")

    try:
        with open(json_file, "r") as f:
            data = json.load(f)
    except Exception as e:
        print(f"❌ Failed to load JSON file: {e}")
        return

    # Extract dataset information
    dataset_name = data.get("dataset_name")
    dataset_id = data.get("dataset_id")
    total_examples = data.get("total_examples", 0)
    examples = data.get("examples", [])

    print(f"📊 Dataset: {dataset_name}")
    print(f"🆔 Dataset ID: {dataset_id}")
    print(f"📈 Total Examples: {total_examples}")

    # Find manually reviewed examples
    manual_reviews = [ex for ex in examples if ex.get("human_review", False)]
    print(f"👀 Manual Reviews: {len(manual_reviews)}")

    if not manual_reviews:
        print("❌ No manual reviews found in the JSON file")
        return

    # Setup LangSmith
    from src.hex_machina.enrichment.evaluation.langsmith import (
        EvaluationDatasetManager,
        setup_langsmith_environment,
    )

    setup_langsmith_environment()
    dataset_manager = EvaluationDatasetManager(logger=logger)

    # Get the dataset
    dataset = dataset_manager.get_dataset(dataset_name)
    if not dataset:
        print(f"❌ Dataset not found in LangSmith: {dataset_name}")
        return

    print(f"✅ Found dataset in LangSmith: {dataset.name}")

    # Get all examples from the dataset
    from langsmith import Client

    client = Client()

    try:
        langsmith_examples = list(client.list_examples(dataset_id=dataset.id))
        print(f"📋 Found {len(langsmith_examples)} examples in LangSmith dataset")

        # Create a mapping of URL to LangSmith example
        url_to_example = {}
        for example in langsmith_examples:
            url = example.inputs.get("url")
            if url:
                url_to_example[url] = example

        print(f"🔗 Created URL mapping for {len(url_to_example)} examples")

        # Update examples with manual corrections
        updated_count = 0
        errors = []

        for manual_review in manual_reviews:
            url = manual_review.get("url")
            if not url:
                continue

            if url not in url_to_example:
                errors.append(f"URL not found in LangSmith dataset: {url}")
                continue

            example = url_to_example[url]

            # Prepare updated outputs and metadata
            updated_outputs = {
                "is_complete": manual_review.get("is_complete", False),
                "detected_issues": manual_review.get("detected_issues", []),
            }

            updated_metadata = {
                "human_labeled": "true",
                "requires_manual_review": manual_review.get(
                    "requires_manual_review", False
                ),
                "confidence": manual_review.get("confidence", "high"),
                "evaluation_method": "manual_review",
                "evaluation_prompt": "manual_feedback",
                "evaluation_model": "human_expert",
                "feedback_source": "langsmith_manual_review",
                "notes": f"Manual review completed - {manual_review.get('title', 'No title')}",
                "content_length": manual_review.get("content_length", 0),
                "content_start": manual_review.get("content_start", ""),
                "content_end": manual_review.get("content_end", ""),
            }

            try:
                # Update the example
                client.update_example(
                    example_id=example.id,
                    outputs=updated_outputs,
                    metadata=updated_metadata,
                )

                updated_count += 1
                print(f"✅ Updated: {url}")

            except Exception as e:
                error_msg = f"Failed to update {url}: {e}"
                errors.append(error_msg)
                print(f"❌ {error_msg}")

        # Summary
        print("\n📊 Update Summary:")
        print(f"   Total manual reviews: {len(manual_reviews)}")
        print(f"   Successfully updated: {updated_count}")
        print(f"   Errors: {len(errors)}")

        if errors:
            print("\n❌ Errors encountered:")
            for error in errors[:10]:  # Show first 10 errors
                print(f"   - {error}")
            if len(errors) > 10:
                print(f"   ... and {len(errors) - 10} more errors")

        if updated_count > 0:
            print(
                f"\n✅ Successfully updated {updated_count} examples in LangSmith dataset"
            )
            print("📊 View updated dataset at: https://smith.langchain.com/")
            print(f"   Dataset: {dataset.name}")

    except Exception as e:
        print(f"❌ Failed to update dataset: {e}")
        import traceback

        traceback.print_exc()


async def show_manual_review_summary():
    """Show a summary of manual reviews in the JSON file."""

    json_file = "ground_truth_test_articles_2025-08-01_001_20250801_163011.json"

    if not os.path.exists(json_file):
        print(f"❌ JSON file not found: {json_file}")
        return

    try:
        with open(json_file, "r") as f:
            data = json.load(f)
    except Exception as e:
        print(f"❌ Failed to load JSON file: {e}")
        return

    examples = data.get("examples", [])
    manual_reviews = [ex for ex in examples if ex.get("human_review", False)]

    print("📊 Manual Review Summary")
    print("=" * 40)
    print(f"Total examples: {len(examples)}")
    print(f"Manual reviews: {len(manual_reviews)}")
    print(f"Review percentage: {len(manual_reviews)/len(examples)*100:.1f}%")

    # Analyze corrections
    corrections = {
        "is_complete_changes": 0,
        "requires_manual_review_changes": 0,
        "detected_issues_changes": 0,
    }

    for review in manual_reviews:
        url = review.get("url", "unknown")
        is_complete = review.get("is_complete", False)
        requires_review = review.get("requires_manual_review", False)
        issues = review.get("detected_issues", [])

        print(f"\n🔍 {url}")
        print(f"   Complete: {is_complete}")
        print(f"   Requires Review: {requires_review}")
        print(f"   Issues: {issues}")

    print("\n📈 Summary:")
    print(f"   Manual reviews completed: {len(manual_reviews)}")
    print("   Ready for LangSmith update")


async def main():
    """Main function."""
    print("🔄 LangSmith Dataset Update Tool")
    print("=" * 50)

    # Show available options
    print("\nAvailable actions:")
    print("1. Show manual review summary")
    print("2. Update LangSmith dataset")
    print("3. Exit")

    choice = input("\nSelect action (1-3): ").strip()

    if choice == "1":
        await show_manual_review_summary()
    elif choice == "2":
        await update_langsmith_dataset()
    elif choice == "3":
        print("👋 Goodbye!")
    else:
        print("❌ Invalid choice")


if __name__ == "__main__":
    asyncio.run(main())
