import shutil
import tempfile
from datetime import datetime, timedelta

from hex_machina.reporting.report_builder import (
    build_markdown_report,
    section_domain_error_table,
    section_error_distribution_by_domain,
    section_field_coverage_summary,
    section_operation_summary,
    section_success_articles_over_time,
)


class DummyIngestionOperation:
    def __init__(self):
        self.id = 42
        self.status = "success"
        self.start_time = datetime(2024, 7, 1, 12, 0, 0)
        self.end_time = self.start_time + timedelta(minutes=5, seconds=30)
        self.num_articles_processed = 10
        self.num_errors = 2
        self.parameters = '{"articles_limit": 10, "date_threshold": "2024-07-01"}'


class DummyArticle:
    def __init__(
        self, url_domain, has_error, published_date, error_status=None, **kwargs
    ):
        self.url_domain = url_domain
        self.ingestion_error_status = (
            error_status if error_status is not None else ("err" if has_error else None)
        )
        self.published_date = published_date
        self.title = kwargs.get("title", None)
        self.html_content = kwargs.get("html_content", None)
        self.author = kwargs.get("author", None)
        self.article_metadata = kwargs.get("article_metadata", {})


def test_section_operation_summary_markdown():
    op = DummyIngestionOperation()
    markdown = section_operation_summary(op, process_type="Ingestion")
    print("\n--- Section Markdown ---\n", markdown)
    assert "## Ingestion Operation Summary" in markdown
    assert str(op.id) in markdown
    assert op.status in markdown
    assert str(op.num_articles_processed) in markdown
    assert str(op.num_errors) in markdown
    assert "Duration" in markdown
    assert "Estimated Time per Article" in markdown


def test_build_markdown_report():
    op = DummyIngestionOperation()
    section = section_operation_summary(op, process_type="Ingestion")
    markdown = build_markdown_report([section], title="Test Report")
    print("\n--- Full Markdown Report ---\n", markdown)
    assert "# Test Report" in markdown
    assert "## Ingestion Operation Summary" in markdown
    assert str(op.id) in markdown


def test_section_domain_error_table():
    articles = [
        DummyArticle("example.com", False, datetime(2024, 7, 1)),
        DummyArticle("example.com", False, datetime(2024, 7, 1)),
        DummyArticle("example.com", True, datetime(2024, 7, 1)),
        DummyArticle("another.com", False, datetime(2024, 7, 2)),
        DummyArticle("another.com", True, datetime(2024, 7, 2)),
        DummyArticle("third.com", True, datetime(2024, 7, 3)),
    ]
    markdown = section_domain_error_table(articles)
    print("\n--- Domain Error Table Markdown ---\n", markdown)
    assert "## Domain Article/Error Distribution" in markdown
    assert "example.com" in markdown
    assert "another.com" in markdown
    assert "third.com" in markdown
    assert "| 3 |" in markdown  # example.com article count
    assert "| 2 |" in markdown  # another.com article count
    assert "| 1 |" in markdown  # third.com article count
    assert "| 1 |" in markdown  # error count for example.com


def test_section_success_articles_over_time():
    # Create dummy articles with published_date, url_domain, and error status
    base_date = datetime(2024, 7, 1)
    articles = []
    for i in range(5):
        articles.append(
            DummyArticle("example.com", False, base_date + timedelta(days=i))
        )
    for i in range(3):
        articles.append(
            DummyArticle("another.com", False, base_date + timedelta(days=i))
        )
    for i in range(2):
        articles.append(DummyArticle("third.com", True, base_date + timedelta(days=i)))
    # Use a temp directory for output
    temp_dir = tempfile.mkdtemp()
    try:
        markdown = section_success_articles_over_time(articles, temp_dir)
        print("\n--- Success Articles Over Time Markdown ---\n", markdown)
        assert "## Successful Articles Over Time by Domain" in markdown
        assert (
            "![Success Articles Over Time](success_articles_over_time.png)" in markdown
        )
        # Check that the image file was created
        import os

        img_path = os.path.join(temp_dir, "success_articles_over_time.png")
        assert os.path.exists(img_path)
    finally:
        shutil.rmtree(temp_dir)


def test_section_error_distribution_by_domain():
    base_date = datetime(2024, 7, 1)
    articles = []
    # Add articles with various error statuses and domains
    for i in range(5):
        articles.append(
            DummyArticle("example.com", False, base_date, error_status=None)
        )
    for i in range(2):
        articles.append(
            DummyArticle("example.com", True, base_date, error_status="timeout")
        )
    for i in range(3):
        articles.append(
            DummyArticle("another.com", False, base_date, error_status=None)
        )
    for i in range(2):
        articles.append(
            DummyArticle("another.com", True, base_date, error_status="parse_error")
        )
    for i in range(1):
        articles.append(
            DummyArticle("third.com", True, base_date, error_status="timeout")
        )
    temp_dir = tempfile.mkdtemp()
    try:
        markdown = section_error_distribution_by_domain(articles, temp_dir)
        print("\n--- Error Distribution by Domain Markdown ---\n", markdown)
        assert "## Error Distribution by Domain and Status" in markdown
        assert "![Error Distribution](error_distribution_by_domain.png)" in markdown
        import os

        img_path = os.path.join(temp_dir, "error_distribution_by_domain.png")
        assert os.path.exists(img_path)
    finally:
        shutil.rmtree(temp_dir)


def test_section_field_coverage_summary():
    # Create dummy articles with no errors and various field coverage
    base_date = datetime(2024, 7, 1)
    articles = [
        DummyArticle(
            "example.com",
            False,
            base_date,
            title="Title 1",
            html_content="<html>...</html>",
            author="Author 1",
            article_metadata={"summary": "Summary 1", "tags": ["tag1", "tag2"]},
        ),
        DummyArticle(
            "example.com",
            False,
            base_date,
            title="Title 2",
            html_content=None,
            author=None,
            article_metadata={"summary": None, "tags": []},
        ),
        DummyArticle(
            "another.com",
            False,
            base_date,
            title=None,
            html_content="<html>...</html>",
            author="Author 2",
            article_metadata={"summary": "Summary 2", "tags": ["tag3"]},
        ),
    ]
    markdown = section_field_coverage_summary(articles)
    print("\n--- Field Coverage Summary Markdown ---\n", markdown)
    assert "## Field Coverage Summary" in markdown
    assert "title" in markdown
    assert "published_date" in markdown
    assert "url_domain" in markdown
    assert "html_content" in markdown
    assert "summary" in markdown
    assert "author" in markdown
    assert "tags" in markdown
    assert "COVERAGE" in markdown
    assert "COUNT" in markdown
