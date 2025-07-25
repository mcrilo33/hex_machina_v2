import argparse
from pathlib import Path
from datetime import datetime

from src.hex_machina.ingestion.ingestion_domain_evaluation_report import (
    generate_html_ingestion_domain_evaluation_report,
)
from src.hex_machina.storage.manager import StorageManager


def main():
    parser = argparse.ArgumentParser(
        description="Generate ingestion domain evaluation reports for all domains."
    )
    parser.add_argument("--db-path", required=True, help="Path to DuckDB file.")
    parser.add_argument(
        "--output-dir", default="reports", help="Directory to save the reports."
    )
    args = parser.parse_args()

    # Load all articles
    storage = StorageManager(args.db_path)
    articles = storage.get_all_articles()
    date_str = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    output_dir = (
        Path(args.output_dir) / f"{date_str}_ingestion_domain_evaluation_report"
    )

    # Find all unique domains
    domains = sorted(
        set(
            getattr(a, "url_domain", None)
            for a in articles
            if getattr(a, "url_domain", None)
        )
    )

    for domain in domains:
        domain_articles = [
            a for a in articles if getattr(a, "url_domain", None) == domain
        ]
        report_path = generate_html_ingestion_domain_evaluation_report(
            domain=domain,
            articles=domain_articles,
            output_dir=output_dir,
        )
        print(f"Domain evaluation report for {domain} saved to: {report_path}")


if __name__ == "__main__":
    main()
