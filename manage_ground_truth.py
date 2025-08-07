#!/usr/bin/env python3
"""Script to manage ground truth data for LangSmith datasets."""

import asyncio
import json
import logging
import os
import sys
from datetime import datetime

# Load environment variables
from dotenv import load_dotenv

load_dotenv()

# Add the src directory to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "src"))

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def export_ground_truth(dataset_name: str, output_file: str = None):
    """Export ground truth data from a LangSmith dataset.

    Args:
        dataset_name: Name of the dataset to export.
        output_file: Output file path. If None, uses default naming.
    """
    print(f"📤 Exporting ground truth from dataset: {dataset_name}")
    print("=" * 60)

    # Import required modules
    from src.hex_machina.enrichment.evaluation.langsmith import (
        EvaluationDatasetManager,
        setup_langsmith_environment,
    )

    # Setup LangSmith
    setup_langsmith_environment()
    dataset_manager = EvaluationDatasetManager(logger=logger)

    # Get the dataset
    dataset = dataset_manager.get_dataset(dataset_name)
    if not dataset:
        print(f"❌ Dataset '{dataset_name}' not found")
        return

    print(f"✅ Found dataset: {dataset.name}")
    print(f"   ID: {dataset.id}")
    print(f"   Examples: {dataset.example_count}")

    # Get all examples
    examples = list(dataset_manager.client.list_examples(dataset_id=dataset.id))
    print(f"📊 Loading {len(examples)} examples...")

    # Export data
    export_data = {
        "dataset_name": dataset_name,
        "dataset_id": str(dataset.id),  # Convert UUID to string
        "exported_at": datetime.now().isoformat(),
        "total_examples": len(examples),
        "examples": [],
    }

    for i, example in enumerate(examples, 1):
        if i % 50 == 0:
            print(f"   Processed {i}/{len(examples)} examples...")

        # Get content and create preview sections
        full_content = example.inputs.get("content", "")
        content_length = len(full_content)

        if content_length <= 2000:
            # If content is short, use full content for both sections
            content_start = full_content
            content_end = full_content
        else:
            # Get first 1000 and last 1000 characters
            content_start = full_content[:1000]
            content_end = full_content[-1000:]

        # Extract ground truth data
        ground_truth = example.outputs or {}

        example_data = {
            "url": example.inputs.get("url", "No URL"),
            "title": example.inputs.get("title", "No title"),
            "content_length": content_length,
            "content_start": content_start,  # First 1000 characters
            "content_end": content_end,  # Last 1000 characters
            "confidence": ground_truth.get("confidence", "unknown"),
            "is_complete": ground_truth.get("is_complete", False),
            "human_review": False,  # New field to track manual modifications
            "detected_issues": ground_truth.get("detected_issues", []),
            "requires_manual_review": (
                example.metadata.get("requires_manual_review", True)
                if example.metadata
                else True
            ),
        }
        export_data["examples"].append(example_data)

    # Save to file
    if output_file is None:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_file = f"ground_truth_{dataset_name}_{timestamp}.json"

    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(export_data, f, indent=2, ensure_ascii=False)

    print(f"✅ Exported ground truth to: {output_file}")
    print("📊 Summary:")
    print(f"   Total examples: {len(examples)}")
    print(f"   File size: {os.path.getsize(output_file) / 1024:.1f} KB")

    return output_file


async def import_ground_truth(input_file: str, dataset_name: str = None):
    """Import updated ground truth data back to LangSmith.

    Args:
        input_file: Path to the JSON file with updated ground truth.
        dataset_name: Dataset name. If None, reads from the file.
    """
    print(f"📥 Importing ground truth from: {input_file}")
    print("=" * 60)

    # Load the data
    with open(input_file, "r", encoding="utf-8") as f:
        data = json.load(f)

    if dataset_name is None:
        dataset_name = data["dataset_name"]

    print(f"📊 Dataset: {dataset_name}")
    print(f"📅 Exported: {data.get('exported_at', 'Unknown')}")
    print(f"📋 Examples: {data['total_examples']}")

    # Import required modules
    from src.hex_machina.enrichment.evaluation.langsmith import (
        EvaluationDatasetManager,
        setup_langsmith_environment,
    )

    # Setup LangSmith
    setup_langsmith_environment()
    dataset_manager = EvaluationDatasetManager(logger=logger)

    # Get the dataset
    dataset = dataset_manager.get_dataset(dataset_name)
    if not dataset:
        print(f"❌ Dataset '{dataset_name}' not found")
        return

    # Update examples
    updated_count = 0
    for i, example_data in enumerate(data["examples"], 1):
        if i % 50 == 0:
            print(f"   Updated {i}/{len(data['examples'])} examples...")

        # Skip if not marked for review
        if not example_data.get("requires_manual_review", False):
            continue

        # Update the example
        try:
            # Find the example by URL since we don't have example_id in simplified format
            examples = list(dataset_manager.client.list_examples(dataset_id=dataset.id))
            target_example = None

            for ex in examples:
                if ex.inputs.get("url") == example_data["url"]:
                    target_example = ex
                    break

            if not target_example:
                print(f"⚠️  Could not find example for URL: {example_data['url']}")
                continue

            # Create updated ground truth
            updated_ground_truth = {
                "is_complete": example_data["is_complete"],
                "detected_issues": example_data["detected_issues"],
                "confidence": example_data["confidence"],
                "requires_manual_review": example_data["requires_manual_review"],
                "human_review": example_data.get("human_review", False),
                "notes": f"Manually reviewed: {example_data.get('human_review', False)}",
            }

            # Get current metadata to preserve other fields
            current_metadata = target_example.metadata or {}

            # Update metadata
            updated_metadata = {
                **current_metadata,
                "requires_manual_review": example_data["requires_manual_review"],
                "human_review": example_data.get("human_review", False),
            }

            dataset_manager.client.update_example(
                example_id=target_example.id,
                outputs=updated_ground_truth,
                metadata=updated_metadata,
            )
            updated_count += 1
        except Exception as e:
            print(f"⚠️  Failed to update example for URL {example_data['url']}: {e}")

    print(f"✅ Successfully updated {updated_count} examples")
    print("📊 View updated dataset at: https://smith.langchain.com/")


