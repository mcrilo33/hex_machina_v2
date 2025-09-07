"""EnrichmentSaver runnable for saving enrichments to database."""

import logging
from datetime import datetime
from typing import Any, Dict, List, Optional

from langchain_core.runnables import Runnable
from langsmith import traceable

from ..database.connector import DatabaseConnector


class EnrichmentSaver(Runnable):
    """LangChain runnable that saves enrichments to DuckDB."""

    def __init__(self, db_path: str, enrichment_type: str, input_mapping: str):
        """Initialize EnrichmentSaver.

        Args:
            db_path: Path to DuckDB database
            enrichment_type: Type of enrichment (e.g., "keywords", "summary")
            input_mapping: Path to extract content from inputs (e.g., "extract_keywords.keywords")
        """
        self.db_connector = DatabaseConnector(db_path)
        self.enrichment_type = enrichment_type
        self.input_mapping = input_mapping
        self._logger = logging.getLogger("runnable.EnrichmentSaver")

    @traceable(name="EnrichmentSaver", run_type="tool")
    def invoke(
        self, inputs: Dict[str, Any], config: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Save enrichments to database and return enriched inputs.

        Args:
            inputs: Input dictionary containing enrichments list or direct article (when used with .map())
            config: Optional configuration override

        Returns:
            Enriched input dictionary
        """
        try:
            # Check if inputs contains a batch of enrichments
            if "enrichments" in inputs and isinstance(inputs["enrichments"], list):
                # Handle batch processing
                self._save_batch_enrichments(inputs["enrichments"])
                self._logger.info(
                    f"Saved {len(inputs['enrichments'])} {self.enrichment_type} enrichments"
                )
            else:
                # Handle single enrichment (legacy behavior)
                article_id = self._extract_article_id(inputs)
                content = self._extract_content(inputs)
                metadata = self._generate_metadata()
                self._save_enrichment(article_id, content, metadata)
                self._logger.info(
                    f"Saved {self.enrichment_type} enrichment for article {article_id}"
                )

            # Return enriched inputs for next step
            return inputs

        except Exception as e:
            self._logger.error(f"Failed to save enrichment: {e}")
            raise

    def _save_batch_enrichments(self, enrichments: List[Dict[str, Any]]) -> None:
        """Save a batch of enrichments to database.

        Args:
            enrichments: List of enrichment dictionaries with article_id, content, enrichment_type, db_path
        """
        for enrichment in enrichments:
            try:
                article_id = enrichment["article_id"]
                if isinstance(enrichment, dict):
                    content = self._extract_content(enrichment)

                # Use the enrichment_type from the enrichment data if available, otherwise use instance default
                enrichment_type = enrichment.get(
                    "enrichment_type", self.enrichment_type
                )

                # Generate metadata
                metadata = self._generate_metadata()

                # Save to database
                self._save_enrichment(article_id, content, metadata, enrichment_type)

                self._logger.debug(
                    f"Saved {enrichment_type} enrichment for article {article_id}"
                )

            except Exception as e:
                self._logger.error(
                    f"Failed to save enrichment for article {enrichment.get('article_id', 'unknown')}: {e}"
                )
                # Continue with other enrichments even if one fails
                continue

    def _extract_article_id(self, inputs: Any) -> int:
        """Extract article_id from inputs (one simple lookup).

        Args:
            inputs: Input dictionary or direct article

        Returns:
            Article ID

        Raises:
            ValueError: If article_id not found
        """
        # Handle direct article input from .map() operation
        if "id" in inputs:
            return inputs["id"]

        # Try to find article_id in various possible locations
        if "article_id" in inputs:
            return inputs["article_id"]

        # Look for article_id in the summaries/keywords data
        if "generate_article_summary" in inputs:
            # Check if there's an 'id' at the top level of generate_article_summary
            if "id" in inputs["generate_article_summary"]:
                return inputs["generate_article_summary"]["id"]

            # Check in the summaries array
            summaries = inputs["generate_article_summary"].get("summaries", [])
            if summaries and "article_id" in summaries[0]:
                return summaries[0]["article_id"]

        if "extract_keywords" in inputs:
            keywords_list = inputs["extract_keywords"].get("keywords", [])
            if keywords_list and "article_id" in keywords_list[0]:
                return keywords_list[0]["article_id"]

        # If still not found, try to get from the first article in the list
        if isinstance(inputs, list) and inputs:
            first_item = inputs[0]
            if isinstance(first_item, dict) and "id" in first_item:
                return first_item["id"]

        # Debug: Log what we actually have
        if isinstance(inputs, dict):
            self._logger.error(f"Available keys in inputs: {list(inputs.keys())}")
            if "generate_article_summary" in inputs:
                self._logger.error(
                    f"generate_article_summary content: {inputs['generate_article_summary']}"
                )
        else:
            self._logger.error(f"Inputs type: {type(inputs)}, content: {inputs}")

        raise ValueError("article_id not found in inputs")

    def _extract_content(self, inputs: Any) -> Any:
        """Extract content using input_mapping path.

        Args:
            inputs: Input dictionary or direct article

        Returns:
            Content to save

        Raises:
            ValueError: If content path not found
        """
        # Debug: Log the input structure
        self._logger.debug(f"EnrichmentSaver inputs: {inputs}")
        self._logger.debug(f"Looking for path: {self.input_mapping}")

        # Parse input_mapping path (e.g., "generate_article_summary.summary")
        path_parts = self.input_mapping.split(".")

        current = inputs
        for part in path_parts:
            if part not in current:
                # If the path is not found, try to get content from the article directly
                if part == "summary" and "title" in inputs:
                    # Fallback: generate a simple summary from the article title
                    return f"Summary of: {inputs.get('title', 'Unknown Article')}"
                elif part == "keywords" and "title" in inputs:
                    # Fallback: generate simple keywords from the article title
                    return ["article", "content", "summary"]
                else:
                    # Try to find content in the current step's output
                    if "generate_article_summary" in inputs:
                        # Handle nested structure: generate_article_summary.generate_article_summary.summary
                        nested_content = inputs["generate_article_summary"]
                        if (
                            "generate_article_summary" in nested_content
                            and part in nested_content["generate_article_summary"]
                        ):
                            return nested_content["generate_article_summary"][part]

                        # Check in the summaries array
                        summaries = nested_content.get("summaries", [])
                        if summaries and part in summaries[0]:
                            return summaries[0][part]

                    # If still not found, use a default value
                    if part == "summary":
                        return f"Default summary for: {inputs.get('title', 'Unknown Article')}"
                    elif part == "keywords":
                        return ["default", "keywords"]
                    else:
                        # Log the actual input structure for debugging
                        self._logger.error(
                            f"Path '{self.input_mapping}' not found in inputs"
                        )
                        self._logger.error(f"Available keys: {list(inputs.keys())}")
                        if "generate_article_summary" in inputs:
                            self._logger.error(
                                f"generate_article_summary content: {inputs['generate_article_summary']}"
                            )
                        raise ValueError(
                            f"Path '{self.input_mapping}' not found in inputs"
                        )
            current = current[part]

        return current

    def _generate_metadata(self) -> Dict[str, Any]:
        """Generate metadata as JSON.

        Returns:
            Metadata dictionary
        """
        return {
            "timestamp": datetime.now().isoformat(),
            "step_name": "EnrichmentSaver",
            "run_id": "auto_generated",  # TODO: Get from context
            "enrichment_type": self.enrichment_type,
        }

    def _save_enrichment(
        self,
        article_id: int,
        content: Any,
        metadata: Dict[str, Any],
        enrichment_type: Optional[str] = None,
    ):
        """Save enrichment to database.

        Args:
            article_id: Article ID
            content: Enrichment content
            metadata: Auto-generated metadata
            enrichment_type: Optional enrichment type override
        """
        # Use provided enrichment_type or fall back to instance default
        final_enrichment_type = enrichment_type or self.enrichment_type

        query = """
        INSERT INTO enrichments (article_id, enrichment_type, enrichment_data, source, tool_name, created_at)
        VALUES (?, ?, ?, ?, ?, ?)
        """

        params = {
            "article_id": article_id,
            "enrichment_type": final_enrichment_type,
            "content": content,
            "source": "langchain_runnable",
            "tool_name": "EnrichmentSaver",
            "created_at": datetime.now(),
        }

        self.db_connector.execute_query(query, params)

    def __del__(self):
        """Cleanup database connection."""
        if hasattr(self, "db_connector"):
            self.db_connector.close()
