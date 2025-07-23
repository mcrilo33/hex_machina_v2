"""Modular Markdown report builder for pipeline operations (ingestion, enrichment, etc.)."""

import os
from collections import Counter, defaultdict
from typing import Any, Optional, Type

import matplotlib.pyplot as plt
import pandas as pd

from hex_machina.storage.duckdb_adapter import DuckDBAdapter
from hex_machina.utils.date_parser import format_datetime_for_report


def build_markdown_report(sections: list[str], title: str = "Pipeline Report") -> str:
    """Assemble the full Markdown report from a list of Markdown section strings.

    Args:
        sections: List of Markdown strings for each report section
        title: Report title (e.g., 'Ingestion Report', 'Enrichment Report')

    Returns:
        Full Markdown report as a string
    """
    markdown = f"# {title}\n\n"
    markdown += "\n".join(sections)
    return markdown


def section_operation_summary(operation: Any, process_type: str = "Pipeline") -> str:
    """Render a summary section for any operation (ingestion, enrichment, etc.).

    Args:
        operation: ORM object with operation fields (must have id, start_time, end_time, status, num_articles_processed, num_errors, parameters)
        process_type: Type of process (e.g., 'Ingestion', 'Enrichment')

    Returns:
        Markdown string for the summary section
    """
    # Extract fields
    op_id = getattr(operation, "id", None)
    status = getattr(operation, "status", "-")
    start_time = getattr(operation, "start_time", None)
    end_time = getattr(operation, "end_time", None)
    # Format datetimes for report
    start_time_str = format_datetime_for_report(start_time)
    end_time_str = format_datetime_for_report(end_time)
    num_articles = getattr(operation, "num_articles_processed", None)
    num_errors = getattr(operation, "num_errors", None)
    parameters = getattr(operation, "parameters", None)
    # Compute duration
    duration = None
    duration_str = "-"
    if start_time and end_time:
        duration = int((end_time - start_time).total_seconds())
        h = duration // 3600
        m = (duration % 3600) // 60
        s = duration % 60
        duration_str = f"{h}:{m}:{s}"
    # Compute time per article
    time_per_article = None
    if duration is not None and num_articles and num_articles > 0:
        time_per_article = int(duration / num_articles)
    # Render as Markdown
    markdown = f"""
## {process_type} Operation Summary

| Field | Value |
|-------|-------|
| ID | {op_id} |
| Status | {status} |
| Start Time | {start_time_str} |
| End Time | {end_time_str} |
| Duration (H:M:S) | **{duration_str}** |
| Articles Processed | {num_articles} |
| Errors | {num_errors} |
| Estimated Time per Article (s) | **{time_per_article}** |
| Parameters | `{parameters}` |

"""
    return markdown


def section_domain_error_table(articles: list) -> str:
    """Render a table of article and error counts per url_domain, including scraper_name counts.

    Args:
        articles: List of article ORM objects (must have url_domain and ingestion_error_status fields)
    Returns:
        Markdown string for the table section
    """
    import json

    # First, collect all scraper_names
    scraper_names = set()
    domain_stats = defaultdict(
        lambda: {"article_count": 0, "error_count": 0, "scraper_counts": Counter()}
    )
    for article in articles:
        domain = getattr(article, "url_domain", "-")
        has_error = getattr(article, "ingestion_error_status", None) is not None
        domain_stats[domain]["article_count"] += 1
        if has_error:
            domain_stats[domain]["error_count"] += 1
        # Parse scraper_name from ingestion_metadata
        scraper_name = None
        ingestion_metadata = getattr(article, "ingestion_metadata", None)
        if ingestion_metadata:
            try:
                meta = json.loads(ingestion_metadata)
                scraper_name = meta.get("scraper_name")
            except Exception:
                scraper_name = None
        if scraper_name:
            domain_stats[domain]["scraper_counts"][scraper_name] += 1
            scraper_names.add(scraper_name)
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
    header = (
        "| URL_DOMAIN | ARTICLE COUNT | ERROR COUNT | SCRAPER NAMES |"
        + " | ".join(scraper_names)
        + " |\n"
    )
    separator = (
        "|------------|---------------|-------------|---------------|"
        + "|".join(["-" * 15] * len(scraper_names))
        + "|\n"
    )
    markdown += header
    markdown += separator
    for domain, stats in sorted_stats:
        unique_scrapers = (
            ", ".join(sorted(stats["scraper_counts"].keys()))
            if stats["scraper_counts"]
            else "-"
        )
        row = f"| {domain} | {stats['article_count']} | {stats['error_count']} | {unique_scrapers} "
        for scraper in scraper_names:
            row += f"| {stats['scraper_counts'].get(scraper, 0)} "
        row += "|\n"
        markdown += row
    markdown += "\n"
    return markdown


