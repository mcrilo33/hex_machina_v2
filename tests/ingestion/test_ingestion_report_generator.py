"""Tests for the ingestion report generator."""

import shutil
import tempfile
from datetime import datetime, timedelta
from pathlib import Path
from unittest.mock import patch

from src.hex_machina.ingestion.ingestion_report_generator import (
    IngestionReportGenerator,
)
from src.hex_machina.reporting.report_builder import ReportBuilder


class DummyIngestionOperation:
    """Dummy ingestion operation for testing."""

    def __init__(self):
        self.id = 42
        self.status = "success"
        self.start_time = datetime(2024, 7, 1, 12, 0, 0)
        self.end_time = self.start_time + timedelta(minutes=5, seconds=30)
        self.num_articles_processed = 10
        self.num_errors = 2
        self.parameters = '{"articles_limit": 10, "date_threshold": "2024-07-01"}'


class DummyArticle:
    """Dummy article for testing."""

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
        self.text_content = kwargs.get("text_content", None)
        self.author = kwargs.get("author", None)
        self.article_metadata = kwargs.get("article_metadata", {})
        self.ingestion_metadata = kwargs.get("ingestion_metadata", {})


class TestReportBuilder:
    """Test the report builder functions."""

    def test_section_operation_summary_markdown(self):
        """Test operation summary section generation."""
        op = DummyIngestionOperation()
        markdown = ReportBuilder.section_operation_summary(op, process_type="Ingestion")

        assert "## Ingestion Operation Summary" in markdown
        assert str(op.id) in markdown
        assert op.status in markdown
        assert str(op.num_articles_processed) in markdown
        assert str(op.num_errors) in markdown
        assert "Duration" in markdown
        assert "Success Rate" in markdown
        assert "Estimated Time per Item" in markdown

    def test_build_markdown_report(self):
        """Test full markdown report building."""
        op = DummyIngestionOperation()
        section = ReportBuilder.section_operation_summary(op, process_type="Ingestion")
        markdown = ReportBuilder.build_markdown_report([section], title="Test Report")

        assert "# Test Report" in markdown
        assert "## Ingestion Operation Summary" in markdown
        assert str(op.id) in markdown

    def test_build_markdown_report_empty_sections(self):
        """Test markdown report building with empty sections."""
        markdown = ReportBuilder.build_markdown_report([], title="Empty Report")
        assert "# Empty Report" in markdown
        assert "No data available" in markdown

    def test_section_domain_error_table(self):
        """Test domain error table section generation."""
        articles = [
            DummyArticle("example.com", False, datetime(2024, 7, 1)),
            DummyArticle("example.com", False, datetime(2024, 7, 1)),
            DummyArticle("example.com", True, datetime(2024, 7, 1)),
            DummyArticle("another.com", False, datetime(2024, 7, 2)),
            DummyArticle("another.com", True, datetime(2024, 7, 2)),
            DummyArticle("third.com", True, datetime(2024, 7, 3)),
        ]
        markdown = ReportBuilder.section_domain_error_table(articles)

        assert "## Domain Article/Error Distribution" in markdown
        assert "example.com" in markdown
        assert "another.com" in markdown
        assert "third.com" in markdown

    def test_section_domain_error_table_empty(self):
        """Test domain error table section with empty articles."""
        markdown = ReportBuilder.section_domain_error_table([])
        assert "No articles available for analysis" in markdown

    def test_section_success_articles_over_time(self):
        """Test success articles over time section generation."""
        articles = [
            DummyArticle("example.com", False, datetime(2024, 7, 1)),
            DummyArticle("example.com", False, datetime(2024, 7, 1)),
            DummyArticle("another.com", False, datetime(2024, 7, 2)),
            DummyArticle("third.com", False, datetime(2024, 7, 3)),
        ]

        with tempfile.TemporaryDirectory() as temp_dir:
            markdown = ReportBuilder.section_success_articles_over_time(
                articles, temp_dir
            )

            assert "## Successful Articles Over Time by Domain" in markdown
            assert "success_articles_over_time.png" in markdown

            # Check if PNG was created
            png_path = Path(temp_dir) / "success_articles_over_time.png"
            assert png_path.exists()

    def test_section_success_articles_over_time_no_success(self):
        """Test success articles over time section with no successful articles."""
        articles = [
            DummyArticle("example.com", True, datetime(2024, 7, 1)),
            DummyArticle("another.com", True, datetime(2024, 7, 2)),
        ]

        with tempfile.TemporaryDirectory() as temp_dir:
            markdown = ReportBuilder.section_success_articles_over_time(
                articles, temp_dir
            )
            assert "No data available to plot" in markdown

    def test_section_error_distribution_by_domain(self):
        """Test error distribution by domain section generation."""
        articles = [
            DummyArticle("example.com", False, datetime(2024, 7, 1)),
            DummyArticle("example.com", True, datetime(2024, 7, 1), "timeout"),
            DummyArticle("another.com", False, datetime(2024, 7, 2)),
            DummyArticle("another.com", True, datetime(2024, 7, 2), "parsing_error"),
            DummyArticle("third.com", True, datetime(2024, 7, 3), "network_error"),
        ]

        with tempfile.TemporaryDirectory() as temp_dir:
            markdown = ReportBuilder.section_error_distribution_by_domain(
                articles, temp_dir
            )

            assert "## Error Distribution by Domain and Status" in markdown
            assert "error_distribution_by_domain.png" in markdown

            # Check if PNG was created
            png_path = Path(temp_dir) / "error_distribution_by_domain.png"
            assert png_path.exists()

    def test_section_error_distribution_by_domain_empty(self):
        """Test error distribution by domain section with empty articles."""
        with tempfile.TemporaryDirectory() as temp_dir:
            markdown = ReportBuilder.section_error_distribution_by_domain([], temp_dir)
            assert "No data available to plot" in markdown

    def test_section_field_coverage_summary(self):
        """Test field coverage summary section generation."""
        articles = [
            DummyArticle(
                "example.com",
                False,
                datetime(2024, 7, 1),
                title="Test Article",
                html_content="<p>Content</p>",
                text_content="Content",
                author="Test Author",
                article_metadata={"tags": ["test"], "summary": "Test summary"},
            ),
            DummyArticle(
                "another.com",
                False,
                datetime(2024, 7, 2),
                title="Another Article",
                html_content="<p>More content</p>",
            ),
        ]

        markdown = ReportBuilder.section_field_coverage_summary(articles)

        assert "## Field Coverage Summary" in markdown
        assert "Total items: 2" in markdown
        assert "title" in markdown
        assert "html_content" in markdown
        assert "text_content" in markdown
        assert "author" in markdown

    def test_section_field_coverage_summary_empty(self):
        """Test field coverage summary section with empty articles."""
        markdown = ReportBuilder.section_field_coverage_summary([])
        assert "No data available for analysis" in markdown


