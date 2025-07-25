"""Generic chart utilities for report generation."""

import os
from collections import Counter
from typing import Any, Dict, List, Optional

import matplotlib.pyplot as plt
import pandas as pd

from src.hex_machina.utils.logging_utils import get_logger


def create_time_series_chart(
    data: List[Dict[str, Any]],
    date_field: str,
    group_field: str = None,
    output_dir: str = ".",
    filename: str = "chart.png",
    title: str = "Time Series Chart",
    max_groups: int = 30,
    max_columns: int = 10,
    filter_func: Optional[callable] = None,
    value_field: str = None,  # <-- Add this
) -> str:
    """Create a time series chart with grouped data. Optionally plot a value_field instead of count."""
    logger = get_logger(__name__)

    try:
        # Filter data if filter function provided
        if filter_func:
            data = [item for item in data if filter_func(item)]

        if not data:
            return f"""
## {title}

No data available to plot.

"""

        # Convert to DataFrame
        df = pd.DataFrame(data)

        # Determine time granularity
        min_date, max_date = df[date_field].min(), df[date_field].max()
        days = (max_date - min_date).days + 1

        if days <= max_columns:
            df["time_unit"] = df[date_field].dt.strftime("%d/%m/%Y")
        elif days / 7 <= max_columns:
            df["time_unit"] = (
                df[date_field]
                .dt.to_period("W")
                .apply(lambda p: p.start_time.strftime("%d/%m/%Y"))
            )
        else:
            df["time_unit"] = (
                df[date_field]
                .dt.to_period("M")
                .apply(lambda p: p.start_time.strftime("%m/%Y"))
            )

        # Top groups
        if group_field:
            top_groups = [
                g for g, _ in Counter(df[group_field]).most_common(max_groups)
            ]
            df["group_category"] = df[group_field].apply(
                lambda g: g if g in top_groups else "Other"
            )
        else:
            df["group_category"] = "All"

        # Pivot table
        if value_field:
            aggfunc = "sum"
            values = value_field
        else:
            aggfunc = "count"
            values = group_field if group_field else date_field

        pivot = pd.pivot_table(
            df,
            index="time_unit",
            columns="group_category",
            values=values,
            aggfunc=aggfunc,
            fill_value=0,
        )
        pivot = pivot.sort_index()

        # Plot as stacked bar
        plt.figure(figsize=(max(10, len(pivot) * 1.2), 6))
        pivot.plot(kind="bar", stacked=True, ax=plt.gca())
        plt.title(title)
        plt.xlabel("Date")
        plt.ylabel(value_field.replace("_", " ").title() if value_field else "Count")
        plt.xticks(rotation=45, ha="right")
        plt.legend(bbox_to_anchor=(1.05, 1), loc="upper left")
        plt.tight_layout()

        # Save PNG
        os.makedirs(output_dir, exist_ok=True)
        img_path = os.path.join(output_dir, filename)
        plt.savefig(img_path, dpi=300, bbox_inches="tight")
        plt.close()

        # Return markdown
        return f"""
## {title}

![{title}]({filename})

"""

    except Exception as e:
        logger.error(f"Error generating time series chart: {e}")
        return f"""
## {title}

**Error**: Failed to generate chart: {e}

"""


def create_distribution_chart(
    data: List[Dict[str, Any]],
    group_field: str,
    status_field: str,
    output_dir: str,
    filename: str,
    title: str,
    max_groups: int = 50,
    filter_func: Optional[callable] = None,
) -> str:
    """Create a distribution chart showing status by group.

    Args:
        data: List of data dictionaries
        group_field: Field name to group by
        status_field: Field name containing status information
        output_dir: Directory to save the chart
        filename: Name of the output file
        title: Chart title
        max_groups: Maximum number of groups to show (others grouped as 'Other')
        filter_func: Optional function to filter data before processing

    Returns:
        Markdown string with image reference
    """
    logger = get_logger(__name__)

    try:
        # Filter data if filter function provided
        if filter_func:
            data = [item for item in data if filter_func(item)]

        if not data:
            return f"""
## {title}

No data available to plot.

"""

        # Convert to DataFrame
        df = pd.DataFrame(data)

        # Top groups
        top_groups = [g for g, _ in Counter(df[group_field]).most_common(max_groups)]
        df["group_category"] = df[group_field].apply(
            lambda g: g if g in top_groups else "Other"
        )

        # Pivot for stacked bar
        pivot = pd.pivot_table(
            df,
            index="group_category",
            columns=status_field,
            values=group_field,
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
        plt.title(title)
        plt.xlabel("Group")
        plt.ylabel("Count")
        plt.xticks(rotation=45, ha="right")
        plt.legend(bbox_to_anchor=(1.05, 1), loc="upper left")
        plt.tight_layout()

        # Save PNG
        os.makedirs(output_dir, exist_ok=True)
        img_path = os.path.join(output_dir, filename)
        plt.savefig(img_path, dpi=300, bbox_inches="tight")
        plt.close()

        # Return markdown
        return f"""
## {title}

![{title}]({filename})

"""

    except Exception as e:
        logger.error(f"Error generating distribution chart: {e}")
        return f"""
## {title}

**Error**: Failed to generate chart: {e}

"""


def create_field_coverage_table(
    data: List[Any],
    field_extractors: List[tuple],
    title: str = "Field Coverage Summary",
) -> str:
    """Create a field coverage summary table.

    Args:
        data: List of data objects
        field_extractors: List of (field_name, extractor_function) tuples
        title: Table title

    Returns:
        Markdown string for the coverage table
    """
    logger = get_logger(__name__)

    try:
        if not data:
            return f"""
## {title}

No data available for analysis.

"""

        total = len(data)
        rows = []

        for field, extractor in field_extractors:
            count = sum(1 for item in data if extractor(item))
            percent = (count / total * 100) if total > 0 else 0
            rows.append((field, percent, count))

        # Build Markdown
        markdown = f"""
## {title}

**Total items: {total:,}**

| Field | Coverage (%) | Count |
|-------|--------------|-------|
"""
        for field, percent, count in rows:
            markdown += f"| {field} | {percent:.1f}% | {count:,} |\n"

        markdown += "\n"
        return markdown

    except Exception as e:
        logger.error(f"Error generating field coverage table: {e}")
        return f"""
## {title}

**Error**: Failed to generate coverage table: {e}

"""
