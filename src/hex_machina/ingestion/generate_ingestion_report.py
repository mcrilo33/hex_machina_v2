import os

import markdown2

from hex_machina.reporting.report_builder import (
    build_markdown_report,
    section_domain_error_table,
    section_error_distribution_by_domain,
    section_field_coverage_summary,
    section_operation_summary,
    section_success_articles_over_time,
)
from hex_machina.storage.models import IngestionOperationDB


def generate_html_ingestion_report(
    op: IngestionOperationDB,
    articles: list,
    output_dir: str,
    logger,
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
    import datetime
    import re

    # Determine date for directory name
    dt = op.end_time or op.start_time
    if not dt:
        dt = datetime.datetime.now()
    date_str = dt.strftime("%Y-%m-%d_%H-%M-%S")
    dir_name = f"ingestion_report_{op.id}_{date_str}"
    report_dir = os.path.join(output_dir, dir_name)
    os.makedirs(report_dir, exist_ok=True)

    # Patch image references in markdown to be just the filename (since images are saved in report_dir)
    def patch_image_paths(md: str) -> str:
        # Replace ![alt](filename.png) with ![alt](filename.png) (no path change needed if images are saved in report_dir)
        return re.sub(
            r"!\[(.*?)\]\((.*?)\)",
            lambda m: f"![{m.group(1)}]({os.path.basename(m.group(2))})",
            md,
        )

    articles_no_error = [
        a for a in articles if getattr(a, "ingestion_error_status", None) is None
    ]
    sections = [
        section_operation_summary(op, process_type="Ingestion"),
        section_domain_error_table(articles),
        section_success_articles_over_time(articles, report_dir),
        section_error_distribution_by_domain(articles, report_dir),
        section_field_coverage_summary(articles_no_error),
    ]
    markdown_report = build_markdown_report(sections, title="Ingestion Report")
    markdown_report = patch_image_paths(markdown_report)
    try:
        html_report = markdown2.markdown(
            markdown_report, extras=["tables", "fenced-code-blocks"]
        )
        html_template = f"""
<!DOCTYPE html>
<html lang=\"en\">
<head>
    <meta charset=\"UTF-8\">
    <title>Ingestion Report {op.id}</title>
    <style>
        body {{ font-family: Arial, sans-serif; margin: 2em; }}
        table {{ border-collapse: collapse; width: 100%; }}
        th, td {{ border: 1px solid #ccc; padding: 0.5em; }}
        th {{ background: #f0f0f0; }}
        img {{ max-width: 100%; height: auto; display: block; margin: 1em 0; }}
        pre {{ background: #f8f8f8; padding: 1em; border-radius: 4px; }}
        h1, h2, h3 {{ color: #2c3e50; }}
    </style>
</head>
<body>
{html_report}
</body>
</html>
"""
        output_path = os.path.join(report_dir, f"ingestion_report_{op.id}.html")
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(html_template)
        logger.info(f"HTML report saved to: {output_path}")
        return output_path
    except Exception as e:
        logger.error(f"Failed to convert Markdown to HTML: {e}")
        return ""
