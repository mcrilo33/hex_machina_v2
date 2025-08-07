#!/usr/bin/env python3
"""Script to create the first dataset from scraped data."""

import asyncio
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


async def create_dataset_from_scraped_data():
    """Create a dataset from your first batch of scraped data."""

    print("📊 Creating Dataset from Scraped Data")
    print("=" * 50)

    # Check API keys
    if not os.getenv("OPENROUTER_API_KEY") or not os.getenv("LANGSMITH_API_KEY"):
        print("❌ API keys not configured")
        print(
            "   Please set OPENROUTER_API_KEY and LANGSMITH_API_KEY in your .env file"
        )
        return

    # Get database configuration
    print("\n🗄️  Database Configuration:")
    print("-" * 30)

    duckdb_path = input("Enter DuckDB path (e.g., 'data/hex_machina.db'): ").strip()
    if not duckdb_path:
        duckdb_path = "data/hex_machina.db"

    # Check if database exists
    if not os.path.exists(duckdb_path):
        print(f"❌ Database not found: {duckdb_path}")
        return

    # List available ingestion operations
    print("\n📋 Available Ingestion Operations:")
    print("-" * 40)
    available_ops = list_ingestion_operations(duckdb_path)

    if not available_ops:
        print("❌ No ingestion operations found in database")
        return

    print("Available ingestion operations:")
    for op in available_ops:
        print(
            f"   ID: {op.id} | {op.start_time} | {op.status} | {op.num_articles_processed} articles"
        )

    # Get ingestion operation ID
    ingestion_op_id = input("\nEnter IngestionOperationDB ID: ").strip()
    if not ingestion_op_id:
        print("❌ Ingestion operation ID is required")
        return

    try:
        ingestion_op_id = int(ingestion_op_id)
    except ValueError:
        print("❌ Ingestion operation ID must be a number")
        return

    # Import required modules
    from src.hex_machina.enrichment.evaluation.langsmith import (
        EvaluationDatasetManager,
        setup_langsmith_environment,
    )
    from src.hex_machina.enrichment.evaluation.langsmith.utils.dataset_naming import (
        DatasetNamingConvention,
    )

    # Setup LangSmith
    setup_langsmith_environment()
    dataset_manager = EvaluationDatasetManager(logger=logger)

    # Get user input for dataset configuration
    print("\n📝 Dataset Configuration:")
    print("-" * 30)

    content_category = input(
        "Enter content category (e.g., 'ai_news', 'tech_blogs', 'research_papers'): "
    ).strip()
    if not content_category:
        content_category = "ai_news"

    batch_id = input("Enter batch ID (e.g., 'batch_001', 'batch_002'): ").strip()
    if not batch_id:
        batch_id = "batch_001"

    # Generate dataset name
    dataset_name = DatasetNamingConvention.create_source_dataset_name(
        content_category=content_category,
        batch_id=batch_id,
    )

    description = DatasetNamingConvention.get_dataset_description(dataset_name)

    print(f"\n📋 Generated Dataset Name: {dataset_name}")
    print(f"📝 Description: {description}")

    # Confirm creation
    confirm = input("\nCreate this dataset? (y/n): ").strip().lower()
    if confirm != "y":
        print("❌ Dataset creation cancelled")
        return

    # Get articles from your scraped data
    print("\n🔍 Loading articles from scraped data...")

    # Load articles from DuckDB
    articles = await load_scraped_articles(duckdb_path, ingestion_op_id)

    if not articles:
        print("❌ No articles found in scraped data")
        return

    print(f"✅ Found {len(articles)} articles")

    # Choose evaluation method
    print("\n🏷️  Ground Truth Creation Method:")
    print("-" * 30)
    use_llm = input("Use LLM evaluation? (y/n, default: y): ").strip().lower()
    if use_llm == "n":
        use_llm = False
    else:
        use_llm = True

    # Create ground truth data
    ground_truth_data = await create_ground_truth_data(articles, use_llm=use_llm)

    # Create the dataset
    print("\n📊 Creating dataset in LangSmith...")
    try:
        dataset = dataset_manager.create_test_dataset_from_articles(
            articles=articles,
            dataset_name=dataset_name,
            ground_truth_data=ground_truth_data,
        )

        print("✅ Successfully created dataset!")
        print(f"   Name: {dataset.name}")
        print(f"   ID: {dataset.id}")
        print(f"   Examples: {dataset.example_count}")
        print(f"   Description: {description}")

        print("\n📊 View your dataset at: https://smith.langchain.com/")
        print(
            f"   Project: {os.getenv('LANGSMITH_PROJECT', 'hex-machina-content-evaluation')}"
        )
        print(f"   Dataset: {dataset.name}")

        # Save dataset info for future reference
        save_dataset_info(dataset_name, dataset.id, description, len(articles))

    except Exception as e:
        print(f"❌ Failed to create dataset: {e}")
        import traceback

        traceback.print_exc()