def section_success_articles_over_time(
    articles: list,
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
    # Filter to successful articles
    rows = []
    for a in articles:
        if getattr(a, "ingestion_error_status", None) is None:
            dt = getattr(a, "published_date", None)
            domain = getattr(a, "url_domain", None)
            if dt and domain:
                rows.append({"published_date": dt, "url_domain": domain})
    if not rows:
        return "## Successful Articles Over Time by Domain\n\nNo successful articles to plot.\n\n"
    from collections import Counter

    df = pd.DataFrame(rows)
    # Determine time granularity
    min_date, max_date = df["published_date"].min(), df["published_date"].max()
    days = (max_date - min_date).days + 1
    if days <= max_columns:
        df["time_unit"] = df["published_date"].dt.strftime("%d/%m/%Y")
    elif days / 7 <= max_columns:
        df["time_unit"] = (
            df["published_date"]
            .dt.to_period("W")
            .apply(lambda p: p.start_time.strftime("%d/%m/%Y"))
        )
    else:
        df["time_unit"] = (
            df["published_date"]
            .dt.to_period("M")
            .apply(lambda p: p.start_time.strftime("%m/%Y"))
        )
    # Top domains
    top_domains = [d for d, _ in Counter(df["url_domain"]).most_common(max_domains)]
    df["domain_group"] = df["url_domain"].apply(
        lambda d: d if d in top_domains else "Other"
    )
    # Pivot table
    pivot = pd.pivot_table(
        df,
        index="time_unit",
        columns="domain_group",
        values="url_domain",
        aggfunc="count",
        fill_value=0,
    )
    pivot = pivot.sort_index()
    # Plot as stacked bar
    plt.figure(figsize=(max(10, len(pivot) * 1.2), 6))
    pivot.plot(kind="bar", stacked=True, ax=plt.gca())
    plt.title("Successful Articles Over Time by Domain")
    plt.xlabel("Date")
    plt.ylabel("Article Count")
    plt.xticks(rotation=45, ha="right")
    plt.tight_layout()
    # Save PNG
    import os

    os.makedirs(output_dir, exist_ok=True)
    img_path = os.path.join(output_dir, filename)
    plt.savefig(img_path)
    plt.close()
    # Markdown
    markdown = f"""
## Successful Articles Over Time by Domain

![Success Articles Over Time]({filename})

"""
    return markdown


def section_error_distribution_by_domain(
    articles: list,
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
    from collections import Counter

    import pandas as pd

    # Prepare data: status = error string or 'no error'
    rows = []
    for a in articles:
        domain = getattr(a, "url_domain", None)
        status = getattr(a, "ingestion_error_status", None) or "no error"
        if domain:
            rows.append({"url_domain": domain, "status": status})
    if not rows:
        return "## Error Distribution by Domain and Status\n\nNo articles to plot.\n\n"
    df = pd.DataFrame(rows)
    # Top domains
    top_domains = [d for d, _ in Counter(df["url_domain"]).most_common(max_domains)]
    df["domain_group"] = df["url_domain"].apply(
        lambda d: d if d in top_domains else "Other"
    )
    # Pivot for stacked bar
    pivot = pd.pivot_table(
        df,
        index="domain_group",
        columns="status",
        values="url_domain",
        aggfunc="count",
        fill_value=0,
    )
    # Sort by total count descending
    pivot["_total"] = pivot.sum(axis=1)
    pivot = pivot.sort_values("_total", ascending=False).drop(columns=["_total"])
    # Plot
    plt.figure(figsize=(max(10, len(pivot) * 0.5), 6))
    pivot.plot(
        kind="bar",
        stacked=True,
        ax=plt.gca(),
        colormap="tab20",
        edgecolor="black",
    )
    plt.title("Error Distribution by Domain and Status")
    plt.xlabel("URL Domain")
    plt.ylabel("Article Count")
    plt.xticks(rotation=45, ha="right")
    plt.tight_layout()
    # Save PNG
    os.makedirs(output_dir, exist_ok=True)
    img_path = os.path.join(output_dir, filename)
    plt.savefig(img_path)
    plt.close()
    # Markdown
    markdown = f"""
## Error Distribution by Domain and Status

![Error Distribution]({filename})

"""
    return markdown


def section_field_coverage_summary(articles: list) -> str:
    """Render a field coverage summary for a list of articles with no errors.

    Args:
        articles: List of article ORM objects (with no errors)
    Returns:
        Markdown string for the field coverage section
    """
    fields = [
        ("title", lambda a: getattr(a, "title", None)),
        ("published_date", lambda a: getattr(a, "published_date", None)),
        ("url_domain", lambda a: getattr(a, "url_domain", None)),
        ("html_content", lambda a: getattr(a, "html_content", None)),
        ("author", lambda a: getattr(a, "author", None)),
        (
            "tags",
            lambda a: getattr(
                getattr(a, "article_metadata", {}), "get", lambda k, d=None: None
            )("tags"),
        ),
        (
            "summary",
            lambda a: getattr(
                getattr(a, "article_metadata", {}), "get", lambda k, d=None: None
            )("summary"),
        ),
    ]
    total = len(articles)
    rows = []
    for field, getter in fields:
        count = sum(1 for a in articles if getter(a))
        percent = (count / total * 100) if total > 0 else 0
        rows.append((field, percent, count))
    # Build Markdown
    markdown = f"""
## Field Coverage Summary

**Total articles (no errors): {total}**

| FIELD | COVERAGE (%) | COUNT |
|-------|--------------|-------|
"""
    for field, percent, count in rows:
        markdown += f"| {field} | {percent:.1f}% | {count} |\n"
    markdown += "\n"
    return markdown


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
