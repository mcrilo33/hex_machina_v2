"""Ingestion-specific report generator."""

import datetime
import json
from pathlib import Path
from typing import Any, List

from src.hex_machina.ingestion.article_models import ArticleModel
from src.hex_machina.reporting.base_report_generator import BaseReportGenerator
from src.hex_machina.reporting.chart_utils import (
    create_distribution_chart,
    create_field_coverage_table,
    create_time_series_chart,
)
from src.hex_machina.reporting.report_builder import ReportBuilder
from src.hex_machina.storage.models import IngestionOperationDB


class IngestionReportGenerator(BaseReportGenerator):
    """Generates comprehensive HTML ingestion reports with embedded visualizations."""

    def _generate_report_sections(
        self,
        operation: IngestionOperationDB,
        articles: List[ArticleModel],
        report_dir: Path,
    ) -> List[str]:
        """Generate all report sections.

        Args:
            operation: Ingestion operation data
            articles: List of articles
            report_dir: Directory for saving report assets

        Returns:
            List of markdown section strings
        """
        # Filter articles with no errors for field coverage
        articles_no_error = [
            a for a in articles if getattr(a, "ingestion_error_status", None) is None
        ]

        sections = [
            ReportBuilder.section_operation_summary(
                operation, process_type="Ingestion"
            ),
            ReportBuilder.section_domain_error_table(articles),
            self._section_success_articles_over_time(articles, report_dir),
            self._section_error_distribution_by_domain(articles, report_dir),
            self._section_field_coverage_summary(articles_no_error),
        ]

        return sections

    def _build_markdown_report(self, sections: List[str]) -> str:
        """Build the markdown report from sections.

        Args:
            sections: List of markdown section strings

        Returns:
            Complete markdown report
        """
        return ReportBuilder.build_markdown_report(sections, title="Ingestion Report")

    def _get_operation_date(self, operation: IngestionOperationDB) -> datetime.datetime:
        """Get the date from the operation for directory naming.

        Args:
            operation: Ingestion operation data

        Returns:
            Operation date
        """
        return operation.end_time or operation.start_time

    def _get_operation_id(self, operation: IngestionOperationDB) -> str:
        """Get the operation ID for file naming.

        Args:
            operation: Ingestion operation data

        Returns:
            Operation ID as string
        """
        return str(operation.id)

    def _get_report_type(self) -> str:
        """Get the report type name.

        Returns:
            Report type name
        """
        return "ingestion_report"

    def _section_success_articles_over_time(
        self, articles: List[ArticleModel], report_dir: Path
    ) -> str:
        """Generate success articles over time chart section.

        Args:
            articles: List of articles
            report_dir: Directory for saving charts

        Returns:
            Markdown section string
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
            output_dir=str(report_dir),
            filename="success_articles_over_time.png",
            title="Successful Articles Over Time by Domain",
            filter_func=lambda item: item.get("published_date") is not None,
        )

    def _section_error_distribution_by_domain(
        self, articles: List[ArticleModel], report_dir: Path
    ) -> str:
        """Generate error distribution chart section.

        Args:
            articles: List of articles
            report_dir: Directory for saving charts

        Returns:
            Markdown section string
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
            output_dir=str(report_dir),
            filename="error_distribution_by_domain.png",
            title="Error Distribution by Domain and Status",
        )

    def _section_field_coverage_summary(self, articles: List[ArticleModel]) -> str:
        """Generate field coverage summary section.

        Args:
            articles: List of articles with no errors

        Returns:
            Markdown section string
        """
        # Define field extractors for articles
        field_extractors = [
            ("title", lambda a: getattr(a, "title", None)),
            ("published_date", lambda a: getattr(a, "published_date", None)),
            ("url_domain", lambda a: getattr(a, "url_domain", None)),
            ("html_content", lambda a: getattr(a, "html_content", None)),
            ("text_content", lambda a: getattr(a, "text_content", None)),
            ("author", lambda a: getattr(a, "author", None)),
            ("tags", lambda a: self._extract_field_from_metadata(a, "tags")),
            ("summary", lambda a: self._extract_field_from_metadata(a, "summary")),
        ]

        return create_field_coverage_table(
            data=articles,
            field_extractors=field_extractors,
            title="Field Coverage Summary",
        )

    def _extract_field_from_metadata(self, article: ArticleModel, field: str) -> Any:
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


def generate_html_ingestion_report(
    op: IngestionOperationDB,
    articles: List[ArticleModel],
    output_dir: str,
    logger=None,
) -> str:
    """Generate an HTML ingestion report with embedded images and save it in a timestamped directory.

    Args:
        op: IngestionOperationDB object
        articles: List of Article objects for this operation
        output_dir: Directory to save the HTML report
        logger: Logger for logging messages

    Returns:
        Path to the saved HTML report
    """
    generator = IngestionReportGenerator(output_dir, logger)
    return generator.generate_report(op, articles) or ""
