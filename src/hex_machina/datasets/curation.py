"""Dataset curation module for manual annotation."""

import logging
from typing import Any, Dict, List, Optional

from src.hex_machina.datasets.langsmith_sync import LangSmithSync
from src.hex_machina.storage.manager import get_storage_manager
from src.hex_machina.storage.models import DatasetDB, DatasetExampleDB

logger = logging.getLogger(__name__)

# Simple field templates for annotation
SIMPLE_FIELD_TEMPLATES = {
    "relevance_score": {
        "type": "int",
        "range": (1, 5),
        "description": "Relevance to AI/ML topic (1=low, 5=high)",
        "validation": lambda x: 1 <= int(x) <= 5,
    },
    "quality_score": {
        "type": "int",
        "range": (1, 5),
        "description": "Content quality (1=low, 5=high)",
        "validation": lambda x: 1 <= int(x) <= 5,
    },
    "category": {
        "type": "choice",
        "options": ["tech", "research", "news", "tutorial", "opinion"],
        "description": "Article category",
    },
    "sentiment": {
        "type": "choice",
        "options": ["positive", "neutral", "negative"],
        "description": "Overall sentiment",
    },
    "difficulty": {
        "type": "choice",
        "options": ["beginner", "intermediate", "advanced"],
        "description": "Content difficulty level",
    },
}