def show_ground_truth_stats(input_file: str):
    """Show statistics about the ground truth data.

    Args:
        input_file: Path to the JSON file with ground truth data.
    """
    print(f"📊 Ground Truth Statistics: {input_file}")
    print("=" * 60)

    with open(input_file, "r", encoding="utf-8") as f:
        data = json.load(f)

    examples = data["examples"]
    total = len(examples)

    # Count completeness
    complete_count = 0
    incomplete_count = 0
    needs_review_count = 0
    reviewed_count = 0

    for example in examples:
        if example.get("is_complete"):
            complete_count += 1
        else:
            incomplete_count += 1

        if example.get("requires_manual_review"):
            needs_review_count += 1
        else:
            reviewed_count += 1

    # Get confidence distribution
    confidence_counts = {}
    for example in examples:
        confidence = example.get("confidence", "unknown")
        confidence_counts[confidence] = confidence_counts.get(confidence, 0) + 1

    print(f"📋 Total examples: {total}")
    print(f"✅ Complete: {complete_count} ({complete_count/total*100:.1f}%)")
    print(f"❌ Incomplete: {incomplete_count} ({incomplete_count/total*100:.1f}%)")
    print(
        f"🔍 Needs review: {needs_review_count} ({needs_review_count/total*100:.1f}%)"
    )
    print(f"✅ Reviewed: {reviewed_count} ({reviewed_count/total*100:.1f}%)")

    if confidence_counts:
        print("\n🎯 Confidence Distribution:")
        for confidence, count in sorted(confidence_counts.items()):
            print(f"   {confidence}: {count} ({count/total*100:.1f}%)")

    # Show issue distribution
    issue_counts = {}
    for example in examples:
        issues = example.get("detected_issues", [])
        for issue in issues:
            issue_counts[issue] = issue_counts.get(issue, 0) + 1

    if issue_counts:
        print("\n🐛 Issue Distribution:")
        for issue, count in sorted(
            issue_counts.items(), key=lambda x: x[1], reverse=True
        ):
            print(f"   {issue}: {count} ({count/total*100:.1f}%)")


async def main():
    """Main function."""
    print("🔍 Ground Truth Management Tool")
    print("=" * 40)

    if len(sys.argv) < 2:
        print("Usage:")
        print("  python manage_ground_truth.py export <dataset_name> [output_file]")
        print("  python manage_ground_truth.py import <input_file> [dataset_name]")
        print("  python manage_ground_truth.py stats <input_file>")
        print("\nExamples:")
        print(
            "  python manage_ground_truth.py export test_articles_2025-07-31_batch_001"
        )
        print(
            "  python manage_ground_truth.py import ground_truth_test_articles_20250731_143022.json"
        )
        print(
            "  python manage_ground_truth.py stats ground_truth_test_articles_20250731_143022.json"
        )
        return

    command = sys.argv[1]

    if command == "export":
        if len(sys.argv) < 3:
            print("❌ Please provide dataset name")
            return
        dataset_name = sys.argv[2]
        output_file = sys.argv[3] if len(sys.argv) > 3 else None
        await export_ground_truth(dataset_name, output_file)

    elif command == "import":
        if len(sys.argv) < 3:
            print("❌ Please provide input file")
            return
        input_file = sys.argv[2]
        dataset_name = sys.argv[3] if len(sys.argv) > 3 else None
        await import_ground_truth(input_file, dataset_name)

    elif command == "stats":
        if len(sys.argv) < 3:
            print("❌ Please provide input file")
            return
        input_file = sys.argv[2]
        show_ground_truth_stats(input_file)

    else:
        print(f"❌ Unknown command: {command}")


if __name__ == "__main__":
    asyncio.run(main())
