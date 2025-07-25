import argparse

from src.hex_machina.ingestion.ingestion_evaluation_report import (
    generate_html_ingestion_evaluation_report,
)
from src.hex_machina.storage.manager import StorageManager


def main():
    parser = argparse.ArgumentParser(
        description="Generate ingestion evaluation report over all operations and articles."
    )
    parser.add_argument("--db-path", required=True, help="Path to DuckDB file.")
    parser.add_argument(
        "--output-dir", default="reports", help="Directory to save the report."
    )
    args = parser.parse_args()

    # Load all operations and articles
    storage = StorageManager(args.db_path)
    operations = storage.get_all_ingestion_operations()
    articles = storage.get_all_articles()

    # Generate report (BaseReportGenerator will create the proper directory structure)
    report_path = generate_html_ingestion_evaluation_report(
        operations=operations,
        articles=articles,
        output_dir=args.output_dir,
    )
    print(f"Ingestion evaluation report saved to: {report_path}")


if __name__ == "__main__":
    main()
