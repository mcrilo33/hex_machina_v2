import datetime
from pathlib import Path
from typing import Any, List

from src.hex_machina.reporting.base_report_generator import BaseReportGenerator
from src.hex_machina.reporting.chart_utils import create_time_series_chart
from src.hex_machina.reporting.report_builder import ReportBuilder


class IngestionDomainEvaluationReportGenerator(BaseReportGenerator):
    def __init__(self, output_dir: str, logger=None, domain: str = None):
        super().__init__(output_dir, logger)
        self.domain = domain

    def _generate_report_sections(
        self,
        operations: List[Any],
        articles: List[Any],
        report_dir: Path,
    ) -> List[str]:
        sections = [
            f"## Domain: {self.domain}\n\n",
            IngestionDomainEvaluationReportGenerator._section_title_by_domain(
                self, articles
            ),
            IngestionDomainEvaluationReportGenerator._section_articles_over_time(
                self, articles, report_dir
            ),
            IngestionDomainEvaluationReportGenerator._section_error_distribution_by_status(
                self, articles, report_dir
            ),
            IngestionDomainEvaluationReportGenerator._section_content_length_distributions(
                self, articles, report_dir
            ),
        ]
        return sections

    def _create_report_directory(self, operation: Any) -> Path:
        """Create directory for the report as {output_dir}/{YYYY-MM-DD_HH-MM-SS}_{report_type}/."""
        report_dir = self.output_dir / f"{self.domain}"
        report_dir.mkdir(parents=True, exist_ok=True)
        return report_dir

    def _build_markdown_report(self, sections: List[str]) -> str:
        return ReportBuilder.build_markdown_report(
            sections, title=f"Ingestion Domain Evaluation Report - {self.domain}"
        )

    def _get_operation_date(self, operations: List[Any]) -> datetime.datetime:
        # For domain reports, we don't have operations, so use current time
        return datetime.datetime.now()

    def _get_operation_id(self, operations: List[Any]) -> str:
        return self.domain

    def _get_report_type(self) -> str:
        return "ingestion_domain_evaluation_report"

    @staticmethod
    def _section_title_by_domain(self, articles: List[Any]) -> str:
        if not articles:
            return "## Articles\n\nNo articles found for this domain.\n\n"

        titles = []
        for article in articles:
            title = getattr(article, "title", "No title")
            url = getattr(article, "url", "No URL")
            published_date = getattr(article, "published_date", None)
            error_status = getattr(article, "ingestion_error_status", None)

            status_icon = "❌" if error_status else "✅"
            date_str = (
                published_date.strftime("%Y-%m-%d")
                if published_date
                else "Unknown date"
            )

            titles.append(f"- {status_icon} **{title}** ({date_str}) - {url}")

        return "## Articles\n\n" + "\n".join(titles) + "\n\n"

    @staticmethod
    def _section_articles_over_time(self, articles: List[Any], report_dir: Path) -> str:
        if not articles:
            return "## Articles Over Time\n\nNo articles found for this domain.\n\n"

        data = []
        for article in articles:
            published_date = getattr(article, "published_date", None)
            error_status = getattr(article, "ingestion_error_status", None)
            if published_date:
                data.append(
                    {
                        "published_date": published_date,
                        "status": "Error" if error_status else "Success",
                    }
                )

        if not data:
            return "## Articles Over Time\n\nNo articles with valid dates found for this domain.\n\n"

        chart = create_time_series_chart(
            data=data,
            date_field="published_date",
            group_field="status",
            output_dir=str(report_dir),
            filename=f"articles_over_time_{self.domain}.png",
            title=f"Articles Over Time - {self.domain}",
            filter_func=lambda item: item.get("published_date") is not None,
        )

        return "## Articles Over Time\n\n" + chart + "\n\n"

    @staticmethod
    def _section_error_distribution_by_status(
        self, articles: List[Any], report_dir: Path
    ) -> str:
        if not articles:
            return "## Error Distribution by Status\n\nNo articles found for this domain.\n\n"

        error_counts = {}
        for article in articles:
            error_status = getattr(article, "ingestion_error_status", None)
            status = error_status if error_status else "Success"
            error_counts[status] = error_counts.get(status, 0) + 1

        if not error_counts:
            return "## Error Distribution by Status\n\nNo error data available for this domain.\n\n"

        # Create a simple text-based distribution since we don't have a pie chart utility
        distribution_text = "## Error Distribution by Status\n\n"
        for status, count in sorted(error_counts.items()):
            percentage = (count / len(articles)) * 100
            distribution_text += (
                f"- **{status}**: {count} articles ({percentage:.1f}%)\n"
            )

        return distribution_text + "\n"

    @staticmethod
    def _section_content_length_distributions(
        self, articles: List[Any], report_dir: Path
    ) -> str:
        if not articles:
            return "## Content Length Distributions\n\nNo articles found for this domain.\n\n"

        # Filter for error-free articles
        error_free_articles = [
            a for a in articles if not getattr(a, "ingestion_error_status", None)
        ]

        if not error_free_articles:
            return "## Content Length Distributions\n\nNo error-free articles found for this domain.\n\n"

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
            return "## Content Length Distributions\n\nNo content data available for this domain.\n\n"

        # Create bar plots for distributions
        import matplotlib.pyplot as plt
        import numpy as np

        charts = []

        # HTML Content Length Distribution
        plt.figure(figsize=(10, 6))
        plt.hist(html_lengths, bins=20, alpha=0.7, color="skyblue", edgecolor="black")
        plt.title(f"HTML Content Length Distribution - {self.domain}")
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

        html_chart_path = report_dir / f"html_length_distribution_{self.domain}.png"
        plt.savefig(html_chart_path, dpi=300, bbox_inches="tight")
        plt.close()
        charts.append(str(html_chart_path))

        # Text Content Length Distribution
        plt.figure(figsize=(10, 6))
        plt.hist(
            text_lengths, bins=20, alpha=0.7, color="lightgreen", edgecolor="black"
        )
        plt.title(f"Text Content Length Distribution - {self.domain}")
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

        text_chart_path = report_dir / f"text_length_distribution_{self.domain}.png"
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
            plt.title(f"Text/HTML Ratio Distribution - {self.domain}")
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

            ratio_chart_path = (
                report_dir / f"text_html_ratio_distribution_{self.domain}.png"
            )
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


def generate_html_ingestion_domain_evaluation_report(
    domain: str,
    articles: List[Any],
    output_dir: str,
    logger=None,
) -> str:
    generator = IngestionDomainEvaluationReportGenerator(output_dir, logger, domain)
    return generator.generate_report([], articles) or ""
