#!/usr/bin/env python3
"""Compare scraping methods between two databases."""

import argparse
import logging
import os
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Dict

import matplotlib.pyplot as plt
import pandas as pd
import seaborn as sns

# Add src to path
sys.path.insert(0, "src")

import duckdb
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.table import Table

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

console = Console()


class DatabaseComparator:
    """Compare articles between two databases."""

    def __init__(self, db1_path: str, db2_path: str, output_dir: str = "reports"):
        self.db1_path = db1_path
        self.db2_path = db2_path
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(exist_ok=True)

        # Database connections
        self.db1_conn = None
        self.db2_conn = None

        # Results storage
        self.comparison_results = {}

    def __enter__(self):
        """Context manager entry."""
        self.db1_conn = duckdb.connect(self.db1_path)
        self.db2_conn = duckdb.connect(self.db2_path)
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        if self.db1_conn:
            self.db1_conn.close()
        if self.db2_conn:
            self.db2_conn.close()

    def get_database_info(self) -> Dict[str, Any]:
        """Get basic information about both databases."""
        info = {}

        # Database 1 info
        db1_stats = self.db1_conn.execute(
            """
            SELECT 
                COUNT(*) as total_articles,
                COUNT(CASE WHEN ingestion_error_status IS NOT NULL THEN 1 END) as error_count,
                COUNT(CASE WHEN ingestion_error_status IS NULL THEN 1 END) as success_count,
                AVG(LENGTH(text_content)) as avg_text_length,
                MIN(ingested_at) as earliest_ingestion,
                MAX(ingested_at) as latest_ingestion
            FROM articles
        """
        ).fetchone()

        info["db1"] = {
            "path": self.db1_path,
            "total_articles": db1_stats[0],
            "error_count": db1_stats[1],
            "success_count": db1_stats[2],
            "avg_text_length": db1_stats[3],
            "earliest_ingestion": db1_stats[4],
            "latest_ingestion": db1_stats[5],
            "error_rate": (
                (db1_stats[1] / db1_stats[0]) * 100 if db1_stats[0] > 0 else 0
            ),
        }

        # Database 2 info
        db2_stats = self.db2_conn.execute(
            """
            SELECT 
                COUNT(*) as total_articles,
                COUNT(CASE WHEN ingestion_error_status IS NOT NULL THEN 1 END) as error_count,
                COUNT(CASE WHEN ingestion_error_status IS NULL THEN 1 END) as success_count,
                AVG(LENGTH(text_content)) as avg_text_length,
                MIN(ingested_at) as earliest_ingestion,
                MAX(ingested_at) as latest_ingestion
            FROM articles
        """
        ).fetchone()

        info["db2"] = {
            "path": self.db2_path,
            "total_articles": db2_stats[0],
            "error_count": db2_stats[1],
            "success_count": db2_stats[2],
            "avg_text_length": db2_stats[3],
            "earliest_ingestion": db2_stats[4],
            "latest_ingestion": db2_stats[5],
            "error_rate": (
                (db2_stats[1] / db2_stats[0]) * 100 if db2_stats[0] > 0 else 0
            ),
        }

        return info

    def find_common_articles(self) -> pd.DataFrame:
        """Find articles that exist in both databases with same url_domain and title."""
        # Query articles from both databases
        db1_query = """
        SELECT 
            url_domain,
            title,
            url,
            LENGTH(text_content) as text_length,
            ingestion_error_status,
            ingestion_error_message,
            ingested_at,
            ingestion_metadata
        FROM articles
        """

        db2_query = """
        SELECT 
            url_domain,
            title,
            url,
            LENGTH(text_content) as text_length,
            ingestion_error_status,
            ingestion_error_message,
            ingested_at,
            ingestion_metadata
        FROM articles
        """

        # Execute queries on respective databases
        db1_articles = self.db1_conn.execute(db1_query).fetchdf()
        db2_articles = self.db2_conn.execute(db2_query).fetchdf()

        # Merge the results on url_domain and title
        common_articles = pd.merge(
            db1_articles,
            db2_articles,
            on=["url_domain", "title"],
            suffixes=("_1", "_2"),
        )

        return common_articles

    def analyze_text_length_comparison(
        self, common_articles: pd.DataFrame
    ) -> Dict[str, Any]:
        """Analyze text length differences between the two methods."""
        if common_articles.empty:
            return {}

        # Calculate text length differences
        common_articles["text_length_diff"] = (
            common_articles["text_length_2"] - common_articles["text_length_1"]
        )
        common_articles["text_length_ratio"] = (
            common_articles["text_length_2"] / common_articles["text_length_1"]
        ).replace([float("inf"), -float("inf")], None)

        # Filter out articles with errors in either database
        successful_articles = common_articles[
            (common_articles["ingestion_error_status_1"].isna())
            & (common_articles["ingestion_error_status_2"].isna())
        ]

        analysis = {
            "total_common_articles": len(common_articles),
            "successful_common_articles": len(successful_articles),
            "text_length_stats": {
                "mean_diff": successful_articles["text_length_diff"].mean(),
                "median_diff": successful_articles["text_length_diff"].median(),
                "std_diff": successful_articles["text_length_diff"].std(),
                "min_diff": successful_articles["text_length_diff"].min(),
                "max_diff": successful_articles["text_length_diff"].max(),
                "mean_ratio": successful_articles["text_length_ratio"].mean(),
                "median_ratio": successful_articles["text_length_ratio"].median(),
            },
            "articles_with_longer_text_in_db2": len(
                successful_articles[successful_articles["text_length_diff"] > 0]
            ),
            "articles_with_longer_text_in_db1": len(
                successful_articles[successful_articles["text_length_diff"] < 0]
            ),
            "articles_with_same_length": len(
                successful_articles[successful_articles["text_length_diff"] == 0]
            ),
            "significant_improvements": len(
                successful_articles[successful_articles["text_length_ratio"] > 1.5]
            ),
            "significant_degradations": len(
                successful_articles[successful_articles["text_length_ratio"] < 0.67]
            ),
        }

        return analysis

    def analyze_error_comparison(self, common_articles: pd.DataFrame) -> Dict[str, Any]:
        """Analyze error differences between the two methods."""
        if common_articles.empty:
            return {}

        # Error analysis
        error_analysis = {
            "total_common_articles": len(common_articles),
            "both_successful": len(
                common_articles[
                    (common_articles["ingestion_error_status_1"].isna())
                    & (common_articles["ingestion_error_status_2"].isna())
                ]
            ),
            "both_failed": len(
                common_articles[
                    (common_articles["ingestion_error_status_1"].notna())
                    & (common_articles["ingestion_error_status_2"].notna())
                ]
            ),
            "db1_success_db2_failed": len(
                common_articles[
                    (common_articles["ingestion_error_status_1"].isna())
                    & (common_articles["ingestion_error_status_2"].notna())
                ]
            ),
            "db1_failed_db2_success": len(
                common_articles[
                    (common_articles["ingestion_error_status_1"].notna())
                    & (common_articles["ingestion_error_status_2"].isna())
                ]
            ),
        }

        # Error type analysis
        error_types_db1 = (
            common_articles["ingestion_error_status_1"].value_counts().to_dict()
        )
        error_types_db2 = (
            common_articles["ingestion_error_status_2"].value_counts().to_dict()
        )

        error_analysis["error_types_db1"] = error_types_db1
        error_analysis["error_types_db2"] = error_types_db2

        # Calculate improvement metrics
        error_analysis["improvement_rate"] = (
            (
                error_analysis["db1_failed_db2_success"]
                / error_analysis["total_common_articles"]
            )
            * 100
            if error_analysis["total_common_articles"] > 0
            else 0
        )

        error_analysis["degradation_rate"] = (
            (
                error_analysis["db1_success_db2_failed"]
                / error_analysis["total_common_articles"]
            )
            * 100
            if error_analysis["total_common_articles"] > 0
            else 0
        )

        return error_analysis

    def analyze_domain_performance(self, common_articles: pd.DataFrame) -> pd.DataFrame:
        """Analyze performance by domain."""
        if common_articles.empty:
            return pd.DataFrame()

        domain_stats = []

        for domain in common_articles["url_domain"].unique():
            domain_articles = common_articles[common_articles["url_domain"] == domain]

            # Text length stats
            successful_domain = domain_articles[
                (domain_articles["ingestion_error_status_1"].isna())
                & (domain_articles["ingestion_error_status_2"].isna())
            ]

            if len(successful_domain) > 0:
                avg_length_diff = successful_domain["text_length_diff"].mean()
                avg_length_ratio = successful_domain["text_length_ratio"].mean()
            else:
                avg_length_diff = 0
                avg_length_ratio = 1.0

            # Error stats
            total_articles = len(domain_articles)
            db1_success = len(
                domain_articles[domain_articles["ingestion_error_status_1"].isna()]
            )
            db2_success = len(
                domain_articles[domain_articles["ingestion_error_status_2"].isna()]
            )

            domain_stats.append(
                {
                    "domain": domain,
                    "total_articles": total_articles,
                    "db1_success_rate": (db1_success / total_articles) * 100,
                    "db2_success_rate": (db2_success / total_articles) * 100,
                    "success_rate_improvement": (
                        (db2_success - db1_success) / total_articles
                    )
                    * 100,
                    "avg_text_length_diff": avg_length_diff,
                    "avg_text_length_ratio": avg_length_ratio,
                    "db1_errors": total_articles - db1_success,
                    "db2_errors": total_articles - db2_success,
                }
            )

        return pd.DataFrame(domain_stats)

    def generate_visualizations(
        self, common_articles: pd.DataFrame, analysis_results: Dict[str, Any]
    ):
        """Generate visualizations for the comparison."""
        if common_articles.empty:
            console.print("[yellow]No common articles found for visualization[/yellow]")
            return

        # Set up the plotting style
        plt.style.use("default")
        sns.set_palette("husl")

        # Create figure with subplots
        fig, axes = plt.subplots(2, 3, figsize=(18, 12))
        fig.suptitle(
            "Scraping Methods Comparison Report", fontsize=16, fontweight="bold"
        )

        # 1. Text Length Comparison
        successful_articles = common_articles[
            (common_articles["ingestion_error_status_1"].isna())
            & (common_articles["ingestion_error_status_2"].isna())
        ]

        if not successful_articles.empty:
            # Text length difference distribution
            axes[0, 0].hist(
                successful_articles["text_length_diff"],
                bins=30,
                alpha=0.7,
                edgecolor="black",
            )
            axes[0, 0].axvline(x=0, color="red", linestyle="--", alpha=0.8)
            axes[0, 0].set_title("Text Length Difference Distribution")
            axes[0, 0].set_xlabel("Text Length Difference (DB2 - DB1)")
            axes[0, 0].set_ylabel("Frequency")

            # Text length ratio distribution
            axes[0, 1].hist(
                successful_articles["text_length_ratio"].dropna(),
                bins=30,
                alpha=0.7,
                edgecolor="black",
            )
            axes[0, 1].axvline(x=1, color="red", linestyle="--", alpha=0.8)
            axes[0, 1].set_title("Text Length Ratio Distribution")
            axes[0, 1].set_xlabel("Text Length Ratio (DB2 / DB1)")
            axes[0, 1].set_ylabel("Frequency")

            # Scatter plot of text lengths
            axes[0, 2].scatter(
                successful_articles["text_length_1"],
                successful_articles["text_length_2"],
                alpha=0.6,
            )
            axes[0, 2].plot(
                [0, successful_articles["text_length_1"].max()],
                [0, successful_articles["text_length_1"].max()],
                "r--",
                alpha=0.8,
            )
            axes[0, 2].set_title("Text Length Comparison")
            axes[0, 2].set_xlabel("DB1 Text Length")
            axes[0, 2].set_ylabel("DB2 Text Length")

        # 2. Error Analysis
        # Error status comparison
        error_comparison = pd.crosstab(
            common_articles["ingestion_error_status_1"].fillna("Success"),
            common_articles["ingestion_error_status_2"].fillna("Success"),
        )

        sns.heatmap(error_comparison, annot=True, fmt="d", cmap="YlOrRd", ax=axes[1, 0])
        axes[1, 0].set_title("Error Status Comparison")
        axes[1, 0].set_xlabel("DB2 Error Status")
        axes[1, 0].set_ylabel("DB1 Error Status")

        # Success rate comparison
        success_rates = ["DB1 Success Rate", "DB2 Success Rate"]
        success_values = [
            (
                len(common_articles[common_articles["ingestion_error_status_1"].isna()])
                / len(common_articles)
            )
            * 100,
            (
                len(common_articles[common_articles["ingestion_error_status_2"].isna()])
                / len(common_articles)
            )
            * 100,
        ]

        bars = axes[1, 1].bar(
            success_rates, success_values, color=["skyblue", "lightgreen"]
        )
        axes[1, 1].set_title("Success Rate Comparison")
        axes[1, 1].set_ylabel("Success Rate (%)")
        axes[1, 1].set_ylim(0, 100)

        # Add value labels on bars
        for bar, value in zip(bars, success_values):
            axes[1, 1].text(
                bar.get_x() + bar.get_width() / 2,
                bar.get_height() + 1,
                f"{value:.1f}%",
                ha="center",
                va="bottom",
            )

        # Domain performance (top 10 domains by article count)
        domain_stats = self.analyze_domain_performance(common_articles)
        if not domain_stats.empty:
            top_domains = domain_stats.nlargest(10, "total_articles")

            x = range(len(top_domains))
            width = 0.35

            axes[1, 2].bar(
                [i - width / 2 for i in x],
                top_domains["db1_success_rate"],
                width,
                label="DB1",
                alpha=0.8,
            )
            axes[1, 2].bar(
                [i + width / 2 for i in x],
                top_domains["db2_success_rate"],
                width,
                label="DB2",
                alpha=0.8,
            )

            axes[1, 2].set_title("Success Rate by Domain (Top 10)")
            axes[1, 2].set_xlabel("Domain")
            axes[1, 2].set_ylabel("Success Rate (%)")
            axes[1, 2].set_xticks(x)
            axes[1, 2].set_xticklabels(top_domains["domain"], rotation=45, ha="right")
            axes[1, 2].legend()
            axes[1, 2].set_ylim(0, 100)

        plt.tight_layout()

        # Save the plot
        plot_path = (
            self.output_dir
            / f"scraping_comparison_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png"
        )
        plt.savefig(plot_path, dpi=300, bbox_inches="tight")
        plt.close()

        console.print(f"[green]Visualization saved to: {plot_path}[/green]")

    def generate_report(self) -> str:
        """Generate a comprehensive comparison report."""
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console,
        ) as progress:

            task1 = progress.add_task("Getting database info...", total=None)
            db_info = self.get_database_info()
            progress.update(task1, completed=True)

            task2 = progress.add_task("Finding common articles...", total=None)
            common_articles = self.find_common_articles()
            progress.update(task2, completed=True)

            task3 = progress.add_task(
                "Analyzing text length differences...", total=None
            )
            text_analysis = self.analyze_text_length_comparison(common_articles)
            progress.update(task3, completed=True)

            task4 = progress.add_task("Analyzing error differences...", total=None)
            error_analysis = self.analyze_error_comparison(common_articles)
            progress.update(task4, completed=True)

            task5 = progress.add_task("Generating visualizations...", total=None)
            self.generate_visualizations(
                common_articles,
                {"text_analysis": text_analysis, "error_analysis": error_analysis},
            )
            progress.update(task5, completed=True)

        # Generate HTML report
        report_html = self._generate_html_report(
            db_info, common_articles, text_analysis, error_analysis
        )

        # Save report
        report_path = (
            self.output_dir
            / f"scraping_comparison_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.html"
        )
        with open(report_path, "w", encoding="utf-8") as f:
            f.write(report_html)

        # Display summary in console
        self._display_summary(db_info, text_analysis, error_analysis)

        return str(report_path)

    def _generate_html_report(
        self,
        db_info: Dict,
        common_articles: pd.DataFrame,
        text_analysis: Dict,
        error_analysis: Dict,
    ) -> str:
        """Generate HTML report."""
        html = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <title>Scraping Methods Comparison Report</title>
            <style>
                body {{ font-family: Arial, sans-serif; margin: 20px; }}
                .header {{ background-color: #f0f0f0; padding: 20px; border-radius: 5px; }}
                .section {{ margin: 20px 0; padding: 15px; border: 1px solid #ddd; border-radius: 5px; }}
                .metric {{ display: inline-block; margin: 10px; padding: 10px; background-color: #f9f9f9; border-radius: 3px; }}
                .improvement {{ color: green; }}
                .degradation {{ color: red; }}
                .neutral {{ color: blue; }}
                table {{ border-collapse: collapse; width: 100%; }}
                th, td {{ border: 1px solid #ddd; padding: 8px; text-align: left; }}
                th {{ background-color: #f2f2f2; }}
                .chart {{ text-align: center; margin: 20px 0; }}
            </style>
        </head>
        <body>
            <div class="header">
                <h1>Scraping Methods Comparison Report</h1>
                <p>Generated on: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
                <p>Comparing: {os.path.basename(self.db1_path)} vs {os.path.basename(self.db2_path)}</p>
            </div>
            
            <div class="section">
                <h2>Database Overview</h2>
                <table>
                    <tr>
                        <th>Metric</th>
                        <th>Database 1</th>
                        <th>Database 2</th>
                        <th>Difference</th>
                    </tr>
                    <tr>
                        <td>Total Articles</td>
                        <td>{db_info['db1']['total_articles']:,}</td>
                        <td>{db_info['db2']['total_articles']:,}</td>
                        <td>{db_info['db2']['total_articles'] - db_info['db1']['total_articles']:,}</td>
                    </tr>
                    <tr>
                        <td>Success Count</td>
                        <td>{db_info['db1']['success_count']:,}</td>
                        <td>{db_info['db2']['success_count']:,}</td>
                        <td>{db_info['db2']['success_count'] - db_info['db1']['success_count']:,}</td>
                    </tr>
                    <tr>
                        <td>Error Count</td>
                        <td>{db_info['db1']['error_count']:,}</td>
                        <td>{db_info['db2']['error_count']:,}</td>
                        <td>{db_info['db2']['error_count'] - db_info['db1']['error_count']:,}</td>
                    </tr>
                    <tr>
                        <td>Error Rate</td>
                        <td>{db_info['db1']['error_rate']:.2f}%</td>
                        <td>{db_info['db2']['error_rate']:.2f}%</td>
                        <td class="{'improvement' if db_info['db2']['error_rate'] < db_info['db1']['error_rate'] else 'degradation'}">
                            {db_info['db2']['error_rate'] - db_info['db1']['error_rate']:.2f}%
                        </td>
                    </tr>
                    <tr>
                        <td>Avg Text Length</td>
                        <td>{db_info['db1']['avg_text_length']:.0f}</td>
                        <td>{db_info['db2']['avg_text_length']:.0f}</td>
                        <td class="{'improvement' if db_info['db2']['avg_text_length'] > db_info['db1']['avg_text_length'] else 'degradation'}">
                            {db_info['db2']['avg_text_length'] - db_info['db1']['avg_text_length']:.0f}
                        </td>
                    </tr>
                </table>
            </div>
            
            <div class="section">
                <h2>Common Articles Analysis</h2>
                <p><strong>Total common articles:</strong> {len(common_articles):,}</p>
                
                <h3>Text Length Analysis</h3>
                <div class="metric">
                    <strong>Mean Length Difference:</strong><br>
                    {text_analysis.get('text_length_stats', {}).get('mean_diff', 0):.0f} characters
                </div>
                <div class="metric">
                    <strong>Mean Length Ratio:</strong><br>
                    {text_analysis.get('text_length_stats', {}).get('mean_ratio', 1.0):.2f}
                </div>
                <div class="metric">
                    <strong>Longer in DB2:</strong><br>
                    {text_analysis.get('articles_with_longer_text_in_db2', 0):,} articles
                </div>
                <div class="metric">
                    <strong>Longer in DB1:</strong><br>
                    {text_analysis.get('articles_with_longer_text_in_db1', 0):,} articles
                </div>
                <div class="metric">
                    <strong>Significant Improvements:</strong><br>
                    {text_analysis.get('significant_improvements', 0):,} articles
                </div>
                <div class="metric">
                    <strong>Significant Degradations:</strong><br>
                    {text_analysis.get('significant_degradations', 0):,} articles
                </div>
                
                <h3>Error Analysis</h3>
                <div class="metric">
                    <strong>Both Successful:</strong><br>
                    {error_analysis.get('both_successful', 0):,} articles
                </div>
                <div class="metric">
                    <strong>Both Failed:</strong><br>
                    {error_analysis.get('both_failed', 0):,} articles
                </div>
                <div class="metric">
                    <strong>DB1 Success, DB2 Failed:</strong><br>
                    {error_analysis.get('db1_success_db2_failed', 0):,} articles
                </div>
                <div class="metric">
                    <strong>DB1 Failed, DB2 Success:</strong><br>
                    {error_analysis.get('db1_failed_db2_success', 0):,} articles
                </div>
                <div class="metric">
                    <strong>Improvement Rate:</strong><br>
                    {error_analysis.get('improvement_rate', 0):.2f}%
                </div>
                <div class="metric">
                    <strong>Degradation Rate:</strong><br>
                    {error_analysis.get('degradation_rate', 0):.2f}%
                </div>
            </div>
            
            <div class="section">
                <h2>Detailed Results</h2>
                <p>For detailed analysis and visualizations, see the generated PNG file.</p>
            </div>
        </body>
        </html>
        """

        return html

    def _display_summary(
        self, db_info: Dict, text_analysis: Dict, error_analysis: Dict
    ):
        """Display summary in console."""
        console.print("\n" + "=" * 80)
        console.print("[bold blue]SCRAPING METHODS COMPARISON SUMMARY[/bold blue]")
        console.print("=" * 80)

        # Database overview
        table = Table(title="Database Overview")
        table.add_column("Metric", style="cyan")
        table.add_column("DB1", style="magenta")
        table.add_column("DB2", style="green")
        table.add_column("Difference", style="yellow")

        table.add_row(
            "Total Articles",
            f"{db_info['db1']['total_articles']:,}",
            f"{db_info['db2']['total_articles']:,}",
            f"{db_info['db2']['total_articles'] - db_info['db1']['total_articles']:,}",
        )

        table.add_row(
            "Success Rate",
            f"{100 - db_info['db1']['error_rate']:.1f}%",
            f"{100 - db_info['db2']['error_rate']:.1f}%",
            f"{db_info['db2']['error_rate'] - db_info['db1']['error_rate']:.1f}%",
        )

        table.add_row(
            "Avg Text Length",
            f"{db_info['db1']['avg_text_length']:.0f}",
            f"{db_info['db2']['avg_text_length']:.0f}",
            f"{db_info['db2']['avg_text_length'] - db_info['db1']['avg_text_length']:.0f}",
        )

        console.print(table)

        # Key findings
        console.print("\n[bold]KEY FINDINGS:[/bold]")

        if text_analysis:
            mean_diff = text_analysis.get("text_length_stats", {}).get("mean_diff", 0)
            if mean_diff > 0:
                console.print(
                    f"✅ [green]Text length improved by {mean_diff:.0f} characters on average[/green]"
                )
            elif mean_diff < 0:
                console.print(
                    f"❌ [red]Text length decreased by {abs(mean_diff):.0f} characters on average[/red]"
                )
            else:
                console.print("➖ [blue]Text length remained similar[/blue]")

        if error_analysis:
            improvement_rate = error_analysis.get("improvement_rate", 0)
            degradation_rate = error_analysis.get("degradation_rate", 0)

            if improvement_rate > degradation_rate:
                console.print(
                    f"✅ [green]Error rate improved by {improvement_rate - degradation_rate:.1f}%[/green]"
                )
            elif degradation_rate > improvement_rate:
                console.print(
                    f"❌ [red]Error rate worsened by {degradation_rate - improvement_rate:.1f}%[/red]"
                )
            else:
                console.print("➖ [blue]Error rate remained similar[/blue]")


def main():
    """Main function."""
    parser = argparse.ArgumentParser(
        description="Compare scraping methods between two databases"
    )
    parser.add_argument(
        "db1", help="Path to first database (e.g., storage/articles4.db)"
    )
    parser.add_argument(
        "db2", help="Path to second database (e.g., storage/articles5.db)"
    )
    parser.add_argument(
        "--output-dir", default="reports", help="Output directory for reports"
    )

    args = parser.parse_args()

    # Validate database files
    if not os.path.exists(args.db1):
        console.print(f"[red]Error: Database 1 not found: {args.db1}[/red]")
        sys.exit(1)

    if not os.path.exists(args.db2):
        console.print(f"[red]Error: Database 2 not found: {args.db2}[/red]")
        sys.exit(1)

    console.print("[green]Comparing databases:[/green]")
    console.print(f"  DB1: {args.db1}")
    console.print(f"  DB2: {args.db2}")
    console.print(f"  Output: {args.output_dir}")

    # Run comparison
    with DatabaseComparator(args.db1, args.db2, args.output_dir) as comparator:
        report_path = comparator.generate_report()

        console.print("\n[bold green]Report generated successfully![/bold green]")
        console.print(f"📊 HTML Report: {report_path}")
        console.print(f"📈 Visualization: {args.output_dir}/scraping_comparison_*.png")


if __name__ == "__main__":
    main()
