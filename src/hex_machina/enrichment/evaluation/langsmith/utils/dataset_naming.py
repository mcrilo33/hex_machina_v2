"""Dataset naming conventions for the iterative evaluation workflow."""

from datetime import datetime
from typing import Optional


class DatasetNamingConvention:
    """Naming conventions for different types of datasets in the iterative workflow."""

    @staticmethod
    def create_source_dataset_name(
        content_category: str,
        date: Optional[str] = None,
        batch_id: Optional[str] = None,
    ) -> str:
        """Create name for source dataset (raw scraped data).

        Args:
            content_category: Category of content (e.g., 'ai_news', 'tech_blogs')
            date: Date in YYYY-MM-DD format. If None, uses current date.
            batch_id: Optional batch identifier.

        Returns:
            Dataset name following convention.
        """
        if not date:
            date = datetime.now().strftime("%Y-%m-%d")

        name_parts = [content_category, "source", date]
        if batch_id:
            name_parts.append(batch_id)

        return "_".join(name_parts)

    @staticmethod
    def create_iterative_dataset_name(
        content_category: str,
        version: str,
        iteration: Optional[int] = None,
    ) -> str:
        """Create name for iterative dataset (after manual review).

        Args:
            content_category: Category of content.
            version: Version identifier (e.g., 'v1_0', 'v2_1').
            iteration: Optional iteration number.

        Returns:
            Dataset name following convention.
        """
        name_parts = [content_category, "iterative", version]
        if iteration:
            name_parts.append(f"iter_{iteration}")

        return "_".join(name_parts)

    @staticmethod
    def create_curated_dataset_name(
        content_category: str,
        curation_type: str,
        version: Optional[str] = None,
    ) -> str:
        """Create name for curated dataset (high-quality ground truth).

        Args:
            content_category: Category of content.
            curation_type: Type of curation (e.g., 'validated', 'expert_reviewed').
            version: Optional version identifier.

        Returns:
            Dataset name following convention.
        """
        name_parts = [content_category, "curated", curation_type]
        if version:
            name_parts.append(version)

        return "_".join(name_parts)

    @staticmethod
    def create_evaluation_dataset_name(
        content_category: str,
        model_name: str,
        prompt_version: str,
    ) -> str:
        """Create name for evaluation dataset (model testing).

        Args:
            content_category: Category of content.
            model_name: Name of the model being evaluated.
            prompt_version: Version of the prompt used.

        Returns:
            Dataset name following convention.
        """
        # Clean model name for URL safety
        clean_model = model_name.replace("/", "_").replace("-", "_")

        return f"{content_category}_eval_{clean_model}_{prompt_version}"

    @staticmethod
    def create_test_dataset_name(content_category: str) -> str:
        """Create name for test dataset.

        Args:
            content_category: Category of content.

        Returns:
            Dataset name following convention.
        """
        return f"{content_category}_test"

    @staticmethod
    def get_dataset_description(dataset_name: str) -> str:
        """Generate description based on dataset name.

        Args:
            dataset_name: Name of the dataset.

        Returns:
            Human-readable description.
        """
        parts = dataset_name.split("_")

        if "source" in parts:
            return f"Source dataset for {parts[0]} content from {parts[2]}"
        elif "iterative" in parts:
            return f"Iterative dataset for {parts[0]} content, version {parts[2]}"
        elif "curated" in parts:
            return f"Curated dataset for {parts[0]} content, {parts[2]} curation"
        elif "eval" in parts:
            return f"Evaluation dataset for {parts[0]} content using {parts[2]} model"
        elif "test" in parts:
            return f"Test dataset for {parts[0]} content"
        else:
            return f"Dataset for {parts[0]} content"

    @staticmethod
    def parse_dataset_name(dataset_name: str) -> dict:
        """Parse dataset name to extract components.

        Args:
            dataset_name: Name of the dataset.

        Returns:
            Dictionary with parsed components.
        """
        parts = dataset_name.split("_")

        result = {
            "content_category": parts[0] if parts else None,
            "dataset_type": None,
            "version": None,
            "date": None,
            "batch_id": None,
            "model_name": None,
            "curation_type": None,
        }

        if len(parts) < 2:
            return result

        if "source" in parts:
            result["dataset_type"] = "source"
            result["date"] = parts[2] if len(parts) > 2 else None
            result["batch_id"] = parts[3] if len(parts) > 3 else None
        elif "iterative" in parts:
            result["dataset_type"] = "iterative"
            result["version"] = parts[2] if len(parts) > 2 else None
        elif "curated" in parts:
            result["dataset_type"] = "curated"
            result["curation_type"] = parts[2] if len(parts) > 2 else None
            result["version"] = parts[3] if len(parts) > 3 else None
        elif "eval" in parts:
            result["dataset_type"] = "evaluation"
            result["model_name"] = parts[2] if len(parts) > 2 else None
            result["version"] = parts[3] if len(parts) > 3 else None
        elif "test" in parts:
            result["dataset_type"] = "test"

        return result

    @staticmethod
    def get_next_version(current_version: str) -> str:
        """Get next version number.

        Args:
            current_version: Current version (e.g., 'v1_0').

        Returns:
            Next version (e.g., 'v1_1').
        """
        if not current_version.startswith("v"):
            return "v1_0"

        try:
            # Extract major and minor version
            version_parts = current_version[1:].split("_")
            major = int(version_parts[0])
            minor = int(version_parts[1]) if len(version_parts) > 1 else 0

            return f"v{major}_{minor + 1}"
        except (ValueError, IndexError):
            return "v1_0"

    @staticmethod
    def get_next_iteration_number(dataset_name: str) -> int:
        """Get next iteration number for iterative dataset.

        Args:
            dataset_name: Name of the dataset.

        Returns:
            Next iteration number.
        """
        parsed = DatasetNamingConvention.parse_dataset_name(dataset_name)

        if parsed["dataset_type"] != "iterative":
            return 1

        # Extract iteration number from name
        parts = dataset_name.split("_")
        for part in parts:
            if part.startswith("iter_"):
                try:
                    return int(part[5:]) + 1
                except ValueError:
                    pass

        return 1