async def load_scraped_articles(duckdb_path: str, ingestion_op_id: int):
    """Load articles from DuckDB based on ingestion operation ID.

    Args:
        duckdb_path: Path to the DuckDB database file.
        ingestion_op_id: ID of the ingestion operation to load articles from.

    Returns:
        List of ArticleDB objects.
    """
    try:
        from sqlalchemy import create_engine
        from sqlalchemy.orm import sessionmaker

        from src.hex_machina.storage.models import ArticleDB, IngestionOperationDB

        # Create database engine
        engine = create_engine(f"duckdb:///{duckdb_path}")
        Session = sessionmaker(bind=engine)
        session = Session()

        try:
            # Verify ingestion operation exists
            ingestion_op = (
                session.query(IngestionOperationDB)
                .filter(IngestionOperationDB.id == ingestion_op_id)
                .first()
            )

            if not ingestion_op:
                print(f"❌ Ingestion operation with ID {ingestion_op_id} not found")
                return []

            print(f"✅ Found ingestion operation: {ingestion_op.id}")
            print(f"   Start time: {ingestion_op.start_time}")
            print(f"   End time: {ingestion_op.end_time}")
            print(f"   Articles processed: {ingestion_op.num_articles_processed}")
            print(f"   Errors: {ingestion_op.num_errors}")
            print(f"   Status: {ingestion_op.status}")

            # Load articles for this ingestion operation
            articles = (
                session.query(ArticleDB)
                .filter(ArticleDB.ingestion_run_id == ingestion_op_id)
                .all()
            )

            print(f"✅ Loaded {len(articles)} articles from database")

            # Show some statistics
            if articles:
                domains = set(article.url_domain for article in articles)
                print(f"   Domains: {', '.join(sorted(domains))}")

                content_lengths = [
                    len(article.text_content)
                    for article in articles
                    if article.text_content
                ]
                if content_lengths:
                    avg_length = sum(content_lengths) / len(content_lengths)
                    print(f"   Average content length: {avg_length:.0f} characters")
                    print(f"   Min content length: {min(content_lengths)} characters")
                    print(f"   Max content length: {max(content_lengths)} characters")

            return articles

        finally:
            session.close()

    except Exception as e:
        print(f"❌ Error loading articles from database: {e}")
        import traceback

        traceback.print_exc()
        return []


def list_ingestion_operations(duckdb_path: str):
    """List all ingestion operations in the database.

    Args:
        duckdb_path: Path to the DuckDB database file.

    Returns:
        List of IngestionOperationDB objects.
    """
    try:
        from sqlalchemy import create_engine
        from sqlalchemy.orm import sessionmaker

        from src.hex_machina.storage.models import IngestionOperationDB

        # Create database engine
        engine = create_engine(f"duckdb:///{duckdb_path}")
        Session = sessionmaker(bind=engine)
        session = Session()

        try:
            # Get all ingestion operations, ordered by start time (newest first)
            operations = (
                session.query(IngestionOperationDB)
                .order_by(IngestionOperationDB.start_time.desc())
                .all()
            )

            return operations

        finally:
            session.close()

    except Exception as e:
        print(f"❌ Error listing ingestion operations: {e}")
        import traceback

        traceback.print_exc()
        return []


