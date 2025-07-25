"""Abstract base classes for report generation."""

import datetime
import os
import re
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any, List, Optional

import markdown2

from src.hex_machina.utils.logging_utils import get_logger


class BaseReportGenerator(ABC):
    """Abstract base class for generating reports with embedded visualizations."""

    def __init__(self, output_dir: str, logger=None):
        """Initialize the report generator.

        Args:
            output_dir: Base directory for report output
            logger: Logger instance (optional)
        """
        self.output_dir = Path(output_dir)
        self.logger = logger or get_logger(__name__)

    def generate_report(
        self,
        operation: Any,
        data: List[Any],
    ) -> Optional[str]:
        """Generate a comprehensive HTML report.

        Args:
            operation: Operation data (e.g., ingestion operation, enrichment operation)
            data: List of data items for this operation

        Returns:
            Path to the generated HTML report, or None if generation failed
        """
        try:
            # Create timestamped report directory
            report_dir = self._create_report_directory(operation)

            # Generate report sections
            sections = self._generate_report_sections(operation, data, report_dir)

            # Build and convert to HTML
            html_path = self._build_html_report(operation, sections, report_dir)

            self.logger.info(f"HTML report generated successfully: {html_path}")
            return str(html_path)

        except Exception as e:
            self.logger.error(f"Failed to generate report: {e}")
            return None

    def _create_report_directory(self, operation: Any) -> Path:
        """Create directory for the report as {output_dir}/{YYYY-MM-DD_HH-MM-SS}_{report_type}/."""
        dt = self._get_operation_date(operation)
        if not dt:
            import datetime

            dt = datetime.datetime.now()
        date_str = dt.strftime("%Y-%m-%d_%H-%M-%S")
        report_type = self._get_report_type()
        report_dir = self.output_dir / f"{date_str}_{report_type}"
        report_dir.mkdir(parents=True, exist_ok=True)
        return report_dir

    def _build_html_report(
        self,
        operation: Any,
        sections: List[str],
        report_dir: Path,
    ) -> Path:
        """Build the final HTML report from markdown sections.

        Args:
            operation: Operation data
            sections: List of markdown section strings
            report_dir: Directory for saving the report

        Returns:
            Path to the generated HTML file
        """
        # Build markdown report
        markdown_report = self._build_markdown_report(sections)

        # Patch image references for relative paths
        markdown_report = self._patch_image_paths(markdown_report)

        # Convert to HTML
        html_content = markdown2.markdown(
            markdown_report, extras=["tables", "fenced-code-blocks"]
        )

        # Apply HTML template
        html_template = self._get_html_template(operation, html_content)

        # Save HTML file
        operation_id = self._get_operation_id(operation)
        html_path = report_dir / f"{self._get_report_type()}_{operation_id}.html"
        html_path.write_text(html_template, encoding="utf-8")

        return html_path

    def _patch_image_paths(self, markdown_content: str) -> str:
        """Patch image references to use relative paths.

        Args:
            markdown_content: Original markdown content

        Returns:
            Markdown content with patched image paths
        """
        return re.sub(
            r"!\[(.*?)\]\((.*?)\)",
            lambda m: f"![{m.group(1)}]({os.path.basename(m.group(2))})",
            markdown_content,
        )

    def _get_html_template(self, operation: Any, html_content: str) -> str:
        """Get the HTML template with embedded styling.

        Args:
            operation: Operation data
            html_content: HTML content to embed

        Returns:
            Complete HTML document
        """
        operation_id = self._get_operation_id(operation)
        report_type = self._get_report_type()

        return f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{report_type.title()} Report {operation_id}</title>
    <style>
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            margin: 0;
            padding: 2em;
            background-color: #f8f9fa;
            color: #333;
            line-height: 1.6;
        }}
        .container {{
            max-width: 1200px;
            margin: 0 auto;
            background: white;
            padding: 2em;
            border-radius: 8px;
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
        }}
        table {{
            border-collapse: collapse;
            width: 100%;
            margin: 1em 0;
            background: white;
        }}
        th, td {{
            border: 1px solid #ddd;
            padding: 0.75em;
            text-align: left;
        }}
        th {{
            background: #f8f9fa;
            font-weight: 600;
            color: #495057;
        }}
        tr:nth-child(even) {{
            background-color: #f8f9fa;
        }}
        img {{
            max-width: 100%;
            height: auto;
            display: block;
            margin: 1em 0;
            border-radius: 4px;
            box-shadow: 0 2px 8px rgba(0,0,0,0.1);
        }}
        pre {{
            background: #f8f9fa;
            padding: 1em;
            border-radius: 4px;
            overflow-x: auto;
            border-left: 4px solid #007bff;
        }}
        h1, h2, h3 {{
            color: #2c3e50;
            margin-top: 1.5em;
            margin-bottom: 0.5em;
        }}
        h1 {{
            border-bottom: 3px solid #007bff;
            padding-bottom: 0.5em;
        }}
        h2 {{
            border-bottom: 1px solid #e9ecef;
            padding-bottom: 0.25em;
        }}
        .highlight {{
            background-color: #fff3cd;
            padding: 0.5em;
            border-radius: 4px;
            border-left: 4px solid #ffc107;
        }}
        .error {{
            color: #dc3545;
            font-weight: 600;
        }}
        .success {{
            color: #28a745;
            font-weight: 600;
        }}
    </style>
