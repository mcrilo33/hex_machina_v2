"""Generic report builder for pipeline operations (ingestion, enrichment, etc.)."""

import json
from collections import Counter, defaultdict
from typing import Any, List, Optional, Type

from src.hex_machina.reporting.base_report_generator import BaseReportBuilder
from src.hex_machina.reporting.chart_utils import (
    create_distribution_chart,
    create_field_coverage_table,
    create_time_series_chart,
)
from src.hex_machina.storage.duckdb_adapter import DuckDBAdapter
from src.hex_machina.utils.logging_utils import get_logger


class ReportBuilder(BaseReportBuilder):
    """Generic report builder for pipeline operations."""

    @staticmethod
    def build_markdown_report(
        sections: List[str], title: str = "Pipeline Report"
    ) -> str:
        """Assemble the full Markdown report from a list of Markdown section strings.

        Args:
            sections: List of Markdown strings for each report section
            title: Report title (e.g., 'Ingestion Report', 'Enrichment Report')

        Returns:
            Full Markdown report as a string
        """
        return BaseReportBuilder.build_markdown_report(sections, title)

    @staticmethod
    def section_operation_summary(
        operation: Any, process_type: str = "Pipeline"
    ) -> str:
        """Render a summary section for any operation (ingestion, enrichment, etc.).

        Args:
            operation: ORM object with operation fields (must have id, start_time, end_time, status, num_articles_processed, num_errors, parameters)
            process_type: Type of process (e.g., 'Ingestion', 'Enrichment')

        Returns:
            Markdown string for the summary section
        """
        return BaseReportBuilder.section_operation_summary(operation, process_type)

    @staticmethod
    def section_domain_error_table(articles: List[Any]) -> str:
        """Render a table of article and error counts per url_domain, including scraper_name counts.

        Args:
            articles: List of article ORM objects (must have url_domain and ingestion_error_status fields)
        Returns:
            Markdown string for the table section
        """
        logger = get_logger(__name__)

        try:
            if not articles:
                return """
## Domain Article/Error Distribution

No articles available for analysis.

"""

            # Collect statistics
            scraper_names = set()
            domain_stats = defaultdict(
                lambda: {
                    "article_count": 0,
                    "error_count": 0,
                    "scraper_counts": Counter(),
                }
            )

            for article in articles:
                domain = getattr(article, "url_domain", "unknown")
                has_error = getattr(article, "ingestion_error_status", None) is not None

                domain_stats[domain]["article_count"] += 1
                if has_error:
                    domain_stats[domain]["error_count"] += 1

                # Parse scraper_name from ingestion_metadata
                scraper_name = _extract_scraper_name(article)
                if scraper_name:
                    domain_stats[domain]["scraper_counts"][scraper_name] += 1
                    scraper_names.add(scraper_name)

            if not domain_stats:
                return """
## Domain Article/Error Distribution

No valid domain data available.

"""

            # Sort scraper_names for consistent column order
            scraper_names = sorted(scraper_names)

            # Sort by article_count descending
            sorted_stats = sorted(
                domain_stats.items(), key=lambda x: x[1]["article_count"], reverse=True
            )

            # Build Markdown table
            markdown = """
## Domain Article/Error Distribution

"""

            # Header
            header = "| URL Domain | Article Count | Error Count | Success Rate | Scraper Names"
            separator = "|------------|---------------|-------------|--------------|---------------"

            if scraper_names:
                header += " | " + " | ".join(scraper_names)
                separator += " | " + "|".join(["-" * 15] * len(scraper_names))

            header += " |\n"
            separator += " |\n"

            markdown += header
            markdown += separator

            # Rows
            for domain, stats in sorted_stats:
                # Calculate success rate
                success_rate = "-"
                if stats["article_count"] > 0:
                    success_count = stats["article_count"] - stats["error_count"]
                    success_rate = (
                        f"{(success_count / stats['article_count']) * 100:.1f}%"
                    )

                unique_scrapers = (
                    ", ".join(sorted(stats["scraper_counts"].keys()))
                    if stats["scraper_counts"]
                    else "-"
                )

                row = f"| {domain} | {stats['article_count']:,} | {stats['error_count']:,} | {success_rate} | {unique_scrapers}"

                if scraper_names:
                    for scraper in scraper_names:
                        row += f" | {stats['scraper_counts'].get(scraper, 0)}"

                row += " |\n"
                markdown += row

            markdown += "\n"
            return markdown

        except Exception as e:
            logger.error(f"Error generating domain error table: {e}")
            return f"""
## Domain Article/Error Distribution

**Error**: Failed to generate domain error table: {e}

"""

    @staticmethod
    def section_success_articles_over_time(
        articles: List[Any],
        output_dir: str,
        filename: str = "success_articles_over_time.png",
        max_domains: int = 30,
        max_columns: int = 10,
    ) -> str:
        """Plot number of successful articles over time by top domains, group others as 'Other'.

        Args:
            articles: List of article ORM objects (must have published_date, url_domain, ingestion_error_status)
            output_dir: Directory to save the PNG
            filename: Name of the PNG file
            max_domains: Max number of top domains to show (others grouped)
            max_columns: Max number of time units (columns) in plot
        Returns:
            Markdown string with image reference
        """
        # Prepare data for chart
        data = []
        for article in articles:
            if getattr(article, "ingestion_error_status", None) is None:
                dt = getattr(article, "published_date", None)
                domain = getattr(article, "url_domain", None)
                if dt and domain:
                    data.append({"published_date": dt, "url_domain": domain})

        return create_time_series_chart(
            data=data,
            date_field="published_date",
            group_field="url_domain",
            output_dir=output_dir,
            filename=filename,
            title="Successful Articles Over Time by Domain",
            max_groups=max_domains,
            max_columns=max_columns,
            filter_func=lambda item: item.get("published_date") is not None,
        )

    @staticmethod
    def section_error_distribution_by_domain(
        articles: List[Any],
        output_dir: str,
        filename: str = "error_distribution_by_domain.png",
        max_domains: int = 50,
    ) -> str:
        """Plot error distribution by url_domain and status (stacked bar, top N domains, others grouped).

        Args:
            articles: List of article ORM objects (must have url_domain and ingestion_error_status)
            output_dir: Directory to save the PNG
            filename: Name of the PNG file
            max_domains: Max number of top domains to show (others grouped)
        Returns:
            Markdown string with image reference
        """
        # Prepare data for chart
        data = []
        for article in articles:
            domain = getattr(article, "url_domain", None)
            status = getattr(article, "ingestion_error_status", None) or "no error"
            if domain:
                data.append({"url_domain": domain, "status": status})

        return create_distribution_chart(
            data=data,
            group_field="url_domain",
            status_field="status",
            output_dir=output_dir,
            filename=filename,
            title="Error Distribution by Domain and Status",
            max_groups=max_domains,
        )

    @staticmethod
    def section_field_coverage_summary(articles: List[Any]) -> str:
        """Render a field coverage summary for a list of articles with no errors.

        Args:
            articles: List of article ORM objects (with no errors)
        Returns:
            Markdown string for the field coverage section
        """
        # Define field extractors for articles
        field_extractors = [
            ("title", lambda a: getattr(a, "title", None)),
            ("published_date", lambda a: getattr(a, "published_date", None)),
            ("url_domain", lambda a: getattr(a, "url_domain", None)),
            ("html_content", lambda a: getattr(a, "html_content", None)),
            ("text_content", lambda a: getattr(a, "text_content", None)),
            ("author", lambda a: getattr(a, "author", None)),
            ("tags", lambda a: _extract_field_from_metadata(a, "tags")),
            ("summary", lambda a: _extract_field_from_metadata(a, "summary")),
        ]

        return create_field_coverage_table(
            data=articles,
            field_extractors=field_extractors,
            title="Field Coverage Summary",
        )

    @staticmethod
    def fetch_operation(
        db_path: str,
        operation_cls: Type,
        operation_id: Optional[int] = None,
    ) -> Optional[Any]:
        """Fetch the latest or specified operation from the DB.

        Args:
            db_path: Path to the database
            operation_cls: ORM class for the operation (e.g., IngestionOperation)
            operation_id: If provided, fetch by ID; else fetch latest

        Returns:
            Operation object or None
        """
        logger = get_logger(__name__)

        try:
            adapter = DuckDBAdapter(db_path=db_path)
            with adapter.SessionLocal() as session:
                if operation_id is not None:
                    op = session.query(operation_cls).filter_by(id=operation_id).first()
                else:
                    op = (
                        session.query(operation_cls)
                        .order_by(operation_cls.end_time.desc())
                        .first()
                    )
            return op

        except Exception as e:
            logger.error(f"Error fetching operation from database: {e}")
            return None


def _extract_scraper_name(article: Any) -> Optional[str]:
    """Extract scraper name from article ingestion metadata.

    Args:
        article: Article object with ingestion_metadata

    Returns:
        Scraper name or None if not found
    """
    try:
        ingestion_metadata = getattr(article, "ingestion_metadata", None)
        if ingestion_metadata:
            if isinstance(ingestion_metadata, str):
                meta = json.loads(ingestion_metadata)
            else:
                meta = ingestion_metadata
            return meta.get("scraper_name")
    except (json.JSONDecodeError, AttributeError, TypeError):
        pass
    return None


def _extract_field_from_metadata(article: Any, field: str) -> Any:
    """Extract a field from article metadata.

    Args:
        article: Article object
        field: Field name to extract

    Returns:
        Field value or None if not found
    """
    try:
        metadata = getattr(article, "article_metadata", None)
        if metadata:
            if isinstance(metadata, str):
                meta = json.loads(metadata)
            else:
                meta = metadata
            value = meta.get(field)
            # Check if value is not empty
            if value and (
                isinstance(value, str)
                and value.strip()
                or isinstance(value, list)
                and len(value) > 0
            ):
                return value
    except (json.JSONDecodeError, AttributeError, TypeError):
        pass
    return None
