import json
import os
from datetime import datetime

import duckdb
import pytest

DB_PATH = "data/hex_machina_test.db"


@pytest.mark.e2e
def test_ingestion_pipeline():
    print("[TEST] Connecting to DuckDB test database...")
    con = duckdb.connect(DB_PATH)

    # Check articles
    articles = con.execute(
        "SELECT title, url_domain, ingestion_metadata FROM articles"
    ).fetchall()
    print(f"[TEST] Articles found: {articles}")
    assert (
        len(articles) == 4
    ), f"Expected 4 unique articles, got {len(articles)}: {articles}"

    # Count articles per scraper_name
    scraper_counts = {}
    for row in articles:
        ingestion_metadata = row[2]
        meta = json.loads(ingestion_metadata) if ingestion_metadata else {}
        scraper_name = meta.get("scraper_name")
        print(f"[TEST] Article ingestion_metadata: {meta}")
        assert scraper_name is not None, "scraper_name missing in ingestion_metadata"
        scraper_counts[scraper_name] = scraper_counts.get(scraper_name, 0) + 1
    print(f"[TEST] Article count per scraper_name: {scraper_counts}")
    scraper_name = "playwright_rss_article_scraper"
    assert (
        scraper_counts[scraper_name] == 3
    ), f"Expected 3 articles for {scraper_name}, got {scraper_counts[scraper_name]}"
    print("[TEST] There was a duplicate article in the first feed")
    scraper_name = "stealth_playwright_rss_article_scraper"
    assert (
        scraper_counts[scraper_name] == 1
    ), f"Expected 1 articles for {scraper_name}, got {scraper_counts[scraper_name]}"
    print("[TEST] There was 3 duplicate articles in the second feed from the first")
    total_articles = sum(scraper_counts.values())
    assert total_articles == 4, f"Expected 4 articles in total, got {total_articles}"

    # Check expected fields in articles
    columns = [
        desc[1] for desc in con.execute("PRAGMA table_info('articles')").fetchall()
    ]
    print(f"[TEST] Article table columns: {columns}")
    fields = [
        "id",
        "title",
        "url",
        "source_url",
        "url_domain",
        "published_date",
        "html_content",
        "text_content",
        "author",
        "article_metadata",
        "ingestion_metadata",
        "ingestion_run_id",
        "ingested_at",
        "ingestion_error_status",
        "ingestion_error_message",
    ]
    for field in fields[1:]:
        assert field in columns, f"Missing field {field} in articles table"

    # Fetch all articles with all fields from the articles table
    all_articles = con.execute("SELECT * FROM articles").fetchall()
    print("[TEST] All articles (full rows):")
    for article in all_articles:
        print(article)

    article_0 = all_articles[0]
    article_1 = all_articles[1]
    expected_article_0 = (
        1,
        "Test Article 1",
        "http://localhost:8000/article1.html",
        "file:///Users/mathieucrilout/Repos/hex_machina_v2/tests/ingestion/data/test_feed_1.xml",
        "localhost:8000",
        datetime(2024, 7, 1, 12, 0),
        '<!DOCTYPE html><html lang="en"><head>\n    <meta charset="UTF-8">\n    <title>Test Article 1</title>\n</head>\n<body>\n    <h1>Test Article 1</h1>\n    <p>This is the content of test article 1.</p>\n\n </body></html>',
        "Test Article 1 This is the content of test article 1.",
        "Author One",
        '{"summary": "Summary of article 1", "tags": ["CISA", "cyberattack", "cybersecurity", "Microsoft", "sharepoint", "us government"]}',
        '{"scraper_name": "playwright_rss_article_scraper"}',
        1,
        datetime(2025, 7, 21, 14, 44, 13, 353976),
        None,
        None,
    )
    expected_article_1 = (
        2,
        "Test Article 2",
        "http://localhost:8000/article2.html",
        "file:///Users/mathieucrilout/Repos/hex_machina_v2/tests/ingestion/data/test_feed_1.xml",
        "localhost:8000",
        datetime(2024, 7, 1, 13, 0),
        '<!DOCTYPE html><html lang="en"><head>\n    <meta charset="UTF-8">\n    <title>Test Article 2</title>\n</head>\n<body>\n    <h1>Test Article 2</h1>\n    <p>This is the content of test article 2.</p>\n\n </body></html>',
        "Test Article 2 This is the content of test article 2.",
        "Author Two",
        '{"summary": "Summary of article 2", "tags": []}',
        '{"scraper_name": "playwright_rss_article_scraper"}',
        1,
        datetime(2025, 7, 21, 15, 12, 58, 39066),
        None,
        None,
    )
    for i, field in enumerate(fields):
        if field == "ingested_at":
            assert isinstance(
                article_0[i], datetime
            ), f"Article 0 {field} is not a datetime: {article_0[i]}"
            assert isinstance(
                article_1[i], datetime
            ), f"Article 1 {field} is not a datetime: {article_1[i]}"
        else:
            assert (
                article_0[i] == expected_article_0[i]
            ), f"Article 0 {field} mismatch: {article_0[i]}"
            assert (
                article_1[i] == expected_article_1[i]
            ), f"Article 1 {field} mismatch: {article_1[i]}"
        print(f"[TEST] Article 0,1 {field}(s) match {article_0[i]},{article_1[i]}")

    article_2 = all_articles[2]
    assert article_2[13] == "http_status_404"
    print(f"[TEST] Article 2 ingestion_error_status: {article_2[13]}")
    assert article_2[14] == "HTTP status 404 for http://localhost:8000/fake.html"
    print(f"[TEST] Article 2 ingestion_error_message: {article_2[14]}")

    # Test the IngestionOperation record created by ingestion_script.py
    ingestion_ops = con.execute("SELECT * FROM ingestion_operations").fetchall()
    assert (
        len(ingestion_ops) == 1
    ), f"Expected 1 ingestion operation, got {len(ingestion_ops)}"

    # Check expected fields in articles
    columns = [
        desc[1]
        for desc in con.execute("PRAGMA table_info('ingestion_operations')").fetchall()
    ]
    print(f"[TEST] IngestionOperation table columns: {columns}")
    fields = [
        "id",
        "start_time",
        "end_time",
        "num_articles_processed",
        "num_errors",
        "status",
        "parameters",
    ]
    for field in fields[1:]:
        assert field in columns, f"Missing field {field} in articles table"
    ingestion_op = ingestion_ops[0]
    expected_ingestion_op = (
        1,
        datetime(2025, 7, 21, 15, 51, 7, 390756),
        datetime(2025, 7, 21, 15, 51, 19, 224968),
        4,
        1,
        "partial",
        '{"articles_limit": 5, "date_threshold": "2024-01-01", "config_path": "tests/ingestion/testing_scraping_config.yaml", "db_path": "data/hex_machina_test.db", "git": {"git_commit": "fc7502372ca688761071c4f4b382faee7b746ef2", "git_branch": "main", "git_repo": "git@github.com:mcrilo33/hex_machina_v2.git"}}',
    )
    for i, field in enumerate(fields):
        if field == "start_time" or field == "end_time":
            assert isinstance(
                ingestion_op[i], datetime
            ), f"IngestionOperation {field} is not a datetime: {ingestion_op[i]}"
        elif field == "parameters":
            parameters = json.loads(ingestion_op[i])
            for key, value in parameters.items():
                assert key in [
                    "articles_limit",
                    "date_threshold",
                    "config_path",
                    "db_path",
                    "git",
                ], f"Unexpected parameter: {key}"
        else:
            assert (
                ingestion_op[i] == expected_ingestion_op[i]
            ), f"IngestionOperation {field} mismatch: {ingestion_op[i]}"
            print(
                f"[TEST] IngestionOperation {field} matches expected: {ingestion_op[i]}"
            )
    con.close()
    # Clean up: delete the test DB
    os.remove(DB_PATH)
    print("[TEST] Test DB deleted.")
