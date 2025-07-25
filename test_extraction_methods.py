#!/usr/bin/env python3
"""
Test script to compare three HTML text extraction methods:
1. Trafilatura
2. Readability-lxml
3. MainContentExtractor

Tests both with and without _clean_markdown processing.
"""

import time
from typing import Dict, List, Tuple

import duckdb
from rich.console import Console
from rich.table import Table

# Import the extraction methods
try:
    import trafilatura

    TRAFILATURA_AVAILABLE = True
except ImportError:
    TRAFILATURA_AVAILABLE = False

try:
    from readability.readability import Document

    READABILITY_AVAILABLE = True
except ImportError:
    READABILITY_AVAILABLE = False

try:
    from main_content_extractor import MainContentExtractor

    MAIN_CONTENT_EXTRACTOR_AVAILABLE = True
except ImportError:
    MAIN_CONTENT_EXTRACTOR_AVAILABLE = False

console = Console()


class ExtractionTester:
    """Test different HTML text extraction methods."""

    def __init__(self):
        self.results = []

    def _clean_markdown(self, text: str) -> str:
        """Clean markdown text (copied from ArticleParser)."""
        if not text:
            return ""

        try:
            # Remove remaining links but keep the link text
            text = re.sub(r"\[([^\]]*?)\]\(.*?\)", r"\1", text, flags=re.DOTALL)

            # Fix dashes separated by line breaks
            text = re.sub(r"(-)\n(\w)", r"\1\2", text)

            # Merge broken lines that are not paragraph breaks
            text = re.sub(r"(\S)\n(?=\S)", r"\1 ", text)

            # Fix markdown bullet lists
            text = re.sub(r"\s*\*\s*", r"\n* ", text)

            # Fix markdown numbered lists
            text = re.sub(r" +(\d+\.) +", r"\n\1 ", text)

            # Remove HTML tags
            text = re.sub(r"<[^>]+>", "", text)

            # Remove HTML entities
            text = re.sub(r"&nbsp;|&amp;|&lt;|&gt;|&quot;|&#39;", "", text)

            # Remove lines full of [ \*#\n]
            text = re.sub(r"\n[ \*#\n]*", r"\n", text, flags=re.DOTALL)

            # Normalize whitespace and line breaks
            text = re.sub(r"\n{2,}", "\n", text)
            text = re.sub(r"[ \t]+", " ", text)

            return text.strip()
        except Exception:
            return text.strip()

    def extract_with_trafilatura(
        self, html: str, clean_markdown: bool = True
    ) -> Tuple[str, float]:
        """Extract text using Trafilatura."""
        if not TRAFILATURA_AVAILABLE:
            return "", 0.0

        start_time = time.time()
        try:
            extracted = trafilatura.extract(
                html, include_formatting=True, include_links=True
            )
            if extracted and clean_markdown:
                extracted = self._clean_markdown(extracted)
            extraction_time = time.time() - start_time
            return extracted or "", extraction_time
        except Exception as e:
            extraction_time = time.time() - start_time
            return f"Error: {e}", extraction_time

    def extract_with_readability(
        self, html: str, clean_markdown: bool = True
    ) -> Tuple[str, float]:
        """Extract text using Readability."""
        if not READABILITY_AVAILABLE:
            return "", 0.0

        start_time = time.time()
        try:
            doc = Document(html)
            extracted = doc.summary()
            if extracted and clean_markdown:
                extracted = self._clean_markdown(extracted)
            extraction_time = time.time() - start_time
            return extracted or "", extraction_time
        except Exception as e:
            extraction_time = time.time() - start_time
            return f"Error: {e}", extraction_time

    def extract_with_main_content_extractor(
        self, html: str, clean_markdown: bool = True
    ) -> Tuple[str, float]:
        """Extract text using MainContentExtractor."""
        if not MAIN_CONTENT_EXTRACTOR_AVAILABLE:
            return "", 0.0

        start_time = time.time()
        try:
            extracted = MainContentExtractor.extract(html, output_format="markdown")
            if extracted and clean_markdown:
                extracted = self._clean_markdown(extracted)
            extraction_time = time.time() - start_time
            return extracted or "", extraction_time
        except Exception as e:
            extraction_time = time.time() - start_time
            return f"Error: {e}", extraction_time

    def test_article(self, article: Dict) -> Dict:
        """Test all extraction methods on a single article."""
        html = article["html_content"]
        original_text = article["text_content"]

        result = {
            "article_id": article["id"],
            "title": article["title"],
            "url": article["url"],
            "url_domain": article["url_domain"],
            "html_length": len(html),
            "original_text_length": len(original_text),
            "original_ratio": (len(original_text) / len(html)) * 100 if html else 0,
        }
        print(result)

        # Test with markdown cleaning
        result["trafilatura_text"], result["trafilatura_time"] = (
            self.extract_with_trafilatura(html, True)
        )
        result["readability_text"], result["readability_time"] = (
            self.extract_with_readability(html, True)
        )
        result["main_extractor_text"], result["main_extractor_time"] = (
            self.extract_with_main_content_extractor(html, True)
        )

        # Test without markdown cleaning
        result["trafilatura_raw_text"], result["trafilatura_raw_time"] = (
            self.extract_with_trafilatura(html, False)
        )
        result["readability_raw_text"], result["readability_raw_time"] = (
            self.extract_with_readability(html, False)
        )
        result["main_extractor_raw_text"], result["main_extractor_raw_time"] = (
            self.extract_with_main_content_extractor(html, False)
        )

        # Calculate lengths and ratios
        result["trafilatura_length"] = len(result["trafilatura_text"])
        result["readability_length"] = len(result["readability_text"])
        result["main_extractor_length"] = len(result["main_extractor_text"])
        result["trafilatura_raw_length"] = len(result["trafilatura_raw_text"])
        result["readability_raw_length"] = len(result["readability_raw_text"])
        result["main_extractor_raw_length"] = len(result["main_extractor_raw_text"])

        result["trafilatura_ratio"] = (
            (result["trafilatura_length"] / len(html)) * 100 if html else 0
        )
        result["readability_ratio"] = (
            (result["readability_length"] / len(html)) * 100 if html else 0
        )
        result["main_extractor_ratio"] = (
            (result["main_extractor_length"] / len(html)) * 100 if html else 0
        )
        result["trafilatura_raw_ratio"] = (
            (result["trafilatura_raw_length"] / len(html)) * 100 if html else 0
        )
        result["readability_raw_ratio"] = (
            (result["readability_raw_length"] / len(html)) * 100 if html else 0
        )
        result["main_extractor_raw_ratio"] = (
            (result["main_extractor_raw_length"] / len(html)) * 100 if html else 0
        )
        print(f"trafilatura_raw_ratio: {result['trafilatura_raw_ratio']}")
        print(f"readability_raw_ratio: {result['readability_raw_ratio']}")
        print(f"main_extractor_raw_ratio: {result['main_extractor_raw_ratio']}")
        print(f"trafilatura_ratio: {result['trafilatura_ratio']}")
        print(f"readability_ratio: {result['readability_ratio']}")
        print(f"main_extractor_ratio: {result['main_extractor_ratio']}")
        import ipdb

        ipdb.set_trace()

        return result

    def display_results(self, results: List[Dict]):
        """Display results in a formatted table."""
        console.print("\n[bold blue]Extraction Method Comparison Results[/bold blue]")
        console.print("=" * 80)

        # Summary table
        table = Table(title="Extraction Method Summary")
        table.add_column("Method", style="cyan")
        table.add_column("Available", style="green")
        table.add_column("Avg Length", style="yellow")
        table.add_column("Avg Ratio %", style="yellow")
        table.add_column("Avg Time (ms)", style="magenta")

        methods = [
            ("Trafilatura", TRAFILATURA_AVAILABLE),
            ("Readability", READABILITY_AVAILABLE),
            ("MainContentExtractor", MAIN_CONTENT_EXTRACTOR_AVAILABLE),
        ]

        for method_name, available in methods:
            if not available:
                table.add_row(method_name, "❌", "N/A", "N/A", "N/A")
                continue

            # Calculate averages
            lengths = []
            ratios = []
            times = []

            for result in results:
                if method_name == "Trafilatura":
                    lengths.append(result["trafilatura_length"])
                    ratios.append(result["trafilatura_ratio"])
                    times.append(result["trafilatura_time"] * 1000)
                elif method_name == "Readability":
                    lengths.append(result["readability_length"])
                    ratios.append(result["readability_ratio"])
                    times.append(result["readability_time"] * 1000)
                elif method_name == "MainContentExtractor":
                    lengths.append(result["main_extractor_length"])
                    ratios.append(result["main_extractor_ratio"])
                    times.append(result["main_extractor_time"] * 1000)

            if lengths:
                avg_length = sum(lengths) / len(lengths)
                avg_ratio = sum(ratios) / len(ratios)
                avg_time = sum(times) / len(times)

                table.add_row(
                    method_name,
                    "✅",
                    f"{avg_length:,.0f}",
                    f"{avg_ratio:.2f}",
                    f"{avg_time:.1f}",
                )

        console.print(table)

        # Comparison: Cleaned vs Raw extraction
        console.print("\n[bold blue]Cleaned vs Raw Extraction Comparison[/bold blue]")
        console.print("=" * 80)

        comparison_table = Table(title="Length Comparison: Cleaned vs Raw")
        comparison_table.add_column("Method", style="cyan")
        comparison_table.add_column("Cleaned Length", style="green")
        comparison_table.add_column("Raw Length", style="yellow")
        comparison_table.add_column("Difference", style="magenta")
        comparison_table.add_column("Reduction %", style="red")

        for method_name, available in methods:
            if not available:
                continue

            cleaned_lengths = []
            raw_lengths = []

            for result in results:
                if method_name == "Trafilatura":
                    cleaned_lengths.append(len(result["trafilatura_text"]))
                    raw_lengths.append(len(result["trafilatura_raw_text"]))
                elif method_name == "Readability":
                    cleaned_lengths.append(len(result["readability_text"]))
                    raw_lengths.append(len(result["readability_raw_text"]))
                elif method_name == "MainContentExtractor":
                    cleaned_lengths.append(len(result["main_extractor_text"]))
                    raw_lengths.append(len(result["main_extractor_raw_text"]))

            if cleaned_lengths:
                avg_cleaned = sum(cleaned_lengths) / len(cleaned_lengths)
                avg_raw = sum(raw_lengths) / len(raw_lengths)
                difference = avg_raw - avg_cleaned
                reduction_pct = (difference / avg_raw) * 100 if avg_raw > 0 else 0

                comparison_table.add_row(
                    method_name,
                    f"{avg_cleaned:,.0f}",
                    f"{avg_raw:,.0f}",
                    f"{difference:+,.0f}",
                    f"{reduction_pct:.1f}%",
                )

        console.print(comparison_table)

        # Detailed results for first few articles
        console.print("\n[bold blue]Detailed Results (First 3 Articles)[/bold blue]")
        console.print("=" * 80)

        for i, result in enumerate(results[:3]):
            console.print(
                f"\n[bold yellow]Article {i+1}: {result['title']}[/bold yellow]"
            )
            console.print(
                f"Domain: {result['url_domain']} | HTML: {result['html_length']:,} chars"
            )

            # Create comparison table for this article
            article_table = Table()
            article_table.add_column("Method", style="cyan")
            article_table.add_column("Length", style="yellow")
            article_table.add_column("Ratio %", style="yellow")
            article_table.add_column("Time (ms)", style="magenta")
            article_table.add_column("Sample", style="white")

            methods_data = [
                (
                    "Original",
                    result["original_text_length"],
                    result["original_ratio"],
                    0,
                    result.get("original_text", "")[:100],
                ),
                (
                    "Trafilatura",
                    result["trafilatura_length"],
                    result["trafilatura_ratio"],
                    result["trafilatura_time"] * 1000,
                    result["trafilatura_text"][:100],
                ),
                (
                    "Readability",
                    result["readability_length"],
                    result["readability_ratio"],
                    result["readability_time"] * 1000,
                    result["readability_text"][:100],
                ),
                (
                    "MainExtractor",
                    result["main_extractor_length"],
                    result["main_extractor_ratio"],
                    result["main_extractor_time"] * 1000,
                    result["main_extractor_text"][:100],
                ),
            ]

            for method, length, ratio, time_ms, sample in methods_data:
                article_table.add_row(
                    method,
                    f"{length:,}",
                    f"{ratio:.2f}",
                    f"{time_ms:.1f}",
                    sample.replace("\n", " ")[:100] + "...",
                )

            console.print(article_table)

            # Show raw vs cleaned comparison for this article
            console.print(
                f"\n[bold cyan]Raw vs Cleaned Comparison for Article {i+1}:[/bold cyan]"
            )
            raw_vs_clean_table = Table()
            raw_vs_clean_table.add_column("Method", style="cyan")
            raw_vs_clean_table.add_column("Raw Length", style="yellow")
            raw_vs_clean_table.add_column("Cleaned Length", style="green")
            raw_vs_clean_table.add_column("Reduction", style="red")

            for method_name in ["Trafilatura", "Readability", "MainContentExtractor"]:
                if method_name == "Trafilatura":
                    raw_len = len(result["trafilatura_raw_text"])
                    clean_len = len(result["trafilatura_text"])
                elif method_name == "Readability":
                    raw_len = len(result["readability_raw_text"])
                    clean_len = len(result["readability_text"])
                elif method_name == "MainContentExtractor":
                    raw_len = len(result["main_extractor_raw_text"])
                    clean_len = len(result["main_extractor_text"])

                reduction = raw_len - clean_len
                reduction_pct = (reduction / raw_len) * 100 if raw_len > 0 else 0

                raw_vs_clean_table.add_row(
                    method_name,
                    f"{raw_len:,}",
                    f"{clean_len:,}",
                    f"{reduction:,} ({reduction_pct:.1f}%)",
                )

            console.print(raw_vs_clean_table)


