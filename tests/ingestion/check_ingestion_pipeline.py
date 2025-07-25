import json
import os
from datetime import datetime

import duckdb
import pytest

DB_PATH = "tests/integration/data/hex_machina_test.db"  # or your test DB path


@pytest.mark.e2e
def test_ingestion_pipeline():
    print("[TEST] Connecting to DuckDB test database...")

    # Check if the database file exists
    if not os.path.exists(DB_PATH):
        pytest.skip(
            f"Database file not found: {DB_PATH}. Run the ingestion pipeline first."
        )

    con = duckdb.connect(DB_PATH)

    # Check articles
    articles = con.execute(
        "SELECT title, url_domain, ingestion_metadata FROM articles"
    ).fetchall()
    print(f"[TEST] Articles found: {articles}")
    assert (
        len(articles) == 6
    ), f"Expected 6 unique articles, got {len(articles)}: {articles}"

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
        scraper_counts[scraper_name] == 4
    ), f"Expected 4 articles for {scraper_name}, got {scraper_counts[scraper_name]}"
    print("[TEST] There was a duplicate article in the first feed")
    scraper_name = "stealth_playwright_rss_article_scraper"
    assert (
        scraper_counts[scraper_name] == 2
    ), f"Expected 2 articles for {scraper_name}, got {scraper_counts[scraper_name]}"
    print("[TEST] There was 3 duplicate articles in the second feed from the first")
    total_articles = sum(scraper_counts.values())
    assert total_articles == 6, f"Expected 6 articles in total, got {total_articles}"

    print(f"[TEST] Article distribution: {scraper_counts}")
    print(f"[TEST] Total articles: {total_articles}")

    # Verify that CAPTCHA article was properly filtered out
    captcha_articles = con.execute(
        "SELECT title, ingestion_error_status, ingestion_error_message FROM articles WHERE title LIKE '%CAPTCHA%'"
    ).fetchall()
    print(f"[TEST] CAPTCHA articles found: {captcha_articles}")

    # If CAPTCHA article exists, it should be marked as content_blocked
    if captcha_articles:
        for article in captcha_articles:
            assert (
                article[1] == "content_blocked"
            ), f"CAPTCHA article should be content_blocked, got {article[1]}"
            assert (
                "captcha" in article[2].lower() or "anti-bot" in article[2].lower()
            ), f"CAPTCHA article should have captcha/anti-bot in error message, got {article[2]}"
        print("[TEST] ✅ CAPTCHA detection working correctly")
    else:
        print("[TEST] ✅ CAPTCHA article properly filtered out")

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
    # Find specific articles for detailed testing
    article_3 = None
    for article in all_articles:
        if article[1] == "Test Article 3":
            article_3 = article
            break

    # Test Article 3 if it exists
    if article_3:
        print(f"[TEST] Testing Article 3: {article_3[1]}")
        # Basic validation of Article 3
        assert (
            article_3[1] == "Test Article 3"
        ), f"Article 3 title mismatch: {article_3[1]}"
        assert (
            article_3[2] == "http://localhost:8000/article3.html"
        ), f"Article 3 URL mismatch: {article_3[2]}"
        assert (
            article_3[4] == "localhost:8000"
        ), f"Article 3 domain mismatch: {article_3[4]}"
        assert (
            article_3[8] == "Author One"
        ), f"Article 3 author mismatch: {article_3[8]}"
        assert (
            article_3[13] is None
        ), f"Article 3 should have no error status: {article_3[13]}"
        print("[TEST] ✅ Article 3 validation passed")
    else:
        print("[TEST] ⚠️ Article 3 not found in database")

    # Test CAPTCHA detection - the article should have the correct ingestion_error_status
    captcha_article = None
    for article in all_articles:
        if article[1] == "Test Article with CAPTCHA":
            captcha_article = article
            break

    # The CAPTCHA article should be in the database with the correct error status
    assert (
        captcha_article is not None
    ), "CAPTCHA test article should be present in the database"
    assert (
        captcha_article[13] == "content_blocked"
    ), f"CAPTCHA test article should have ingestion_error_status 'content_blocked', got {captcha_article[13]}"
    print(
        "[TEST] ✅ CAPTCHA article present with correct ingestion_error_status 'content_blocked'"
    )

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
    # The expected values reflect that CAPTCHA article is filtered out
    expected_ingestion_op = (
        1,
        datetime(
            2025, 7, 21, 15, 51, 7, 390756
        ),  # start_time - will be checked as datetime
        datetime(
            2025, 7, 21, 15, 51, 19, 224968
        ),  # end_time - will be checked as datetime
        6,  # num_articles_processed - CAPTCHA article is filtered out
        3,  # num_errors - CAPTCHA article is filtered out, not stored as error
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