class TestIngestionReportGenerator:
    """Test the IngestionReportGenerator class."""

    def setup_method(self):
        """Set up test fixtures."""
        self.temp_dir = tempfile.mkdtemp()
        self.generator = IngestionReportGenerator(self.temp_dir)

    def teardown_method(self):
        """Clean up test fixtures."""
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_init(self):
        """Test generator initialization."""
        assert self.generator.output_dir == Path(self.temp_dir)
        assert self.generator.logger is not None

    def test_create_report_directory(self):
        """Test report directory creation."""
        op = DummyIngestionOperation()
        report_dir = self.generator._create_report_directory(op)

        assert report_dir.exists()
        assert "ingestion_report_42_" in report_dir.name

    def test_generate_report_sections(self):
        """Test report sections generation."""
        op = DummyIngestionOperation()
        articles = [
            DummyArticle("example.com", False, datetime(2024, 7, 1)),
            DummyArticle("another.com", True, datetime(2024, 7, 2)),
        ]

        sections = self.generator._generate_report_sections(
            op, articles, Path(self.temp_dir)
        )

        assert len(sections) == 5
        assert any("Ingestion Operation Summary" in section for section in sections)
        assert any(
            "Domain Article/Error Distribution" in section for section in sections
        )

    def test_patch_image_paths(self):
        """Test image path patching."""
        markdown = "![Chart](path/to/chart.png)"
        patched = self.generator._patch_image_paths(markdown)
        assert patched == "![Chart](chart.png)"

    def test_get_html_template(self):
        """Test HTML template generation."""
        op = DummyIngestionOperation()
        html_content = "<h1>Test</h1>"
        template = self.generator._get_html_template(op, html_content)

        assert "<!DOCTYPE html>" in template
        assert "<h1>Test</h1>" in template
        assert "Ingestion_Report Report 42" in template

    @patch("src.hex_machina.reporting.base_report_generator.markdown2")
    def test_build_html_report(self, mock_markdown2):
        """Test HTML report building."""
        mock_markdown2.markdown.return_value = "<h1>Test</h1>"
        op = DummyIngestionOperation()
        sections = ["## Test Section"]
        report_dir = Path(self.temp_dir)

        html_path = self.generator._build_html_report(op, sections, report_dir)

        assert html_path.exists()
        assert html_path.name == "ingestion_report_42.html"
        mock_markdown2.markdown.assert_called_once()

    def test_generate_report_success(self):
        """Test successful report generation."""
        op = DummyIngestionOperation()
        articles = [
            DummyArticle("example.com", False, datetime(2024, 7, 1)),
            DummyArticle("another.com", True, datetime(2024, 7, 2)),
        ]

        with patch.object(self.generator, "_build_html_report") as mock_build:
            mock_build.return_value = Path(self.temp_dir) / "test.html"
            result = self.generator.generate_report(op, articles)

            assert result is not None
            assert "test.html" in result

    def test_generate_report_failure(self):
        """Test report generation failure."""
        op = DummyIngestionOperation()
        articles = []

        with patch.object(
            self.generator,
            "_generate_report_sections",
            side_effect=Exception("Test error"),
        ):
            result = self.generator.generate_report(op, articles)
            assert result is None


class TestGenerateHtmlIngestionReport:
    """Test the generate_html_ingestion_report function."""

    def setup_method(self):
        """Set up test fixtures."""
        self.temp_dir = tempfile.mkdtemp()

    def teardown_method(self):
        """Clean up test fixtures."""
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_generate_html_ingestion_report(self):
        """Test the main function."""
        from src.hex_machina.ingestion.ingestion_report_generator import (
            generate_html_ingestion_report,
        )

        op = DummyIngestionOperation()
        articles = [
            DummyArticle("example.com", False, datetime(2024, 7, 1)),
            DummyArticle("another.com", True, datetime(2024, 7, 2)),
        ]

        with patch(
            "src.hex_machina.ingestion.ingestion_report_generator.IngestionReportGenerator"
        ) as mock_generator_class:
            mock_generator = mock_generator_class.return_value
            mock_generator.generate_report.return_value = str(
                Path(self.temp_dir) / "test.html"
            )

            result = generate_html_ingestion_report(op, articles, self.temp_dir)

            assert result == str(Path(self.temp_dir) / "test.html")
            mock_generator.generate_report.assert_called_once_with(op, articles)
