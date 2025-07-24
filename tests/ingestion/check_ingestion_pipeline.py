import json
import os
from datetime import datetime

import duckdb
import pytest

DB_PATH = "tests/integration/data/hex_machina_test.db"  # or your test DB path


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
        len(articles) == 5
    ), f"Expected 5 unique articles, got {len(articles)}: {articles}"

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
        scraper_counts[scraper_name] == 2
    ), f"Expected 1 articles for {scraper_name}, got {scraper_counts[scraper_name]}"
    print("[TEST] There was 3 duplicate articles in the second feed from the first")
    total_articles = sum(scraper_counts.values())
    assert total_articles == 5, f"Expected 5 articles in total, got {total_articles}"

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

    for article in all_articles:
        if article[1] == "Test Article 3":
            article_3 = article
        if article[1] == "Test Article 4":
            article_4 = article

    expected_article_3 = (
        1,
        "Test Article 3",
        "http://localhost:8000/article3.html",
        "file:///Users/mathieucrilout/Repos/hex_machina_v2/tests/integration/data/test_feed_2.xml",
        "localhost:8000",
        datetime(2024, 7, 1, 12, 0),
        '<!DOCTYPE html><html lang="en"><head>\n    <meta charset="UTF-8">\n    <title>Test Article 3</title>\n</head>\n<body>\n    <h1>Test Article 3</h1>\n    <p>This is the content of test article 3.</p>\n\n </body></html>',
        "Test Article 3 This is the content of test article 3.",
        "Author One",
        '{"summary": "Summary of article 3", "tags": []}',
        '{"scraper_name": "stealth_playwright_rss_article_scraper", "captcha_found": false}',
        1,
        datetime(2025, 7, 24, 0, 26, 19, 419542),
        None,
        None,
    )
    expected_article_4 = (
        2,
        "Test Article 4",
        "http://localhost:8000/article4.html",
        "file:///Users/mathieucrilout/Repos/hex_machina_v2/tests/integration/data/test_feed_1.xml",
        "localhost:8000",
        datetime(2024, 7, 1, 13, 0),
        "",
        "",
        "Author Four",
        '{"summary": "Summary of article 4", "tags": []}',
        '{"scraper_name": "playwright_rss_article_scraper"}',
        1,
        datetime(2025, 7, 24, 0, 26, 6, 392950),
        "404",
        "",
    )
    for i, field in enumerate(fields):
        if field == "id":
            continue
        if field == "ingested_at":
            assert isinstance(
                article_3[i], datetime
            ), f"Article 3 {field} is not a datetime: {article_3[i]}"
            assert isinstance(
                article_4[i], datetime
            ), f"Article 4 {field} is not a datetime: {article_4[i]}"
        else:
            assert (
                article_3[i] == expected_article_3[i]
            ), f"Article 3 {field} mismatch: {article_3[i]}"
            assert (
                article_4[i] == expected_article_4[i]
            ), f"Article 4 {field} mismatch: {article_4[i]}"
        print(f"[TEST] Article 3,4 {field}(s) match {article_3[i]},{article_4[i]}")

    assert article_4[13] == "404"
    print(f"[TEST] Article 4 ingestion_error_status: {article_4[13]}")
    assert article_4[14] == ""
    print(f"[TEST] Article 4 ingestion_error_message: {article_4[14]}")

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
        5,
        2,
        "completed",
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
                    "db_path",
                    "articles_limit",
                    "date_threshold",
                    "log_level",
                    "scrapy",
                    "scrapers",
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