async def create_ground_truth_data(articles, use_llm: bool = True):
    """Create ground truth data for the articles.

    Args:
        articles: List of ArticleDB objects.
        use_llm: Whether to use LLM evaluation or simple heuristics.

    Returns:
        Dict mapping article URLs to ground truth data.
    """
    if use_llm:
        print("🏷️  Creating ground truth data using LLM evaluation...")
        return await create_ground_truth_with_llm(articles)
    else:
        print("🏷️  Creating ground truth data using heuristics...")
        return await create_ground_truth_with_heuristics(articles)


async def create_ground_truth_with_heuristics(articles):
    """Create ground truth using simple heuristics."""
    ground_truth = {}

    for article in articles:
        url = article.url
        content = article.text_content or ""
        content_length = len(content)

        # Enhanced heuristics for content completeness
        issues = []

        # Check ingestion error status
        if article.ingestion_error_status:
            issues.append(f"ingestion_error_{article.ingestion_error_status}")

        # Determine completeness
        is_complete = len(issues) == 0 and content_length >= 500

        # Create ground truth entry
        ground_truth[url] = {
            "is_complete": is_complete,
            "detected_issues": issues if issues else ["no_issues"],
            "notes": f"Auto-classified based on content analysis ({content_length} chars, {len(issues)} issues)",
            "requires_manual_review": not is_complete,  # Only incomplete articles need manual review
            "confidence": "high" if issues else "low",
            "evaluation_method": "heuristics",
            "evaluation_prompt": None,
            "evaluation_model": None,
        }

    # Print summary
    complete_count = sum(1 for gt in ground_truth.values() if gt["is_complete"])
    incomplete_count = len(ground_truth) - complete_count
    needs_review_count = sum(
        1 for gt in ground_truth.values() if gt["requires_manual_review"]
    )

    # Get evaluation method info
    evaluation_methods = set(
        gt.get("evaluation_method", "unknown") for gt in ground_truth.values()
    )
    method_str = ", ".join(evaluation_methods)

    print(f"   Auto-classified {complete_count} articles as complete (trusted)")
    print(f"   Auto-classified {incomplete_count} articles as incomplete")
    print(
        f"   {needs_review_count} articles marked for manual review (incomplete only)"
    )
    print(f"   Evaluation method(s): {method_str}")

    return ground_truth


