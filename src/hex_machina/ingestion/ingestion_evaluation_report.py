import datetime
from pathlib import Path
from typing import Any, List

from src.hex_machina.ingestion.ingestion_report import IngestionReportGenerator
from src.hex_machina.reporting.base_report_generator import BaseReportGenerator
from src.hex_machina.reporting.chart_utils import create_time_series_chart
from src.hex_machina.reporting.report_builder import ReportBuilder
from src.hex_machina.storage.models import IngestionOperationDB


class IngestionEvaluationReportGenerator(BaseReportGenerator):
    """Generates an evaluation report over all ingestion operations and articles."""

    def _generate_report_sections(
        self,
        operations: List[IngestionOperationDB],
        articles: List[Any],  # ArticleModel or ArticleDB
        report_dir: Path,
    ) -> List[str]:
        sections = [
            IngestionEvaluationReportGenerator._section_operations_over_time(
                operations, report_dir
            ),
            # Reuse the following from IngestionReportGenerator
            IngestionReportGenerator._section_success_articles_over_time(
                self, articles, report_dir
            ),
            IngestionReportGenerator._section_error_distribution_by_domain(
                self, articles, report_dir
            ),
            IngestionReportGenerator._section_field_coverage_summary(self, articles),
            IngestionEvaluationReportGenerator._section_content_length_distributions(
                self, articles, report_dir
            ),
            IngestionEvaluationReportGenerator._section_short_html_by_domain(
                self, articles, report_dir
            ),
            IngestionEvaluationReportGenerator._section_short_text_by_domain(
                self, articles, report_dir
            ),
            IngestionEvaluationReportGenerator._section_low_text_html_ratio_by_domain(
                self, articles, report_dir
            ),
        ]
        return sections

    def _build_markdown_report(self, sections: List[str]) -> str:
        return ReportBuilder.build_markdown_report(
            sections, title="Ingestion Evaluation Report"
        )

    def _get_operation_date(
        self, operations: List[IngestionOperationDB]
    ) -> datetime.datetime:
        # For evaluation reports, use current time instead of operation dates
        return datetime.datetime.now()

    def _get_operation_id(self, operations: List[IngestionOperationDB]) -> str:
        return "all"

    def _get_report_type(self) -> str:
        return "ingestion_evaluation_report"

    @staticmethod
    def _section_operations_over_time(
        operations: List[IngestionOperationDB], report_dir: Path
    ) -> str:
        # Prepare data for chart
        data = []
        for op in operations:
            if op.start_time and op.end_time:
                duration = (op.end_time - op.start_time).total_seconds()
            else:
                duration = None
            items_processed = op.num_articles_processed or 0
            errors = op.num_errors or 0
            total = items_processed + errors
            success_rate = items_processed / total if total else 0
            time_per_item = duration / items_processed if items_processed else None
            data.append(
                {
                    "start_time": op.start_time,
                    "duration": duration,
                    "items_processed": items_processed,
                    "errors": errors,
                    "success_rate": success_rate,
                    "time_per_item": time_per_item,
                }
            )

        # Plot each metric over time
        charts = []
        for metric, label in [
            ("duration", "Duration (s)"),
            ("items_processed", "Items Processed"),
            ("errors", "Errors"),
            ("success_rate", "Success Rate"),
            ("time_per_item", "Estimated Time per Item (s)"),
        ]:
            chart = create_time_series_chart(
                data=data,
                date_field="start_time",
                group_field=None,
                value_field=metric,
                output_dir=str(report_dir),
                filename=f"{metric}_over_time.png",
                title=f"{label} Over Time",
                filter_func=lambda item: item.get("start_time") is not None
                and item.get(metric) is not None,
            )
            charts.append(chart)
        # Combine charts into a markdown section
        section = "## Ingestion Operations Overview\n\n"
        section += "\n".join(charts)
        return section

    @staticmethod
    def _section_content_length_distributions(
        self, articles: List[Any], report_dir: Path
    ) -> str:
        if not articles:
            return "## Content Length Distributions\n\nNo articles found.\n\n"

        # Filter for error-free articles
        error_free_articles = [
            a for a in articles if not getattr(a, "ingestion_error_status", None)
        ]

        if not error_free_articles:
            return (
                "## Content Length Distributions\n\nNo error-free articles found.\n\n"
            )

        html_lengths = []
        text_lengths = []
        ratios = []

        for article in error_free_articles:
            html_content = getattr(article, "html_content", "")
            text_content = getattr(article, "text_content", "")

            html_length = len(html_content) if html_content else 0
            text_length = len(text_content) if text_content else 0
            ratio = text_length / html_length if html_length > 0 else 0

            # Filter out articles with text_content length over 20000
            if ratio > 0.05 or text_length > 5000 or html_length > 50000:
                continue

            html_lengths.append(html_length)
            text_lengths.append(text_length)
            ratios.append(ratio)

        if not html_lengths:
            return "## Content Length Distributions\n\nNo content data available.\n\n"

        # Create bar plots for distributions
        import matplotlib.pyplot as plt
        import numpy as np

        charts = []

        # HTML Content Length Distribution
        plt.figure(figsize=(10, 6))
        plt.hist(html_lengths, bins=20, alpha=0.7, color="skyblue", edgecolor="black")
        plt.title("HTML Content Length Distribution - All Articles")
        plt.xlabel("HTML Content Length (characters)")
        plt.ylabel("Number of Articles")
        plt.grid(True, alpha=0.3)

        # Add statistics as text
        mean_html = np.mean(html_lengths)
        median_html = np.median(html_lengths)
        plt.axvline(
            mean_html, color="red", linestyle="--", label=f"Mean: {mean_html:.0f}"
        )
        plt.axvline(
            median_html,
            color="orange",
            linestyle="--",
            label=f"Median: {median_html:.0f}",
        )
        plt.legend()

        html_chart_path = report_dir / "html_length_distribution_all.png"
        plt.savefig(html_chart_path, dpi=300, bbox_inches="tight")
        plt.close()
        charts.append(str(html_chart_path))

        # Text Content Length Distribution
        plt.figure(figsize=(10, 6))
        plt.hist(
            text_lengths, bins=20, alpha=0.7, color="lightgreen", edgecolor="black"
        )
        plt.title("Text Content Length Distribution - All Articles")
        plt.xlabel("Text Content Length (characters)")
        plt.ylabel("Number of Articles")
        plt.grid(True, alpha=0.3)

        # Add statistics as text
        mean_text = np.mean(text_lengths)
        median_text = np.median(text_lengths)
        plt.axvline(
            mean_text, color="red", linestyle="--", label=f"Mean: {mean_text:.0f}"
        )
        plt.axvline(
            median_text,
            color="orange",
            linestyle="--",
            label=f"Median: {median_text:.0f}",
        )
        plt.legend()

        text_chart_path = report_dir / "text_length_distribution_all.png"
        plt.savefig(text_chart_path, dpi=300, bbox_inches="tight")
        plt.close()
        charts.append(str(text_chart_path))

        # Text/HTML Ratio Distribution (as percentage)
        if ratios:
            # Convert ratios to percentages
            ratio_percentages = [ratio * 100 for ratio in ratios]

            plt.figure(figsize=(10, 6))
            plt.hist(
                ratio_percentages,
                bins=20,
                alpha=0.7,
                color="lightcoral",
                edgecolor="black",
            )
            plt.title("Text/HTML Ratio Distribution - All Articles")
            plt.xlabel("Text/HTML Ratio (%)")
            plt.ylabel("Number of Articles")
            plt.grid(True, alpha=0.3)

            # Add statistics as text
            mean_ratio = np.mean(ratio_percentages)
            median_ratio = np.median(ratio_percentages)
            plt.axvline(
                mean_ratio,
                color="red",
                linestyle="--",
                label=f"Mean: {mean_ratio:.1f}%",
            )
            plt.axvline(
                median_ratio,
                color="orange",
                linestyle="--",
                label=f"Median: {median_ratio:.1f}%",
            )
            plt.legend()

            ratio_chart_path = report_dir / "text_html_ratio_distribution_all.png"
            plt.savefig(ratio_chart_path, dpi=300, bbox_inches="tight")
            plt.close()
            charts.append(str(ratio_chart_path))

        # Create summary statistics text
        import statistics

        html_stats = {
            "count": len(html_lengths),
            "mean": statistics.mean(html_lengths),
            "median": statistics.median(html_lengths),
            "min": min(html_lengths),
            "max": max(html_lengths),
        }

        text_stats = {
            "count": len(text_lengths),
            "mean": statistics.mean(text_lengths),
            "median": statistics.median(text_lengths),
            "min": min(text_lengths),
            "max": max(text_lengths),
        }

        ratio_stats = {
            "count": len(ratios),
            "mean": statistics.mean(ratios),
            "median": statistics.median(ratios),
            "min": min(ratios),
            "max": max(ratios),
        }

        section = "## Content Length Distributions\n\n"

        # Add charts
        section += "### HTML Content Length Distribution\n\n"
        section += f"![HTML Content Length Distribution]({html_chart_path.name})\n\n"
        section += f"- Count: {html_stats['count']}\n"
        section += f"- Mean: {html_stats['mean']:.0f} characters\n"
        section += f"- Median: {html_stats['median']:.0f} characters\n"
        section += f"- Range: {html_stats['min']} - {html_stats['max']} characters\n\n"

        section += "### Text Content Length Distribution\n\n"
        section += f"![Text Content Length Distribution]({text_chart_path.name})\n\n"
        section += f"- Count: {text_stats['count']}\n"
        section += f"- Mean: {text_stats['mean']:.0f} characters\n"
        section += f"- Median: {text_stats['median']:.0f} characters\n"
        section += f"- Range: {text_stats['min']} - {text_stats['max']} characters\n\n"

        if ratios:
            section += "### Text/HTML Ratio Distribution\n\n"
            section += f"![Text/HTML Ratio Distribution]({ratio_chart_path.name})\n\n"
            section += f"- Count: {ratio_stats['count']}\n"
            section += f"- Mean: {ratio_stats['mean'] * 100:.1f}%\n"
            section += f"- Median: {ratio_stats['median'] * 100:.1f}%\n"
            section += f"- Range: {ratio_stats['min'] * 100:.1f}% - {ratio_stats['max'] * 100:.1f}%\n\n"
        return section

    @staticmethod
    def _section_short_html_by_domain(
        self, articles: List[Any], report_dir: Path
    ) -> str:
        """Create a bar plot showing percentage of articles with HTML content < 5000 by domain."""
        if not articles:
            return "## Short HTML Content by Domain\n\nNo articles found.\n\n"

        # Filter for error-free articles
        error_free_articles = [
            a for a in articles if not getattr(a, "ingestion_error_status", None)
        ]
        if not error_free_articles:
            return (
                "## Short HTML Content by Domain\n\nNo error-free articles found.\n\n"
            )

        # Count total articles by domain
        total_domain_counts = {}
        for article in error_free_articles:
            domain = getattr(article, "url_domain", "Unknown")
            total_domain_counts[domain] = total_domain_counts.get(domain, 0) + 1

        # Filter for error-free articles with HTML content < 5000
        short_html_articles = [
            a for a in error_free_articles if len(getattr(a, "html_content", "")) < 5000
        ]
        if not short_html_articles:
            return "## Short HTML Content by Domain\n\nNo articles with HTML content < 5000 found.\n\n"

        # Count short HTML articles by domain and calculate percentages
        domain_percentages = {}
        for article in short_html_articles:
            domain = getattr(article, "url_domain", "Unknown")
            domain_percentages[domain] = domain_percentages.get(domain, 0) + 1
        for domain in domain_percentages:
            total_articles = total_domain_counts.get(domain, 0)
            if total_articles > 0:
                domain_percentages[domain] = (
                    domain_percentages[domain] / total_articles
                ) * 100

        # Sort by percentage descending
        sorted_domains = sorted(
            domain_percentages.items(), key=lambda x: x[1], reverse=True
        )

        # Create bar plot
        import matplotlib.pyplot as plt

        domains = [item[0] for item in sorted_domains]
        percentages = [item[1] for item in sorted_domains]
        plt.figure(figsize=(12, 8))
        bars = plt.bar(
            range(len(domains)),
            percentages,
            color="lightcoral",
            alpha=0.7,
            edgecolor="black",
        )
        plt.title("% of Articles with HTML Content < 5000 Characters by Domain")
        plt.xlabel("Domain")
        plt.ylabel("% of Articles")
        plt.xticks(range(len(domains)), domains, rotation=45, ha="right")
        plt.grid(True, alpha=0.3)
        for bar, pct in zip(bars, percentages):
            plt.text(
                bar.get_x() + bar.get_width() / 2,
                bar.get_height() + 0.1,
                f"{pct:.1f}%",
                ha="center",
                va="bottom",
            )
        plt.tight_layout()
        chart_path = report_dir / "short_html_by_domain.png"
        plt.savefig(chart_path, dpi=300, bbox_inches="tight")
        plt.close()
        section = "## Short HTML Content by Domain\n\n"
        section += f"![Short HTML Content by Domain]({chart_path.name})\n\n"
        section += "Bar heights show the percentage of articles for each domain with HTML content < 5000 characters.\n\n"
        section += "### Top Domains with Short HTML Content (by %):\n\n"
        for domain, pct in sorted_domains[:10]:
            section += f"- **{domain}**: {pct:.1f}%\n"
        if len(sorted_domains) > 10:
            section += f"\n*... and {len(sorted_domains) - 10} more domains*\n"
        return section

    @staticmethod
    def _section_short_text_by_domain(
        self, articles: List[Any], report_dir: Path
    ) -> str:
        """Create a bar plot showing percentage of articles with text content < 5000 by domain."""
        if not articles:
            return "## Short Text Content by Domain\n\nNo articles found.\n\n"
        # Filter for error-free articles
        error_free_articles = [
            a for a in articles if not getattr(a, "ingestion_error_status", None)
        ]
        if not error_free_articles:
            return (
                "## Short Text Content by Domain\n\nNo error-free articles found.\n\n"
            )
        # Count total articles by domain
        total_domain_counts = {}
        for article in error_free_articles:
            domain = getattr(article, "url_domain", "Unknown")
            total_domain_counts[domain] = total_domain_counts.get(domain, 0) + 1
        # Filter for error-free articles with text content < 5000
        short_text_articles = [
            a for a in error_free_articles if len(getattr(a, "text_content", "")) < 5000
        ]
        if not short_text_articles:
            return "## Short Text Content by Domain\n\nNo articles with text content < 5000 found.\n\n"
        # Count short text articles by domain and calculate percentages
        domain_percentages = {}
        for article in short_text_articles:
            domain = getattr(article, "url_domain", "Unknown")
            domain_percentages[domain] = domain_percentages.get(domain, 0) + 1
        for domain in domain_percentages:
            total_articles = total_domain_counts.get(domain, 0)
            if total_articles > 0:
                domain_percentages[domain] = (
                    domain_percentages[domain] / total_articles
                ) * 100
        # Sort by percentage descending
        sorted_domains = sorted(
            domain_percentages.items(), key=lambda x: x[1], reverse=True
        )
        # Create bar plot
        import matplotlib.pyplot as plt

        domains = [item[0] for item in sorted_domains]
        percentages = [item[1] for item in sorted_domains]
        plt.figure(figsize=(12, 8))
        bars = plt.bar(
            range(len(domains)),
            percentages,
            color="lightblue",
            alpha=0.7,
            edgecolor="black",
        )
        plt.title("% of Articles with Text Content < 5000 Characters by Domain")
        plt.xlabel("Domain")
        plt.ylabel("% of Articles")
        plt.xticks(range(len(domains)), domains, rotation=45, ha="right")
        plt.grid(True, alpha=0.3)
        for bar, pct in zip(bars, percentages):
            plt.text(
                bar.get_x() + bar.get_width() / 2,
                bar.get_height() + 0.1,
                f"{pct:.1f}%",
                ha="center",
                va="bottom",
            )
        plt.tight_layout()
        chart_path = report_dir / "short_text_by_domain.png"
        plt.savefig(chart_path, dpi=300, bbox_inches="tight")
        plt.close()
        section = "## Short Text Content by Domain\n\n"
        section += f"![Short Text Content by Domain]({chart_path.name})\n\n"
        section += "Bar heights show the percentage of articles for each domain with text content < 5000 characters.\n\n"
        section += "### Top Domains with Short Text Content (by %):\n\n"
        for domain, pct in sorted_domains[:10]:
            section += f"- **{domain}**: {pct:.1f}%\n"
        if len(sorted_domains) > 10:
            section += f"\n*... and {len(sorted_domains) - 10} more domains*\n"
        return section

    @staticmethod
    def _section_low_text_html_ratio_by_domain(
        self, articles: List[Any], report_dir: Path
    ) -> str:
        """Create a bar plot showing percentage of articles with text/HTML ratio < 0.5% by domain."""
        if not articles:
            return "## Low Text/HTML Ratio by Domain\n\nNo articles found.\n\n"
        # Filter for error-free articles
        error_free_articles = [
            a for a in articles if not getattr(a, "ingestion_error_status", None)
        ]
        if not error_free_articles:
            return (
                "## Low Text/HTML Ratio by Domain\n\nNo error-free articles found.\n\n"
            )
        # Count total articles by domain
        total_domain_counts = {}
        for article in error_free_articles:
            domain = getattr(article, "url_domain", "Unknown")
            total_domain_counts[domain] = total_domain_counts.get(domain, 0) + 1
        # Filter for error-free articles with text/HTML ratio < 0.5%
        low_ratio_articles = []
        for article in error_free_articles:
            html_content = getattr(article, "html_content", "")
            text_content = getattr(article, "text_content", "")
            html_length = len(html_content) if html_content else 0
            text_length = len(text_content) if text_content else 0
            if html_length > 0:
                ratio = text_length / html_length
                if ratio < 0.005:  # 0.5%
                    low_ratio_articles.append(article)
        if not low_ratio_articles:
            return "## Low Text/HTML Ratio by Domain\n\nNo articles with text/HTML ratio < 0.5% found.\n\n"
        # Count low ratio articles by domain and calculate percentages
        domain_percentages = {}
        for article in low_ratio_articles:
            domain = getattr(article, "url_domain", "Unknown")
            domain_percentages[domain] = domain_percentages.get(domain, 0) + 1
        for domain in domain_percentages:
            total_articles = total_domain_counts.get(domain, 0)
            if total_articles > 0:
                domain_percentages[domain] = (
                    domain_percentages[domain] / total_articles
                ) * 100
        # Sort by percentage descending
        sorted_domains = sorted(
            domain_percentages.items(), key=lambda x: x[1], reverse=True
        )
        # Create bar plot
        import matplotlib.pyplot as plt

        domains = [item[0] for item in sorted_domains]
        percentages = [item[1] for item in sorted_domains]
        plt.figure(figsize=(12, 8))
        bars = plt.bar(
            range(len(domains)),
            percentages,
            color="lightyellow",
            alpha=0.7,
            edgecolor="black",
        )
        plt.title("% of Articles with Text/HTML Ratio < 0.5% by Domain")
        plt.xlabel("Domain")
        plt.ylabel("% of Articles")
        plt.xticks(range(len(domains)), domains, rotation=45, ha="right")
        plt.grid(True, alpha=0.3)
        for bar, pct in zip(bars, percentages):
            plt.text(
                bar.get_x() + bar.get_width() / 2,
                bar.get_height() + 0.1,
                f"{pct:.1f}%",
                ha="center",
                va="bottom",
            )
        plt.tight_layout()
        chart_path = report_dir / "low_text_html_ratio_by_domain.png"
        plt.savefig(chart_path, dpi=300, bbox_inches="tight")
        plt.close()
        section = "## Low Text/HTML Ratio by Domain\n\n"
        section += f"![Low Text/HTML Ratio by Domain]({chart_path.name})\n\n"
        section += "Bar heights show the percentage of articles for each domain with text/HTML ratio < 0.5%.\n\n"
        section += "### Top Domains with Low Text/HTML Ratio (by %):\n\n"
        for domain, pct in sorted_domains[:10]:
            section += f"- **{domain}**: {pct:.1f}%\n"
        if len(sorted_domains) > 10:
            section += f"\n*... and {len(sorted_domains) - 10} more domains*\n"
        return section


def generate_html_ingestion_evaluation_report(
    operations: List[IngestionOperationDB],
    articles: List[Any],
    output_dir: str,
    logger=None,
) -> str:
    generator = IngestionEvaluationReportGenerator(output_dir, logger)
    return generator.generate_report(operations, articles) or ""