</head>
<body>
    <div class="container">
        {html_content}
    </div>
</body>
</html>"""

    def _extract_field_from_metadata(self, article: Any, field: str) -> Any:
        """Extract a field from article metadata.

        Args:
            article: Article object
            field: Field name to extract

        Returns:
            Field value or None if not found
        """
        import json

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
                    (isinstance(value, str) and value.strip())
                    or (isinstance(value, list) and len(value) > 0)
                ):
                    return value
        except (json.JSONDecodeError, AttributeError, TypeError):
            pass
        return None

    @abstractmethod
    def _generate_report_sections(
        self,
        operation: Any,
        data: List[Any],
        report_dir: Path,
    ) -> List[str]:
        """Generate all report sections.

        Args:
            operation: Operation data
            data: List of data items
            report_dir: Directory for saving report assets

        Returns:
            List of markdown section strings
        """
        pass

    @abstractmethod
    def _build_markdown_report(self, sections: List[str]) -> str:
        """Build the markdown report from sections.

        Args:
            sections: List of markdown section strings

        Returns:
            Complete markdown report
        """
        pass

    @abstractmethod
    def _get_operation_date(self, operation: Any) -> Optional[datetime.datetime]:
        """Get the date from the operation for directory naming.

        Args:
            operation: Operation data

        Returns:
            Operation date or None
        """
        pass

    @abstractmethod
    def _get_operation_id(self, operation: Any) -> str:
        """Get the operation ID for file naming.

        Args:
            operation: Operation data

        Returns:
            Operation ID as string
        """
        pass

    @abstractmethod
    def _get_report_type(self) -> str:
        """Get the report type name.

        Returns:
            Report type name (e.g., 'ingestion_report', 'enrichment_report')
        """
        pass


class BaseReportBuilder:
    """Abstract base class for building report sections."""

    @staticmethod
    def build_markdown_report(sections: List[str], title: str = "Report") -> str:
        """Assemble the full Markdown report from a list of Markdown section strings.

        Args:
            sections: List of Markdown strings for each report section
            title: Report title

        Returns:
            Full Markdown report as a string
        """
        if not sections:
            return f"# {title}\n\nNo data available for report generation.\n"

        markdown = f"# {title}\n\n"
        markdown += "\n".join(sections)
        return markdown

    @staticmethod
    def section_operation_summary(
        operation: Any, process_type: str = "Operation"
    ) -> str:
        """Render a summary section for any operation.

        Args:
            operation: ORM object with operation fields
            process_type: Type of process (e.g., 'Ingestion', 'Enrichment')

        Returns:
            Markdown string for the summary section
        """
        logger = get_logger(__name__)

        try:
            # Extract fields with safe defaults
            op_id = getattr(operation, "id", "N/A")
            status = getattr(operation, "status", "unknown")
            start_time = getattr(operation, "start_time", None)
            end_time = getattr(operation, "end_time", None)
            num_items = getattr(
                operation,
                "num_articles_processed",
                getattr(operation, "num_items_processed", 0),
            )
            num_errors = getattr(operation, "num_errors", 0)
            parameters = getattr(operation, "parameters", "{}")

            # Format datetimes for report
            from src.hex_machina.utils.date_parser import format_datetime_for_report

            start_time_str = format_datetime_for_report(start_time)
            end_time_str = format_datetime_for_report(end_time)

            # Compute duration
            duration_str = "-"
            time_per_item = "-"

            if start_time and end_time:
                duration = int((end_time - start_time).total_seconds())
                h = duration // 3600
                m = (duration % 3600) // 60
                s = duration % 60
                duration_str = f"{h:02d}:{m:02d}:{s:02d}"

                # Compute time per item
                if num_items and num_items > 0:
                    time_per_item = f"{duration / num_items:.1f}s"

            # Calculate success rate
            success_rate = "-"
            if num_items > 0:
                success_count = num_items - num_errors
                success_rate = f"{(success_count / num_items) * 100:.1f}%"

            # Render as Markdown
            markdown = f"""
## {process_type} Operation Summary

| Field | Value |
|-------|-------|
| **ID** | {op_id} |
| **Status** | {status} |
| **Start Time** | {start_time_str} |
| **End Time** | {end_time_str} |
| **Duration (H:M:S)** | {duration_str} |
| **Items Processed** | {num_items:,} |
| **Errors** | {num_errors:,} |
| **Success Rate** | {success_rate} |
| **Estimated Time per Item** | {time_per_item} |
| **Parameters** | `{parameters}` |

"""
            return markdown

        except Exception as e:
            logger.error(f"Error generating operation summary: {e}")
            return f"""
## {process_type} Operation Summary

**Error**: Failed to generate operation summary: {e}

"""