async def create_ground_truth_with_llm(articles):
    """Create ground truth using ContentCompletenessEvaluator."""
    from langchain_openai import ChatOpenAI

    from src.hex_machina.enrichment.evaluation.langchain.chains.evaluation_chains import (
        ContentCompletenessEvaluator,
    )

    # Create LLM instance
    llm = ChatOpenAI(
        model="google/gemini-2.5-flash",
        temperature=0,
        openai_api_base="https://openrouter.ai/api/v1",
        openai_api_key=os.getenv("OPENROUTER_API_KEY"),
    )

    # Create the evaluator
    evaluator = ContentCompletenessEvaluator(llm=llm, logger=logger)

    ground_truth = {}

    print(f"🤖 Using LLM: {llm.model_name}")
    print("📝 Using ContentCompletenessEvaluator")

    for i, article in enumerate(articles, 1):
        if i % 50 == 0:
            print(f"   Evaluated {i}/{len(articles)} articles...")

        try:
            # Use the evaluator to get structured evaluation
            evaluation = await evaluator.evaluate_article(article)
            if not evaluation.is_complete and len(evaluation.detected_issues) > 0:
                confidence = "high"
            elif not evaluation.is_complete and len(evaluation.detected_issues) == 0:
                confidence = "low"
            elif evaluation.is_complete and len(evaluation.detected_issues) > 0:
                confidence = "low"
            elif evaluation.is_complete and len(evaluation.detected_issues) == 0:
                confidence = "high"

            # Create ground truth entry from evaluation result
            ground_truth[article.url] = {
                "is_complete": evaluation.is_complete,
                "detected_issues": evaluation.detected_issues,
                "notes": "LLM evaluation using ContentCompletenessEvaluator",
                "requires_manual_review": not evaluation.is_complete
                or (
                    len(evaluation.detected_issues) > 0
                    and "no_issues" not in evaluation.detected_issues
                ),
                "confidence": confidence,  # LLM confidence
                "evaluation_method": "llm",
                "evaluation_prompt": "ContentCompletenessEvaluator",
                "evaluation_model": evaluation.llm_model_used,
                "processing_time_seconds": evaluation.processing_time_seconds,
                "evaluation_status": evaluation.evaluation_status,
            }

        except Exception as e:
            print(f"⚠️  LLM evaluation failed for {article.url}: {e}")
            # Fallback to heuristics
            content_length = len(article.text_content or "")
            issues = []
            if article.ingestion_error_status:
                issues.append(f"ingestion_error_{article.ingestion_error_status}")

            is_complete = len(issues) == 0 and content_length >= 500

            ground_truth[article.url] = {
                "is_complete": is_complete,
                "detected_issues": issues if issues else ["no_issues"],
                "notes": f"Fallback to heuristics due to LLM error: {str(e)}",
                "requires_manual_review": not is_complete,
                "confidence": "low",
                "evaluation_method": "heuristics_fallback",
                "evaluation_prompt": None,
                "evaluation_model": None,
            }

    return ground_truth


def save_dataset_info(dataset_name, dataset_id, description, article_count):
    """Save dataset information for future reference."""
    info = {
        "dataset_name": dataset_name,
        "dataset_id": str(dataset_id),  # Convert UUID to string
        "description": description,
        "article_count": article_count,
        "created_at": datetime.now().isoformat(),
    }

    # Save to a JSON file
    import json

    filename = f"dataset_info_{dataset_name}.json"

    try:
        with open(filename, "w") as f:
            json.dump(info, f, indent=2)
        print(f"💾 Dataset info saved to: {filename}")
    except Exception as e:
        print(f"⚠️  Could not save dataset info: {e}")


def show_naming_examples():
    """Show examples of the naming convention."""
    print("\n📋 Naming Convention Examples:")
    print("-" * 40)

    from src.hex_machina.enrichment.evaluation.langsmith.utils.dataset_naming import (
        DatasetNamingConvention,
    )

    examples = [
        (
            "Source Dataset",
            DatasetNamingConvention.create_source_dataset_name("ai_news"),
        ),
        (
            "Source Dataset (Custom)",
            DatasetNamingConvention.create_source_dataset_name(
                "tech_blogs", "2024-01-10", "batch_002"
            ),
        ),
        (
            "Iterative Dataset",
            DatasetNamingConvention.create_iterative_dataset_name("ai_news", "v1_0"),
        ),
        (
            "Curated Dataset",
            DatasetNamingConvention.create_curated_dataset_name("ai_news", "validated"),
        ),
        (
            "Evaluation Dataset",
            DatasetNamingConvention.create_evaluation_dataset_name(
                "ai_news", "gpt35", "v1_0"
            ),
        ),
        (
            "Test Dataset",
            DatasetNamingConvention.create_test_dataset_name("ai_news"),
        ),
    ]

    for name, example in examples:
        print(f"{name:20}: {example}")


async def main():
    """Main function."""
    print("🚀 Dataset Creation Tool")
    print("=" * 30)

    # Show naming examples
    show_naming_examples()

    # Create dataset
    await create_dataset_from_scraped_data()

    print("\n" + "=" * 30)
    print("✅ Dataset creation completed!")
    print("\n📋 Next Steps:")
    print("1. Review your dataset in LangSmith dashboard")
    print("2. Manually validate ground truth data")
    print("3. Use the dataset for iterative building workflow")
    print("4. Run evaluation tests on the dataset")


if __name__ == "__main__":
    asyncio.run(main())