def main():
    """Main test function."""
    console.print("[bold green]HTML Text Extraction Method Comparison[/bold green]")
    console.print("Testing Trafilatura, Readability, and MainContentExtractor")
    console.print("=" * 80)

    # Check availability
    console.print(f"Trafilatura available: {'✅' if TRAFILATURA_AVAILABLE else '❌'}")
    console.print(f"Readability available: {'✅' if READABILITY_AVAILABLE else '❌'}")
    console.print(
        f"MainContentExtractor available: {'✅' if MAIN_CONTENT_EXTRACTOR_AVAILABLE else '❌'}"
    )

    if not any(
        [TRAFILATURA_AVAILABLE, READABILITY_AVAILABLE, MAIN_CONTENT_EXTRACTOR_AVAILABLE]
    ):
        console.print(
            "[red]No extraction methods available! Please install at least one.[/red]"
        )
        return

    # Connect to database
    try:
        con = duckdb.connect("migration/test_db/test_duckdb.db")
        console.print("✅ Connected to database")
    except Exception as e:
        console.print(f"❌ Failed to connect to database: {e}")
        return

    # Get articles with no errors, ordered by text content length
    query = """
    SELECT 
        id,
        title,
        url,
        url_domain,
        LENGTH(html_content) as html_length,
        LENGTH(text_content) as text_length,
        html_content,
        text_content
    FROM articles 
    WHERE ingestion_error_status IS NULL 
    AND LENGTH(html_content) > 10000
    ORDER BY LENGTH(text_content) ASC
    LIMIT 30
    """

    try:
        results = con.execute(query).fetchall()
        console.print(f"✅ Found {len(results)} articles to test")
    except Exception as e:
        console.print(f"❌ Failed to query articles: {e}")
        con.close()
        return

    if not results:
        console.print("❌ No suitable articles found")
        con.close()
        return

    # Convert to list of dictionaries
    articles = []
    for row in results:
        articles.append(
            {
                "id": row[0],
                "title": row[1],
                "url": row[2],
                "url_domain": row[3],
                "html_length": row[4],
                "text_length": row[5],
                "html_content": row[6],
                "text_content": row[7],
            }
        )

    # Test extraction methods
    tester = ExtractionTester()
    test_results = []

    console.print(f"\n[bold]Testing {len(articles)} articles...[/bold]")
    for article in articles:
        result = tester.test_article(article)
        test_results.append(result)

    # Display results
    tester.display_results(test_results)

    con.close()
    console.print("\n[bold green]Test completed![/bold green]")


if __name__ == "__main__":
    import re

    main()
