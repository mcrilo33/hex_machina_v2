"""Generic chart utilities for report generation."""

import logging
import os
from collections import Counter
from typing import Any, Dict, List, Optional

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

# Suppress matplotlib font manager debug messages
logging.getLogger("matplotlib.font_manager").setLevel(logging.WARNING)


def create_content_length_distribution(
    data: List[Dict[str, Any]],
    length_field: str,
    output_dir: str,
    filename: str,
    title: str,
    bins: int = 20,
    max_length: Optional[int] = None,
    filter_func: Optional[callable] = None,
) -> str:
    """Create a histogram distribution chart for content lengths.

    Args:
        data: List of data objects
        length_field: Field name containing the length values
        output_dir: Directory to save the chart
        filename: Output filename
        title: Chart title
        bins: Number of histogram bins
        max_length: Maximum length to include (for outlier handling)
        filter_func: Optional filter function for data

    Returns:
        Markdown string for the chart
    """
    logger = logging.getLogger(__name__)

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

        # Extract length values
        lengths = df[length_field].dropna()

        if len(lengths) == 0:
            return f"""
## {title}

No valid length data available.

"""

        # Apply max_length filter if specified
        if max_length is not None:
            lengths = lengths[lengths <= max_length]

        if len(lengths) == 0:
            return f"""
## {title}

No data within the specified length range.

"""

        # Create histogram
        plt.figure(figsize=(12, 6))

        # Calculate optimal bin width using Freedman-Diaconis rule
        q75, q25 = np.percentile(lengths, [75, 25])
        iqr = q75 - q25
        bin_width = 2 * iqr / (len(lengths) ** (1 / 3))
        bin_count = max(10, min(bins, int((lengths.max() - lengths.min()) / bin_width)))

        plt.hist(lengths, bins=bin_count, edgecolor="black", alpha=0.7)
        plt.title(title)
        plt.xlabel(f"{length_field.replace('_', ' ').title()} Length")
        plt.ylabel("Frequency")

        # Add statistics
        mean_length = lengths.mean()
        median_length = lengths.median()
        plt.axvline(
            mean_length, color="red", linestyle="--", label=f"Mean: {mean_length:.0f}"
        )
        plt.axvline(
            median_length,
            color="green",
            linestyle="--",
            label=f"Median: {median_length:.0f}",
        )
        plt.legend()

        plt.grid(True, alpha=0.3)
        plt.tight_layout()

        # Save PNG
        os.makedirs(output_dir, exist_ok=True)
        img_path = os.path.join(output_dir, filename)
        plt.savefig(img_path, dpi=300, bbox_inches="tight")
        plt.close()

        # Calculate statistics for markdown
        stats = {
            "count": len(lengths),
            "mean": lengths.mean(),
            "median": lengths.median(),
            "std": lengths.std(),
            "min": lengths.min(),
            "max": lengths.max(),
            "q25": lengths.quantile(0.25),
            "q75": lengths.quantile(0.75),
        }

        # Return markdown
        return f"""
## {title}

![{title}]({filename})

**Statistics:**
- **Count**: {stats['count']:,}
- **Mean**: {stats['mean']:.0f}
- **Median**: {stats['median']:.0f}
- **Std Dev**: {stats['std']:.0f}
- **Min**: {stats['min']:.0f}
- **Max**: {stats['max']:.0f}
- **Q25**: {stats['q25']:.0f}
- **Q75**: {stats['q75']:.0f}

"""

    except Exception as e:
        logger.error(f"Error generating content length distribution: {e}")
        return f"""
## {title}

**Error**: Failed to generate chart: {e}

"""


def create_text_html_ratio_distribution(
    data: List[Dict[str, Any]],
    html_length_field: str,
    text_length_field: str,
    output_dir: str,
    filename: str,
    title: str = "Text-to-HTML Ratio Distribution",
    bins: int = 20,
    max_ratio: float = 1.0,
    filter_func: Optional[callable] = None,
) -> str:
    """Create a histogram distribution chart for text-to-HTML ratios.

    Args:
        data: List of data objects
        html_length_field: Field name containing HTML content lengths
        text_length_field: Field name containing text content lengths
        output_dir: Directory to save the chart
        filename: Output filename
        title: Chart title
        bins: Number of histogram bins
        max_ratio: Maximum ratio to include (for outlier handling)
        filter_func: Optional filter function for data

    Returns:
        Markdown string for the chart
    """
    logger = logging.getLogger(__name__)

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

        # Calculate ratios
        df["ratio"] = df[text_length_field] / df[html_length_field]
        ratios = df["ratio"].dropna()

        # Filter out invalid ratios (negative, infinite, or NaN)
        ratios = ratios[(ratios > 0) & (ratios < np.inf)]

        if len(ratios) == 0:
            return f"""
## {title}

No valid ratio data available.

"""

        # Apply max_ratio filter if specified
        if max_ratio is not None:
            ratios = ratios[ratios <= max_ratio]

        if len(ratios) == 0:
            return f"""
## {title}

No data within the specified ratio range.

"""

        # Create histogram
        plt.figure(figsize=(12, 6))

        # Calculate optimal bin width
        q75, q25 = np.percentile(ratios, [75, 25])
        iqr = q75 - q25
        bin_width = 2 * iqr / (len(ratios) ** (1 / 3))
        bin_count = max(10, min(bins, int((ratios.max() - ratios.min()) / bin_width)))

        plt.hist(ratios, bins=bin_count, edgecolor="black", alpha=0.7)
        plt.title(title)
        plt.xlabel("Text-to-HTML Ratio")
        plt.ylabel("Frequency")

        # Add statistics
        mean_ratio = ratios.mean()
        median_ratio = ratios.median()
        plt.axvline(
            mean_ratio, color="red", linestyle="--", label=f"Mean: {mean_ratio:.3f}"
        )
        plt.axvline(
            median_ratio,
            color="green",
            linestyle="--",
            label=f"Median: {median_ratio:.3f}",
        )
        plt.legend()

        plt.grid(True, alpha=0.3)
        plt.tight_layout()

        # Save PNG
        os.makedirs(output_dir, exist_ok=True)
        img_path = os.path.join(output_dir, filename)
        plt.savefig(img_path, dpi=300, bbox_inches="tight")
        plt.close()

        # Calculate statistics for markdown
        stats = {
            "count": len(ratios),
            "mean": ratios.mean(),
            "median": ratios.median(),
            "std": ratios.std(),
            "min": ratios.min(),
            "max": ratios.max(),
            "q25": ratios.quantile(0.25),
            "q75": ratios.quantile(0.75),
        }

        # Return markdown
        return f"""
## {title}

![{title}]({filename})

**Statistics:**
- **Count**: {stats['count']:,}
- **Mean**: {stats['mean']:.3f}
- **Median**: {stats['median']:.3f}
- **Std Dev**: {stats['std']:.3f}
- **Min**: {stats['min']:.3f}
- **Max**: {stats['max']:.3f}
- **Q25**: {stats['q25']:.3f}
- **Q75**: {stats['q75']:.3f}

"""

    except Exception as e:
        logger.error(f"Error generating text-to-HTML ratio distribution: {e}")
        return f"""
## {title}

**Error**: Failed to generate chart: {e}

"""


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
    logger = logging.getLogger(__name__)

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
    logger = logging.getLogger(__name__)

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
    logger = logging.getLogger(__name__)

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