class DatasetCurationManager:
    """Simple dataset curation manager using LangSmith splits."""

    def __init__(self):
        self.storage_manager = get_storage_manager()
        self.langsmith_sync = LangSmithSync()

    def curate_dataset(
        self,
        dataset_name: str,
        split: Optional[str] = None,
        display_fields: Optional[List[str]] = None,
        annotate_fields: Optional[List[str]] = None,
    ) -> None:
        """Interactively curate a dataset - creates LangSmith splits."""

        # Get dataset
        dataset = self._get_dataset(dataset_name)
        if not dataset:
            raise ValueError(f"Dataset '{dataset_name}' not found")

        # Get examples to curate
        examples = self._get_examples(dataset, split)
        if not examples:
            raise ValueError(
                f"No examples found for dataset '{dataset_name}' split '{split or 'all'}'"
            )

        # Set default fields if not specified
        if not display_fields:
            display_fields = ["title", "url", "url_domain", "text_content"]
        if not annotate_fields:
            annotate_fields = ["relevance_score", "quality_score"]

        # Validate fields
        self._validate_fields(display_fields, annotate_fields)

        # Run curation session
        self._run_curation_session(dataset, examples, display_fields, annotate_fields)

    def _get_dataset(self, dataset_name: str) -> Optional[DatasetDB]:
        """Get dataset by name."""
        with self.storage_manager.session() as session:
            return (
                session.query(DatasetDB).filter(DatasetDB.name == dataset_name).first()
            )

    def _get_examples(
        self, dataset: DatasetDB, split: Optional[str] = None
    ) -> List[DatasetExampleDB]:
        """Get examples from dataset."""
        from sqlalchemy.orm import joinedload

        with self.storage_manager.session() as session:
            query = (
                session.query(DatasetExampleDB)
                .options(joinedload(DatasetExampleDB.article))
                .filter(DatasetExampleDB.dataset_id == dataset.id)
            )
            if split:
                # Handle comma-separated splits - find examples that contain the specified split
                query = query.filter(DatasetExampleDB.split.contains(split))
            return query.all()

    def _validate_fields(
        self, display_fields: List[str], annotate_fields: List[str]
    ) -> None:
        """Validate field names."""
        all_fields = set(display_fields) | set(annotate_fields)
        valid_fields = set(SIMPLE_FIELD_TEMPLATES.keys()) | {
            "title",
            "url",
            "url_domain",
            "text_content",
            "published_date",
            "author",
        }

        invalid_fields = all_fields - valid_fields
        if invalid_fields:
            raise ValueError(
                f"Invalid fields: {invalid_fields}. Valid fields: {valid_fields}"
            )

    def _run_curation_session(
        self,
        dataset: DatasetDB,
        examples: List[DatasetExampleDB],
        display_fields: List[str],
        annotate_fields: List[str],
    ) -> None:
        """Run interactive curation session."""

        print(f"🎯 Starting curation session for {len(examples)} examples")
        print(f"📝 Display fields: {', '.join(display_fields)}")
        print(f"🔧 Annotate fields: {', '.join(annotate_fields)}")
        print("Press Ctrl+C to exit\n")

        for i, example in enumerate(examples, 1):
            try:
                # Display article
                self._display_article(example, display_fields, i, len(examples))

                # Get annotations
                annotations = self._get_annotations(annotate_fields)

                                # Create split name
                split_name = self._create_split_name(annotations)
                
                # Get current splits and append new one
                current_splits = example.split.split(",") if example.split else []
                if split_name not in current_splits:
                    current_splits.append(split_name)
                new_splits = ",".join(current_splits)
                
                # Update splits in both LangSmith and local database
                if dataset.langsmith_dataset_id and example.langsmith_example_id:
                    self.langsmith_sync.update_examples_split(
                        dataset_id=dataset.langsmith_dataset_id,
                        examples=[example],
                        new_split=new_splits,
                    )
                
                # Update local database
                with self.storage_manager.session() as session:
                    session.query(DatasetExampleDB).filter(
                        DatasetExampleDB.id == example.id
                    ).update({"split": new_splits})
                    session.commit()
                
                print(f"✅ Article {i} → {new_splits}")

                print()  # Empty line for readability

            except KeyboardInterrupt:
                print(f"\n🛑 Curation stopped at article {i}")
                break
            except Exception as e:
                print(f"❌ Error processing article {i}: {e}")
                continue

        print(f"🎉 Curation completed! Processed {i} articles.")

    def _display_article(
        self,
        example: DatasetExampleDB,
        display_fields: List[str],
        current: int,
        total: int,
    ) -> None:
        """Display article information."""
        print(
            f"📄 Article {current}/{total}: {example.example_metadata.get('article_title', 'Unknown')}"
        )

        # Get article data (already loaded via joinedload)
        article = example.article
        if not article:
            print("   ❌ Article not found")
            return

        # Display requested fields
        for field in display_fields:
            if field == "title":
                print(f"   Title: {article.title}")
            elif field == "url":
                print(f"   URL: {article.url}")
            elif field == "url_domain":
                print(f"   Domain: {article.url_domain}")
            elif field == "published_date":
                print(f"   Published: {article.published_date}")
            elif field == "author":
                print(f"   Author: {article.author or 'Unknown'}")
            elif field == "text_content":
                # Show first 200 characters
                content = article.text_content or ""
                preview = content[:200] + "..." if len(content) > 200 else content
                print(f"   Text: {preview}")

        print()  # Empty line

    def _get_annotations(self, annotate_fields: List[str]) -> Dict[str, Any]:
        """Get user annotations for specified fields."""
        annotations = {}

        print("🔧 Annotations:")
        for field in annotate_fields:
            template = SIMPLE_FIELD_TEMPLATES.get(field, {})
            description = template.get("description", field)

            if template.get("type") == "choice":
                options = template.get("options", [])
                print(f"   {field}: {description}")
                print(f"      Options: {', '.join(options)}")
                while True:
                    value = input("      > ").strip().lower()
                    if value in options:
                        annotations[field] = value
                        break
                    elif value == "":
                        print(f"      Skipping {field}")
                        break
                    else:
                        print(
                            f"      Invalid option. Choose from: {', '.join(options)}"
                        )

            elif template.get("type") == "int":
                range_info = template.get("range", (1, 5))
                print(f"   {field}: {description}")
                while True:
                    value = input(f"      [{range_info[0]}-{range_info[1]}] > ").strip()
                    if value == "":
                        print(f"      Skipping {field}")
                        break
                    try:
                        int_value = int(value)
                        if range_info[0] <= int_value <= range_info[1]:
                            annotations[field] = int_value
                            break
                        else:
                            print(
                                f"      Value must be between {range_info[0]} and {range_info[1]}"
                            )
                    except ValueError:
                        print("      Please enter a valid number")

        return annotations

    def _create_split_name(self, annotations: Dict[str, Any]) -> str:
        """Create split name from annotations."""
        if not annotations:
            return "annotated_skipped"

        parts = []
        for field, value in annotations.items():
            parts.append(f"{field}_{value}")
        return f"annotated_{'_'.join(parts)}"
